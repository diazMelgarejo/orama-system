# 02. Idempotent Installs — Execute Bits, capture_output, Model Discovery

**TL;DR:** `npm install -g` does not guarantee execute bits; `PermissionError` is not `CalledProcessError`; never hardcode model names — query the backend at runtime.

---

## Root Cause (2026-04-07)

Three separate issues in bootstrap/install flows:

1. **`capture_output=True` hides all subprocess output** — install appears frozen; user cannot see progress or errors
2. **`npm install -g` missing execute bit** — `shutil.which("openclaw")` finds the binary, but `subprocess.run(["openclaw", ...])` raises `PermissionError: [Errno 13]` because `+x` was not set
3. **Hardcoded model names** — LM Studio returns `400 Bad Request` and Ollama returns `404 Not Found` when the configured model isn't loaded

---

## Fix

### Execute bit
```python
import stat, shutil
from pathlib import Path

path = shutil.which("binary_name")
if path and not (Path(path).stat().st_mode & stat.S_IXUSR):
    Path(path).chmod(Path(path).stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
```

### Exception handling
```python
try:
    subprocess.run(["openclaw", "--version"], check=True)
except subprocess.CalledProcessError as e:
    print(f"openclaw exited with {e.returncode}")
except PermissionError:
    print("Fix: chmod +x $(which openclaw)")
```

### Runtime model discovery
```python
def _resolve_lmstudio_model(host, port, preferred):
    r = httpx.get(f"http://{host}:{port}/v1/models", timeout=5)
    models = r.json().get("data", [])
    ids = [m["id"] for m in models]
    return preferred if preferred in ids else (ids[0] if ids else preferred)

def _resolve_ollama_model(host, port, preferred):
    r = httpx.get(f"http://{host}:{port}/api/tags", timeout=5)
    names = [m["name"] for m in r.json().get("models", [])]
    return preferred if preferred in names else (names[0] if names else preferred)
```

---

## Verification

```bash
# Confirm binary is executable
stat $(which openclaw) | grep Mode

# Confirm model auto-discovery works
curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; print([m['name'] for m in json.load(sys.stdin)['models']])"
```

---

## Rules

1. **Never use `capture_output=True` in bootstrap/install subprocess calls**
2. **After any `npm install -g`, verify and fix execute bits** before running the binary
3. **Catch `PermissionError` separately from `CalledProcessError`** in every subprocess block
4. **Never hardcode model names** — query `/v1/models` or `/api/tags` at runtime; fall back to first available
5. **Keep `AgentTracker.agents.json` on a distinct path** from routing/config state files
6. **All `_load()` methods for typed records must `isinstance(v, dict)`** before `**v` unpacking

---

## Related

- [Session log 2026-04-07](../LESSONS.md#2026-04-07--claude--idempotent-installs-subprocess-permissions--model-auto-discovery)
- Commits: `3c9a4a8` (UTS bootstrap), `23bd01d` (UTS capture_output), `ffb1be0` (PT model discovery), `d9e4f50` (PT tracker)


---

## Addendum (2026-11-15) - Transient PyPI failures: retry EVERY install, not just the one that failed

The agent-audit security-scan job died on `IncompleteRead` (PyPI truncated wheel) - a runner
network blip, not a code defect. Three independent fixes then fragmented across three branches:
an inline 3-attempt loop on one call site (merged), a reusable helper on another branch covering
two call sites, and a superseded test patch. The census that ended the fragmentation found the
real number: **the script had 8 `pip install` call sites and the fixes protected 3**.

**Rule: classify the failure class first (transient infrastructure vs code defect), then census
EVERY exposure point in the file and protect all of them with one shared helper.**

```bash
# Env-tunable so a flaky runner day needs no script edit; delay grows linearly per attempt.
pip_install_retry() {
  local attempts="${PIP_INSTALL_ATTEMPTS:-3}"
  local delay="${PIP_INSTALL_RETRY_DELAY_SEC:-5}"
  local n
  for ((n = 1; n <= attempts; n++)); do
    if python3 -m pip install "$@"; then return 0; fi
    if (( n < attempts )); then
      log "WARN pip install failed (attempt ${n}/${attempts}); retrying in $((delay * n))s"
      sleep "$((delay * n))"
    fi
  done
  return 1
}
```

Keep the owning scan's explicit guarded failure at its critical site
(`if ! pip_install_retry -q -e ...; then echo "... failed after attempts" >&2; return 1; fi`)
and convert every bare `python3 -m pip install` to the helper. Smoke-test the helper with a
stubbed `python3` (fail twice then succeed -> rc 0 after exactly 3 calls; always-fail with
`PIP_INSTALL_ATTEMPTS=2` -> rc 1 after exactly 2 calls) before pushing. Synthesis PR: #516.
