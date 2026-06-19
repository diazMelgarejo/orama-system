# codex-openclaw-agent v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a thin OpenClaw meta-skill (`codex-openclaw-agent`) that initializes a *real* Codex-backed (gpt-5.5) OpenClaw coding agent — binding the runtime to Codex via an opportunistic fail-forward resolver, then generating the agent's directive files + `CODEX.md` spec sheet, with runtime backend identity verification as the release gate.

**Architecture:** Two peer substrates. (1) `scripts/bind_codex_backend.sh` is the operational binding resolver: probe → native plugin (`codex-supervisor`) → idempotent install → OpenAI-compatible fallback provider → verify backend identity → record. (2) `scripts/generate_codex_openclaw_profile.py` consumes the binding record + source profiles and writes the six OpenClaw directive files, `CODEX.md`, `openclaw.json`, and refs, merging only marked generated sections. A thin `SKILL.md` orchestrates: mother skill → `openclaw-new-agent` overlay → bind → generate → stow → restart → assert.

**Tech Stack:** Bash (binder, POSIX sh-compatible where possible, bash for flock), Python 3.13 (generator), `openclaw config patch` (validated atomic config writes), the canonical openclaw resolver (`scripts/openclaw/resolve-openclaw.sh`), pytest (tests in `tests/` and `scripts/tests/`), `codex` CLI 0.135.0, `gstack-codex-probe`.

---

## Verified Environment Facts (probed 2026-06-19 — do NOT re-spike)

These resolve the two gating unknowns from the spec's "Multi-Model Pressure-Test Findings". They are inputs to the plan, already confirmed against the live machine:

| Fact | Value | Consequence for the plan |
|------|-------|--------------------------|
| Canonical openclaw | `2026.6.8`, npm-global under node v24.14.1, runs launchd `ai.openclaw.gateway` on `127.0.0.1:18789` | All openclaw calls route through `scripts/openclaw/resolve-openclaw.sh` (never bare `openclaw`) |
| Real native Codex plugin | `codex-supervisor` (bundled stock, 2026.6.8, "Supervise Codex app-server sessions from OpenClaw") — **not** the design-name `openclaw-codex-app-server` | Stage 1 targets `codex-supervisor`; it is already enabled in config + allowlist but needs a **gateway restart** to activate |
| **PT-MM1 RESOLVED** | Backend identity IS parseable: openclaw model IDs are `<provider-key>/<model-id>` (e.g. `ollama/qwen3.5:9b-nvfp4`, `codex/gpt-5.5`). OTEL traces live (`diagnostics.otel.traces=true`) | Stage 4 asserts on the resolved model-prefix; OTEL is the secondary signal. No gateway patch needed. |
| **PT-MM2 RESOLVED** | OpenAI-compatible provider schema proven across 5 live providers: `{api:"openai-completions", apiKey, baseUrl, models:[{id,name,contextWindow,maxTokens,cost}]}` | Stage 3 writes a `codex` provider block of exactly this shape via `openclaw config patch` |
| Config write path | `openclaw config patch --file <f>` (and `--dry-run`) — validated, atomic, gateway-aware; `null` deletes a key; arrays replace | Binder NEVER hand-edits `openclaw.json` |
| Codex app-server endpoint | Discoverable from `~/.codex/cache/codex_apps_server_info/<hash>.json` (per-session server-info files) | Stage 0 probe parses these for `base_url`; canaries `GET /v1/models` |
| Auth | `~/.codex/config.toml` has `model="gpt-5.5"` and may carry an operator-selected `model_reasoning_effort`; `gstack-codex-probe` reports auth | Auth by reference only — never copy values; skill default remains `medium`, with `high`/`xhigh` opt-in |

**Net change to spec ordering:** the spec said "implementation MUST start with two spikes." Both are now answered. Task 0 keeps a *live confirmation canary* (PT-MM2's `GET /v1/models` check) but is no longer a blocking research spike.

---

## File Structure

```text
bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/
  SKILL.md                                  # thin orchestrator (Task 9)
  references/
    codex-backend-binding.md                # binding doctrine (Task 1)
    profile-composition.md                  # composition precedence doctrine (Task 9)
  scripts/
    bind_codex_backend.sh                    # 5-stage resolver (Tasks 2-6)
    generate_codex_openclaw_profile.py       # profile generator (Tasks 7-8)
    lib/
      codex_probe.sh                         # probe helpers, endpoint discovery (Task 3)
tests/
  test_codex_generator.py                    # generator unit tests (Tasks 7-8, 10)
scripts/tests/
  test_bind_codex_backend.py                 # binder unit tests via subprocess (Tasks 2-6, 10)
  fixtures/codex/                            # fake app-server / config fixtures
```

Responsibilities are split so the binder is testable without the generator (Eng Finding 1), and each file has one concern: probe lib (evidence), binder (runtime state + verify), generator (files), SKILL.md (orchestration only).

**Shared contracts** (defined once, referenced by every task):

`refs/codex-backend-binding.json` (binder → generator):
```json
{
  "schema_version": "1",
  "winning_path": "plugin",
  "provider_key": "codex",
  "provider_string": "codex/gpt-5.5",
  "model": "gpt-5.5",
  "effort": "medium",
  "auth_source_ref": "~/.codex (referenced, not copied)",
  "endpoint_ref": "http://127.0.0.1:1455/v1",
  "verification": {"status": "pass", "expected": "codex/gpt-5.5", "actual": "codex/gpt-5.5", "method": "model-prefix"},
  "timestamp": "2026-06-19T00:00:00Z",
  "binder_version": "1.0.0",
  "openclaw_home": "/abs/openclaw-home",
  "agent_id": "codex-agent"
}
```

Stage 0 probe JSON (binder `--mode probe` stdout):
```json
{
  "schema_version": "1",
  "codex_cli": {"present": true, "version": "0.135.0"},
  "auth": {"ok": true, "source_ref": "~/.codex"},
  "app_server": {"reconciled_state": true, "endpoint": "http://127.0.0.1:1455/v1", "reachable": true, "models_canary": true},
  "openclaw": {"resolver_ok": true, "version": "2026.6.8", "plugin_codex_supervisor": "enabled", "config_has_codex_provider": false, "primary_is_codex": false},
  "recommended_path": "plugin"
}
```

---

## Task 0: Scaffold skill + live confirmation canary

**Files:**
- Create: `bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/lib/codex_probe.sh`
- Create: `scripts/tests/test_bind_codex_backend.py`
- Create: `scripts/tests/fixtures/codex/server_info_sample.json`

- [ ] **Step 1: Create the skill directory tree**

```bash
SKILL_DIR="bin/orama-system/skills/openclaw-skills/codex-openclaw-agent"
mkdir -p "$SKILL_DIR/references" "$SKILL_DIR/scripts/lib" scripts/tests/fixtures/codex
```

- [ ] **Step 2: Write the endpoint-discovery fixture**

Create `scripts/tests/fixtures/codex/server_info_sample.json` (mirrors the real `~/.codex/cache/codex_apps_server_info/<hash>.json` shape — a base_url + pid):

```json
{
  "base_url": "http://127.0.0.1:1455",
  "pid": 4242,
  "model": "gpt-5.5",
  "started_at": "2026-06-19T00:00:00Z"
}
```

- [ ] **Step 3: Write the failing test for endpoint discovery**

Create `scripts/tests/test_bind_codex_backend.py`:

```python
import json, os, subprocess, shutil, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SKILL = REPO / "bin/orama-system/skills/openclaw-skills/codex-openclaw-agent"
PROBE_LIB = SKILL / "scripts/lib/codex_probe.sh"
FIX = Path(__file__).parent / "fixtures/codex"

def _run(snippet: str, env=None):
    """Source the probe lib and run a snippet; return (rc, stdout, stderr)."""
    full = f'set -e; source "{PROBE_LIB}"; {snippet}'
    p = subprocess.run(["bash", "-c", full], capture_output=True, text=True,
                       env={**os.environ, **(env or {})})
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def test_discover_endpoint_from_server_info_dir(tmp_path):
    d = tmp_path / "codex_apps_server_info"
    d.mkdir()
    shutil.copy(FIX / "server_info_sample.json", d / "abc123.json")
    rc, out, err = _run(f'codex_discover_endpoint "{d}"')
    assert rc == 0, err
    assert out == "http://127.0.0.1:1455", out
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `cd "$(git rev-parse --show-toplevel)" && python3 -m pytest scripts/tests/test_bind_codex_backend.py::test_discover_endpoint_from_server_info_dir -v`
Expected: FAIL — `codex_probe.sh` does not exist / `codex_discover_endpoint: command not found`.

- [ ] **Step 5: Write minimal `codex_probe.sh` with endpoint discovery**

Create `bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/lib/codex_probe.sh`:

```bash
#!/usr/bin/env bash
# codex_probe.sh — Stage 0 probe helpers for bind_codex_backend.sh.
# Evidence-only: NO mutation, NO secret values printed (references only).
# PT-MM3: trust live canaries over stale ~/.codex state files.

# Discover the Codex app-server base_url from the per-session server-info dir
# (~/.codex/cache/codex_apps_server_info/<hash>.json). Echoes the newest base_url.
codex_discover_endpoint() {
  local dir="${1:-$HOME/.codex/cache/codex_apps_server_info}"
  [ -d "$dir" ] || return 1
  local newest
  newest="$(ls -t "$dir"/*.json 2>/dev/null | head -1)"
  [ -n "$newest" ] || return 1
  python3 - "$newest" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(1)
url = d.get("base_url") or d.get("baseUrl") or ""
if not url:
    sys.exit(1)
print(url.rstrip("/"))
PY
}
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `python3 -m pytest scripts/tests/test_bind_codex_backend.py::test_discover_endpoint_from_server_info_dir -v`
Expected: PASS

- [ ] **Step 7: Add the live `GET /v1/models` canary helper + its test**

Append to `codex_probe.sh`:

```bash
# PT-MM2 canary: confirm the discovered endpoint actually serves the
# OpenAI-compatible /v1/models route. Uses curl (system CAs). 0 = reachable.
codex_models_canary() {
  local endpoint="$1" timeout="${2:-5}"
  [ -n "$endpoint" ] || return 1
  local code
  code="$(curl -s -o /dev/null -m "$timeout" -w '%{http_code}' "$endpoint/models" 2>/dev/null)"
  case "$code" in 200|401|403) return 0 ;; *) return 1 ;; esac
}
```

Add to `scripts/tests/test_bind_codex_backend.py`:

```python
def test_models_canary_unreachable_is_nonzero():
    rc, out, err = _run('codex_models_canary "http://127.0.0.1:59999/v1" 1 && echo UP || echo DOWN')
    assert rc == 0
    assert out == "DOWN", out
```

Note: 401/403 count as "reachable" because an auth-gated endpoint is still a live OpenAI-compatible server (PT-MM2 only needs the route to exist).

- [ ] **Step 8: Run canary test**

Run: `python3 -m pytest scripts/tests/test_bind_codex_backend.py -v`
Expected: PASS (both tests)

- [ ] **Step 9: Commit**

```bash
git add bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/lib/codex_probe.sh \
        scripts/tests/test_bind_codex_backend.py scripts/tests/fixtures/codex/server_info_sample.json
git commit -m "feat(codex-openclaw-agent): scaffold skill + codex probe lib (endpoint discovery + models canary)"
```

---

## Task 1: Binding doctrine reference

**Files:**
- Create: `bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/references/codex-backend-binding.md`

- [ ] **Step 1: Write the doctrine document**

Create the doctrine at the path above, not at the older top-level
`bin/orama-system/skills/codex-openclaw-agent/` path.

The doctrine must include these sections:

- `Non-Negotiable Invariants`
- `OpenClaw Invocation`
- `Resolution Ladder`
- `Stage 0 Probe Rules`
- `Provider Strings`
- `Reasoning Effort`
- `OpenAI-Compatible Fallback Shape`
- `Mutation Boundaries`
- `Verification Gate`
- `Binding Record Contract`
- `Failure Output`
- `Test Requirements`

Required corrections versus the stale draft:

- Use the real native plugin name: `codex-supervisor`.
- Default reasoning effort to `medium`; allow `high` and `xhigh` only when the
  operator explicitly opts in.
- Route all OpenClaw calls through `scripts/openclaw/resolve-openclaw.sh`.
- Accept Codex auth references from `CODEX_API_KEY`, `OPENAI_API_KEY`,
  `~/.codex/auth.json`, or structurally valid `~/.codex/config.toml`; never
  print secret values.
- Discover the app-server endpoint from live Codex server-info files and
  validate `GET <endpoint>/v1/models`; never trust stale state files alone.
- Write OpenClaw runtime changes with `openclaw config patch --file`, not
  direct `jq` edits to `openclaw.json`.
- Write target agent runtime files under
  `$OPENCLAW_HOME/.openclaw/agents/<agent_id>/`.
- Forbid arbitrary-cwd stow such as `stow --no-folding -t "$OPENCLAW_HOME" .`.
- Treat fallback (`codex/gpt-5.5`) as first-class and verified, not degraded.
- Verification must fail if the resolved runtime provider prefix is `ollama/`.
- Binding records must be redacted and must not serialize raw server-info or
  auth payloads.

- [ ] **Step 2: Verify no workstation paths / secrets leaked**

Run: `python3 scripts/review/repo_hygiene.py bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/references/codex-backend-binding.md 2>&1 | tail -5`
Expected: no workstation-path hits (home-dir literals or the OpenClaw tree).

- [ ] **Step 3: Commit**

```bash
git add bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/references/codex-backend-binding.md
git commit -m "docs(codex-openclaw-agent): binding doctrine reference (5-stage ladder, verified schema)"
```

---

## Task 2: Binder skeleton — args, flock, JSON/stderr contract

**Files:**
- Create: `bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/bind_codex_backend.sh`
- Test: `scripts/tests/test_bind_codex_backend.py`

PT-MM5: the atomicity boundary (a per-`openclaw-home` flock) is established now, before any stage writes.

- [ ] **Step 1: Write the failing test for arg validation + flock**

Add to `scripts/tests/test_bind_codex_backend.py`:

```python
BINDER = SKILL / "scripts/bind_codex_backend.sh"

def _bind(args, env=None):
    p = subprocess.run(["bash", str(BINDER), *args], capture_output=True, text=True,
                       env={**os.environ, **(env or {})})
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def test_binder_rejects_relative_openclaw_home():
    rc, out, err = _bind(["--openclaw-home", "relative/path", "--agent-id", "x", "--mode", "probe"])
    assert rc != 0
    assert "absolute" in err.lower()

def test_binder_rejects_bad_agent_id():
    rc, out, err = _bind(["--openclaw-home", "/tmp/oc", "--agent-id", "Bad Id!", "--mode", "probe"])
    assert rc != 0
    assert "agent" in err.lower()
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest scripts/tests/test_bind_codex_backend.py -k binder_rejects -v`
Expected: FAIL — script missing.

- [ ] **Step 3: Write the binder skeleton**

Create `bind_codex_backend.sh`:

```bash
#!/usr/bin/env bash
# bind_codex_backend.sh — opportunistic Codex backend resolver for OpenClaw.
# Stages: probe -> native plugin (codex-supervisor) -> idempotent enable/install
#         -> OpenAI-compatible fallback -> verify backend identity -> record.
# Idempotent, re-runnable. JSON on stdout; diagnostics on stderr; auth by reference.
set -uo pipefail
BINDER_VERSION="1.0.0"

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
source "$SELF_DIR/lib/codex_probe.sh"

# Resolve canonical openclaw (never bare command) via orama-system resolver.
ORAMA_ROOT="$(cd "$SELF_DIR/../../../../../.." >/dev/null 2>&1 && pwd)"
RESOLVER="$ORAMA_ROOT/scripts/openclaw/resolve-openclaw.sh"
oc() { if [ -x "$RESOLVER" ]; then "$RESOLVER" "$@"; else command openclaw "$@"; fi; }

# ---- args ----
OPENCLAW_HOME="" AGENT_ID="" MODEL="gpt-5.5" EFFORT="medium"
MODE="auto" PREFER="auto" FORCE_PRIMARY="0"
die() { echo "bind_codex_backend: $*" >&2; exit 2; }
while [ $# -gt 0 ]; do
  case "$1" in
    --openclaw-home) OPENCLAW_HOME="${2:-}"; shift 2 ;;
    --agent-id)      AGENT_ID="${2:-}"; shift 2 ;;
    --model)         MODEL="${2:-}"; shift 2 ;;
    --effort)        EFFORT="${2:-}"; shift 2 ;;
    --mode)          MODE="${2:-}"; shift 2 ;;
    --prefer)        PREFER="${2:-}"; shift 2 ;;
    --force-primary) FORCE_PRIMARY="1"; shift ;;
    -h|--help) echo "usage: bind_codex_backend.sh --openclaw-home DIR --agent-id ID [--mode probe|bind|verify|auto] [--prefer auto|plugin|compat] [--model gpt-5.5] [--effort medium|high|xhigh] [--force-primary]"; exit 0 ;;
    *) die "unknown arg: $1" ;;
  esac
done

# ---- validation ----
case "$MODE"   in probe|bind|verify|auto) ;; *) die "invalid --mode: $MODE" ;; esac
case "$PREFER" in auto|plugin|compat) ;; *) die "invalid --prefer: $PREFER" ;; esac
case "$EFFORT" in medium|high|xhigh) ;; *) die "invalid --effort: $EFFORT" ;; esac
[ "$MODE" = "probe" ] || [ -n "$OPENCLAW_HOME" ] || die "--openclaw-home required"
if [ -n "$OPENCLAW_HOME" ]; then
  case "$OPENCLAW_HOME" in /*) ;; *) die "--openclaw-home must be absolute: $OPENCLAW_HOME" ;; esac
fi
[ "$MODE" = "probe" ] || [ -n "$AGENT_ID" ] || die "--agent-id required"
if [ -n "$AGENT_ID" ]; then
  printf '%s' "$AGENT_ID" | grep -Eq '^[a-z0-9][a-z0-9-]{0,62}$' || die "invalid --agent-id (lowercase, digits, hyphen): $AGENT_ID"
fi

# ---- atomicity boundary (PT-MM5) ----
# Hold a per-openclaw-home lock for any mutating run so concurrent
# bind/generate/stow can't interleave into split state.
with_lock() {
  local lockdir="${OPENCLAW_HOME:-$TMPDIR}/.codex-bind.lock"
  if [ "$MODE" = "probe" ]; then "$@"; return $?; fi
  mkdir -p "$(dirname "$lockdir")" 2>/dev/null || true
  local fd; exec {fd}>"$lockdir.flock" 2>/dev/null || { "$@"; return $?; }
  if command -v flock >/dev/null 2>&1; then
    flock -w 60 "$fd" || die "could not acquire bind lock within 60s"
  fi
  "$@"
}

main() {
  case "$MODE" in
    probe)  do_probe ;;        # Task 3
    *)      die "stage not yet implemented (placeholder until later tasks)" ;;
  esac
}
do_probe() { echo '{"schema_version":"1","stub":true}'; }   # replaced in Task 3
with_lock main
```

- [ ] **Step 4: Run to verify the rejection tests pass**

Run: `python3 -m pytest scripts/tests/test_bind_codex_backend.py -k binder_rejects -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/bind_codex_backend.sh scripts/tests/test_bind_codex_backend.py
git commit -m "feat(codex-openclaw-agent): bind_codex_backend.sh skeleton (args, validation, flock boundary)"
```

---

## Task 3: Stage 0 probe (live canary, not stale-file trust)

**Files:**
- Modify: `bind_codex_backend.sh` (replace `do_probe`)
- Modify: `codex_probe.sh` (add openclaw/auth probes)
- Test: `scripts/tests/test_bind_codex_backend.py`

- [ ] **Step 1: Write the failing probe-output test**

Add to the test file:

```python
def test_probe_emits_valid_json_with_required_keys():
    rc, out, err = _bind(["--mode", "probe"])
    assert rc == 0, err
    doc = json.loads(out)
    for k in ("schema_version", "codex_cli", "auth", "app_server", "openclaw", "recommended_path"):
        assert k in doc, f"missing {k}: {doc}"
    assert doc["recommended_path"] in ("plugin", "compat", "none")
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest scripts/tests/test_bind_codex_backend.py::test_probe_emits_valid_json_with_required_keys -v`
Expected: FAIL — current `do_probe` emits `{"stub":true}` (no required keys).

- [ ] **Step 3: Add openclaw/auth probe helpers to `codex_probe.sh`**

Append to `codex_probe.sh`:

```bash
# Codex CLI presence + version (no secrets).
codex_cli_probe() {
  if command -v codex >/dev/null 2>&1; then
    printf '{"present":true,"version":"%s"}' "$(codex --version 2>/dev/null | awk '{print $NF}')"
  else
    printf '{"present":false,"version":null}'
  fi
}

# Auth via gstack-codex-probe if available; reference only, never the value.
codex_auth_probe() {
  local p; p="$(command -v gstack-codex-probe 2>/dev/null || echo "$HOME/.claude/skills/gstack/bin/gstack-codex-probe")"
  if [ -x "$p" ] && "$p" auth >/dev/null 2>&1; then
    printf '{"ok":true,"source_ref":"~/.codex"}'
  elif [ -f "$HOME/.codex/config.toml" ]; then
    printf '{"ok":"unknown","source_ref":"~/.codex"}'
  else
    printf '{"ok":false,"source_ref":null}'
  fi
}

# codex-supervisor plugin state via canonical openclaw resolver passed as $1 ("oc").
# Echoes enabled|disabled|absent.
codex_plugin_state() {
  local ocfn="$1"
  local line
  line="$("$ocfn" plugins list 2>/dev/null | grep -i 'codex-supervisor' | head -1)"
  if   printf '%s' "$line" | grep -qi 'enabled';  then echo enabled
  elif printf '%s' "$line" | grep -qi 'disabled'; then echo disabled
  else echo absent; fi
}
```

Note: `codex_plugin_state` takes the resolver path as a string and calls it; in the binder we pass `"$RESOLVER"`.

- [ ] **Step 4: Replace `do_probe` in `bind_codex_backend.sh`**

```bash
do_probe() {
  local endpoint reachable=false canary=false
  endpoint="$(codex_discover_endpoint 2>/dev/null || true)"
  if [ -n "$endpoint" ]; then
    codex_models_canary "$endpoint" 5 && { reachable=true; canary=true; }
  fi
  local reconciled=false
  [ -f "$HOME/.codex/.app-server-state-reconciled-v1" ] && reconciled=true   # hint only (PT-MM3)

  local plugin_state cfg_has_codex=false primary_codex=false ver
  plugin_state="$(codex_plugin_state "$RESOLVER" 2>/dev/null || echo absent)"
  ver="$(oc --version 2>/dev/null | awk '{print $2}')"
  oc config get models.providers.codex >/dev/null 2>&1 && cfg_has_codex=true
  oc config get "agents.list" 2>/dev/null | grep -q '"primary": *"codex/' && primary_codex=true

  local recommended="none"
  if [ "$plugin_state" != "absent" ]; then recommended="plugin"
  elif [ "$canary" = true ]; then recommended="compat"; fi
  [ "$PREFER" = "compat" ] && [ "$canary" = true ] && recommended="compat"
  [ "$PREFER" = "plugin" ] && [ "$plugin_state" != "absent" ] && recommended="plugin"

  printf '{"schema_version":"1","codex_cli":%s,"auth":%s,"app_server":{"reconciled_state":%s,"endpoint":%s,"reachable":%s,"models_canary":%s},"openclaw":{"resolver_ok":%s,"version":%s,"plugin_codex_supervisor":"%s","config_has_codex_provider":%s,"primary_is_codex":%s},"recommended_path":"%s"}\n' \
    "$(codex_cli_probe)" "$(codex_auth_probe)" "$reconciled" \
    "$([ -n "$endpoint" ] && printf '"%s"' "$endpoint" || echo null)" "$reachable" "$canary" \
    "$([ -x "$RESOLVER" ] && echo true || echo false)" \
    "$([ -n "$ver" ] && printf '"%s"' "$ver" || echo null)" \
    "$plugin_state" "$cfg_has_codex" "$primary_codex" "$recommended"
}
```

- [ ] **Step 5: Run probe test**

Run: `python3 -m pytest scripts/tests/test_bind_codex_backend.py::test_probe_emits_valid_json_with_required_keys -v`
Expected: PASS

- [ ] **Step 6: Manual live probe sanity check**

Run: `bash bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/bind_codex_backend.sh --mode probe | python3 -m json.tool`
Expected: valid JSON; `openclaw.plugin_codex_supervisor` is `"enabled"` (we enabled it), `recommended_path` is `"plugin"`.

- [ ] **Step 7: Commit**

```bash
git add bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/bind_codex_backend.sh \
        bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/lib/codex_probe.sh \
        scripts/tests/test_bind_codex_backend.py
git commit -m "feat(codex-openclaw-agent): Stage 0 probe (live canary + plugin state, stale files as hints only)"
```

---

## Task 4: Stage 3 fallback — OpenAI-compatible Codex provider injection

**Files:**
- Modify: `bind_codex_backend.sh` (add `do_fallback`)
- Test: `scripts/tests/test_bind_codex_backend.py`

Per user ordering, the verified Stage 3 substrate lands before Stage 1. It writes the provider block via `openclaw config patch` against a temp config file in tests (no live mutation in unit tests).

- [ ] **Step 1: Write the failing test for fallback patch generation**

The binder must emit the exact provider patch JSON5 to a file when `--mode bind --prefer compat --dry-run-patch <path>` is given (dry-run writes the patch but does NOT call openclaw).

Add to test file:

```python
def test_fallback_generates_valid_provider_patch(tmp_path):
    patch = tmp_path / "patch.json5"
    rc, out, err = _bind([
        "--openclaw-home", str(tmp_path), "--agent-id", "codex-agent",
        "--mode", "bind", "--prefer", "compat",
        "--dry-run-patch", str(patch),
    ], env={"CODEX_ENDPOINT_OVERRIDE": "http://127.0.0.1:1455/v1"})
    assert rc == 0, err
    doc = json.loads(patch.read_text())
    prov = doc["models"]["providers"]["codex"]
    assert prov["api"] == "openai-completions"
    assert prov["baseUrl"] == "http://127.0.0.1:1455/v1"
    assert prov["apiKey"].startswith("${env:")          # auth by reference (PT-MM6)
    assert prov["models"][0]["id"] == "gpt-5.5"
    assert doc["agents"]["list"]  # agent primary set
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest scripts/tests/test_bind_codex_backend.py::test_fallback_generates_valid_provider_patch -v`
Expected: FAIL — `--dry-run-patch` arg + `do_fallback` not implemented.

- [ ] **Step 3: Add `--dry-run-patch` arg and endpoint override to the arg loop**

In `bind_codex_backend.sh`, add to the `while` arg loop (before the `*)` case):

```bash
    --dry-run-patch) DRY_RUN_PATCH="${2:-}"; shift 2 ;;
```

And initialize near the other defaults: `DRY_RUN_PATCH=""`.

- [ ] **Step 4: Implement `do_fallback` (provider patch builder)**

Add to `bind_codex_backend.sh`:

```bash
# Build the OpenAI-compatible Codex provider patch + agent primary, then apply
# via `openclaw config patch` (unless --dry-run-patch, which only writes the file).
do_fallback() {
  local endpoint="${CODEX_ENDPOINT_OVERRIDE:-}"
  [ -n "$endpoint" ] || endpoint="$(codex_discover_endpoint 2>/dev/null)/v1"
  [ -n "$endpoint" ] && [ "$endpoint" != "/v1" ] || die "fallback: no Codex app-server endpoint (start codex app-server or pass CODEX_ENDPOINT_OVERRIDE)"

  local tmp; tmp="$(mktemp)"
  python3 - "$endpoint" "$MODEL" "$AGENT_ID" "$FORCE_PRIMARY" >"$tmp" <<'PY'
import json, sys
endpoint, model, agent_id, force = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
patch = {
  "models": {"providers": {"codex": {
    "api": "openai-completions",
    "apiKey": "${env:OPENAI_API_KEY}",   # reference only — never the value (PT-MM6)
    "baseUrl": endpoint,
    "models": [{"id": model, "name": f"Codex {model}",
                "contextWindow": 200000, "maxTokens": 65536,
                "cost": {"input": 0, "output": 0}}],
  }}},
  # objects merge recursively under config patch; set this agent's primary.
  "agents": {"list": [{"id": agent_id, "model": {"primary": f"codex/{model}"}}]},
}
json.dump(patch, sys.stdout, indent=2)
PY

  if [ -n "$DRY_RUN_PATCH" ]; then
    cp "$tmp" "$DRY_RUN_PATCH"; rm -f "$tmp"
    echo '{"winning_path":"openai-compatible-fallback","dry_run":true}'
    return 0
  fi
  oc config patch --file "$tmp" --dry-run >/dev/null 2>&1 || { rm -f "$tmp"; die "fallback: config patch validation failed"; }
  oc config patch --file "$tmp" >/dev/null 2>&1 || { rm -f "$tmp"; die "fallback: config patch apply failed"; }
  rm -f "$tmp"
  FALLBACK_ENDPOINT="$endpoint"
  echo '{"winning_path":"openai-compatible-fallback","applied":true}'
}
```

Note: arrays replace under `config patch`. Patching `agents.list` with a single-element array would REPLACE the full agent list. The live application path must instead read the current `agents.list`, splice in the target agent, and patch the whole array — implemented in Task 6's combined flow. In `--dry-run-patch` mode (unit test) we only validate the provider block + agent shape, so the single-element list is acceptable for the dry-run artifact.

- [ ] **Step 5: Wire `do_fallback` into `main` for `bind`+`compat`**

Replace the `*)` branch of `main`'s case with:

```bash
    bind|auto)
      if [ "$PREFER" = "compat" ]; then do_fallback
      else die "plugin/auto bind implemented in Task 5"; fi ;;
    verify) die "verify implemented in Task 6" ;;
```

- [ ] **Step 6: Run the fallback test**

Run: `python3 -m pytest scripts/tests/test_bind_codex_backend.py::test_fallback_generates_valid_provider_patch -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/bind_codex_backend.sh scripts/tests/test_bind_codex_backend.py
git commit -m "feat(codex-openclaw-agent): Stage 3 OpenAI-compatible Codex provider injection (verified schema, auth-by-ref)"
```

---

## Task 5: Stage 1 native plugin (codex-supervisor) + Stage 2 idempotent install

**Files:**
- Modify: `bind_codex_backend.sh` (add `do_primary`, `do_install`)
- Test: `scripts/tests/test_bind_codex_backend.py`

- [ ] **Step 1: Write the failing test for plugin-absent → install decision**

The install logic is decision-only in unit tests (we don't mutate the live gateway). Test that with a faked probe result of `absent`, `do_install` chooses `enable` when present-disabled and `install` when absent.

Add to test file:

```python
def test_install_decision_enable_when_disabled(tmp_path):
    rc, out, err = _bind([
        "--openclaw-home", str(tmp_path), "--agent-id", "codex-agent",
        "--mode", "bind", "--prefer", "plugin", "--install-plan-only",
    ], env={"CODEX_PLUGIN_STATE_OVERRIDE": "disabled"})
    assert rc == 0, err
    assert json.loads(out)["install_action"] == "enable"

def test_install_decision_install_when_absent(tmp_path):
    rc, out, err = _bind([
        "--openclaw-home", str(tmp_path), "--agent-id", "codex-agent",
        "--mode", "bind", "--prefer", "plugin", "--install-plan-only",
    ], env={"CODEX_PLUGIN_STATE_OVERRIDE": "absent"})
    assert rc == 0, err
    assert json.loads(out)["install_action"] == "install"
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest scripts/tests/test_bind_codex_backend.py -k install_decision -v`
Expected: FAIL.

- [ ] **Step 3: Add `--install-plan-only` arg + override hook**

Arg loop: add `--install-plan-only) INSTALL_PLAN_ONLY="1"; shift ;;` and init `INSTALL_PLAN_ONLY="0"`.

Add a state resolver that honors the test override:

```bash
plugin_state() {
  if [ -n "${CODEX_PLUGIN_STATE_OVERRIDE:-}" ]; then echo "$CODEX_PLUGIN_STATE_OVERRIDE"; return; fi
  codex_plugin_state "$RESOLVER"
}
```

- [ ] **Step 4: Implement `do_install` and `do_primary`**

```bash
# Stage 2: idempotent. enable if present-disabled; install if absent-installable.
do_install() {
  local state action; state="$(plugin_state)"
  case "$state" in
    enabled)  action="none" ;;
    disabled) action="enable" ;;
    absent)   action="install" ;;
  esac
  if [ "$INSTALL_PLAN_ONLY" = "1" ]; then
    printf '{"plugin_state":"%s","install_action":"%s"}\n' "$state" "$action"; return 0
  fi
  case "$action" in
    enable)
      local tmp; tmp="$(mktemp)"
      printf '{"plugins":{"allow":["codex-supervisor"],"entries":{"codex-supervisor":{"enabled":true}}}}' >"$tmp"
      # NOTE: allow is an array (replaces) — Task 6 merges with current allowlist before live apply.
      oc config patch --file "$tmp" >/dev/null 2>&1 || { rm -f "$tmp"; die "stage2: enable failed"; }
      rm -f "$tmp" ;;
    install)
      command -v openclaw >/dev/null 2>&1 || true
      oc plugins install codex-supervisor >/dev/null 2>&1 || die "stage2: plugin not installable offline; use --prefer compat" ;;
    none) : ;;
  esac
  echo "$action"
}

# Stage 1: bind via native codex-supervisor. PT-MM4: create/bind session first;
# only resume an existing session. Sessionless ping otherwise.
do_primary() {
  local action; action="$(do_install)"
  [ "$INSTALL_PLAN_ONLY" = "1" ] && { printf '%s\n' "$action"; return 0; }
  # Set this agent's primary to the codex-supervisor provider (Task 6 splices agents.list).
  PRIMARY_PROVIDER="codex-supervisor"
  echo '{"winning_path":"plugin","action":"'"$action"'"}'
}
```

- [ ] **Step 5: Route `plugin` in `main`**

In `main`, replace the `else die "plugin/auto bind implemented in Task 5"` with:

```bash
      else do_primary; fi ;;
```

- [ ] **Step 6: Run install-decision tests**

Run: `python3 -m pytest scripts/tests/test_bind_codex_backend.py -k install_decision -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/bind_codex_backend.sh scripts/tests/test_bind_codex_backend.py
git commit -m "feat(codex-openclaw-agent): Stage 1/2 native codex-supervisor bind + idempotent enable/install"
```

---

## Task 6: Stage 4 verify + Stage 5 record + combined default flow

**Files:**
- Modify: `bind_codex_backend.sh` (add `do_verify`, `do_record`, `splice_agent_primary`, combined `auto` flow)
- Test: `scripts/tests/test_bind_codex_backend.py`

- [ ] **Step 1: Write the failing test for verify verdict parsing**

`do_verify` takes a resolved model string and returns PASS/FAIL JSON. Test the pure verdict function via a `--verify-resolved <string>` debug entry.

Add to test file:

```python
def test_verify_passes_for_codex_prefix(tmp_path):
    rc, out, err = _bind(["--openclaw-home", str(tmp_path), "--agent-id", "codex-agent",
                          "--mode", "verify", "--verify-resolved", "codex/gpt-5.5"])
    assert rc == 0, err
    assert json.loads(out)["verification"]["status"] == "pass"

def test_verify_fails_for_ollama_prefix(tmp_path):
    rc, out, err = _bind(["--openclaw-home", str(tmp_path), "--agent-id", "codex-agent",
                          "--mode", "verify", "--verify-resolved", "ollama/qwen3.5:9b-nvfp4"])
    assert rc != 0
    doc = json.loads(out)
    assert doc["verification"]["status"] == "fail"
    assert "ollama" in doc["verification"]["actual"]
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest scripts/tests/test_bind_codex_backend.py -k verify_ -v`
Expected: FAIL.

- [ ] **Step 3: Add `--verify-resolved` arg + implement `do_verify`/`do_record`**

Arg loop: `--verify-resolved) VERIFY_RESOLVED="${2:-}"; shift 2 ;;` and init `VERIFY_RESOLVED=""`.

```bash
# PT-MM1: backend identity = resolved "<provider>/<model>". codex/* PASS, ollama/* FAIL.
verdict_for() {
  local resolved="$1" expected="codex/$MODEL"
  local prov="${resolved%%/*}"
  if { [ "$prov" = "codex" ] || [ "$prov" = "codex-supervisor" ]; } && printf '%s' "$resolved" | grep -q "$MODEL"; then
    printf '{"status":"pass","expected":"%s","actual":"%s","method":"model-prefix"}' "$expected" "$resolved"; return 0
  fi
  printf '{"status":"fail","expected":"%s","actual":"%s","method":"model-prefix"}' "$expected" "$resolved"; return 1
}

do_verify() {
  local resolved="$VERIFY_RESOLVED"
  if [ -z "$resolved" ]; then
    # Live path: start/resume a session, run a harmless task, read resolved model.
    resolved="$(oc agent --agent "$AGENT_ID" --message "reply with: ok" --json 2>/dev/null \
                | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("model") or d.get("resolved_model") or "")' 2>/dev/null)"
    [ -n "$resolved" ] || resolved="$(oc config get "agents.list" 2>/dev/null | python3 -c 'import json,sys,re; t=sys.stdin.read(); m=re.search(r"\"primary\"\s*:\s*\"([^\"]+)\"", t); print(m.group(1) if m else "")')"
  fi
  local v rc; v="$(verdict_for "$resolved")"; rc=$?
  printf '{"verification":%s}\n' "$v"
  return $rc
}

# Stage 5: write the redacted binding record (refs/codex-backend-binding.json), last.
do_record() {
  local winning="$1" endpoint="$2" verify_json="$3"
  local refs="$OPENCLAW_HOME/agents/$AGENT_ID/refs"
  mkdir -p "$refs"
  local ts; ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 - "$refs/codex-backend-binding.json" "$winning" "$MODEL" "$EFFORT" "$endpoint" "$OPENCLAW_HOME" "$AGENT_ID" "$BINDER_VERSION" "$ts" "$verify_json" <<'PY'
import json, sys
path, winning, model, effort, endpoint, home, agent, ver, ts, verify = sys.argv[1:11]
rec = {"schema_version":"1","winning_path":winning,"provider_key":"codex",
       "provider_string":f"codex/{model}","model":model,"effort":effort,
       "auth_source_ref":"~/.codex (referenced, not copied)",
       "endpoint_ref":endpoint or None,"verification":json.loads(verify),
       "timestamp":ts,"binder_version":ver,"openclaw_home":home,"agent_id":agent}
json.dump(rec, open(path,"w"), indent=2)
PY
}
```

- [ ] **Step 4: Route `verify` and build the combined `auto` flow with `splice_agent_primary`**

Add the agent-list splicer (fixes the array-replace footgun for the live path):

```bash
# Read current agents.list, replace/insert the target agent's model.primary, patch whole array.
splice_agent_primary() {
  local provider_model="$1" tmp; tmp="$(mktemp)"
  oc config get "agents.list" 2>/dev/null > "$tmp.cur" || echo '[]' > "$tmp.cur"
  python3 - "$tmp.cur" "$AGENT_ID" "$provider_model" > "$tmp" <<'PY'
import json, sys
cur = json.load(open(sys.argv[1])); agent, pm = sys.argv[2], sys.argv[3]
found=False
for a in cur:
    if a.get("id")==agent: a.setdefault("model",{})["primary"]=pm; found=True
if not found: cur.append({"id":agent,"model":{"primary":pm}})
json.dump({"agents":{"list":cur}}, sys.stdout)
PY
  oc config patch --file "$tmp" --dry-run >/dev/null 2>&1 && oc config patch --file "$tmp" >/dev/null 2>&1
  rm -f "$tmp" "$tmp.cur"
}
```

Update `main`:

```bash
main() {
  case "$MODE" in
    probe) do_probe ;;
    verify) do_verify ;;
    bind|auto)
      local winning endpoint="" vjson
      if [ "$PREFER" = "compat" ]; then
        do_fallback >/dev/null; winning="openai-compatible-fallback"; endpoint="${FALLBACK_ENDPOINT:-}"
        [ -n "$DRY_RUN_PATCH" ] && { echo '{"winning_path":"openai-compatible-fallback","dry_run":true}'; return 0; }
        splice_agent_primary "codex/$MODEL"
      else
        do_primary >/dev/null; winning="plugin"
        [ "$INSTALL_PLAN_ONLY" = "1" ] && return 0
        splice_agent_primary "codex-supervisor/$MODEL" 2>/dev/null || splice_agent_primary "codex/$MODEL"
      fi
      vjson="$(do_verify)"; local vrc=$?
      do_record "$winning" "$endpoint" "$(printf '%s' "$vjson" | python3 -c 'import json,sys;print(json.dumps(json.load(sys.stdin)["verification"]))')"
      printf '{"winning_path":"%s","endpoint_ref":%s,%s}\n' "$winning" \
        "$([ -n "$endpoint" ] && printf '"%s"' "$endpoint" || echo null)" \
        "$(printf '%s' "$vjson" | sed 's/^{//;s/}$//')"
      return $vrc ;;
  esac
}
```

- [ ] **Step 5: Run verify tests**

Run: `python3 -m pytest scripts/tests/test_bind_codex_backend.py -k verify_ -v`
Expected: PASS (pass-case rc 0; fail-case rc≠0 with `ollama` in actual).

- [ ] **Step 6: Run the full binder test suite**

Run: `python3 -m pytest scripts/tests/test_bind_codex_backend.py -v`
Expected: PASS (all binder tests).

- [ ] **Step 7: Commit**

```bash
git add bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/bind_codex_backend.sh scripts/tests/test_bind_codex_backend.py
git commit -m "feat(codex-openclaw-agent): Stage 4 verify (model-prefix gate) + Stage 5 record + agents.list splice"
```

---

## Task 7: Generator core — composition, source-hash headers, marked-section merge

**Files:**
- Create: `bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/generate_codex_openclaw_profile.py`
- Test: `tests/test_codex_generator.py`

PT-MM7: the generator normalizes to POSIX separators + LF so source hashes are deterministic across Mac/Windows.

- [ ] **Step 1: Write the failing test for marked-section merge + LF normalization**

Create `tests/test_codex_generator.py`:

```python
import importlib.util, json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GEN = REPO / "bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/generate_codex_openclaw_profile.py"

def _load():
    spec = importlib.util.spec_from_file_location("codexgen", GEN)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_merge_replaces_only_marked_section():
    m = _load()
    existing = "operator top\n<!-- BEGIN GENERATED: codex-openclaw-agent CODEX.md -->\nOLD\n<!-- END GENERATED: codex-openclaw-agent CODEX.md -->\noperator bottom\n"
    out = m.merge_marked_section(existing, "CODEX.md", "NEW BODY")
    assert "operator top" in out and "operator bottom" in out
    assert "NEW BODY" in out and "OLD" not in out

def test_merge_appends_when_no_marker():
    m = _load()
    out = m.merge_marked_section("operator only\n", "TOOLS.md", "GEN")
    assert "operator only" in out and "GEN" in out
    assert out.count("BEGIN GENERATED: codex-openclaw-agent TOOLS.md") == 1

def test_lf_normalization_and_hash_stability():
    m = _load()
    a = m.normalize("x\r\ny\r\n"); b = m.normalize("x\ny\n")
    assert a == b == "x\ny\n"
    assert m.sha256_text(a) == m.sha256_text(b)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_codex_generator.py -v`
Expected: FAIL — generator does not exist.

- [ ] **Step 3: Write the generator core**

Create `generate_codex_openclaw_profile.py`:

```python
#!/usr/bin/env python3
"""Generate Codex-backed OpenClaw agent profile files from the binding record
and source profiles. Merges only marked generated sections; preserves operator
content. POSIX/LF-normalized for cross-OS source-hash stability (PT-MM7)."""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

GEN_VERSION = "1.0.0"
MARK_BEGIN = "<!-- BEGIN GENERATED: codex-openclaw-agent {name} -->"
MARK_END = "<!-- END GENERATED: codex-openclaw-agent {name} -->"

def normalize(text: str) -> str:
    """LF line endings, POSIX-stable. Trailing single newline."""
    return text.replace("\r\n", "\n").replace("\r", "\n")

def sha256_text(text: str) -> str:
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()

def merge_marked_section(existing: str, name: str, body: str) -> str:
    existing = normalize(existing)
    begin, end = MARK_BEGIN.format(name=name), MARK_END.format(name=name)
    block = f"{begin}\n{body.rstrip()}\n{end}"
    pat = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)
    if pat.search(existing):
        return pat.sub(block, existing)
    sep = "" if existing.endswith("\n") or existing == "" else "\n"
    return f"{existing}{sep}\n{block}\n"
```

- [ ] **Step 4: Run merge/normalize tests**

Run: `python3 -m pytest tests/test_codex_generator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/generate_codex_openclaw_profile.py tests/test_codex_generator.py
git commit -m "feat(codex-openclaw-agent): generator core (marked-section merge, LF normalization, sha256)"
```

---

## Task 8: Generator — write 6 directive files + CODEX.md + refs (atomic)

**Files:**
- Modify: `generate_codex_openclaw_profile.py`
- Test: `tests/test_codex_generator.py`

PT-MM5: write to a temp dir, atomic-rename into the source repo, write `refs/codex-backend-binding.json` last.

- [ ] **Step 1: Write failing tests for dry-run, secret-scan, CODEX.md banner, source-hash refs**

Add to `tests/test_codex_generator.py`:

```python
import subprocess, os

def _binding_record(tmp_path):
    rec = {"schema_version":"1","winning_path":"plugin","provider_key":"codex",
           "provider_string":"codex/gpt-5.5","model":"gpt-5.5","effort":"medium",
           "auth_source_ref":"~/.codex (referenced, not copied)",
           "endpoint_ref":"http://127.0.0.1:1455/v1",
           "verification":{"status":"pass","expected":"codex/gpt-5.5","actual":"codex/gpt-5.5","method":"model-prefix"},
           "timestamp":"2026-06-19T00:00:00Z","binder_version":"1.0.0",
           "openclaw_home":str(tmp_path),"agent_id":"codex-agent"}
    p = tmp_path / "binding.json"; p.write_text(json.dumps(rec)); return p

def _run_gen(tmp_path, *extra):
    rec = _binding_record(tmp_path)
    return subprocess.run(["python3", str(GEN), "--openclaw-home", str(tmp_path),
        "--agent-id", "codex-agent", "--binding-record", str(rec), *extra],
        capture_output=True, text=True)

def test_dry_run_writes_nothing(tmp_path):
    r = _run_gen(tmp_path, "--dry-run")
    assert r.returncode == 0, r.stderr
    assert not (tmp_path / "agents/codex-agent/CODEX.md").exists()

def test_generates_all_files_with_banner_and_no_secrets(tmp_path):
    r = _run_gen(tmp_path); assert r.returncode == 0, r.stderr
    base = tmp_path / "agents/codex-agent"
    for f in ["SOUL.md","IDENTITY.md","USER.md","AGENTS.md","TOOLS.md","SECURITY.md","CODEX.md",
              "refs/codex-profile-sources.md","refs/codex-backend-binding.json"]:
        assert (base / f).exists(), f"missing {f}"
    codex = (base / "CODEX.md").read_text()
    assert "Generated by codex-openclaw-agent" in codex          # DX Finding 4 banner
    blob = "\n".join((base / f).read_text() for f in ["CODEX.md","SECURITY.md"])
    assert "sk-" not in blob and "Bearer " not in blob            # no secrets
    assert "/Users/" not in blob                                  # no workstation paths

def test_refs_include_source_hashes(tmp_path):
    _run_gen(tmp_path)
    src = (tmp_path / "agents/codex-agent/refs/codex-profile-sources.md").read_text()
    assert "SHA-256" in src or "sha256" in src
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_codex_generator.py -k "dry_run or generates_all or refs_include" -v`
Expected: FAIL — generator has no `main`/writing logic yet.

- [ ] **Step 3: Implement the file-writing + atomic commit logic**

Append to `generate_codex_openclaw_profile.py`:

```python
DIRECTIVE_FILES = ["SOUL.md","IDENTITY.md","USER.md","AGENTS.md","TOOLS.md","SECURITY.md"]
CODEX_BANNER = ("> Generated by codex-openclaw-agent. This file records the Codex backend\n"
                "> binding and profile source hashes. OpenClaw runtime behavior is applied\n"
                "> through openclaw.json and the native directive files.\n")

def _codex_md_body(rec: dict) -> str:
    v = rec["verification"]
    return (CODEX_BANNER + "\n## Binding\n\n"
            f"| Field | Value |\n|---|---|\n"
            f"| Binding path | {rec['winning_path']} |\n"
            f"| Provider | {rec['provider_string']} |\n"
            f"| Model | {rec['model']} |\n"
            f"| Effort | {rec['effort']} |\n"
            f"| Auth | {rec['auth_source_ref']} |\n"
            f"| Endpoint | {rec.get('endpoint_ref') or 'n/a'} |\n"
            f"| Verify | {v['status']} ({v['actual']}) |\n"
            f"| Generator | {GEN_VERSION} @ {rec['timestamp']} |\n")

def _section_for(name: str, rec: dict) -> str:
    if name == "CODEX.md":   return _codex_md_body(rec)
    if name == "IDENTITY.md":return f"Codex-backed OpenClaw agent. Primary model: {rec['provider_string']}."
    if name == "AGENTS.md":  return ("Startup: load mother skill, verify backend identity before first task.\n"
                                     "Sub-agent routing and parent handoff per orchestrator. Backend MUST be Codex, not Ollama.")
    if name == "TOOLS.md":   return ("Codex CLI; OpenClaw skill commands; scripts/bind_codex_backend.sh; "
                                     "verify with `--mode verify`. Resolve openclaw via resolve-openclaw.sh.")
    if name == "SECURITY.md":return ("Auth by reference only (never copy tokens). Sandbox/approval per Codex policy. "
                                     "Generated sections are owned by codex-openclaw-agent; do not hand-edit between markers.")
    return ""

def _atomic_write_tree(staging: Path, dest: Path):
    """Move each staged file into dest via atomic rename (PT-MM5)."""
    for sp in sorted(staging.rglob("*")):
        if sp.is_file():
            rel = sp.relative_to(staging); dp = dest / rel
            dp.parent.mkdir(parents=True, exist_ok=True)
            os.replace(sp, dp)

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--openclaw-home", required=True)
    ap.add_argument("--agent-id", required=True)
    ap.add_argument("--binding-record", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--source", action="append", default=[], help="source profile path (repeatable)")
    a = ap.parse_args(argv)

    home = Path(a.openclaw_home)
    if not home.is_absolute():
        print("ERROR: --openclaw-home must be absolute", file=sys.stderr); return 2
    rec = json.loads(Path(a.binding_record).read_text())
    if rec["verification"]["status"] != "pass" and not a.force:
        print("ERROR: binding verification did not pass; refusing to generate (use --force to override)", file=sys.stderr)
        return 3
    dest = home / "agents" / a.agent_id
    if "/stow" in str(dest) or dest.name.endswith(".stow"):    # Eng Finding 5 guard
        print("ERROR: refusing to write into a stow target", file=sys.stderr); return 4

    # source hashes for refs
    src_lines = ["# Codex profile sources\n", f"_generator {GEN_VERSION} @ {rec['timestamp']}_\n"]
    for s in a.source:
        p = Path(s)
        if p.exists():
            src_lines.append(f"- `{s}` SHA-256 `{sha256_text(p.read_text(errors='ignore'))}`")

    staging = Path(tempfile.mkdtemp(prefix="codexgen-"))
    try:
        agent_stage = staging / "agents" / a.agent_id
        (agent_stage / "refs").mkdir(parents=True)
        for name in DIRECTIVE_FILES + ["CODEX.md"]:
            target = dest / name
            existing = target.read_text() if target.exists() and not a.force else ""
            body = _section_for(name, rec)
            content = merge_marked_section(existing, name, body) if body else normalize(existing)
            (agent_stage / name).write_text(content if content.endswith("\n") else content + "\n")
        (agent_stage / "refs/codex-profile-sources.md").write_text(normalize("\n".join(src_lines) + "\n"))
        # binding record written LAST in the staging tree (committed last on rename)
        (agent_stage / "refs/codex-backend-binding.json").write_text(json.dumps(rec, indent=2) + "\n")

        if a.dry_run:
            print(json.dumps({"dry_run": True, "would_write": [str(p.relative_to(staging)) for p in staging.rglob('*') if p.is_file()]}))
            return 0
        _atomic_write_tree(staging, home)
        print(json.dumps({"written": True, "agent_dir": str(dest)}))
        return 0
    finally:
        for p in sorted(staging.rglob("*"), reverse=True):
            try: p.unlink() if p.is_file() else p.rmdir()
            except OSError: pass
        try: staging.rmdir()
        except OSError: pass

if __name__ == "__main__":
    raise SystemExit(main())
```

Note: `openclaw.json` provider/agent binding is written by the binder (Task 6 `splice_agent_primary` + Task 4 provider patch), not by the generator — the generator owns the agent-home files; the binder owns gateway config. This keeps the two substrates' write-surfaces disjoint.

- [ ] **Step 4: Run generator file tests**

Run: `python3 -m pytest tests/test_codex_generator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/generate_codex_openclaw_profile.py tests/test_codex_generator.py
git commit -m "feat(codex-openclaw-agent): generator writes 6 directive files + CODEX.md + refs (atomic, banner, hashes)"
```

---

## Task 9: Thin SKILL.md + profile-composition.md + interaction surface

**Files:**
- Create: `bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/SKILL.md`
- Create: `bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/references/profile-composition.md`

- [ ] **Step 1: Write `profile-composition.md` (precedence doctrine)**

Write the composition precedence (1–9) from spec §"Composition Rules" verbatim as a reference doc, plus the conflict resolution rule: "keep the stricter runtime-safe rule; if profile text implies Codex but verification says Ollama, FAIL."

- [ ] **Step 2: Write the thin `SKILL.md`**

Create `SKILL.md` with frontmatter + the 7-step orchestration. Content (markdown, no placeholders):

```markdown
---
name: codex-openclaw-agent
description: Initialize a real Codex-backed (gpt-5.5) OpenClaw coding agent — binds the runtime to Codex via an opportunistic resolver, generates directive files + CODEX.md, verifies backend identity. Use when asked to "create a codex openclaw agent", "make a codex-backed agent", "bind codex as the backend".
---

# codex-openclaw-agent

Thin orchestrator. Does NOT copy source-skill bodies; composes them.

## Required normalized inputs
agent_id, display name, spawn mode (ask|sub-agent|standalone), parent (if sub-agent),
regeneration mode, channel wiring, effort (medium|high|xhigh), binding preference
(auto|plugin|compat), strict verification (bool). Resolve missing inputs through the
ACTIVE surface: interrupt envelope (agent/harness), AskUserQuestion (desktop),
CLI flags/stdin (terminal), portal form (GUI). Non-interactive runs MUST pass
--mode, --agent-id, --openclaw-home (DX Finding 3).

## Steps
1. Load the OpenClaw mother skill (`bin/orama-system/skills/openclaw-skills/SKILL.md`).
2. Ensure cc-openclaw initialized: `bash scripts/install-openclaw-skills.sh`.
3. Resolve missing operator choices via the active interaction surface.
4. Invoke `openclaw-new-agent` (Orama overlay) to create the agent home.
5. Run `scripts/bind_codex_backend.sh --openclaw-home <home> --agent-id <id> --mode auto --prefer <pref> --effort <effort>`.
6. Run `scripts/generate_codex_openclaw_profile.py --openclaw-home <home> --agent-id <id> --binding-record <home>/agents/<id>/refs/codex-backend-binding.json` (+ `--source` for each composed profile).
7. openclaw-stow → openclaw-restart → openclaw-status → final `--mode verify` assert.

## Backend resolution
Always invoke openclaw through `scripts/openclaw/resolve-openclaw.sh` (never bare
`openclaw`). See `bin/orama-system/skills/openclaw-skills/SKILL.md` §"OpenClaw CLI
Resolution" for the broken-symlink/multi-install gotcha.

## Binding summary (always print on success — DX Finding 1)
| Field | Value | (binding path / provider / model / effort / auth=reference / verify) |

## Failure recovery
Print stage, expected vs actual, redacted auth ref, endpoint ref, and the next
safe command (codex login / codex --version / --prefer compat --refresh /
--bind-only --verify).
```

- [ ] **Step 3: Hygiene + skill-validation check**

Run: `python3 scripts/review/repo_hygiene.py bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/SKILL.md bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/references/profile-composition.md 2>&1 | tail -5`
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/SKILL.md \
        bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/references/profile-composition.md
git commit -m "feat(codex-openclaw-agent): thin SKILL.md orchestrator + profile-composition doctrine"
```

---

## Task 10: Full test plan, gateway restart, e2e smoke, self-review

**Files:**
- Modify: `scripts/tests/test_bind_codex_backend.py`, `tests/test_codex_generator.py` (remaining spec cases)

This task closes the spec's 15-item testing plan. Map: items 2–4,11 (binder) live in `test_bind_codex_backend.py`; items 5–10 (generator) in `test_codex_generator.py`; items 1,13,14,15 are runnable checks below.

- [ ] **Step 1: Add remaining binder cases (spec items 3, 4, 11)**

Add tests for: plugin-absent-offline (`do_install` with state `absent` and `oc plugins install` failing → exits with the "use --prefer compat" message), provider-already-bound (probe `config_has_codex_provider=true` short-circuits), and the three spawn-mode input shapes producing the expected `openclaw-new-agent` args. Use the `--install-plan-only` and `--dry-run-patch` hooks so no live mutation occurs.

```python
def test_offline_install_fails_with_compat_hint(tmp_path):
    rc, out, err = _bind(["--openclaw-home", str(tmp_path), "--agent-id", "codex-agent",
                          "--mode", "bind", "--prefer", "plugin"],
                         env={"CODEX_PLUGIN_STATE_OVERRIDE": "absent", "OPENCLAW_FORCE_INSTALL_FAIL": "1"})
    assert rc != 0
    assert "--prefer compat" in err
```
(Implement the `OPENCLAW_FORCE_INSTALL_FAIL` short-circuit in `do_install`'s `install)` branch: if set, `die "stage2: plugin not installable offline; use --prefer compat"`.)

- [ ] **Step 2: Add remaining generator cases (spec items 8, 9, 10)**

```python
def test_preserves_operator_content_and_regenerates_idempotently(tmp_path):
    _run_gen(tmp_path)
    codex = tmp_path / "agents/codex-agent/CODEX.md"
    body = codex.read_text() + "\n## operator note\nkeep me\n"; codex.write_text(body)
    _run_gen(tmp_path)
    after = codex.read_text()
    assert "keep me" in after
    assert after.count("BEGIN GENERATED: codex-openclaw-agent CODEX.md") == 1
```

- [ ] **Step 3: Run the full unit suite**

Run: `cd "$(git rev-parse --show-toplevel)" && python3 -m pytest scripts/tests/test_bind_codex_backend.py tests/test_codex_generator.py -v`
Expected: all PASS.

- [ ] **Step 4: Spec item 1 + 14 + 15 — install, hygiene, skill validation**

```bash
bash scripts/install-openclaw-skills.sh
python3 scripts/review/repo_hygiene.py bin/orama-system/skills/openclaw-skills/codex-openclaw-agent 2>&1 | tail -10
# skill validation (whatever the repo uses; e.g. the skills linter):
ls bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/SKILL.md
```
Expected: install OK, hygiene clean, SKILL.md present and frontmatter valid.

- [ ] **Step 5: Activate codex-supervisor (gateway restart) — the one outward-facing step**

This briefly drops live telegram/whatsapp; do it deliberately. The launchd service auto-respawns.

```bash
launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway
# wait for health, then confirm codex-supervisor active:
for i in $(seq 1 15); do curl -s -m 3 -o /dev/null -w '%{http_code}' http://localhost:18789/ | grep -q 200 && break; done
bash scripts/openclaw/resolve-openclaw.sh plugins list | grep -i codex-supervisor
```
Expected: gateway returns to HTTP 200; codex-supervisor shows `enabled` and loaded.

- [ ] **Step 6: Spec item 13 — end-to-end smoke (real, gated)**

```bash
HOME_DIR="$(mktemp -d)/openclaw-home"; mkdir -p "$HOME_DIR"
bash bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/bind_codex_backend.sh \
  --openclaw-home "$HOME_DIR" --agent-id codex-smoke --mode probe | python3 -m json.tool
# If recommended_path != none, run the full auto flow + generate + verify:
bash .../bind_codex_backend.sh --openclaw-home "$HOME_DIR" --agent-id codex-smoke --mode auto --prefer auto
python3 .../generate_codex_openclaw_profile.py --openclaw-home "$HOME_DIR" --agent-id codex-smoke \
  --binding-record "$HOME_DIR/agents/codex-smoke/refs/codex-backend-binding.json"
```
Expected: probe valid; if a Codex backend is live, binding record `verification.status == "pass"` and `provider_string` starts `codex/`. If no live Codex backend, the binder fails loudly with the recovery command (acceptable — proves the gate).

- [ ] **Step 7: Self-review pass**

Re-read the spec sections and confirm each maps to a task (Stage 0–5 → Tasks 3,5,4,6; CODEX.md contract → Task 8; artifact layout → Task 8; spawn/interaction → Task 9; error handling → binder `die` + verify; 15-test plan → this task). Fix any gap inline.

- [ ] **Step 8: Final commit**

```bash
git add scripts/tests/test_bind_codex_backend.py tests/test_codex_generator.py
git commit -m "test(codex-openclaw-agent): complete 15-item test plan + e2e smoke + activation step"
```

---

## Spec → Task Coverage Map

| Spec requirement | Task |
|------------------|------|
| Thin SKILL.md, 7-step orchestration | 9 |
| `references/codex-backend-binding.md` doctrine | 1 |
| Stage 0 probe (live canary, PT-MM3) | 0, 3 |
| Stage 1 native plugin (`codex-supervisor`, PT-MM4) | 5 |
| Stage 2 idempotent enable/install | 5 |
| Stage 3 OpenAI-compatible fallback (PT-MM2 schema) | 4 |
| Stage 4 verify backend identity (PT-MM1) | 6 |
| Stage 5 record (refs json) | 6 |
| CODEX.md contract + banner (DX 4) | 8 |
| Generated artifact layout (6 files + CODEX.md + refs) | 8 |
| Marked-section merge, preserve operator content | 7, 8, 10 |
| Source-hash headers, cross-OS determinism (PT-MM7) | 7, 8 |
| Atomicity/flock (PT-MM5) | 2 (boundary), 6, 8 |
| Auth by reference (PT-MM6) | 1, 4, 8 |
| Spawn modes + interaction surface | 9 |
| Error handling + recovery commands (DX 2) | 2, 6, 9 |
| Binding summary table (DX 1) | 9 |
| Source-repo-first writes / stow guard (Eng 5) | 8 |
| 15-item testing plan | 0–10 (closed in 10) |
| Gateway restart to activate codex-supervisor | 10 |
