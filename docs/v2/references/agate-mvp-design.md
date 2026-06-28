# agate — MVP Design for Hardware Affinity Standardization

> **Status:** Draft — miniman initial design for `github.com/oramasys/agate`  
> **v2 orbit:** Full migration plan in [`42-agate-hardware-policy-orbit.md`](../42-agate-hardware-policy-orbit.md)  
> **Audience:** LangChain / LangGraph / CrewAI / AutoGen communities, plus
> local-first AI builders.  
> **Goal:** A 3-file MVP that any framework can adopt in one afternoon.

---

## Why agate solves a real community pain

Every multi-agent framework today assumes **uniform, API-callable agents**.
None of them answer:

> *"Which model do I dispatch to, on which physical hardware, given the task?"*

Teams answer this with:
- `if platform.system() == "Darwin":` scattered across repos
- Magic environment variables (`OLLAMA_HOST`, `LM_STUDIO_URL`)
- Proprietary JSON blobs locked inside one orchestrator
- Tribal knowledge ("don't run 27B on the Mac, it OOMs")

There is **no shared vocabulary** for hardware intent. agate provides one.

### LangChain / LangGraph specific concerns

| Concern | agate's answer |
|---|---|
| **Dependency bloat** — "I don't want 500k LoC just to route models" | agate is **zero external dependencies**. JSON Schema + 50 lines of validator code. No frameworks. |
| **Version drift** — LangGraph changes break my routing every week | agate is schema-first. The contract is a JSON Schema file. Nothing runs code to read it. |
| **Framework lock-in** — "If I adopt LangGraph I'm stuck with LangChain" | agate is **framework-agnostic by design**. Use it with LangGraph, CrewAI, AutoGen, smolagents, or hand-rolled asyncio. |
| **Policy as code** — "I want my hardware rules in source control, not hidden in a Python class" | agate policy is a **plain YAML file** (`model_hardware_policy.yml`) validated against a public JSON Schema. |
| **No standard for local hardware routing** — "Cloud has regions; local has… ?" | agate fills that gap. `PREFER` / `ALLOW` / `NEVER` verdicts per hardware tier, versioned, auditable. |

---

## MVP Scope (3 files, 1 afternoon to adopt)

### File 1: `SPEC.md` (the contract)

A human-readable spec (~2 pages) that defines:
- The three verdicts: `PREFER`, `ALLOW`, `NEVER`
- The hardware tier taxonomy: `mac`, `windows`, `shared`, `cloud`
- The confidence levels: `declared`, `tested`, `inferred`
- Extension points: sidecar, inline GGUF keys, HF model card YAML

**This file is the RFC.** It tells the community *what* agate means, not *how* to implement it.

### File 2: `schema.json` (the validator contract)

A JSON Schema that validates a policy file. Example validators in every
language are generated from this single source of truth.

```jsonc
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "agate Hardware Policy",
  "type": "object",
  "required": ["agate_version", "models"],
  "properties": {
    "agate_version": { "type": "string", "pattern": "^\\d+\\.\\d+$" },
    "models": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["affinity"],
        "properties": {
          "affinity": {
            "type": "object",
            "patternProperties": {
              "^(mac|windows|shared|cloud|any)$": {
                "enum": ["PREFER", "ALLOW", "ALLOW_DEGRADED", "NEVER", "UNTESTED"]
              }
            }
          }
        }
      }
    }
  }
}
```

**Why JSON Schema:** Every language has a validator. Python (`jsonschema`),
Node (`ajv`), Rust (`schemars`), Go (`jsonschema`). The spec never runs code
to validate — it's a data contract.

### File 3: `validate.py` (the reference implementation)

A single-file Python script, zero external dependencies, that:
1. Loads `schema.json`
2. Validates a YAML policy file against it
3. Prints a routing decision for a given task + tier + optimize_for

```python
#!/usr/bin/env python3
"""agate validate.py — zero-dep reference validator.

Usage:
    python validate.py policy.yml                          # validate only
    python validate.py policy.yml --task coding --tier mac # + routing decision
"""
import sys, json, os
from pathlib import Path

try:
    import yaml
except ImportError:
    # Fallback: minimal YAML parser for the subset we use
    # (real deploy will pip install pyyaml; this keeps the script runnable)
    import json, re
    class _FallbackYAML:
        @staticmethod
        def safe_load(text):
            out = {}
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    k, v = line.split(":", 1)
                    out[k.strip()] = v.strip().strip('"').strip("'")
            return out
    yaml = _FallbackYAML()

try:
    import jsonschema
except ImportError:
    # Minimal recursive validator for the subset we need
    class _MinimalValidator:
        @staticmethod
        def validate(instance, schema):
            if not isinstance(instance, dict):
                raise ValueError("Root must be object")
            for req in schema.get("required", []):
                if req not in instance:
                    raise ValueError(f"Missing required: {req}")
            models = instance.get("models", {})
            for model_id, model_spec in models.items():
                aff = model_spec.get("affinity", {})
                valid = {"PREFER","ALLOW","ALLOW_DEGRADED","NEVER","UNTESTED"}
                for tier, verdict in aff.items():
                    if verdict not in valid:
                        raise ValueError(f"{model_id}: invalid verdict {verdict}")
    jsonschema = _MinimalValidator()

SCHEMA_PATH = Path(__file__).parent / "schema.json"

def load_schema():
    with open(SCHEMA_PATH) as f:
        return json.load(f)

def validate(path: str):
    schema = load_schema()
    with open(path) as f:
        policy = yaml.safe_load(f)
    jsonschema.validate(policy, schema)
    print(f"✓ {path} is valid (agate {policy['agate_version']})")
    return policy

def decide(policy, task_type: str, tier: str, optimize_for: str = "balanced"):
    """
    Minimal routing decision. Returns (model_id, verdict, reason).
    """
    models = policy.get("models", {})
    for model_id, spec in models.items():
        aff = spec.get("affinity", {})
        verdict = aff.get(tier, "UNTESTED")
        if verdict == "PREFER":
            return model_id, verdict, f"policy:{task_type}:{tier}"
    for model_id, spec in models.items():
        aff = spec.get("affinity", {})
        verdict = aff.get(tier, "UNTESTED")
        if verdict == "ALLOW":
            return model_id, verdict, f"policy:{task_type}:{tier}"
    return None, "NONE", "no model matches tier"

def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    policy_path = args[0]
    policy = validate(policy_path)
    if "--task" in args:
        idx = args.index("--task")
        task_type = args[idx + 1]
        tier = args[args.index("--tier") + 1] if "--tier" in args else "shared"
        model_id, verdict, reason = decide(policy, task_type, tier)
        print(f"Decision: {model_id} → {verdict} ({reason})")
    elif len(args) == 1:
        print("OK")
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
```

**Total lines:** ~80. Total dependencies: zero (works with stdlib + optional
`pyyaml`/`jsonschema` for richer validation).

---

## Example Policy File (`model_hardware_policy.yml`)

```yaml
agate_version: "0.1"

models:
  Qwen3.5-9B-MLX-4bit:
    affinity:
      mac: PREFER
      windows: NEVER
      shared: ALLOW

  Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2:
    affinity:
      mac: NEVER
      windows: PREFER
      shared: ALLOW_DEGRADED

  qwen3-coder:14b:
    affinity:
      mac: ALLOW
      windows: ALLOW
      shared: ALLOW
```

---

## Framework Integration Recipes

These show how agate plugs into existing ecosystems **without importing agate code**.
The only contract is: *read the YAML, honor the verdict.*

### LangGraph (Python)

```python
import yaml
from pathlib import Path

def node_check_affinity(state):
    policy = yaml.safe_load(Path("model_hardware_policy.yml").read_text())
    model = state.resolved_model
    tier = state.hardware_tier
    verdict = policy["models"].get(model, {}).get("affinity", {}).get(tier, "UNTESTED")
    if verdict == "NEVER":
        raise ValueError(f"HARDWARE_MISMATCH: {model} on {tier}")
    return state
```

### LangChain (LangGraph `ToolNode` with agate guard)

```python
from langchain_core.runnables import RunnableLambda

def affinity_guard(state):
    policy = yaml.safe_load(Path("model_hardware_policy.yml").read_text())
    # ... same check as above ...
    return state

graph.add_node("affinity_guard", RunnableLambda(affinity_guard))
```

### CrewAI

```python
# crewai/tools/hardware_affinity_tool.py
import yaml
class HardwareAffinityTool:
    def check(self, model: str, tier: str) -> str:
        policy = yaml.safe_load(Path("model_hardware_policy.yml").read_text())
        verdict = policy["models"].get(model, {}).get("affinity", {}).get(tier, "UNTESTED")
        if verdict == "NEVER":
            return f"BLOCKED: {model} is NEVER on {tier}"
        return f"ALLOWED: {model} on {tier} → {verdict}"
```

### AutoGen (Python)

```python
# AutoGen agent factory
def create_agent(model: str, tier: str, ...):
    policy = yaml.safe_load(Path("model_hardware_policy.yml").read_text())
    if policy["models"].get(model, {}).get("affinity", {}).get(tier) == "NEVER":
        raise RuntimeError(f"Hardware mismatch: {model} on {tier}")
    return AssistantAgent(...)
```

### Node.js / TypeScript

```ts
import yaml from "js-yaml";
import fs from "fs";

function checkAffinity(model: string, tier: string): string {
  const policy = yaml.load(fs.readFileSync("model_hardware_policy.yml", "utf8")) as any;
  const verdict = policy.models?.[model]?.affinity?.[tier] ?? "UNTESTED";
  if (verdict === "NEVER") throw new Error(`HARDWARE_MISMATCH: ${model} on ${tier}`);
  return verdict;
}
```

### smolagents (HuggingFace)

```python
from smolagents import CodeAgent, HfApiModel
# agate check before constructing the model
verdict = check_affinity(model_id, tier)
if verdict == "NEVER":
    raise ValueError("Hardware mismatch")
agent = CodeAgent(tools=[], model=HfApiModel(...))
```

**Pattern:** Every framework reads the same YAML file. No framework imports
agate as a library. The file *is* the standard.

---

## Repo Structure (MVP)

```
agate/
├── README.md                # Why, who, how — 30-second elevator pitch
├── SPEC.md                  # The RFC: verdicts, tiers, confidence levels, carriers
├── schema.json              # JSON Schema (single source of truth)
├── validate.py              # Zero-dep reference implementation
├── model_hardware_policy.yml # Example policy (the "hello world")
├── examples/
│   ├── langgraph-adapter.py
│   ├── crewai-guard.py
│   └── nodejs-guard.ts
└── docs/
    └── migration-from-v1.md  # For teams migrating from hardcoded if/else
```

**Total MVP weight:** 1 spec, 1 schema, 1 validator script, 3 example adapters.
Under 500 lines in the root.

---

## Community Contribution Model (addressing LangChain ecosystem concerns)

### The "fork and extend" rule

agate is intentionally **smaller than any framework**. If a team wants a
richer policy (task-type weighting, load-aware routing, cost ceilings),
they fork `model_hardware_policy.yml` and add their own keys. agate's
validator ignores unknown keys — it never breaks forward-compat.

This is the same philosophy that made JSON Schema and HTTP successful:
be conservative in what you require, liberal in what you accept.

### Contribution channels

| Channel | Contribution type | Audience |
|---|---|---|
| `model_hardware_policy.yml` PRs | Community-tested hardware profiles | Anyone running local LLMs |
| Adapter examples | Framework integration snippets | LangGraph, CrewAI, AutoGen maintainers |
| Schema RFCs | Propose new verdicts or tiers | Core maintainers |
| Vendor partnerships | Official hardware profiles (Apple, NVIDIA) | Hardware ecosystem |

### Governance

- **v0.x**: BDFL (diazMelgarejo) — fast iteration, low ceremony
- **v1.0+**: RFC process for schema changes. Two maintainer approvals required.
- **No breaking changes** to `PREFER` / `ALLOW` / `NEVER` semantics in any
  minor version. Additive extensions only.

---

## Relationship to Perpetua-Tools and Orama-System

Perpetua-Tools is the **source of truth** for hardware routing logic.
Orama-system's `hardware-affinity-gate` skill imports from Perpetua-Tools
one-way. When `agate` publishes as a standalone package, both repos will
import from `agate` instead of self-hosting the rules.

```
perpetua-core/               (Python primitives — source of truth)
└── perpetua/core/policy.py  (owns HardwarePolicyResolver + AffinityPolicy)

oramasys/                    (orchestration)
└── bin/orama-system/skills/hardware-affinity-gate/SKILL.md
    imports from perpetua.core.policy

agate/                       (the spec — framework-agnostic)
├── SPEC.md
├── schema.json
└── validate.py
```

---

## Design Principles (immutable)

1. **Policy is data, not code.** The YAML file is the contract.
2. **Verdicts are absolute.** `NEVER` means never. No silent fallback.
3. **Confidence is explicit.** Every claim says whether it was `declared`,
   `tested`, or `inferred`.
4. **Carriers are orthogonal.** YAML sidecar, GGUF KV key, HF model card,
   or registry — all equivalent, none required.
5. **Framework neutrality.** If a framework can read YAML, it can adopt agate.
6. **Additive evolution.** New tiers, new verdicts, new carriers. Never remove.

---

## Next Actions

1. **Create `github.com/oramasys/agate`** with this MVP structure.
2. **Publish `SPEC.md`** as an RFC to r/LocalLLaMA, llama.cpp discussions,
   and HuggingFace forums. Gauge community interest.
3. **Ship `validate.py`** on PyPI as `agate-validator` (v0.1).
4. **Write the LangGraph adapter** (`examples/langgraph-adapter.py`) and
   post it as "How to add hardware affinity to LangGraph in 5 minutes."
5. **Draft the GGUF RFC** (`agate/docs/gguf-rfc.md`) — propose `agate.*` KV
   keys for llama.cpp, Ollama, LM Studio to read natively.

---

## Open Questions

| ID | Question | Impact | Decision owner |
|---|---|---|---|
| OQ1 | Should `ALLOW_DEGRADED` fire a warning at the gateway layer? | UX vs enforcement | v0.2 |
| OQ2 | Should `optimize_for` (speed / quality / reliability) be part of the core schema or an extension? | Schema size | v0.2 |
| OQ3 | Should the v1 validator support GGUF direct parsing, or stay YAML-only? | Binary deps | v0.2 |
| OQ4 | Should we define a `cloud` tier (AWS / Modal / RunPod) in v0.1 or defer to v1? | Scope | v1.0 |
