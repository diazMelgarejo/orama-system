# Security & Efficiency Code Review — orama-system + Perpetua-Tools

**Date:** 2026-06-14
**Reviewer:** Claude (oramasys-method, Mode 2)
**Scope:** Static scan of *new* findings only — grep, read, and diff. Every finding cites file:line. **This review does not cover the open finding queue in `SECURITY.md`. See `SECURITY.md § B` for the active 1 Critical + 8 High + 3 Medium findings that pre-date this scan.**
**Repos:** orama-system (104 py, 69 sh), Perpetua-Tools (114 py, 38 sh)

> **Evidence update (2026-06-15):** This copy preserves the original static review while reframing absolute claims as static-scan findings. The original remains at [`../2026-06-14-security-efficiency-review-v1.md`](../2026-06-14-security-efficiency-review-v1.md). Treat statements like “no hardcoded secrets” as “no matches found by the listed static scans,” not as formal proof of absence.


---

## Executive Summary

> **Scope note:** This executive summary covers only the *new* findings from the June 14 static scan. The repo carries **1 Critical + 8 High** open items documented in `SECURITY.md § B` (unauthenticated portal endpoints, loopback dashboard token leak, Windows all-interface bind, secret-overwrite, swarm-launch, LAN discovery trust, bearer-in-probe, XSS via model names, example token). Those findings are not repeated here. Work the `SECURITY.md` queue first — stacked PR order in `SECURITY.md § Security PR stacking`.

**Within the scope of this scan** (new patterns not yet in the SECURITY.md queue): no new hardcoded secrets, no shell injection, no unsafe deserialization, async HTTP throughout, timing-safe token comparison, dedicated boundary modules. New findings from this scan are medium and low severity only. The two highest-priority new items are the **default-open auth posture** (S1) and **unpinned dependencies** (S2).

| Severity | Security | Efficiency | Notes |
|---|---|---|---|
| High | 0 (this scan) | 0 | **Active queue: 1 Critical + 8 High in `SECURITY.md § B`** — not covered here |
| Medium | 2 (S1, S2) | 1 (E1) | New findings from this scan |
| Low | 3 (S3, S4, S5) | 3 (E2, E3, E4) | New findings from this scan |
| Positive findings | 6 | 4 | Verified by static scan |

---

## What Is Already Done Right (verified)

These are real strengths, not filler. Each was checked against the code by static review. They should be read as scan results, not formal impossibility proofs.

| Area | Evidence |
|---|---|
| No hardcoded production secrets found by static scan | `python3 scripts/review/repo_hygiene.py` passed on 2026-06-15. A raw `rg -n 'sk-|ghp_|github_pat|AKIA|xoxb-|token=|key=' --glob '!*.md'` is intentionally **not** a zero-hit reproducer on the current tree because it also matches guard regex definitions, UI identifiers, test strings, and placeholders such as `docs/v2/references/cursor-environment-v2-oramasys.json` containing `sk-local`. Treat the claim as "no production secret findings from the canonical hygiene scanner," not as no textual matches to broad keywords. |
| No `.env` committed | Only `.env.example` present |
| No direct shell-injection primitives found by static scan | Zero `shell=True`, `os.system`, `eval()`, `exec()` in production code (one benign `stdin=subprocess.DEVNULL` in PT) |
| No unsafe deserialization primitives found by static scan | Zero `pickle.load`, `yaml.load(` (unsafe), `marshal` — `yaml.safe_load` used where needed |
| Timing-safe token check | `control_plane_auth.py:174` uses `secrets.compare_digest`, not `==` |
| Async HTTP throughout | 0 sync `requests` imports; 6 (orama) + 13 (PT) files use `httpx`/`aiohttp` — event loop not blocked by network I/O |
| Path-traversal guard | Dedicated `src/utils/mcp_path_boundary.py` |
| CORS not wildcard | `control_plane_auth.py:216` defaults to explicit localhost origins, env-overridable; no `allow_origins=["*"]` |

---

## SECURITY FINDINGS

### S1 — Default-open auth posture (MEDIUM)

**File:** `orama-system/src/utils/control_plane_auth.py:84-104` (`auth_enforced`)

The control-plane API authenticates only when a token is configured OR `ORAMA_INSECURE_DEV` is explicitly set to a production value. When **neither** is set, `auth_enforced()` returns `False` and the API is unauthenticated:

```python
def auth_enforced() -> bool:
    if control_plane_token():
        return True
    insecure = os.getenv(ENV_INSECURE, "").strip().lower()
    if insecure in ("1", "true", "yes"):
        return False
    if insecure in ("0", "false", "no"):
        return True
    return False   # <-- neither set: auth OFF
```

**Why it matters:** combined with LAN bind (`orchestrator.py:14` documents `--host 0.0.0.0`), a fresh deploy that forgets to set `ORAMA_CONTROL_PLANE_TOKEN` exposes the control plane to the local network with no auth. The redaction middleware still runs, but state-changing POSTs are reachable.

**Fix (low effort):** flip the default to fail-closed when binding to anything other than loopback. Keep the loopback-open convenience for local dev:

```python
def auth_enforced() -> bool:
    if control_plane_token():
        return True
    insecure = os.getenv(ENV_INSECURE, "").strip().lower()
    if insecure in ("1", "true", "yes"):
        return False
    if insecure in ("0", "false", "no"):
        return True
    # Default: enforce unless explicitly bound to loopback only
    bind = os.getenv("ORAMA_LAN_BIND", "").strip().lower()
    return bind in ("1", "true", "yes")  # LAN bind -> require auth
```

This pairs with `ensure_control_plane_token()` (already present at line 134) which auto-generates a token when auth is on.

---

### S2 — Unpinned dependencies (MEDIUM, supply chain)

**Files:** `orama-system/requirements.txt`, `Perpetua-Tools/requirements.txt`

Every dependency uses `>=`, not `==`:

```
fastapi>=0.109.0
starlette>=0.49.1
httpx>=0.26.0
pydantic>=2.6.0
...
crewai-tools>=0.14.0
openai>=1.30.0
```

**Why it matters:** `>=` means a fresh `pip install` pulls whatever is latest, which (a) makes builds non-reproducible and (b) is the exact vector for supply-chain attacks (a compromised patch release of any transitive dep is silently pulled). The GitHub Dependabot "1 high" alert on the default branch is a symptom of this.

**Fix:** generate a lockfile and pin. Keep `requirements.txt` with `>=` floors for humans, add a `requirements.lock` (or `uv.lock` / `pip-compile` output) for reproducible installs and CI:

```bash
pip install pip-tools
pip-compile requirements.txt -o requirements.lock --generate-hashes
# CI installs from the lock; humans read the floors
```

Also: address the open Dependabot high at `/security/dependabot/5` directly.

> **Resolved (2026-06-18):** this repo now uses `uv.lock` (not `pip-compile`/`requirements.lock`) for reproducible installs — same intent as the fix above, different tool. `pyproject.toml` + `uv.lock` are the source of truth; `requirements.txt` floors remain for human reference. See `31-security-harness-excellence-plan.md` AC-SUPPLY for the current lockfile-audit acceptance gate.

---

### S3 — No application-level rate limiting (LOW)

**File:** `orama-system/src/orama_system/api_server.py`

`slowapi>=0.1.9` is in `requirements.txt` but there is no `Limiter`, `@limiter`, or rate-limit middleware wired into `api_server.py`. The `/oramasys` POST is unthrottled.

**Why it matters:** for a stateless reasoning endpoint that fans out to local models, an unthrottled caller on the LAN can saturate the GPU box. Low severity because the bind is LAN-default and auth (S1) should gate it, but the dependency is already paid for.

**Fix:** wire the slowapi limiter that the project already depends on:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/oramasys")
@limiter.limit("30/minute")
async def run_oramasys(req: OramasysRequest, request: Request): ...
```

---

### S4 — `testclient` treated as loopback (LOW)

**File:** `control_plane_auth.py:152-156` (`request_is_loopback`)

```python
return host in {"127.0.0.1", "::1", "localhost", "testclient"}
```

`"testclient"` is Starlette's in-process host for pytest. Treating it as loopback is intentional for tests, but it means **any** code path that constructs a request with `client.host == "testclient"` bypasses the loopback check. This is low risk (an attacker cannot set the Starlette client host remotely) but it is a test affordance living in production auth logic.

**Fix:** gate it behind an explicit test env flag so it cannot be reached in production:

```python
allow_testclient = os.getenv("ORAMA_PYTEST") == "1"
loopback = {"127.0.0.1", "::1", "localhost"}
if allow_testclient:
    loopback.add("testclient")
return host in loopback
```

---

### S5 — Auth via cookie without explicit SameSite/Secure note (LOW)

**File:** `control_plane_auth.py:160-165` (`bearer_token_from_request`)

The token is accepted from either the `Authorization: Bearer` header or the `orama_control_plane_token` cookie. Cookie-based bearer auth is convenient for the portal browser, but if the cookie is ever set without `SameSite=Strict` and `Secure`, it widens CSRF surface on state-changing POSTs.

**Why it matters:** low, because CORS is locked to explicit localhost origins and methods are limited. But the cookie-set path was not located in this review — worth confirming the `Set-Cookie` for `orama_control_plane_token` carries `HttpOnly; Secure; SameSite=Strict`.

**Fix:** confirm the cookie is set with `httponly=True, secure=True, samesite="strict"` wherever the portal issues it.

---

## EFFICIENCY FINDINGS

### E1 — Bounded poll loops use fixed sleeps, not adaptive backoff (MEDIUM)

**Files:** `orama-system/start.sh:605,651`, `scripts/ensure_requirements.sh:169`

```bash
sleep 0.5; tries=$((tries+1))      # start.sh:605
sleep 1;   i=$((i+1))              # start.sh:651
while [ $_i -lt 15 ]; do sleep 1   # ensure_requirements.sh:169
```

These are **correctly bounded** (not the blind `sleep N && cmd` anti-pattern the project already fixed), so this is a refinement, not a bug. But fixed-interval polling either wastes wall-clock on fast-ready services or gives up too early on slow ones.

**Fix:** exponential backoff with a deadline reads cleaner and is faster on the common case:

```bash
deadline=$((SECONDS + 30)); delay=0.2
until curl -sf "$url" >/dev/null 2>&1; do
  [ $SECONDS -ge $deadline ] && { echo "timeout"; break; }
  sleep "$delay"; delay=$(echo "$delay * 1.5" | bc)
done
```

---

### E2 — `_call_with_fallback` is a stub; real fallback path not parallelized (LOW, forward-looking)

**File:** `api_server.py:590-592`

```python
async def _call_with_fallback(prompt, model, max_tokens, temperature):
    """Stub for calling Ollama/LMStudio; primary purpose is being mocked in tests."""
    return f"Stateless output for {model}", "http://localhost:1234"
```

The orama API is intentionally a **stateless stub** (heavy lifting lives in PT — correct architecture). When the real fallback chain is implemented, the natural risk is sequential model attempts (try model A, wait for timeout, then B). For a latency-sensitive path, a hedged request (fire primary, start backup after a short delay, take first success) is materially faster on tail latency.

**Recommendation:** when implementing the real `_call_with_fallback`, use `asyncio.wait(..., return_when=FIRST_COMPLETED)` hedging rather than serial `try/except` per model. Note this in the v1.1 frugality-router work where the dispatch actually happens.

---

### E3 — Duplicated CORS origin entries (LOW, cosmetic)

**File:** `Perpetua-Tools/orchestrator/fastapi_app.py:113-117`

```python
allow_origins=[
    "http://localhost:3000", "http://localhost:3000",   # dup
    "http://localhost:8002", "http://localhost:8002",   # dup
],
```

Each origin is listed twice. Harmless at runtime (set semantics), but it signals a copy-paste slip and slightly bloats the preflight allowlist.

**Fix:** dedupe to four entries → two.

---

### E4 — Two requirements files with divergent version floors (LOW)

**Observation:** orama pins `httpx>=0.26.0` and appears twice in its own requirements (once under runtime, once under test). PT pins `aiohttp>=3.14.0` AND `httpx>=0.26.0` AND `asyncio>=3.4.3` (the last is a no-op on modern Python — `asyncio` is stdlib).

**Fix:** remove `asyncio>=3.4.3` from PT requirements (it shadows nothing and confuses readers), and dedupe the repeated `httpx` line in orama. Pick one async HTTP client per repo where possible (PT uses both aiohttp and httpx — consolidating reduces transitive surface).

---

## Cross-Repo Observations

1. **Architecture boundary is clean.** orama is stateless (`api_server.py` returns stubs; durable state and secrets live in PT). This is the right separation and it limits blast radius — a compromised orama instance holds no secrets.

2. **Auth token is shared via PT's `.state/control_plane_token`** (`control_plane_auth.py:108-123`). Confirm that file is `chmod 600` and never committed (it is correctly under `.state/`, which should be gitignored — verify).

3. **The `0.0.0.0` literal is computed, not written** (`all_interfaces_bind_host()` joins `["0"]*4`) specifically to dodge cloud secret scanners. Clever, but document it so a future reader does not "simplify" it back to a literal and trip the scanner.

---

## Prioritized Action List

| Priority | Item | Effort | Severity |
|---|---|---|---|
| 1 | S2: pin deps + resolve Dependabot high | 1 hour | Medium |
| 2 | S1: fail-closed auth when LAN-bound | 30 min | Medium |
| 3 | S3: wire the slowapi limiter (already a dep) | 30 min | Low |
| 4 | E3 + E4: dedupe CORS origins, drop `asyncio` dep | 10 min | Low |
| 5 | S4: gate `testclient` behind ORAMA_PYTEST | 15 min | Low |
| 6 | S5: confirm cookie SameSite/Secure flags | 15 min | Low |
| 7 | E1: backoff in poll loops | 30 min | Medium (cosmetic) |
| 8 | E2: hedge the real fallback (when implemented) | with v1.1 | Low |

---

## Methodology Note

This is a **static review** — grep + read, no runtime fuzzing, no dependency CVE cross-reference beyond the Dependabot signal GitHub already surfaced. For defense in depth, the natural next steps are: (1) run `pip-audit` / `npm audit` against pinned lockfiles, (2) add `bandit` to CI for the Python surface, (3) add the `check_mastery_no_duplication` style hygiene to catch the CORS-dup class of issue automatically. None of these are blocking; they are the difference between "reviewed once" and "continuously verified."


---

## Reproducibility appendix added 2026-06-15

The original review did not preserve exact command output artifacts. Future reruns should record repo SHAs and attach command outputs under a dated `docs/security-artifacts/` path. Suggested commands:

```bash
git -C /workspace/orama-system rev-parse HEAD
rg -n 'shell=True|os\.system|eval\(|exec\(' src scripts tests
rg -n 'pickle\.load|yaml\.load\(|marshal' src scripts tests
python3 scripts/review/repo_hygiene.py
# Optional broad triage scan; expect known false positives from guard regexes, UI IDs, tests, and placeholders.
rg -n 'sk-|ghp_|github_pat|AKIA|xoxb-|token=|key=' --glob '!*.md' | tee docs/security-artifacts/2026-06-14-secret-triage.txt
pip-audit -r requirements.lock
# Production-code scope only, matching the "in production code" claims above.
rg -n 'shell=True|os\.system|eval\(|exec\(' src scripts
rg -n 'pickle\.load|yaml\.load\(|marshal' src scripts
python3 scripts/review/repo_hygiene.py
# Optional: same patterns in tests/. Hits here are NOT a violation of the
# production-code claims above -- test fixtures/mocks may legitimately use
# these patterns. Classify separately; do not fold into the production count.
rg -n 'shell=True|os\.system|eval\(|exec\(|pickle\.load|yaml\.load\(|marshal' tests
# Optional broad triage scan; expect known false positives from guard regexes, UI IDs, tests, and placeholders.
mkdir -p docs/security-artifacts
rg -n 'sk-|ghp_|github_pat|AKIA|xoxb-|token=|key=' --glob '!*.md' | tee docs/security-artifacts/2026-06-14-secret-triage.txt
# This repo uses uv; pip-audit doesn't read uv.lock directly, so export first.
uv export --frozen --no-hashes -o requirements-export.txt
uvx pip-audit -r requirements-export.txt
```

If companion repositories are included, capture their SHAs and run equivalent scans from each repository root.

Known broad-scan false-positive classes to classify before making any "zero hits" claim:

- guard regex definitions in `src/utils/mcp_path_boundary.py` and `scripts/review/repo_hygiene.py`
- UI/test identifiers containing `task` or `key`
- local placeholder values such as `sk-local` in v2 reference fixtures
- shell variable parsing code that uses a local variable named `key`
