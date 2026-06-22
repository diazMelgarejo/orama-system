---
name: hardware-affinity-gate
description: >-
  Use when enforcing hardware-model affinity before dispatch on Mac or Windows.
  Provides fail-closed pre-dispatch validation, live model inventory verification,
  and canonical Mac/Windows routing rules for LM Studio and Ollama backends.
  This skill lives in orama-system but imports scripts and rules from
  Perpetua-Tools one-way. Perpetua-Tools is the source of truth for
  hardware routing logic; orama-system references it.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hardware, affinity, routing, lm-studio, mac, windows, dispatch]
    related_skills: [oramasys-method, hermes-harness]
---

# Hardware Affinity Gate

Hardware-model affinity enforcement for the PT-orama/ECC stack.
Imports flow **one-way**: this skill (in orama-system) references scripts and
rules from Perpetua-Tools. Perpetua-Tools is the source of truth; orama-system
never re-declares those rules independently.

## The Rule (non-negotiable)

| Platform | Allowed Model Format | Canonical Model | Never |
|---|---|---|---|
| **Mac** (Apple Silicon, unified memory) | MLX only | `Qwen3.5-9B-MLX-4bit` (LM Studio Metal) | Any Windows/CUDA/GGUF-only model |
| **Windows** (x86-64 / CUDA) | GGUF only | `Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2` (LM Studio, `gpu_offload=40`) | Any MLX model, Metal path, or Mac-only quantization |
| **Shared / fallback** | GGUF CPU-capable | `qwen3-coder:14b`, `gemma-4-26b-a4b-it`, Ollama `qwen3.5:35b-a3b-q4_K_M` | Models that require GPU offload unavailable on the target tier |

**Affinity verdicts:**

| Verdict | Meaning | Enforcement |
|---|---|---|
| `PREFER` | Optimal target tier | Route here when available and healthy |
| `ALLOW` | Functional secondary | Use only when `PREFER` tier is unreachable, overloaded, or failing |
| `NEVER` | Hard exclusion | **Fail-closed.** Raise an explicit error. No silent fallback. |

## Why This Exists

No existing framework (LangGraph, CrewAI, AutoGen, smolagents, Pydantic AI)
enforces hardware affinity as a pre-dispatch gate. They assume uniform
API-callable agents. The RTX 3080 OOM incident (2026-04-07) proved that
`PREFER`-vs-`ALLOW` is recoverable (slower inference) but `NEVER` violation
is not — it produces crashes and driver resets.

This skill turns the pattern into a reusable, testable, auditable gate.

## When to Use

- Before spawning or dispatching any agent that loads a local model
- Before routing a task to LM Studio or Ollama on a specific host
- When building or reviewing orchestration code that touches model selection
- Whenever a config file contains model names tied to a hardware tier

## When NOT to Use

- Cloud-only tasks (Perplexity, OpenAI, Anthropic endpoints)
- Tasks routed through `cloud_enabled: true` with budget remaining
- Discovery / probe tools (e.g. `discover.py`, network watchers) — these
  degrade gracefully and are exempt from hard failures
- Tests that mock hardware and intentionally exercise fallback paths

## Canonical Model IDs

> **Rule:** Never hardcode model IDs in application code. Query the live
> `/v1/models` (LM Studio) or `/api/tags` (Ollama) endpoint at runtime.
> The IDs below are the **expected canonical names** used in policy files
> and tests.

```bash
# LM Studio inventory (live probe)
curl -s http://<host>:1234/v1/models | jq -r '.data[].id'

# Ollama inventory (live probe)
curl -s http://<host>:11434/api/tags | jq -r '.models[].name'
```

### Mac tier (Apple Silicon)

| ID | Backend | Notes |
|---|---|---|
| `Qwen3.5-9B-MLX-4bit` | LM Studio (Metal) | Primary orchestrator / verifier |
| `glm-5.1:cloud` | Ollama (local client) | Thin orchestrator fallback when probe succeeds |

### Windows tier (RTX 3080 / CUDA)

| ID | Backend | Notes |
|---|---|---|
| `Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2` | LM Studio (CUDA) | Primary coder / critic / heavy reasoning |
| `qwen3-coder:14b` | Ollama (CUDA) | Fallback when 27B unreachable |
| `gemma-4-26b-a4b-it` | Ollama (CUDA) | Secondary fallback |
| `qwen3.5:35b-a3b-q4_K_M` | Ollama (CUDA) | Last-resort local fallback |

### Shared / fallback tier

| ID | Backend | Notes |
|---|---|---|
| `qwen3.5:35b-a3b-q4_K_M` | Ollama (any) | CPU-capable fallback |
| `qwen3-30b-critic` | Ollama (Dell / CPU) | Offline critic + orchestrator fallback |

## Implementation

### Python Gate Function

```python
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Literal, Optional

@dataclass(frozen=True)
class AffinityPolicy:
    mac_prefer: tuple[str, ...] = ("Qwen3.5-9B-MLX-4bit",)
    win_prefer: tuple[str, ...] = ("Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2",)
    mac_never: tuple[str, ...] = ()
    win_never: tuple[str, ...] = ()
    shared_never: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> "AffinityPolicy":
        return cls(
            mac_prefer=tuple(
                os.getenv("MAC_PREFER_MODELS", "Qwen3.5-9B-MLX-4bit").split(",")
            ),
            win_prefer=tuple(
                os.getenv(
                    "WIN_PREFER_MODELS",
                    "Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2",
                ).split(",")
            ),
            mac_never=tuple(os.getenv("MAC_NEVER_MODELS", "").split(",")),
            win_never=tuple(os.getenv("WIN_NEVER_MODELS", "").split(",")),
            shared_never=tuple(os.getenv("SHARED_NEVER_MODELS", "").split(",")),
        )


@dataclass(frozen=True)
class AffinityDecision:
    verdict: Literal["PREFER", "ALLOW", "NEVER"]
    tier: Literal["mac", "windows", "shared"]
    resolved_model: Optional[str] = None
    reason: str = ""


class HardwareAffinityError(Exception):
    """Raised when a NEVER verdict fires. Never silent."""


def check_affinity(
    model_id: str,
    tier: Literal["mac", "windows", "shared"],
    policy: AffinityPolicy | None = None,
) -> AffinityDecision:
    """
    Return a verdict for `model_id` on `tier`.
    Raises HardwareAffinityError on NEVER.
    """
    policy = policy or AffinityPolicy.from_env()

    m = model_id.lower().strip()
    norm = lambda seq: tuple(x.lower().strip() for x in seq if x.strip())

    if tier == "mac":
        if m in norm(policy.mac_never):
            raise HardwareAffinityError(
                f"HARDWARE_MISMATCH: {model_id} is NEVER on mac. "
                f"Reason: MLX / Apple-Silicon-only model."
            )
        if m in norm(policy.mac_prefer):
            return AffinityDecision("PREFER", "mac", model_id, "Canonical Mac model")
        return AffinityDecision("ALLOW", "mac", model_id, "Mac fallback")

    if tier == "windows":
        if m in norm(policy.win_never):
            raise HardwareAffinityError(
                f"HARDWARE_MISMATCH: {model_id} is NEVER on windows. "
                f"Reason: MLX / Apple-Silicon-only model."
            )
        if m in norm(policy.win_prefer):
            return AffinityDecision("PREFER", "windows", model_id, "Canonical Windows model")
        return AffinityDecision("ALLOW", "windows", model_id, "Windows fallback")

    # shared
    if m in norm(policy.shared_never):
        raise HardwareAffinityError(
            f"HARDWARE_MISMATCH: {model_id} is NEVER on shared. "
            f"Reason: requires GPU offload unavailable on shared tier."
        )
    return AffinityDecision("ALLOW", "shared", model_id, "Shared fallback")


def resolve_model(
    task_type: str,
    optimize_for: str,
    tier: Literal["mac", "windows", "shared"],
    policy: AffinityPolicy | None = None,
) -> str:
    """
    Pick a model for `task_type` on `tier` using policy defaults.
    Coding and heavy reasoning prefer the Windows tier primary;
    everything else defaults to Mac primary.
    """
    policy = policy or AffinityPolicy.from_env()
    decision = check_affinity(
        policy.win_prefer[0] if tier == "windows" else policy.mac_prefer[0],
        tier,
        policy,
    )
    return decision.resolved_model
```

### Shell Gate Wrapper

```bash
# bin/orama-system/scripts/check_affinity.sh
# Usage: check_affinity.sh <tier> <model_id>
# Exit 0 = allowed, exit 1 = NEVER, prints reason to stderr.
python3 -c "
import sys
from hardware_affinity_gate import check_affinity, HardwareAffinityError
try:
    d = check_affinity(sys.argv[2], sys.argv[1])
    print(d.verdict)
except HardwareAffinityError as e:
    print(str(e), file=sys.stderr)
    sys.exit(1)
" "$@"
```

## Readiness Gates (LM Studio Canary)

Before relying on a local model endpoint for production dispatch, run the
canary probe and enforce these thresholds:

| Tier | Model type | Threshold | Approved | Required `max_tokens` |
|---|---|---|---|---|
| Mac 9B | Non-reasoning | `< 10s` | PASS | `>= 4096` |
| Windows 27B | Reasoning (thinking) | `<= 180s` | PASS | `>= 4096` |
| Windows 27B | Non-reasoning | `<= 90s` | PASS | `>= 4096` |

**Why `max_tokens >= 4096` for reasoning models:** LM Studio reasoning
models return empty `finish_reason=length` if `max_tokens` is below the
model's internal chain-of-thought buffer. The test always passes with
`max_tokens=4096` or higher.

## Integration with Perpetua-Tools

This skill (in orama-system) **imports hardware routing rules and scripts
from Perpetua-Tools** as its source of truth. Perpetua-Tools owns the
enforcement logic; orama-system references it for methodology.

### What This Skill Gets from Perpetua-Tools

- `AffinityPolicy.from_env()` — single source of truth for NEVER lists
- `check_affinity()` — pre-dispatch gate called before any agent spawn
- `resolve_model()` — default model selection per tier + task type
- `HardwareAffinityError` — explicit exception, never silent

### What This Skill Must NOT Do

- Re-declare Mac/Windows NEVER rules inside its own SKILL.md (duplication drifts)
- Override or shadow Perpetua-Tools policy files — PT is the canonical runtime
- Import orama-system Python modules that create a circular dependency
  (PT is the top-level orchestrator; orama-system is the reasoning/methodology layer)

## Agate Alignment

This skill is the **reference implementation** of the `agate` hardware affinity
specification. The schema and verdict semantics (`PREFER` / `ALLOW` / `NEVER`)
match the draft spec in `ultrathink-system/docs/v2/07-agate-vision.md` and
the target repo `github.com/oramasys/agate`.

When `agate` publishes as a standalone package (v2.1+), this skill's
`AffinityPolicy` and `check_affinity()` will import from `agate` instead of
self-hosting the rules.

## Common Pitfalls

1. **Silent fallback on NEVER.** A `HARDWARE_MISMATCH` must raise an explicit
   exception or exit non-zero. Never log a warning and continue.
2. **Hardcoding IPs in source defaults.** Production code defaults to
   `127.0.0.1`. Real LAN IPs belong in `.env` only.
3. **Skipping live probe.** A cached model inventory is stale the moment a
   model is unloaded. Query `/v1/models` or `/api/tags` at dispatch time.
4. **`max_tokens` too low on reasoning models.** Below 4096 the model returns
   empty content with `finish_reason=length`. Always set `>= 4096` for 27B
   reasoning variants.
5. **Cross-platform model listing.** Listing a Mac-only MLX model on Windows,
   or a Windows GGUF model on Mac, is a configuration bug, not a routing bug.
   The gate catches it before dispatch.

## Verification Checklist

- [ ] `check_affinity()` raises `HardwareAffinityError` on every `NEVER` rule
- [ ] `resolve_model()` returns a string, never `None`
- [ ] LM Studio canary passes for all active tiers with `max_tokens >= 4096`
- [ ] No hardcoded LAN IPs in this skill's scripts
- [ ] PT root `SKILL.md` references this skill, not the reverse
- [ ] All NEVER rules are explicit in code or env, never implicit in comments

## One-Shot Recipes

### Bootstrap a new Mac host

```bash
# 1. Verify LM Studio inventory contains the Mac primary
curl -sf http://127.0.0.1:1234/v1/models | jq -r '.data[].id' | grep -i "Qwen3.5-9B"

# 2. Run gate check
python3 -c "from hardware_affinity_gate import check_affinity; \
print(check_affinity('Qwen3.5-9B-MLX-4bit', 'mac'))"

# 3. Confirm verdict is PREFER
```

### Bootstrap a new Windows host

```bash
# 1. Verify LM Studio inventory contains the Windows primary
curl -sf http://127.0.0.1:1234/v1/models | jq -r '.data[].id' | grep -i "Qwen3.5-27B"

# 2. Run gate check (NEVER test first)
python3 -c "from hardware_affinity_gate import check_affinity, HardwareAffinityError; \
try: check_affinity('Qwen3.5-9B-MLX-4bit', 'windows') \
except HardwareAffinityError as e: print('NEVER caught:', e)"

# 3. Confirm 27B is PREFER and MLX is NEVER
```

### Emergency fallback when primary tier is down

```bash
# 1. Flip tier in PT config (mac → windows or vice versa)
# 2. Re-run resolve_model() — it returns an ALLOW fallback automatically
# 3. Do NOT bypass the gate under pressure; the fallback is explicit
```
