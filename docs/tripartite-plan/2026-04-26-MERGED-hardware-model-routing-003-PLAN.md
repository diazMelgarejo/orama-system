# Hardware-Bound Model Routing — Final Merged Plan

**Version:** 3.0 (Codex + Gemini + Grok corrections applied)  
**Date:** 2026-04-26  
**Repos in scope:** `Perpetua-Tools` (L2 adapter/middleware) · `orama-system` (L3 intelligence/orchestration)  
**Status:** Pre-implementation — ready for dev execution

Review the suggestions in this plan and consider their effects to the overall logic and integrity of both systems?

If any clarification or conflict-resolution is needed, AskUserQuestion and wait for confirmation before proceeding.

If you have better ideas, discovered better implementations, or competing proposals, be very thorough and save alternative plan for consideration first, and defend with your own justifications? We will always choose the best option at each stage!

---

## Root Cause

`orama-system/scripts/discover.py` blindly trusts `/v1/models` from each LM Studio endpoint and writes raw, unfiltered model lists into:

- `~/.openclaw/openclaw.json`
- `~/.openclaw/state/discovery.json`
- `~/.openclaw/state/last_discovery.json`
- `.env.lmstudio`

**Current known pollution in live config:**

Remember why and surface this existing logic in all markdown documentations?

- `lmstudio-mac` is advertising Windows-only 27B/26B models — hardware damage risk.
- `lmstudio-win` is advertising Mac-only 9B MLX/Gemma E4B models — resource mismatch.

Discovery filtering alone is insufficient. If someone manually edits `openclaw.json` or the filter fails silently, there is no second line of defense. This plan implements both lines.

---

## Architecture: Defense-in-Depth

```ascii
┌─────────────────────────────────────────────────────────────────────┐
│  L1 — Source Hygiene (Perpetua-Tools)                               │
│  discover.py reads policy → filters model lists → writes clean JSON │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ clean openclaw.json
┌─────────────────────────▼───────────────────────────────────────────┐
│  L2 — Runtime Enforcement (Perpetua-Tools · alphaclaw_manager.py)   │
│  validate_routing_affinity() called before every agent spawn        │
│  Raises HardwareAffinityError on violation — hard kill-switch       │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ affinity-cleared spawn signal
┌─────────────────────────▼───────────────────────────────────────────┐
│  L3 — API Pre-flight (orama-system · api_server.py)                 │
│  Pre-flight check queries PT manager before agent spawn             │
│  Returns HTTP 400 HARDWARE_MISMATCH on violation                    │
└─────────────────────────────────────────────────────────────────────┘
```

**Repository ownership:**

- `Perpetua-Tools` — owns discovery hygiene, the canonical policy file, and L2 enforcement.
- `orama-system` — owns L3 agent registry, API pre-flight, and shared intelligence docs.

---

## Authoritative Model Policy

**Source of truth:** `Perpetua-Tools/config/model_hardware_policy.yml`

All other references (SKILL.md, MODEL_HARDWARE_MATRIX.md, AGENT_RESUME.md) cite this file — they do not duplicate it. Harmonize and deduplicate all related content by progressive disclosure of more context only when needed.

> ⚠️ **Hallucination alert (corrected):** `qwen3-coder-14b` and `gemma4:e4b` appeared in earlier AI-generated drafts of this plan. They are NOT real models in this system. Do NOT add them to the policy file or any config. Removed permanently. Add to all pre-commit hooks, so we do not hallucinate and cause errors down the line!

### Verified Model List (from source files only)

- try all variants, and check which one loads?
- remember which one loads so we keep it, and remove non-working variants from all examples and document this decision?

**Windows-only** — exceeds Mac VRAM/cooling limits. Tag: `NEVER_MAC`

| Model ID | Case-sensitive variants |
|---|---|
| `gemma-4-26b-a4b-it` | `gemma-4-26B-A4B-it-Q4_K_M` |
| `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2` | `Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2` |

**Mac-only** — MLX weights / Apple Silicon optimized. Tag: `NEVER_WIN`

| Model ID | Case-sensitive variants |
|---|---|
| `gemma-4-e4b-it` | *(no variants)* |
| `qwen3.5-9b-mlx` | `Qwen3.5-9B-MLX-4bit`, `qwen3.5-9b-mlx-4bit` |

**Shared/neutral** — allowed on both platforms only if explicitly named:
> NONE! ⚠️ Leave this section **empty until verified**. Do NOT populate with inferred or hallucinated model IDs. Add only after confirming with `python3 discover.py --status` on both machines. Add to all documentations on hardware and model matrix markdowns?

```yaml
# Perpetua-Tools/config/model_hardware_policy.yml
# SINGLE SOURCE OF TRUTH — all enforcement reads this file

windows_only:
  - gemma-4-26b-a4b-it
  - gemma-4-26B-A4B-it-Q4_K_M
  - qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2
  - Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2

mac_only:
  - gemma-4-e4b-it
  - qwen3.5-9b-mlx
  - qwen3.5-9b-mlx-4bit
  - Qwen3.5-9B-MLX-4bit

shared:
  # INTENTIONALLY EMPTY — do not populate without verification
  # Add only confirmed cross-platform models here
```

---

## Phase 1 — Knowledge & Policy Layer (Perpetua-Tools)

**Goal:** Establish the canonical policy file. No code changes yet.

### 1.1 Create policy file

```
Perpetua-Tools/config/model_hardware_policy.yml
```

Use the YAML block above verbatim. This is the first commit.

### 1.2 Update hardware/SKILL.md

In the Role Matrix, add a `Constraint` column. Mark:

- `NEVER_MAC` for all Windows-only model IDs
- `NEVER_WIN` for all Mac-only model IDs
- Cite `config/model_hardware_policy.yml` as the machine-readable source

### 1.3 Update docs/MODEL_HARDWARE_MATRIX.md

Add a header note:

```markdown
> **Machine-enforced policy:** See `config/model_hardware_policy.yml`.
> This document is the human-readable reference. The YAML file is the
> authoritative source for all runtime enforcement.
```

All our edits are additive, merging, and integrative; NEVER replace any content but repurpose, correct, modify, or extend only.

---

## Phase 2 — L1 Source Hygiene (orama-system · discover.py)

**Goal:** Filter model lists at discovery time so config files are never written with polluted data.

### 2.1 Update orama-system/scripts/discover.py

Add a `load_policy()` helper that reads `Perpetua-Tools/config/model_hardware_policy.yml` (use a relative path from repo root or an env var `PERPETUA_TOOLS_ROOT`).

Add a `filter_models_for_platform(models: list, platform: str, policy: dict) -> list` pure function — no side effects, easy to unit test.

Call the filter before every write to `openclaw.json`, `discovery.json`, `last_discovery.json`, and `.env.lmstudio`.

```python
# Pseudocode — implement in discover.py

def filter_models_for_platform(models: list, platform: str, policy: dict) -> list:
    """Remove models that are forbidden on the given platform."""
    if platform == "mac":
        forbidden = set(m.lower() for m in policy.get("windows_only", []))
    elif platform == "win":
        forbidden = set(m.lower() for m in policy.get("mac_only", []))
    else:
        forbidden = set()
    return [m for m in models if m.lower() not in forbidden]
```

### 2.2 Add unit tests — orama-system/scripts/tests/test_discover.py

Test cases required:

- Mixed input to `lmstudio-mac` → Windows-only models stripped, Mac-only models retained
- Mixed input to `lmstudio-win` → Mac-only models stripped, Windows-only models retained
- Clean input → no change
- Unknown model → passes through (not silently blocked)

Run: `python3 -m pytest scripts/tests/test_discover.py -q`

---

## Phase 3 — L2 Runtime Enforcement (Perpetua-Tools · alphaclaw_manager.py)

**Goal:** Hard kill-switch that fires even if configs are manually edited or discovery is bypassed.

### ⚠️ Open Architecture Question — Resolve Before Implementing

**The question:** Should `validate_routing_affinity()` be an **instance method** on `AlphaClawManager` or a **standalone module-level function**?

**Arguments for instance method (Grok's recommendation):**

- Consistent with how `AlphaClawManager` already encapsulates `load_policy()`
- Allows the manager to cache the policy dict after first load instead of re-reading YAML on every call
- Single entry point — any caller that has a manager instance automatically gets both policy loading and validation together
- Easier to mock in tests (patch the manager, not a global function)

**Arguments for standalone function:**

- `discover.py` also needs to call the filter logic — if it's on the manager instance, discover.py must instantiate the full manager (heavy dependency) just to filter a list
- A pure function `filter_models_for_platform(models, platform, policy)` is trivially testable with no class overhead

**Recommended resolution (needs owner confirmation before merge):**
Split into two layers:

1. A **standalone pure function** `filter_models_for_platform()` in a shared utils module (e.g., `Perpetua-Tools/utils/hardware_policy.py`) — used by both `discover.py` and the manager
2. An **instance method** `validate_routing_affinity(model_id, platform)` on `AlphaClawManager` that calls the shared util and raises `HardwareAffinityError`

This avoids the circular dependency (discover.py importing the full manager) while keeping enforcement consistent.

> **Action required:** Confirm this split with the repo owner before Phase 3 implementation.

### 3.1 Add typed exception

```python
# Perpetua-Tools/utils/hardware_policy.py

class HardwareAffinityError(RuntimeError):
    """
    Raised when a model is assigned to hardware it cannot safely run on.
    Catch this in api_server.py and return HTTP 400 HARDWARE_MISMATCH.
    """
    pass
```

### 3.2 Add shared utility function

```python
# Perpetua-Tools/utils/hardware_policy.py

import yaml
from pathlib import Path

_POLICY_CACHE: dict | None = None

def load_policy(policy_path: Path | None = None) -> dict:
    global _POLICY_CACHE
    if _POLICY_CACHE is not None:
        return _POLICY_CACHE
    if policy_path is None:
        policy_path = Path(__file__).parent.parent / "config/model_hardware_policy.yml"
    with open(policy_path) as f:
        _POLICY_CACHE = yaml.safe_load(f)
    return _POLICY_CACHE

def check_affinity(model_id: str, platform: str, policy: dict | None = None) -> None:
    """
    Raises HardwareAffinityError if model_id is forbidden on platform.
    platform: 'mac' | 'win'
    """
    if policy is None:
        policy = load_policy()
    model_lower = model_id.lower()
    if platform == "mac":
        forbidden = {m.lower() for m in policy.get("windows_only", [])}
        if model_lower in forbidden:
            raise HardwareAffinityError(
                f"[alphaclaw] Fatal: '{model_id}' is NEVER_MAC. "
                f"Assign to lmstudio-win only."
            )
    elif platform == "win":
        forbidden = {m.lower() for m in policy.get("mac_only", [])}
        if model_lower in forbidden:
            raise HardwareAffinityError(
                f"[alphaclaw] Fatal: '{model_id}' is NEVER_WIN. "
                f"Assign to lmstudio-mac only."
            )
```

### 3.3 Add instance method to AlphaClawManager

```python
# Perpetua-Tools/orchestrator/alphaclaw_manager.py

from utils.hardware_policy import check_affinity, HardwareAffinityError

class AlphaClawManager:

    def validate_routing_affinity(self, model_id: str, platform: str) -> bool:
        """
        Instance method wrapper around check_affinity().
        Call this during --resolve sequence and before every agent spawn.
        Raises HardwareAffinityError on violation.
        """
        check_affinity(model_id, platform)  # raises on violation
        return True
```

### 3.4 Inject into agent_launcher.py probe loop

Add the validation call in the probe loop before any spawn attempt:

```python
# Perpetua-Tools/agent_launcher.py — probe loop injection point

from utils.hardware_policy import check_affinity, HardwareAffinityError

# Inside probe loop, before spawn:
try:
    check_affinity(model_id=resolved_model, platform=resolved_platform)
except HardwareAffinityError as e:
    log.error(str(e))
    continue  # skip this agent, do not spawn
```

---

## Phase 4 — L3 API Pre-flight (orama-system · api_server.py)

**Goal:** Return a clean HTTP 400 at the API boundary before any agent spawning occurs.

### 4.1 Update orama-system/api_server.py

```python
# orama-system/api_server.py — pre-flight block

import sys
sys.path.insert(0, PERPETUA_TOOLS_ROOT)  # env var or relative path
from utils.hardware_policy import check_affinity, HardwareAffinityError

# In the spawn handler:
try:
    check_affinity(model_id=request.model, platform=request.platform)
except HardwareAffinityError as e:
    return JSONResponse(
        status_code=400,
        content={"error": "HARDWARE_MISMATCH", "detail": str(e)}
    )
```

### 4.2 Update orama-system/bin/config/agent_registry.json

Add `"affinity"` key to every agent definition:

```json
{
  "openclaw_agents": {
    "mac-primary": {
      "model": "Qwen3.5-9B-MLX-4bit",
      "provider": "lmstudio-mac",
      "affinity": "mac"
    },
    "win-coder": {
      "model": "Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2",
      "provider": "lmstudio-win",
      "affinity": "win"
    }
  }
}
```

---

## Phase 5 — Live Config Repair

**Do this after all code changes are committed and tests pass.**

### 5.1 Backup first

```bash
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-$(date +%Y%m%d)
cp ~/.openclaw/state/discovery.json ~/.openclaw/state/discovery.json.bak-$(date +%Y%m%d)
cp ~/.openclaw/state/last_discovery.json ~/.openclaw/state/last_discovery.json.bak-$(date +%Y%m%d)
```

### 5.2 Repair and verify

```bash
# Re-run discovery with the new filter active
python3 ~/.openclaw/scripts/discover.py --status

# Validate the live config passes the policy
python3 - <<'EOF'
import json, yaml, sys
from pathlib import Path

config = json.loads(Path("~/.openclaw/openclaw.json").expanduser().read_text())
policy = yaml.safe_load(Path("Perpetua-Tools/config/model_hardware_policy.yml").read_text())

win_only = {m.lower() for m in policy["windows_only"]}
mac_only = {m.lower() for m in policy["mac_only"]}

errors = []
for provider in config.get("providers", []):
    platform = "mac" if "mac" in provider["id"] else "win"
    for model in provider.get("models", []):
        m = model.lower()
        if platform == "mac" and m in win_only:
            errors.append(f"VIOLATION: {model} in mac provider {provider['id']}")
        if platform == "win" and m in mac_only:
            errors.append(f"VIOLATION: {model} in win provider {provider['id']}")

if errors:
    print("❌ Config violations found:")
    for e in errors: print(f"  {e}")
    sys.exit(1)
else:
    print("✅ Live config passes hardware policy check.")
EOF
```

**Expected clean state after repair:**

- `lmstudio-mac` providers: `gemma-4-e4b-it`, `qwen3.5-9b-mlx`, `qwen3.5-9b-mlx-4bit`
- `lmstudio-win` providers: `gemma-4-26b-a4b-it`, `gemma-4-26B-A4B-it-Q4_K_M`, `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2`

Also fix while you're there:

- Malformed `LM_STUDIO_WIN_ENDPOINTS` default value
- Stale `win-rtx3080` LAN IP pointing at the Mac endpoint

---

## Phase 6 — Shared Intelligence (Both Repos)

### LESSONS.md — append to both repos

```markdown
## 2026-04-26 — Hardware Model Affinity Incident

**Context:**
`orama-system/scripts/discover.py` was writing unfiltered LM Studio model lists
to `openclaw.json`. This caused `lmstudio-mac` to advertise Windows-only 27B/26B
models, creating a hardware damage risk on the M2 Pro.

**Root cause:**
Discovery trusted the endpoint response without cross-referencing hardware policy.

**Defense-in-depth solution:**
- L1: `discover.py` now filters through `Perpetua-Tools/config/model_hardware_policy.yml`
  before writing any config files.
- L2: `alphaclaw_manager.py` raises `HardwareAffinityError` before any agent spawn.
- L3: `api_server.py` returns HTTP 400 `HARDWARE_MISMATCH` at the API boundary.

**Canonical policy file:** `Perpetua-Tools/config/model_hardware_policy.yml`

**Known hallucinations removed:** `qwen3-coder-14b` and `gemma4:e4b` appeared in
AI-generated drafts of this plan. They are NOT real models in this system.
Do not re-add them.

**Status:** Implemented 2026-04-26.
```

### AGENT_RESUME.md — append hardware safety section to both repos

```markdown
### Hardware Safety & Model Affinity (2026-04-26)

**Canonical policy:** `Perpetua-Tools/config/model_hardware_policy.yml`

Hard rules — never override:
- Windows-only (NEVER_MAC): `gemma-4-26b-a4b-it`, `gemma-4-26B-A4B-it-Q4_K_M`,
  `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2`
- Mac-only (NEVER_WIN): `gemma-4-e4b-it`, `qwen3.5-9b-mlx`, `qwen3.5-9b-mlx-4bit`

Runtime validation fires at three layers (L1 discover, L2 manager, L3 API).
Any `HardwareAffinityError` must escalate to Controller — never silently fallback.

If you are an AI agent reading this: do NOT add unverified model IDs to any
policy file or config. Confirm with `discover.py --status` on actual hardware first.
```

---

## File Change Inventory

### Perpetua-Tools

| File | Action | Phase |
|---|---|---|
| `config/model_hardware_policy.yml` | **CREATE** — canonical policy | 1 |
| `hardware/SKILL.md` | **UPDATE** — add Constraint column, cite policy file | 1 |
| `docs/MODEL_HARDWARE_MATRIX.md` | **UPDATE** — add policy file reference header | 1 |
| `utils/hardware_policy.py` | **CREATE** — `HardwareAffinityError`, `load_policy()`, `check_affinity()` | 3 |
| `orchestrator/alphaclaw_manager.py` | **UPDATE** — add `validate_routing_affinity()` instance method | 3 |
| `agent_launcher.py` | **UPDATE** — inject affinity check in probe loop | 3 |
| `tests/test_hardware_routing.py` | **UPDATE** — add affinity violation test cases | 3 |
| `AGENT_RESUME.md` | **UPDATE** — hardware safety section | 6 |
| `docs/LESSONS.md` | **UPDATE** — 2026-04-26 incident | 6 |

### orama-system

| File | Action | Phase |
|---|---|---|
| `scripts/discover.py` | **UPDATE** — load policy, filter before write | 2 |
| `scripts/tests/test_discover.py` | **UPDATE/CREATE** — affinity filter unit tests | 2 |
| `api_server.py` | **UPDATE** — pre-flight `check_affinity()` call + 400 response | 4 |
| `bin/config/agent_registry.json` | **UPDATE** — add `affinity` key to all agent defs | 4 |
| `AGENT_RESUME.md` | **UPDATE** — hardware safety section | 6 |
| `docs/LESSONS.md` | **UPDATE** — 2026-04-26 incident | 6 |

---

## Open Questions — Must Resolve Before Phase 3

| # | Question | Impact |
|---|---|---|
| 1 | **Confirm the `alphaclaw_manager.py` class structure.** Does the existing `AlphaClawManager` already have `load_policy()`? If not, the instance method approach adds a new dependency — confirm before refactoring. | Phase 3 design |
| 2 | **Path resolution for policy file in `orama-system`.** Is `PERPETUA_TOOLS_ROOT` an env var already set in the orama runtime, or does it need to be added to `.env`? | Phase 2, 4 |
| 3 | **Shared/neutral model list.** After running `discover.py --status` on both machines, document any genuinely cross-platform models and add them to the `shared:` section of the policy YAML. Currently intentionally empty. | Phase 1 |
| 4 | **Who owns `utils/hardware_policy.py`?** If `orama-system` imports from `Perpetua-Tools/utils`, there is a cross-repo import. Alternatives: copy the module, publish as a pip package, or use a git submodule. Decide before Phase 3. | Phase 3, 4 |

---

## Commit Order (Safe Sequence)

```
1. Perpetua-Tools: config/model_hardware_policy.yml + SKILL.md + MODEL_HARDWARE_MATRIX.md
2. Perpetua-Tools: utils/hardware_policy.py (no breaking changes — new file only)
3. orama-system:   scripts/discover.py + test_discover.py
4. Perpetua-Tools: alphaclaw_manager.py + agent_launcher.py
5. orama-system:   api_server.py + agent_registry.json
6. Both repos:     AGENT_RESUME.md + LESSONS.md
7. Both repos:     Run full test suites, then live config repair
```

Each commit is independently safe. Rollback at any step does not break the previous step.

---

*Plan synthesized from: `2026-04-26-codex-001-PLAN.md`, `2026-04-26-gemini-002-PLAN.md`, Grok corrections (2026-04-26), and owner corrections (repo rename, hallucination removal, architecture open question flagged).*
