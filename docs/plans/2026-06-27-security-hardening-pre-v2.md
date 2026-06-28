<!-- lint-ignore LINT-013 LINT-014 -->
# Security-in-Depth Hardening — Pre-v2 Feature Freeze

> **Status:** 🚧 IN PROGRESS — Mac E2E ✅ local; Windows E2E ✅ 2026-06-28; Mac↔Win cross-harness ⏳  
> **Target:** Last release before snapshot as `v1.x-stable` → migration to `oramasys/*`  
> **Versions:** orama-system `1.1.1.0` · Perpetua-Tools `1.1.1.0` → freeze tag `v1.1.1`  
> **Approval gate:** Explicit "approve" from user before any execution tier.

---

## Platform schedule (tomorrow vs Linux cloud)

Steps marked **🍎 macOS** or **🪟 Windows 11** require the main machines — schedule for tomorrow.  
Steps marked **🐧 Linux** run non-interactively on the cloud VM (Gstack/Gbrain/Ollama/LM Studio CLI where available).

| Tier | Item | Platform | Status |
|------|------|----------|--------|
| T1-A | routing.json schema validation | 🐧 Linux | ✅ done |
| T1-B | Module URL canonicalization | 🐧 Linux | ✅ done |
| T1-C | Policy enforcement audit | 🐧 Linux | ✅ done |
| T2-A | LINT-014 argv secret scan | 🐧 Linux | ✅ done |
| T2-B | Model ID allowlist (`check_model_ids.py`) | 🐧 Linux | ✅ done |
| T2-C | Line-level LINT-013 | 🐧 Linux | ✅ done |
| T3-A | Concurrent lock stress test | 🐧 Linux | ✅ done |
| T3-B | Commit-message fuzz tests | 🐧 Linux | ✅ done |
| T3-C | Engine orphan conflict archive | 🐧 Linux | ✅ done |
| T4-A | Dependency pinning verification | 🐧 Linux | ✅ done |
| T4-B | LM Studio token default warning | 🐧 Linux (script only) | ✅ done |
| T4-C | SBOM stub (`cyclonedx-py`) | 🐧 Linux | ✅ done |
| E2E | `start.sh` full stack | 🍎 macOS + 🪟 Windows 11 | ✅ Mac clean; ✅ Win testdrive 2026-06-28 |
| E2E | `probe_required_endpoints` Ollama + models | 🍎 macOS | ✅ done — qwen3.5:9b-nvfp4 + bge-m3 OK |
| E2E | `LM_STUDIO_WIN_ENDPOINTS` LAN probes | 🪟 Windows 11 | ✅ Win local; ⏳ Mac-side cross-probe |
| E2E | `start.sh --hardware-policy` live harness | 🍎 macOS + 🪟 Windows 11 | ✅ Mac clean; ✅ Win `--validate` (OpenClaw optional) |
| E2E | Claude Desktop MCPB `--open` install | 🍎 macOS | ✅ done — gbrain+CRG both `ClaudeDesktop=ok` |
| E2E | Keychain credential flows (`security` CLI) | 🍎 macOS | ⚠️ partial — Gemini main + fallback ✅ stored; TELEGRAM_BOT_TOKEN ✅ stored (2026-06-28); `load_keychain_secrets.sh` helper added; **user must still store `openclaw.gateway-auth-token`** |
| E2E | Cross-harness hardware affinity verification | 🍎 macOS + 🪟 Windows 11 | ⏳ pending Mac LAN probe to Win |
| T5 | Git tags `v1.1.1`, releases, `oramasys/v2-foundation` | After Mac/Win E2E green | ⏳ blocked on Mac↔Win cross-harness |

**Tomorrow checklist (Mac):** See [`2026-06-28-mac-e2e-handoff.md`](2026-06-28-mac-e2e-handoff.md) — `start.sh --status`, Ollama probes, Keychain `openclaw.gateway-auth-token`, Win LAN curl, cross-harness `--hardware-policy`, T5 tags.

**Tomorrow checklist (Win 11):** LM Studio server up; `LM_STUDIO_WIN_ENDPOINTS` reachable from Mac LAN; Windows Ollama probes if configured.

---

## Threat model (from session learnings — steelmanned)

### What we are protecting

| Asset | Value | Threat surface |
|---|---|---|
| API keys / credentials | Compromise = full model spend theft | env vars, argv, process list, git history |
| Hardware affinity policy | Bypass = wrong model on wrong hardware (36B GGUF on Mac → OOM crash) | policy parser, CLI duplicate, alias merge |
| Agent identity / attribution | Bypass = inject unauthorized code author into git history | commit hook fall-through, display-name marker |
| Network topology | Leak = attacker knows internal LAN layout | docs, routing.json, LAN IP in tracked files |
| Lock file integrity | Race = concurrent apply corrupts registry | TOCTOU in store.py |
| State file integrity | Injection = malicious routing.json → wrong endpoints | _load_pt_state no schema validation |
| Model ID integrity | Hallucination = invented model name causes silent wrong dispatch | check_no_hallucinated_models.py scope |
| URL scheme contract | Bare host:port → HTTP client crash or scheme confusion | _heal_pt_endpoint_url (just fixed PR #152) |

---

## Steelmanned critiques (strongest version of each gap)

### S1 — Secrets in argv (FIXED: F6/store_keychain_secret.sh)
**Steelman:** Even with stdin pipe fixed, the *old* command form (`-w $secret`) may still exist in:
- operator muscle memory (they run it from history)  
- other SKILL.md files that haven't been audited  
- `.hermes/plans/` local files that reference the old form  
**Risk:** A local attacker (or malicious background process) running `ps aux` at the right moment captures a live credential.  
**Gap:** No scan verifies the old argv form is absent across ALL skill/plan/doc files.

### S2 — check_commit_message.sh: display-name marker bypass (FIXED: email gate)
**Steelman:** The fix correctly gates on email-first and never falls through to markers when an email is present. BUT: the WELL_KNOWN_COAUTHOR_NAME_MARKERS list is extremely broad (`hermes`, `qwen`, `llama`, `cody`). A display-name-only `Co-authored-by: Hermes <attacker@evil.com>` line — if the email somehow fails to parse (malformed `<>`) — would pass via the `hermes` marker.  
**Risk:** Malformed or specially-crafted Co-authored-by lines with an unparseable email field could bypass the gate.  
**Gap:** No fuzzing of edge cases (no `<>`, multiple `<>`, non-ASCII in address field).

### S3 — Hardware affinity: duplicate parser drift (FIXED: PR #131)
**Steelman:** The CLI now delegates to the canonical API. But `launch_researchers.py` still constructs routing decisions inline. If `hardware_policy.load_policy()` ever changes its alias or normalization logic, `launch_researchers.py` may silently use the old behavior.  
**Risk:** "listed-but-forbidden" bypass can re-emerge in any file that makes policy decisions without going through `load_policy()`.  
**Gap:** No grep-based audit or test ensures that every policy-enforcement site in the codebase uses `load_policy()`.

### S4 — _load_pt_state: unvalidated JSON from filesystem
**Steelman:** `_load_pt_state()` reads any file at `$PT_AGENTS_STATE` with `json.load()` and passes the dict directly to `build_openclaw_config()` and `build_role_routing()`. A malicious or corrupted `routing.json` file could inject:
- Arbitrary `mac_lmstudio_endpoint` pointing to an attacker-controlled server
- A `coder_model` string that contains shell metacharacters (if ever passed to subprocess)
- A boolean field coerced to cause wrong backend selection

**Risk:** Supply-chain attack on the routing file → model traffic redirected.  
**Gap:** No schema validation, no field-type enforcement, no allowlist for endpoint hostnames.

### S5 — LAN IP topology in docs (FIXED: LINT-013 + exemptions)
**Steelman:** The exemptions cover 15+ pre-existing docs. Each exemption is a permanent bypass of LINT-013. A future agent may copy content from an exempted file into a non-exempted file, moving the IP without triggering the lint error.  
**Risk:** Topology leaks propagate through copy-paste even with LINT-013 active.  
**Gap:** Exemptions should be bounded to specific line ranges or patterns, not entire files.

### S6 — TOCTOU in store.py (FIXED: 3-attempt loop)
**Steelman:** The fix uses `time.sleep(0)` (OS yield) between unlink and retry. On a heavily loaded system, `sleep(0)` may not provide enough scheduling time for a competing process to write its lock before we retry O_CREAT|O_EXCL. The window is narrowed but not eliminated.  
**Risk:** Under high concurrent load (e.g. CI matrix with 4 parallel workers), a race condition can still occur.  
**Gap:** No test simulates concurrent lock acquisition under load. The 3-attempt limit also means that under adversarial conditions (continuous lock contention), the third attempt raises `LockHeld(-1)` rather than identifying who holds the lock.

### S7 — Model ID hallucination scope (PARTIALLY MITIGATED)
**Steelman:** `check_no_hallucinated_models.py` only checks the FORBIDDEN set (`qwen3-coder-14b`, `gemma4:e4b`). The broader risk is *any* invented model ID being accepted at dispatch time. A future agent could introduce `qwen3.5-27b-v3-ultra` (a plausible-sounding but non-existent model) and it would pass all current checks.  
**Risk:** Silent wrong dispatch — the model server returns an error, but if the error handling is permissive, the agent may proceed with no output.  
**Gap:** Allowlist (only known-good IDs pass) rather than denylist (only known-bad IDs fail) is the correct model for security-critical dispatch.

### S8 — URL scheme contract (JUST FIXED: PR #152)
**Steelman:** `_canonical_endpoint()` ensures scheme on the return path. But `build_openclaw_config` also constructs baseUrls from `LMS_MAC`, `LMS_WIN`, `OLLAMA_MAC`, `OLLAMA_WIN` module-level constants that are set at import time from env vars. If an env var is set to a bare `host:port`, the constant is already bare when `_canonical_endpoint` is called on the return path of the *helper* — but never on the *constant* itself.  
**Risk:** If `OLLAMA_MAC` is `192.168.254.110:11434` (no scheme), it passes through to `baseUrl` without the `_canonical_endpoint` guard because it bypasses the helper entirely in the `else` branch of `build_openclaw_config`.  
**Gap:** Module-level URL constants are not canonicalized at import time.

---

## Implementation plan (5 tiers, ordered by severity)

### Tier 1 — Critical (must ship before freeze)

#### T1-A: Validate routing.json schema before consuming (S4)

**File:** `src/perpetua_tools/alphaclaw_bootstrap.py`

```python
# Add after _load_pt_state definition:
_PT_STATE_SCHEMA = {
    "type": "object",
    "properties": {
        "mac_lmstudio_endpoint": {"type": "string", "pattern": r"^https?://"},
        "lmstudio_endpoint":     {"type": "string", "pattern": r"^https?://"},
        "manager_endpoint":      {"type": "string", "pattern": r"^https?://"},
        "coder_endpoint":        {"type": "string", "pattern": r"^https?://"},
        "coder_model":           {"type": "string", "maxLength": 128},
        "manager_model":         {"type": "string", "maxLength": 128},
        "coder_backend":         {"type": "string",
                                  "enum": ["windows-lmstudio", "windows-ollama",
                                           "mac-lmstudio", "mac-ollama", "mac-degraded",
                                           "unknown"]},
        "mac_lmstudio_ok":       {"type": "boolean"},
        "manager_backend":       {"type": "string"},
    },
    "additionalProperties": True,   # tolerate extra keys from future versions
}

def _validate_pt_state(state: dict) -> dict:
    """Schema-validate routing.json before use. Raises ValueError on violation."""
    from jsonschema import validate, ValidationError
    try:
        validate(state, _PT_STATE_SCHEMA)
    except ValidationError as exc:
        raise ValueError(f"routing.json schema violation: {exc.message}") from exc
    # Allowlist endpoint hostnames — reject non-RFC-1918 targets
    _ALLOWED_HOST_RE = re.compile(
        r'^(localhost|127\.\d+\.\d+\.\d+|::1'
        r'|10\.\d+\.\d+\.\d+'
        r'|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+'
        r'|192\.168\.\d+\.\d+)$'
    )
    for key in ("mac_lmstudio_endpoint", "lmstudio_endpoint",
                "manager_endpoint", "coder_endpoint"):
        url = state.get(key, "")
        if url:
            from urllib.parse import urlparse
            host = urlparse(url if "://" in url else f"http://{url}").hostname or ""
            if host and not _ALLOWED_HOST_RE.match(host):
                raise ValueError(
                    f"routing.json {key}={url!r} resolves to non-RFC-1918 host {host!r}. "
                    "Only localhost and RFC-1918 addresses are permitted."
                )
    return state
```

Update `_load_pt_state` to call `_validate_pt_state` before returning.

**Tests:** 3 new tests — valid state passes, extra keys tolerated, non-RFC-1918 endpoint rejected.

---

#### T1-B: Canonicalize module-level URL constants at import time (S8)

**File:** `src/perpetua_tools/alphaclaw_bootstrap.py`

```python
# After the current RUNNING_ON_* block and before module-level URL assignments,
# apply _canonical_endpoint to every URL constant:

LMS_MAC    = _canonical_endpoint(os.getenv("LM_STUDIO_MAC_ENDPOINT",
    "http://localhost:1234" if RUNNING_ON_MAC else f"http://{MAC_IP}:1234"))
LMS_WIN    = _canonical_endpoint(os.getenv("LM_STUDIO_WIN_ENDPOINTS", "").split(",")[0].strip()
    or ("http://localhost:1234" if RUNNING_ON_WINDOWS else f"http://{WIN_IP}:1234"))
OLLAMA_MAC = _canonical_endpoint(os.getenv("OLLAMA_MAC_ENDPOINT",
    "http://localhost:11434" if RUNNING_ON_MAC else f"http://{MAC_IP}:11434"))
OLLAMA_WIN = _canonical_endpoint(os.getenv("OLLAMA_WINDOWS_ENDPOINT",
    "http://localhost:11434" if RUNNING_ON_WINDOWS else f"http://{WIN_IP}:11434"))
```

**Tests:** 2 new tests — bare env var `192.168.254.110:1234` produces `http://192.168.254.110:1234` at import time.

---

#### T1-C: Policy enforcement audit — all sites must use load_policy() (S3)

**New file:** `scripts/audit_policy_enforcement.py`

```python
"""Verify every policy decision site uses load_policy(), never inline logic."""
import ast, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN_INLINE = {"NEVER_MAC", "NEVER_WIN", "ALWAYS_MAC", "ALWAYS_WIN"}
EXEMPT = {"src/utils/hardware_policy.py"}

violations = []
for py in ROOT.rglob("*.py"):
    rel = str(py.relative_to(ROOT))
    if rel in EXEMPT or ".venv" in rel or "__pycache__" in rel:
        continue
    source = py.read_text(encoding="utf-8", errors="ignore")
    if any(kw in source for kw in FORBIDDEN_INLINE):
        # Ensure it only appears via an import from hardware_policy, not inline
        if "from src.utils.hardware_policy import" not in source and \
           "from utils.hardware_policy import" not in source and \
           "hardware_policy.load_policy" not in source:
            violations.append(f"{rel}: inline policy keyword without hardware_policy import")

if violations:
    print("\n".join(violations), file=sys.stderr); sys.exit(1)
print("OK: all policy enforcement sites use hardware_policy")
```

Add to `.pre-commit-config.yaml` as `policy-enforcement-audit`.

---

### Tier 2 — High (ship before freeze)

#### T2-A: Secret argv scan across ALL skill/plan/doc files (S1)

**Add to `repo_hygiene.py` as LINT-014:**

```python
# LINT-014: argv-form secret passing in skill/plan/doc files
# The pattern "security add-generic-password -w" with a variable
# is the specific anti-pattern fixed in PR #106.
_ARGV_SECRET_RE = re.compile(
    r'security\s+add-generic-password\s+.*-w\s+["\']?\$',
    re.IGNORECASE
)
if not rel.endswith(".py") and _ARGV_SECRET_RE.search(text):
    errors.append(
        f"LINT-014: argv secret passing in {rel} "
        "— use store_keychain_secret.sh (stdin pipe)"
    )
```

---

#### T2-B: Model ID allowlist (positive, not negative) (S7)

**New file:** `scripts/check_model_ids.py`

```python
"""Positive allowlist for model IDs. Only known-good IDs may appear in config."""
ALLOWED_MODEL_IDS = {
    # Mac MLX
    "qwen3.5-9b-mlx",
    # Windows GGUF
    "qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2",
    # Remote / Nous
    "qwen/qwen3-coder:free",
    "stepfun/step-3.7-flash:free",
    # OpenRouter stack
    "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    "openrouter/minimax/minimax-m2.5:free",
    "openrouter/deepseek/deepseek-v4-flash:free",
    "openrouter/openai/gpt-oss-120b:free",
    "openrouter/z-ai/glm-4.5-air:free",
    "openrouter/inclusionai/ling-2.6-flash:free",
}
# Model ID fields in config files must exactly match an entry in ALLOWED_MODEL_IDS.
# Add new IDs here when a model is adopted. Never add partial strings.
```

Scan only `config/models.yml` and `.env.example` for model ID fields. This is more targeted than the current denylist.

---

#### T2-C: LINT-013 exemptions bounded to specific patterns (S5)

Replace file-level `<!-- lint-ignore LINT-013 -->` in pre-existing docs with line-level suppression using a custom comment pattern. The file-level exemption prevents future IP additions from being caught. A line-level pattern is more surgical.

**Change:** Add line-level check: `# lint-ignore-line LINT-013` or `<!-- LINT-013-ok -->` on the same line as a known historical IP. The file-level pragma is deprecated for new files (new files must be clean or use line-level suppression).

This is a hygiene improvement, not a breaking change.

---

### Tier 3 — Medium (ship before freeze)

#### T3-A: TOCTOU — add concurrent stress test (S6)

```python
# tests/test_concurrent_lock.py
def test_concurrent_lock_acquisition_no_corruption(tmp_path):
    """No two processes should simultaneously hold the lock."""
    import threading, time
    lock_path = tmp_path / "test.lock"
    winners = []
    def try_acquire():
        try:
            _acquire_lock(lock_path, {"pid": os.getpid()})
            time.sleep(0.05)   # hold briefly
            winners.append(os.getpid())
            _release_lock(lock_path)
        except LockHeld:
            pass
    threads = [threading.Thread(target=try_acquire) for _ in range(8)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert len(winners) >= 1, "at least one thread must win"
    # Critical: never more than 1 simultaneous holder
    # (This test verifies serialization, not just liveness)
```

---

#### T3-B: commit-message edge-case fuzzing (S2)

```python
# tests/test_check_commit_message.py — add edge cases
MALFORMED_COAUTHOR_CASES = [
    "Co-authored-by: Hermes <<attacker@evil.com>>",   # double-angle
    "Co-authored-by: Claude <noreply@anthropic.com",   # unclosed bracket
    "Co-authored-by: <noreply@anthropic.com>",          # no display name
    "Co-Authored-By: Qwen <ünïcödé@evil.com>",         # non-ASCII in email
    "co-authored-by: hermes",                            # display-name-only — must pass via marker
    "Co-authored-by: Random Person <random@gmail.com>", # must FAIL
]
```

---

#### T3-C: engine.py deferred items (orama-system)

Two deferred items from `cc8c581`:
1. **Orphan conflict cleanup:** when the `ConflictStore` finds an orphan (a conflict whose originating `apply` process is no longer alive), it should archive the conflict to `registry/orphan-conflicts/` rather than silently deleting, so the state is auditable.
2. **Cooperative timeout bypass:** if an `apply` invocation is killed mid-execution (SIGKILL, not SIGTERM), the cooperative budget counter is not decremented. On restart, the counter starts at 0 again, which is correct — but the lock file from the killed process may persist. The TOCTOU fix handles this via `_should_overwrite_existing()`, but the orphan-conflict state is separate and may reference the now-dead apply.

---

### Tier 4 — Low (nice-to-have before freeze)

#### T4-A: Dependency pinning verification

The pre-commit hooks run `ruff v0.4.0` and `pre-commit-hooks v4.6.0`. Before freeze, pin all dependency versions in `pyproject.toml` `[project.optional-dependencies]` or `requirements-dev.txt` and add a CI step that fails if unpinned `>=` specifiers appear.

#### T4-B: LM Studio API token rotation reminder

`LM_STUDIO_API_TOKEN` defaults to `lm-studio` (the public dev default). Add a check to `scripts/check-local-env.sh` that warns if this default is in use, prompting rotation before production use.

#### T4-C: SBOM stub

Before the v2 migration, generate a Software Bill of Materials:
```bash
pip install cyclonedx-bom
cyclonedx-py environment > sbom-v1.1.0.xml
```
Commit to `docs/sbom/` as a snapshot artifact.

---

### Tier 5 — Freeze procedure

```bash
# 1. All T1-T3 items shipped and CI green
# 2. Version bump
#    orama-system: edit src/orama_system/_version.py → "1.1.1"
#                  python3 scripts/sync_version.py
#    Perpetua-Tools: edit pyproject.toml version → "1.0.0"
# 3. Tag
git tag -a v1.1.1 -m "Pre-v2 feature freeze: security hardening complete"
git tag -a v1.0.0 -m "Pre-v2 feature freeze: security hardening complete"
# 4. Push tags
git push origin v1.1.1
git push origin v1.0.0
# 5. GitHub Release
#    Title: "v1.x-stable — Pre-v2 Snapshot"
#    Body: link to this plan + SBOM
# 6. Create v2 migration branch
git checkout -b oramasys/v2-foundation
```

---

## Success metrics

| Item | Gate |
|---|---|
| T1-A routing.json schema | 3 new tests pass; non-RFC-1918 endpoint rejected |
| T1-B module URL constants | Import-time canonicalization verified; `baseUrl` never bare |
| T1-C policy audit script | `python scripts/audit_policy_enforcement.py` exits 0 |
| T2-A LINT-014 | `security add-generic-password -w $` blocked in skill/docs |
| T2-B model allowlist | Only known-good IDs in config; new IDs require explicit addition |
| T3-A concurrent lock test | 8 threads, no corruption |
| T3-B commit-message fuzz | All edge cases pass/fail correctly |
| Freeze | `git tag v1.1.1 && git tag v1.0.0`; CI green on both |

---

## Approval tiers

- **"approve T1"** — execute Tier 1 (critical) only  
- **"approve T1-T3"** — execute T1 through T3  
- **"approve all"** — execute T1-T5 + freeze procedure  

*No execution begins without explicit approval.*
