# 17 — Hardware Policy Enforcement (v1 as-built, 2026-05-17/18)

> Records the full 4-layer hardware enforcement chain enshrined during the
> RC-1 post-ship policy audit. These patterns are the **required blueprint**
> for v2 / agate — the policy surface must be at least this complete, and
> ideally stricter, from day one.
>
> **2026-06-24 update:** Cross-harness wiring (OpenClaw + Hermes) and gap closure
> #128–#131 are documented in
> [Cross-Harness Hardware Policy Architecture](../hermes-hardware-policy-cross-harness.md).

Status: **canonical reference** — describes v1 (`diazMelgarejo/Perpetua-Tools`) as-built.

---

## The Core Problem: LM Studio's LAN Proxy

**Discovered 2026-04-29.**

LM Studio silently proxies all configured remote LAN endpoints' model lists
as "local" models. Concretely:

- Mac's `/v1/models` returns Win models AND Mac models (proxied + native).
- Win's `/v1/models` returns Mac models AND Win models (proxied + native).

**Consequence**: You CANNOT determine a model's physical home hardware by
looking at which endpoint lists it. `qwen3.5-27b` appearing in Mac's
`/v1/models` does NOT mean the Mac can run it — it's a mirror entry pointing
back to the Windows machine.

**Impact if ignored**: Dispatching a heavy Win-native GGUF (e.g.
`qwen3.5-27b`) to the Mac LM Studio mirror endpoint triggers a proxy call
back to Windows. If a user simultaneously dispatches the same model directly
to Windows, both hit the RTX 3080 at once — "double barrel" GPU load.
On a 10GB VRAM card this causes OOM or driver instability.

This is why the Mac LM Studio endpoint (`localhost:1234`) is **MIRROR ONLY**
— discovery visibility, never dispatch target.

---

## The 4-Layer Enforcement Chain

### Layer 1: `config/devices.yml` — hardware topology

Single source of truth for which physical machine owns what.

```yaml
# win-rtx3080: exclusive runner for heavy GGUF models
win-rtx3080:
  lan_ip: "192.168.254.103"
  lm_studio_port: 1234
  description: "Windows PC — RTX 3080 10GB. Exclusive runner for
    qwen3.5-27b (Q4_K_M, GPU Offload=40) and gemma-4-26b."

# mac-studio: Ollama only for inference; LM Studio is MIRROR ONLY
mac-studio:
  default_backend: "ollama"
  lm_studio_port: 1234        # MIRROR ONLY — discovery, never dispatch
  description: "Mac Apple Silicon M2. Ollama = primary inference backend.
    LM Studio Mac = mirror of Win models over LAN. Do NOT dispatch to
    lmstudio-mac."
```

**Key corrections made 2026-05-17:**
- `win-rtx3080.lan_ip` was `""` (empty) → corrected to `"192.168.254.103"`
- `mac-studio.default_backend` was `"mlx"` → corrected to `"ollama"`
- `mac-studio.secondary_backend` removed (contradicted mirror policy)
- `shared-ollama.lan_ip` was incorrectly `".103"` → corrected to `""`

---

### Layer 2: `config/model_hardware_policy.yml` — hard enforcement

Promoted from "performance routing hints" to **hard enforcement** on 2026-05-17.

```yaml
mac_only: []

# HARD POLICY: models that physically run ONLY on Win RTX 3080.
# Dispatching to lmstudio-mac = proxy call back to Win = double-barrel risk.
windows_only:
  - qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2
  - gemma-4-26b-a4b-it

# These run natively on both machines (or small enough for either):
shared:
  - qwen3.5-9b-mlx
  - gemma-4-e4b-it
  - text-embedding-nomic-embed-text-v1.5

windows_only_aliases:
  - Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2
  - gemma-4-26B-A4B-it-Q4_K_M
```

**Prior state (wrong):** `windows_only:` was absent; `qwen3.5-27b` was listed
under `shared:` framed as "performance routing, not hard enforcement." This
would have allowed dispatch to Mac mirror = double-barrel GPU risk.

---

### Layer 3: `perpetua/discovery/selector.py` — code enforcement

Two mechanisms:

#### `_MIRROR_BACKENDS` frozenset
```python
_MIRROR_BACKENDS: frozenset[str] = frozenset({"lmstudio-mac"})
```

Every candidate selection path checks `b.name not in _MIRROR_BACKENDS` before
adding a backend to the candidate pool. The mirror cannot be returned by
`select_backend()` regardless of tier, task type, or model hint.

#### `_TIER_HOSTS` — Mac tier excludes lmstudio-mac
```python
_TIER_HOSTS = {
    "mac":     {"ollama-local"},    # never lmstudio-mac (mirror only)
    "windows": {"lmstudio-win"},
    "shared":  set(),               # any non-mirror backend
}
```

**Prior state (wrong):** `_TIER_HOSTS["mac"]` included `"lmstudio-mac"` as a
valid Mac-tier dispatch target. This was the code-level reflection of the
wrong policy in Layer 2.

#### `_TIER_PREF` — Mac tier uses Ollama only
```python
_TIER_PREF = {
    ("mac", "coding"):    (BackendKind.OLLAMA,),
    ("mac", "reasoning"): (BackendKind.OLLAMA,),
    ...
}
```

Mac task types now only prefer Ollama backends — never LM Studio.

---

### Layer 4: `agent_launcher.py` — non-TTY fail-closed

When a `windows_only:` model is routed to Mac hardware, `HardwareAffinityError`
is raised. The root `agent_launcher.py` was updated to fail closed in
non-interactive contexts (CI, pytest, background jobs):

```python
async def _await_manager_override_async(exc, timeout=10.0):
    if not sys.stdin.isatty():
        print(
            f"[non-interactive] auto-denying — fail closed on "
            f"hardware policy violation."
        )
        return False
    # ... interactive override prompt for human operator
```

**Why needed:** `model_hardware_policy.yml` promotion to `windows_only:` caused
`HardwareAffinityError` to fire during pytest runs (because Mac LM Studio
mirror was responding with the Win model listed). Without the TTY guard,
the test suite hung waiting for stdin.

---

## Registry seed annotations

`perpetua/discovery/registry.py` now annotates the mirror backend in `_SEEDS`:

```python
_SEEDS: dict[str, tuple[str, BackendKind, tuple[str, ...]]] = {
    "lmstudio-mac": (
        # MIRROR ONLY: Mac LM Studio proxies Win models via LAN.
        # Listed for discovery visibility; _MIRROR_BACKENDS in selector.py
        # prevents dispatch. Do NOT remove this comment.
        "http://localhost:1234/v1",
        BackendKind.LMSTUDIO,
        (),
    ),
    ...
}
```

---

## v2 / agate requirements derived from this

When implementing the v2 `perpetua-core` policy layer and `agate`, these
patterns must be honored from day one:

| Requirement | Layer | Mechanism |
|-------------|-------|-----------|
| Mirror backends cannot be dispatch targets | selector | `_MIRROR_BACKENDS` frozenset pattern |
| Physical hardware ownership is a topology fact, not an endpoint inference | config | `devices.yml` with explicit `lan_ip` per physical machine |
| `windows_only:` models must raise `HardwareAffinityError` if routed to non-Windows | policy | `HardwarePolicyResolver.check_affinity()` |
| Fail closed (not fail open) under non-interactive conditions | launcher | `sys.stdin.isatty()` guard before any override prompt |
| Policy document must use `windows_only:` not "windows preferred" | config | Semantic precision — NEVER vs. PREFER is a hard safety boundary |

### agate schema implication

`model_hardware_policy.yml` must distinguish **three** affinity levels, not two:

| agate verdict | Meaning | v1 equivalent |
|---------------|---------|---------------|
| `NEVER` (enforced) | Model physically cannot run on this tier. Dispatching = hardware damage risk. | `windows_only:` with `_MIRROR_BACKENDS` |
| `PREFER` | Works best here; other tiers allowed as fallback. | `shared:` with win-first or mac-first sort order |
| `ALLOW` | Works here, but not the preferred tier. | `shared:` with secondary sort position |

The current v1 `model_hardware_policy.yml` implements `NEVER` (via
`windows_only:`) and `PREFER/ALLOW` (via `shared:` + selector sort order) but
does not yet expose these as named verdicts. v2 / agate should make these
explicit in the schema.

---

## Test coverage added (2026-05-17)

| Test | File | What it proves |
|------|------|----------------|
| `test_selector_excludes_mirror_backend` | `tests/test_selector.py` | `_MIRROR_BACKENDS` filter works end-to-end |
| `test_selector_mac_tier_never_returns_mirror` | `tests/test_selector.py` | `target_tier="mac"` cannot return `lmstudio-mac` |
| `test_resolver_picks_lmstudio_win_for_shared_coding` | `tests/test_backend_resolver.py` | Shared coding task routes to Win LM Studio |
| `test_resolver_honors_base_url_override_matching_known_backend` | `tests/test_backend_resolver.py` | URL override resolves to registered backend |
| `test_resolver_override_synthesizes_adhoc_backend_for_unknown_url` | `tests/test_backend_resolver.py` | Unknown URL override synthesizes ad-hoc backend |

All 36/36 v1 tests pass after these additions.

---

## LESSONS.md entry (2026-05-17)

The full learning is enshrined in `docs/LESSONS.md` under:
> "Hardware mirror policy — LM Studio LAN proxy gotcha (2026-05-17)"

Short form:
> Mac LM Studio appears in `/v1/models` as having Win models. It does not
> own them. It is a proxy. Dispatch to it when a Win-native model is needed
> = double barrel GPU = OOM. Solution: `_MIRROR_BACKENDS` + `windows_only:` +
> fail-closed TTY guard.
