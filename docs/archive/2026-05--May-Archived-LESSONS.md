# orama-system LESSONS.md archive — May 2026

> Archived from `docs/LESSONS.md` on 2026-08-16. Entries below are unchanged
> from the original file (same heading text, same content) except reordered
> oldest-first within this archive. See `docs/LESSONS.md` for the live log
> and links to the other archive files.

---

## 2026-05-02 — Claude — v2 packages scaffolded + instinct sync

### v2 Phase 1–3 complete: perpetua-core + oramasys + agate (2026-05-02)

Three Python packages built and pushed to GitHub under `oramasys` org. All tests green:

- `perpetua-core` 32/32 tests — `PerpetuaState`, `LLMClient`, `HardwarePolicyResolver`, `MiniGraph` (~70 lines), `GossipBus`, 6 graph plugins (checkpointer, interrupts, streaming, structured_output, subgraphs, tool)
- `oramasys` 4/4 tests — FastAPI glass-window `/run` + `/health`, hardware-routed 3-node graph
- `agate` — JSON Schema + examples for `model_hardware_policy.yml`

Local paths: `~/code/oramasys/{perpetua-core,oramasys,agate}`
GitHub: `github.com/oramasys/{perpetua-core,oramasys,agate}`

**Phase 4 (parity tests) is next.** `dispatch_node` is still an echo stub — needs real `LLMClient` wiring.

Missing from spec (still TODO): `message.py`, `graph/nodes.py`, `graph/edges.py`, `config/model_hardware_policy.example.yml`, `GossipBus` integration in graph.

### Python runtime split on this machine (2026-05-02)

Two Python runtimes coexist:

- **Python 3.13**: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3` — has oramasys packages installed
- **Python 3.12**: `~/miniconda3/bin/python` — does NOT have v2 packages

Use `python3` (or full path `pytest`) for v2 tests. Running `python -m pytest` from miniconda shell fails with `ModuleNotFoundError: No module named 'perpetua_core'`.

### instinct-import CLI not installed — copy YAML workaround (2026-05-02)

`continuous-learning-v2` script (`~/.claude/skills/continuous-learning-v2/scripts/instinct-cli.py`) does not exist on disk — plugin is listed but not installed. Running `/instinct-import` fails silently.

**Workaround**: copy YAML files directly into `.claude/homunculus/instincts/inherited/` so future installs pick them up. Done for:

- `Perpetua-Tools-instincts.yaml` → `orama-system/.claude/homunculus/instincts/inherited/`
- `everything-claude-code-instincts.yaml` → `orama-system/.claude/homunculus/instincts/inherited/`

Key instincts to apply manually until script is available: snake_case filenames, relative imports, `@field_validator` not `@validator`, scoped conventional commits (`feat(x):`), tests in `tests/` directory.

### gitStatus in session context is a snapshot — always re-verify (2026-05-02)

The `gitStatus` block injected at session start is captured once at launch. By the time a new session starts, repos may have been committed and pushed. Always run `git status` before assuming there is work to do. Both orama-system and Perpetua-Tools appeared dirty in the snapshot but were fully clean when re-checked.

---

## 2026-05-02 — Document Integrity & Archiving Policy

- **Symptom**: Critical legacy documentation (AGENT_RESUME.md) was overwritten by an automated summary, losing v1 context.
- **Cause**: AI tendency to replace files rather than merge or archive (destructive behavior).
- **Rule**: NEVER delete or overwrite historical context. Always archive legacy documentation to /docs/archive/ or wiki entries.
- **Merge Strategy**: We are additive. All new summaries must be appended to the current state or moved to dedicated files while preserving the parent document's soul.
- **Reference**: Legacy AGENT_RESUME.md recovered and archived at docs/archive/AGENT_RESUME_v1_legacy.md.

---

## 2026-05-02 — Roadmap Granularity & Documentation Ergonomics

- **Symptom**: Premature "DONE" markers in v2 build order led to confusion about active implementation vs. planned hardening.
- **Cause**: AI tendency to mark design completion as task completion.
- **Solution**: Split roadmap into explicit **PLANNING** and **Implementation** phases. Architecture is "launched" (a living process), not merely "concluded."
- **Rule**: Documentation MUST link to both Archived (v1) and Active (v2) repository organizations to maintain cross-generational visibility.
- **Formatting**: Use `ascii` tags for non-executable code blocks and blockquotes for high-level summaries to improve UX for the next agent.

---

## 2026-05-04 — Codex — Priority execution (P1–P6), checklist and fail-closed hardening

### What was learned

- Large multi-priority migrations are easy to report as complete while still missing execution-level proof unless a strict post-block checklist is run.
- Hardware-bound requests (`lmstudio-*`, `ollama-*`) must fail closed when policy authority is unavailable; warnings are not sufficient.
- Verification command drift (doc command vs repo script reality) causes false confidence and noisy handoffs.

### Decisions made

- Added a consolidated checklist discipline after each priority block with pass/warn/fail reporting.
- Added in-repo helper `scripts/hardware_policy_cli.py --check-openclaw` to make the documented check executable.
- Promoted this incident to the wiki for durable cross-session visibility.

### Open follow-ups

- Historical docs still contain many `Perplexity-Tools` references; active-path docs are cleaned first, historical artifacts are tracked as non-blocking warnings.

→ [wiki/09-policy-fail-closed-and-checklist.md](wiki/09-policy-fail-closed-and-checklist.md)

---

---

## 2026-05-04 — Technical Architecture: Ghost Path Extraction

- **Symptom**: Advanced v1 features (symlink automation, IP sync) were lost during the structural rewrite to orama-system.
- **Cause**: Focus on 'clean lineage' led to a feature regression by discarding the 'messy' main backup.
- **Solution**: Use the `recovery-20260424` branch as a clean-room for extraction.
- **Rule**: Every 'v1 hack' is a potential v2 primitive. Audit the `backup-main` tag (1675ab4) for high-value logic before finalizing the v2 microkernel.
- **Reference**: Symlink automation logic identified in Commit 1675ab4 (start.sh).

---

---

## 2026-05-06 — Claude — Cherry-pick conflict resolution silently truncates files

**Agent**: Claude (Sonnet 4.6)
**Branch**: check-recovery-gemini
**Severity**: High — data loss risk on every multi-commit cherry-pick

### Problem

After cherry-picking 4 recovery commits (16eacf9, 9e70566, 4de7b09, 9876706)
onto a branch based on main, conflict resolution incorrectly took the *recovery
branch's older/shorter* file versions instead of main's richer ones — for 5 files
across two separate incidents:

| File | main lines | branch after cherry-pick | Lost |
|------|-----------|--------------------------|------|
| `scripts/review/repo_hygiene.py` | 363 | 204 | 159 lines of checks |
| `tests/test_repo_hygiene.py` | 147 | 34 | 113 lines of tests |
| `scripts/git/check_identity.sh` | 32 | 27 (elif reimpl.) | loop extensibility |
| `docs/wiki/08-git-hygiene-and-branching.md` | 122 | 122 (wrong content) | Codex identity text |
| `CLAUDE.md` | 217 | 225 (duplicate block) | duplicate cyre-only block injected |

The first two were silent — `pytest` still ran (just against the 34-line stub),
reporting 147 passed. No error surfaced until human review of the PR diff.

### Root cause

During `git cherry-pick` with `--strategy-option=ours`, "ours" means the branch
being cherry-picked INTO at that point in time — which is based on main. But
add/add conflicts and some content conflicts were resolved in the wrong direction,
taking the recovery commit's older version of files that main had substantially
expanded.

### Detection method that works

After any cherry-pick with conflicts, run:

```bash
for f in $(git diff --name-only main...HEAD); do
  main_n=$(git show "main:$f" 2>/dev/null | wc -l | tr -d ' ')
  branch_n=$(git show "HEAD:$f" 2>/dev/null | wc -l | tr -d ' ')
  [ "$branch_n" -lt "$main_n" ] && echo "SHORTER ⚠  $f  main=$main_n branch=$branch_n"
done
```

Any file where branch < main line count is suspicious. Then do a full `git diff
main HEAD -- <file>` on each and classify every removed line as either intentional
or accidental.

### Fix

Restore truncated files verbatim from main:

```bash
git show main:path/to/file > path/to/file
git add path/to/file
```

Then verify content diffs for zero-delta files (same line count ≠ same content —
check for replaced paragraphs, reversed identity text, injected duplicates).

### Rule going forward

**Assume everything is wrong after a cherry-pick with conflicts.**
Treat the line-count audit as mandatory before any push, not optional.
Files shorter than main = immediate stop and manual review.
Line-count parity is necessary but not sufficient — run full `git diff main HEAD`
on every changed file and justify each removed line.

### Open follow-ups

- Add line-count audit step to `scripts/review/repo_hygiene.py` as a pre-merge
  CI gate for branches with cherry-pick history (future work).

---

## 2026-05-06 — Claude — Idempotency, validator drift, and CWD anchoring (Codex P1/P2)

**Agent**: Claude (Sonnet 4.6) + Codex (chatgpt-codex-connector)
**Branch**: check-recovery-gemini → PR #32
**Severity**: High — three latent footguns in `start.sh` + cross-validator drift

### What Codex caught that single-pass review missed

PR #32 (commit b7733f1) integrated the `_ensure_symlink` automation from
commit 1675ab4. Local `pytest` was green and a manual run of the symlink
logic against the real PT path "worked." Codex review then surfaced three
issues that would only manifest in production startups:

1. **Regular-file crash under `set -e`** — `_ensure_symlink` only checked
   `[ ! -L "$link" ]` (not a symlink) before `ln -s`. When the link path
   was a tracked regular file (e.g. `network_autoconfig.py` is a real
   tracked Python module in this repo), `ln -s` returned exit 1 with
   "File exists" and `set -e` killed `start.sh` before any service
   launched. **Local manual tests missed this** because the link path
   was empty during testing — the test environment hadn't simulated the
   tracked-file case.

2. **Validator policy drift** — `repo_hygiene.py` had momentarily been
   restored to a single-identity policy (`cyre <Lawrence@cyre.me>`),
   while `check_identity.sh` accepted both `cyre` and `Codex`. Codex
   sessions would pass the gate-script but fail the hygiene script and
   the test that wraps it. The two validators must enforce the *same*
   set or one becomes a fiction.

3. **CWD-dependent symlink** — `_ensure_symlink "network_autoconfig.py"
   "$_REL_NET_CONFIG"` ran with whatever CWD `start.sh` was invoked
   from, not `$SCRIPT_DIR`. Worked in dev because we always ran from
   the repo root. Would silently misroute the symlink the moment a user
   typed `/path/to/start.sh` from elsewhere.

### Root patterns

These three findings collapse to **two patterns** worth promoting to
v2 design decisions:

#### Pattern A — Idempotent filesystem helpers (4-state guard)

Any helper that mutates the filesystem must explicitly handle every
state of the destination, in priority order:

```bash
_ensure_symlink() {
  local link="$1" target="$2"
  if [ -L "$link" ] && [ -e "$link" ]; then
    return 0                                      # 1. valid symlink → no-op
  elif [ -L "$link" ] && [ ! -e "$link" ]; then
    # 2. broken symlink → re-link if target exists
    [ -e "$target" ] && rm "$link" && ln -s "$target" "$link"
  elif [ -e "$link" ]; then
    # 3. regular file/dir → warn and skip (do NOT clobber)
    echo "WARN: $link occupies path as regular file; skipping symlink"
  else
    # 4. nothing → create
    ln -s "$target" "$link"
  fi
}
```

The non-negotiable property: every branch returns 0. No state crashes
under `set -e`. Idempotent across N invocations.

#### Pattern B — Single-source policy, multi-validator consumption

Allowed-identity lists, hardware policies, port assignments, allow/deny
patterns — anything that two scripts both check — must live in **one
file** that both scripts load. Constants duplicated across `bash` and
`python` will drift. Drift only surfaces when the rare branch fires.

In v1 today: two validators, two source-of-truth lists. In v2:
`config/identities.yaml` (or equivalent), loaded by both bash and
python via shared shim.

#### Pattern C — Anchor every CWD-sensitive call

Operations that resolve paths from `pwd` (`ln -s`, `cd`, relative
`subprocess` calls, `Path()` without absolute prefix) must run inside
`(cd "$SCRIPT_DIR" && ...)` or use absolute paths. Defaulting to "the
caller's CWD" is a footgun that hides until invoked from elsewhere.

### Detection method

For any new shell script touching the filesystem:

```bash
# Smoke test — assume the worst case for every state
TMPDIR=$(mktemp -d) && cd "$TMPDIR"
echo "tracked" > foo                    # state: regular file
_ensure_symlink "foo" "/some/target"    # must NOT crash under set -e
ln -s /nonexistent broken_link          # state: broken symlink
_ensure_symlink "broken_link" "."       # must re-link or warn
ln -s . valid_link                      # state: valid symlink
_ensure_symlink "valid_link" "."        # must be no-op
_ensure_symlink "fresh" "."             # state: nothing
_ensure_symlink "fresh" "."             # second run — still no error (idempotency)
```

Run all four states. Run each twice. Exit code must be 0 every time.

### Multi-agent review beats single-agent review

This is the third independent finding from a Codex pass that Claude
single-pass review missed (Gemini caught the api_server.py state-env
mismatch on a prior session; Codex caught the cherry-pick truncation
on this session; Codex caught these three on the same PR). For
significant changes, multi-model review pays for itself.

### Open follow-ups → see v2 design

These patterns are now first-class v2 design requirements. See:
- `docs/v2/11-idempotency-and-guard-patterns.md` — codified patterns
- `docs/v2/10-v1-hacks-automation-orbit.md` — Link Watcher must use
  the 4-state guard from day one
- `docs/v2/01-kernel-spec.md` — kernel filesystem helpers MUST be
  idempotent + CWD-anchored; pre-merge CI gate must run the smoke
  test above against every fs helper

---

---

## 2026-05-06 — xAI model retirement 2026-05-15; grok-4.3 + grok-4.20-non-reasoning defaults

**What changed**

xAI is retiring 8 model IDs on 2026-05-15 12:00 PM PT. Any
`model_hardware_policy.yml` entry or router constant still referencing them
will cause a hard dispatch failure at that time.

**Retired IDs**

`grok-4-1-fast-reasoning`, `grok-4-1-fast-non-reasoning`,
`grok-4-fast-reasoning`, `grok-4-fast-non-reasoning`, `grok-4-0709`,
`grok-code-fast-1`, `grok-3`, `grok-imagine-image-pro`

**Replacement routing (v2 defaults)**

| Workload | New model | Notes |
|----------|-----------|-------|
| Reasoning / coding | `grok-4.3` | Coding → PLAN-ONLY until Win-coder slot available; reasoning → full ACT always |
| Non-reasoning / non-coding | `grok-4.20-non-reasoning` | research, ops, chat, summarisation |
| Image generation | *(no announced replacement)* | Surface error to user; do not silently fall back |

**Coding ACT gate**: resumes when `swarm_state.md` reports `WIN_CODER: AVAILABLE`
(same file already polled by the Windows-sequential-load rule).

**Design rule promoted to v2**

- All model ID lists must be single-source in `perpetua-core/config/` (Pattern B
  from `11-idempotency-and-guard-patterns.md`) — never duplicated in bash + python.
- Add CI gate `test_no_retired_model_ids` that greps `model_hardware_policy.yml`
  for any known-retired ID and fails if found.

**Spec doc**: `docs/v2/12-xai-model-migration-2026-05.md`

---

---

## 2026-05-07 — Codex CLI unknown-model fallback; local_models.json strategy; qwen3.5-local renamed

### Problem

Codex CLI ships a built-in model catalog for OpenAI cloud models only.
When pointing it at a local Ollama endpoint with an unregistered model ID
(`qwen3.5:9b-nvfp4`), Codex falls back to 272K token defaults. The local
server never sees a context that large; it crashes with overflow errors.
Plan mode and structured output also break silently because capability
flags (`supports_reasoning`, `supports_tools`) are unknown.

Compounding this: the previous local alias `qwen3.5-local:latest` was
deleted from Ollama and replaced by `qwen3.5:9b-nvfp4` — 6 source files
across two repos still referenced the old ID.

### Fix (immediate — local machine)

1. Created `~/.codex/local_models.json` with correct context caps and
   capability flags for all Ollama models (local + cloud-proxy).
2. Added `model_catalog_json = "~/.codex/local_models.json"` to
   `[model_providers.ollama-launch]` in `~/.codex/config.toml`.
3. Key values for `qwen3.5:9b-nvfp4`:
   - native `context_length = 262144` (from `ollama api/show model_info`)
   - safe local cap: `context_window = 32768` (Mac RAM constraint)
   - `supports_reasoning = true`, `supports_tools = true`

### Model ID rename sweep

| File | Old → New |
|------|-----------|
| `orama-system/setup_macos.py` | `qwen3.5-local:latest` → `qwen3.5:9b-nvfp4` |
| `orama-system/portal_server.py`a-circumflex+euro+quote (cp1252-misread em-dash)`PT/packages/local-agents/src/client.js` | DEFAULTS + comment |
| `PT/packages/local-agents/tests/client.test.js`a-circumflex+euro+quote (cp1252-misread em-dash)`~/.codex/local_models.json` is the **single source of truth** for
  local Ollama model metadata (context caps, capability flags).
- Auto-generate with `scripts/gen_local_models_json.py` whenever Ollama
  model list changes. Never edit manually.
- In v2: `perpetua-core/config/ollama_catalog.json` mirrors this schema;
  `ollama_catalog.example.json` ships with the repo; real file gitignored.
- Apply Pattern B (`11-idempotency-and-guard-patterns.md` §3): one config
  file, many consumers (Codex CLI, HardwarePolicyResolver, LocalAgentClient).
- CI gate: `test_no_stale_model_ids` greps for retired / old-alias model
  IDs in all source files and fails if any are found.

**Spec doc**: `docs/v2/13-local-model-catalog-strategy.md`

---

## 2026-05-08 — V1 supervisor shipped; v2/14 spec written

**Context:** Three reference files synthesised into V1 implementation + V2 spec.

**Perpetua-Tools changes (all in same commit):**
- `orchestrator/supervisor.py` — V1 `OrchestrationSupervisor` (jsonl, no DB)
- `orchestrator/worker_registry.py` — static WORKER_REGISTRY (echo, ollama-mac, lmstudio-mac, codex, gemini)
- `utils/action_validator.py` — two-phase gate
- `scripts/mac_probe.sh` — hardware detection (Mac14,9 = 16GB/16GPU/arm64/standard tier)
- 5 new FastAPI endpoints under `/v1/jobs`
- 192/192 tests green (including 13 new smoke tests)

**orama-system v2 spec added:**
- `docs/v2/14-supervisor-and-anthropic-patterns.md` — V2 DB persistence, audit log, MAESTRO/SWARM gates, token-efficiency rules, hardware-aware installer plan

**Key rules confirmed for all agent sessions:**
- `MAX_DEPTH=1`, `MAX_THREADS=25` (Anthropic hard limits)
- All backends: use POST API, never `ollama run` in a shell
- `gemini --yolo` required for non-interactive dispatch
- Checkpoint written BEFORE CancelledError propagation

**Legacy `orchestrator.py` FastAPI unchanged** — backwards-compatible, will be superseded by V2.

---

---

## 2026-05-08 — Cross-platform portal + start.sh + Windows counterpart

**Context:** All `start.sh` CLI modes were only surfaced at the terminal; the portal UI had no stop/restart/discover/policy buttons. `pid_on_port()` and `wait_for_port()` used `lsof` and `nc` exclusively, which are macOS-only. No Windows entry point existed.

### What broke / what was missing

| Gap | Root cause |
|-----|-----------|
| Portal version stuck at 0.9.9.7 | Forgot to bump `VERSION` constant after v1 work |
| `/v1/jobs` not visible in UI | V1 supervisor endpoints added to PT but portal never polled them |
| `--stop`, `--discover`, `--hardware-policy` terminal-only | `portal_server.py` had no corresponding routes |
| `lsof -ti tcp:PORT` fails on Linux | `lsof` not always installed; `ss` is the Linux equivalent |
| `nc -z` fails on bare containers | Minimal Docker images ship without `nc`; bash `/dev/tcp` is always available |
| `nc -z -w 1`a-circumflex+euro+quote (cp1252-misread em-dash)`setup_macos.py` runs on Linux/CI | Preflight has macOS-specific `xattr` and `codesign` calls; hard-errors on Linux |
| No Windows start script | No way to boot the stack on the Windows node without WSL |

### Fixes shipped (commit 252a473 on main)

**`portal_server.py`:**

1. `VERSION = "0.9.9.8"` — bump.
2. **Service Controls bar** (`_render_service_control_section()`):
   - `POST /api/stop` — SIGTERMs all three services using `_pid_on_port()` (cross-platform: `lsof` → `ss` → fallback)
   - `POST /api/restart/{service}` — kills + `subprocess.Popen(start_new_session=True)` respawn; logs to `.logs/<svc>.log`
   - `POST /api/rediscover` — runs `discover.py --force` in a thread executor; returns updated IP summary
   - `GET /api/hardware-policy` already existed; JS now calls it from the "Re-check Policy" button and toasts result
3. **Supervisor Jobs panel** (`_render_supervisor_jobs_section()`):
   - `_probe_supervisor_jobs()` added to the `asyncio.gather` in `api_status()` — zero extra RTT; result included in `supervisor_jobs` key
   - `GET /api/v1/jobs` proxies to PT; JS `refreshJobs()` polls every 8s independently
4. New CSS: `.svc-btn`, `.svc-ctrl`, `.jobs-table` — dark theme compatible
5. `import signal, subprocess, time` added (were missing)

**`start.sh`:**

```bash
# Before (macOS-only):
pid_on_port() { lsof -ti "tcp:$1" 2>/dev/null | head -1 || true; }
while ! nc -z localhost "$port" 2>/dev/null; do

# After (cross-platform):
pid_on_port() {
  if command -v lsof; then lsof -ti "tcp:$1" | head -1
  elif command -v ss;  then ss -tlnp "sport = :$1" | grep -oP 'pid=\K\d+' | head -1
  elif command -v fuser; then fuser "$1/tcp" | awk '{print $1}' | head -1
  fi
}
_port_open() {
  if command -v nc; then nc -z localhost "$1" 2>/dev/null
  else (echo >/dev/tcp/localhost/"$1") 2>/dev/null; fi
}
while ! _port_open "$port"; do
```

- `_nc_probe()` helper in banner — same `nc` vs `/dev/tcp` dual path; all 3 probes remain parallel
- `setup_macos.py` now guarded: `[ "$_OS_NAME" = "Darwin" ]` — Linux/CI skip with INFO log

**`windows/` folder:**

| File | Role |
|------|------|
| `start.ps1` | All 6 CLI modes; `Get-PidOnPort` (netstat), `Wait-ForPort` (TcpClient), `Start-Service` (Popen equivalent via `ProcessStartInfo`) |
| `install.ps1` | Idempotent venv + deps + openclaw.json defaults; pywin32 + colorama |
| `requirements-windows.txt` | pywin32, colorama, netifaces |
| `README.md` | Parity table + architecture notes |

**`windows/start.ps1` platform-translation table:**

| bash | PowerShell |
|------|-----------|
| `lsof -ti tcp:PORT` | `netstat -ano` + regex for LISTENING PID |
| `nc -z localhost PORT` | `TcpClient.ConnectAsync().Wait(500ms)` |
| `open URL` | `Start-Process URL` |
| `ipconfig getifaddr en0` | `Get-NetRoute` gateway → `.110` heuristic |
| `kill PID` | `Stop-Process -Id PID -Force` |
| subprocess bg `&` | `ProcessStartInfo(CreateNoWindow=true)` + async stream copy |
| `.paths` sourced file | `.paths.ps1` dot-sourced with `$PtDir`, `$UsPython` vars |

### Key rules derived

- **Never assume `lsof`** — it is missing on Debian minimal, Alpine, and distroless containers. Always cascade: `lsof → ss → fuser`.
- **Never assume `nc`** — Alpine and scratch images ship without it. Bash `/dev/tcp` is a shell built-in and always available.
- **`setup_macos.py` guard is mandatory** — the script calls `xattr -cr` and `codesign -s -` which are macOS-only binaries. It will `FileNotFoundError` on Linux.
- **`-w 1` (timeout) must come before the host in `nc`** — `-z -w 1 host port` works; `-z host port -w 1` silently ignores the flag on some Linux builds.
- **`Start-Job` vs `ProcessStartInfo`** — PowerShell `Start-Job` creates a new PS host (slow, large). `System.Diagnostics.ProcessStartInfo` with `CreateNoWindow=true` is the correct analogue of bash `cmd &`.
- **Windows GPU: 1 model at a time** — `install.ps1` prints this as a hard warning; `start.ps1` never sets `LM_STUDIO_WIN_ENDPOINTS` to multiple URLs.

### Verification

```bash
# macOS
bash -n start.sh && echo OK                           # syntax
bash scripts/mac_probe.sh | python3 -m json.tool       # JSON valid
python3 -c "import ast; ast.parse(open('portal_server.py').read()); print('OK')"

# Linux (simulate)
_OS_NAME=Linux bash start.sh --status                  # setup_macos skipped
ss --version && lsof --version || true                 # check which probe tools exist
```

### Deferred

- `start.ps1` end-to-end on a real Windows + PowerShell 5.1 box (no WSL)
- `install.ps1` tested with Python 3.11 from python.org (not conda/pyenv)
- Portal `POST /api/restart/portal` self-restart (kills the process serving the request — needs supervisor process or systemd watchdog to respawn)

---

---

## Session 2026-05-08 — start.sh Warm-Cache + Parallel Probes (Layer-3 side)

**Problem:** When PT's `alphaclaw_manager --resolve` failed (Python missing, network blip), `start.sh` fell back to bare offline defaults — services started with empty endpoints. Banner tier-detection ran 3 sequential `nc -z` probes (3s worst case).

**Fixes shipped (1 commit on `main`):**

1. **Warm-cache fallback** — when PT resolve fails, read `.state/routing.json` (last known good state from PT) and re-export `PT_MODE=cached`, `PT_DISTRIBUTED`, `PT_ALPHACLAW_PORT`, `WIN_IP`, `PT_SCENARIO`, `PT_MODE_SOURCE=cache`, `PT_AGENTS_STATE`. Stale-data warning is always printed so operators know cache is in use.
2. **Parallel banner probes** — 3 `nc -z -w 1` calls now run as background subshells writing to mktemp files, then `wait`. Total banner delay = max(1s) instead of 3s.

**Why this matters with PT v0.9.9.9:**
- PT now writes `scenario_name` into routing.json. Warm cache reads it and exports `PT_SCENARIO` so banner + portal can show the *last* scenario when resolve is dead.
- The PT scenario engine + warm cache together mean the constellation degrades gracefully: live → cached → offline-defaults, never opaque hang.

**Gemini CLI syntax update:** `gemini` invocations must now use `--yolo` (alias `-y`) so the subprocess auto-approves tool prompts. Without it Gemini stalls on the first sandbox gate. Patched `scripts/spawn_agents.py:_dispatch_gemini` and the `SKILL.md` example.

**Deferred** (both Mac + Win required):
- Live `start.sh` validation across LAN (cache hits when Win .108 unreachable but Mac .110 still pingable)
- Verify banner tier=1 (FULL) when both nodes online

Re-run in ~2 days:
```bash
./start.sh --probe-only       # just probes, no service start
nc -z -w 1 192.168.x.108 1234  # confirm Win LMS reachable
```

---

---

## 2026-05-14: Monumental Error — Wrong Repo Build Documented as Canonical Phase 1

**Session:** docs/v2 enrichment (intended: post-Phase 1 reconciliation)
**Artifact:** `docs/wiki/10-wrong-repo-build-what-not-to-do.md` ← read this for the full delta record

### What happened

An AI agent (Claude) built a v2 kernel in the **wrong local directory**
(`OpenClaw/perpetua-core`) instead of the correct one (`code/oramasys/perpetua-core`),
pushed it to a **non-canonical GitHub remote** (`diazMelgarejo/perpetua-core`), then created
`docs/v2/15-phase1-as-built.md` and modified 4 other `docs/v2/` files documenting this
wrong build **as if it were the canonical Phase 1 implementation**.

The canonical v2 build had already been shipped **13 days earlier** (2026-05-01) at:
- `oramasys/perpetua-core` — commit `2f717f5`, 32 tests, 65-line kernel + all 6 plugins
- `oramasys/oramasys` — commit `d123420`, 4 tests, FastAPI glass-window
- `oramasys/agate` — commits `755e1de`/`f1d5a57`, hardware policy spec + GGUF RFC

All 3 canonical repos were `0 ahead / 0 behind` their GitHub remotes. The docs were
correct before the wrong commit (`5f21e83`).

### Violations of the agreed spec

| Spec decision | Canonical (`oramasys/perpetua-core`) | Divergent (`diazMelgarejo/perpetua-core`) |
|---------------|--------------------------------------|------------------------------------------|
| D8 revision: 65-line + plugins | ✅ 65-line engine + `graph/plugins/` | ❌ ~130-line integrated, no plugins/ |
| D7: Pydantic v2 BaseModel | ✅ `class PerpetuaState(BaseModel)` | ❌ `pydantic.dataclasses.dataclass` |
| Spec: `scratchpad: dict[str,Any]` | ✅ `scratchpad: dict[str, Any]` | ❌ `scratchpad: str = ""` |
| D2: `oramasys` org | ✅ `oramasys/perpetua-core` | ❌ `diazMelgarejo/perpetua-core` |
| Python 3.11+ | ✅ `requires-python = ">=3.11"` | ❌ Python 3.9.6 |
| `@tool` decorator | ✅ `graph/plugins/tool.py` done | ❌ absent |
| Async GossipBus | ✅ `aiosqlite` | ❌ `sqlite3` sync |

### Root cause

- Did not verify `git remote -v` before first push of the new repo
- Did not check whether canonical build already existed before "building Phase 1"
- Skipped the AskUserQuestion gates that the plan required
- Proceeded without brainstorming/planning approval

### Fix applied (this commit)

- `docs/v2/15-phase1-as-built.md` (wrong-build doc) → **MOVED** to `docs/wiki/10-wrong-repo-build-what-not-to-do.md` as a cautionary artifact
- `docs/v2/00-context-and-decisions.md`, `04-build-order.md`, `06-open-questions.md`, `README.md` → **REVERTED** to `935ce54` (pre-5f21e83, correct state)

### Never again

1. **Before any `git push` to a new repo:** run `git remote -v` and confirm the remote matches the agreed org (`oramasys/*` for v2, `diazMelgarejo/*` for v1-legacy)
2. **Before "building Phase 1":** search for the repo in the correct org — it may already exist
3. **Never skip `AskUserQuestion` gates** in a plan — they exist precisely to prevent this
4. **`oramasys/*` is the ONLY valid home for v2 code.** `diazMelgarejo/*` is v1-legacy only.
5. **The shipped canonical scaffold (`oramasys/*`) takes precedence** over any in-session build

**Full agent-readable post-mortem:** `docs/wiki/10-wrong-repo-build-what-not-to-do.md` — enriched 2026-05-16 with complete incident timeline, failure mode analysis, spec violation table, and "what future agents MUST do" checklist. Read this before any v2 docs/ or oramasys/ work.

---

---

## 2026-05-16 — Codex — Claude CLI auth must run outside sandbox

### What was learned

- Symptom: `claude -p --permission-mode dontAsk --max-budget-usd 0.25 "Reply with exactly: claude-ready"` returned `Not logged in · Please run /login`.
- False lead: repeated `claude auth login --claudeai` inside the sandbox printed `Login successful`, but `claude auth status --text` stayed unauthenticated.
- Root cause: Claude's OAuth callback server and credential persistence can fail inside a sandbox. Debug output showed `Failed to start OAuth callback server: Failed to start server. Is port 0 in use?`.
- A second risk was an install split: PATH `claude` pointed to a native install while the npm-global binary was newer. Auth probes must use the same binary that orchestration will call.

### Decisions made

- Run `claude auth login --claudeai` outside the sandbox or with explicit escalation when fixing auth for automated Claude workers.
- Treat `Login successful` as insufficient until both `claude auth status --text` and a real `claude -p` probe pass.
- Compare `which claude`, `claude --version`, and any known full binary path before debugging orchestration failures.

### Runbook

```bash
which claude
claude --version
claude auth login --claudeai
claude auth status --text
claude -p --permission-mode dontAsk --max-budget-usd 0.25 "Reply with exactly: claude-ready"
```

If failure persists:

```bash
claude --debug --debug-file /tmp/claude-auth-debug.log auth login --claudeai
sed -n '1,120p' /tmp/claude-auth-debug.log
```

Do not trust sandboxed login loops when the debug log reports an OAuth callback server failure.

---

## 2026-05-16 — Codex — GitHub MCP invalid transport postmortem

### What was learned

- `invalid transport` in `~/.codex/config.toml` is a schema error before it is an auth error.
- The npm GitHub MCP server is a stdio server: use `command = "npx"`, GitHub server `args`, and
  `[mcp_servers.github.env]`.
- `bearer_token_env_var` belongs to HTTP MCP config, not this stdio GitHub setup.
- A set PAT is not proof of a working MCP config; `codex mcp list` must parse, classify, launch, and
  show the env mapping.
- The failure was a classification failure: Codex stayed in "auth missing" mode while Claude moved to
  "transport schema invalid" mode and validated each change.
- Nuance matters: GitHub's remote HTTP MCP endpoint validly uses `bearer_token_env_var`; the local
  npm stdio server does not.

### Decisions made

- Saved this as a Codex memory and repo skill guidance.
- Future agents must validate MCP fixes with `codex mcp list`, not visual inspection.
- Created reusable skills for Codex MCP debugging and agent failure postmortems.

### Open questions

- Codex should improve its own warning so GitHub stdio setup does not suggest an HTTP-only auth field.

→ [wiki/11-codex-github-mcp-config.md](wiki/11-codex-github-mcp-config.md)

---

## 2026-05-16: `.gbrain-source` is machine-local — never commit it

`.gbrain-source` is a kubectl-style worktree pin written by `/sync-gbrain`. It contains
the name of the indexed gbrain source for this worktree on this machine (e.g. `orama-src`).
Different machines register different source names; committing it would break gbrain routing
on every other machine that clones the repo.

**Fix:** Added `.gbrain-source` to `.gitignore` (2026-05-16).
**Rule:** If you see `.gbrain-source` untracked in any repo, add it to `.gitignore` immediately. Do not `git add` it.

- Linux `ip route get 8.8.8.8` — validate on Ubuntu 22.04 + Debian 12 + Alpine 3.19

---

---

## 2026-05-16: RC-1 Orchestration Session — Gemini routing, OpenRouter smart-merge, Vite pitfalls

### 1. Gemini is NOT the default reader — "Gemini-Analyzer use-case only"

**Decision (locked in RC-1 master plan):** Gemini is routed ONLY for:
- Visual diff / screenshot comparison
- Whole-repo architecture mapping (>5000-line diffs, multi-file cross-cutting)
- Multi-file stale-doc detection
- Second-opinion code review when explicitly requested

**The default reading/coding agent is the OpenRouter free-model stack** (Nemotron 3 Super → MiniMax M2.5 → DeepSeek V4 Flash → gpt-oss-120b → GLM 4.5 Air → Ling 2.6 Flash → Free Router).

**Why this matters:** Previous practice had Gemini mentioned generically as "the reader" — this caused agents to default to Gemini for every file read, wasting quota and adding latency. Gemini is a specialized instrument, not the default hammer.

**Canonical policy:** `bin/orama-system/mcp-orchestration/SKILL.md` §2 "Routing strategy".

---

### 2. Smart-merge pattern for OpenClaw config patching

**Problem:** Naively patching `openclaw.json` with a model policy risks overriding the user's local `primary` (which must remain `ollama/qwen3.5:9b-nvfp4` on Mac per CLAUDE.md hard requirement).

**Pattern established:**
- Policy file uses `fallbacks_to_merge` and `models_to_merge` keys (NOT `primary`/`fallbacks`)
- Apply script PRESERVES existing `agents.defaults.model.primary` unless `--force-primary` flag is passed
- Removes Gemini from the front of any existing fallbacks list before appending the OpenRouter chain
- Gemini is pushed to END of fallbacks as 3rd-choice (not 1st)
- Script lives at: `scripts/apply-openrouter-free-defaults.sh`
- Verify with: `scripts/verify-openrouter-models.sh`

**Rule:** Any script that patches live config must read the existing primary first and only append/merge fallbacks. Never clobber local primary.

---

### 3. jq dedup-preserve-order — avoid `unique_by(.)`

**Problem:** `unique_by(.)` in jq sorts alphabetically as a side effect. When deduping a fallbacks array after merging, this silently promoted Gemini to the top of the list (alphabetically first `google/*`), defeating the entire "Gemini as last resort" policy.

**Correct pattern:**
```bash
| reduce .[] as $item (
    [];
    if any(.[]; . == $item) then . else . + [$item] end
  )
```
This deduplicates while preserving insertion order — first occurrence wins. Use this whenever you need dedup-without-sort in jq.

**Why `unique_by(.)` is wrong:** It's documented to sort, but in practice you expect it to just dedupe. The combination of merge + unique_by produces a sorted array, not a priority-ordered one.

---

### 4. Vite + TypeScript composite-project pitfalls

Two distinct issues that both caused build/typecheck failures:

**Issue A: tsconfig composite conflict**
- Problem: `tsconfig.json` had `"include": ["src", "vite.config.ts"]`. The `tsconfig.node.json` used `composite: true` and also covered `vite.config.ts`. TypeScript expected pre-built `.d.ts`/`.js` output for the composite sub-project and errored with TS6305.
- Fix: Remove `vite.config.ts` from `tsconfig.json` include. The file is already handled by the node sub-project.
- Canonical: `"include": ["src"]` in `tsconfig.json`

**Issue B: Path aliases must be declared in BOTH places**
- Problem: `@/*` alias declared in `tsconfig.json` paths works for TypeScript type resolution but Vite's Rollup bundler doesn't read tsconfig. Build failed with "Rollup failed to resolve import `@/components/Shell`".
- Fix: Add `resolve.alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) }` to `vite.config.ts` in addition to the tsconfig paths entry.
- Rule: Every `@/*`-style alias needs two registrations: one in tsconfig (for tsc/IDE) and one in vite.config.ts (for Rollup/bundler).

---

### 5. MCP orchestration canonical SKILL.md location

**Before:** Two drift-prone root files (`OpenClaw/MCP_ORCHESTRATION_SKILL.md`, `OpenClaw/MCP_ORCHESTRATION_SKILL_v2.md`) each evolving independently.

**After:** Single canonical skill at `bin/orama-system/mcp-orchestration/SKILL.md`. The old root files are redirect stubs pointing to it.

**Rule:** If you see multiple files claiming to be "the MCP orchestration policy", the canonical one is in `bin/orama-system/mcp-orchestration/SKILL.md`. The others are stubs — do not edit them.

---

### 6. Vite operator console — build-verified RC-1 baseline

- Stack: React 18 + Vite 5 + TanStack Query 5 + Tailwind 3
- Source: `src/` (16 files, 0 TypeScript errors, build output ~68KB gzip)
- Backend proxy: `/api/*` → `http://localhost:8001` (portal_server.py)
- Key files: `src/features/command-center/CommandCenter.tsx` polls `/api/app/state` every 5s; falls back to `mockState` on error
- `src/data/mockState.ts` provides offline-capable fixtures so the console always renders
- Commit: `1cfb31e` on `web-app-orchestration-v2-implementation`

---

### 7. Branch hygiene — FF-merge timing

When feature work spans multiple commits across a branch and partial work is already on main:
- Merge foundation commits to main early (after a coherent milestone) so history stays linear
- Use `git merge --ff-only` when the branch has only additive commits ahead of main — avoids a merge commit in the log
- Do NOT squash multi-session work that has already been reviewed — preserves attribution per commit

---

---

## 2026-05-16 — Claude — No sleep chains: `sleep N && cmd` is blocked

> *First triggered: 2026-05-16 session (npm install wait). Re-triggered: 2026-05-29 session (claude update wait). Canonicalized as a low-level skill on 2026-05-29.*

### What was learned

The shell hook detects `sleep` as the leading token of a Bash command and rejects the entire call. This covers:
- `sleep N && <command>`
- `sleep N; <command>`
- Chains of shorter sleeps attempting to work around the block (`sleep 5 && sleep 5 && cmd`)

Correct mental model: **the block is on the first token, not on the sleep duration**. There is no threshold below which the chain becomes acceptable.

Pattern that re-triggered the rule on 2026-05-29: waiting for a `claude update` background task output file by running `sleep 15 && cat <file>` then `sleep 20 && cat <file>`. Both rejected. The correct form — an until-loop or waiting for the `run_in_background` notification — was only reached on the third attempt.

### Decisions made

The rule is now **canonical** — ported from the ephemeral `~/.claude/projects/.../memory/feedback_no_sleep_chains.md` into:

1. **`orama-system/bin/orama-system/skills/no-sleep-chains/SKILL.md`** — low-level skill with correct-pattern quick reference, invocable by any agent.
2. **`docs/LESSONS.md`** (this entry) — dated audit trail.
3. Original memory file retained in `~/.claude/projects/…/memory/` as the session-scoped pointer.

### Correct patterns (canonical)

| Situation | Correct form |
|-----------|-------------|
| `run_in_background: true` task | Wait for system notification — do nothing |
| Poll file for keyword | `until grep -q "..." file; do sleep 3; done` |
| Poll file for size | `until [ "$(wc -l < file)" -gt N ]; do sleep 3; done` |
| Wait for service port | `until curl -s http://host/health >/dev/null; do sleep 2; done` |
| Wait for PID to exit | `until ! kill -0 $PID 2>/dev/null; do sleep 2; done` |

Full patterns with examples: [`bin/orama-system/skills/no-sleep-chains/SKILL.md`](../bin/orama-system/skills/no-sleep-chains/SKILL.md)

### Open questions

None — rule is fully specified and enforced at the shell level.

---

---

## 2026-05-17 — Codex — Gemini is opt-in, gbrain sync comes from the gstack sync skill

### What was learned

- Gemini should not be treated as the default reader path. Keep it behind the explicit analyzer lane.
- The default agent path is local ollama on Mac first, then OpenRouter free-model fallbacks, with Windows local coder lanes used when available.
- From Codex, gbrain sync is driven by the gstack `sync-gbrain` skill and the `gstack-brain-sync` binary in the installed gstack toolchain.

### Decisions made

- Update orchestration docs so Gemini is analyzer-only by explicit request.
- Use `~/.claude/skills/gstack/bin/gstack-brain-sync --discover-new` to refresh queued worktree changes, then `--once` to drain and push.

### Runbook

```bash
~/.claude/skills/gstack/bin/gstack-brain-sync --discover-new
~/.claude/skills/gstack/bin/gstack-brain-sync --once
```a-circumflex+euro+quote (cp1252-misread em-dash)`047ec27`)
faithfully captures the direction without pixel-matching: layout positions,
copy, icon glyphs, exact colors may diverge from the mockup as long as the
aesthetic holds. Future visual upgrades should reference the mockup as a
tone-setter, not a spec.

This explicit "non-binding mockup" framing keeps the operator console
**fluid**: the backend routes shipped first; the UI tracks the routes; the
mockup tracks the UI's vibe. None of the three is a contract for the others.

---

## 2026-05-17 — `install-mcp-stack.sh --mirror-skills` ships orama SKILL.md cross-platform

Added `--mirror-skills` flag to `bin/orama-system/scripts/install-mcp-stack.sh`.
Copies the 7 orama-system SKILL.md files (mother + afrp + cidf + gstack +
mcp-install + mcp-orchestration + skillify) to:

- `~/.claude/skills/<name>/SKILL.md` (Claude Code)
- `~/.codex/skills/<name>/SKILL.md` (Codex CLI)
- `~/.gemini/skills/<name>/SKILL.md` (Gemini CLI, if dir exists)
- OpenClaw skill registry (via `openclaw skill set` if CLI present)

Idempotent (sha256-compares before copy), dry-run-safe, silently skips
absent platform directories. Hermes/ECC will adopt by adding their own
target line to `_PLATFORMS` array — one-line extension per new platform.

---

## 2026-05-17 — Salvage code translation spec written

Spec at `docs/superpowers/specs/2026-05-17-salvage-translation-design.md`
covers the *how* of porting wrong-repo
(`diazMelgarejo/perpetua-core@9cb153a`) valuable assets into canonical
(`oramasys/perpetua-core@2f717f5`) plugin structure. Companion to the
existing selection spec (`2026-05-14-salvage-plugins-design.md`).

Key decisions:
- Multi-agent labor split: Gemini reads, Codex writes, Sonnet reviews,
  Opus orchestrates
- Branch model: local `feat/salvage-plugins-rc1` in canonical clone with
  `PROGRESS.md` as living tasklist + git-native distributed locking
- TDD: unit + integration + Hypothesis property-based, against canonical's
  32 tests + new plugin tests
- Waved ordering: Wave 0 parallel reads → Wave 1 engine foundation
  (AFRP gate) → Waves 2+3 parallel ports → Wave 4 integrative decisions
- Architectural revision protocol: kernel reshape permitted during port if
  bounded and AFRP-gated

---

## 2026-05-17 — Salvage translation + v1 IP-aware discovery landed (73 tests green)

Generation labeling (per Canonical Repo Registry):

- **v2-planning (`oramasys/perpetua-core` on `feat/salvage-plugins-rc1`):** max_steps cycle guard (Task 5, a3712b2); set_entry/compile (Task 6, ad67577); 5 new plugins — routing/LabelRouter (Task 7, 283af1a), tool_node/ToolNode async subprocess (Task 8), validator/Validated pre-post (Task 9), interrupt_guard/resume_policy (Task 10, a7c9772), parallel/parallel_dispatch (Task 11, 8eaba56); typed ChatMessage/ChatHistory closing OQ17 (Task 12, 309c60a); canonical perpetua_core/discovery/ verbatim port from v1 (Task 13, 222450b); Hypothesis invariants (Task 15, 8b1a3f1). Engine grew 66→102 lines; all 32 baseline tests still green; 24 new tests added; full suite 56/56.

- **v2-planning (`oramasys/oramasys` on `feat/dispatch-discovery-bridge`):** dispatch_node now accepts an optional BackendRegistry and calls select_backend() from canonical perpetua_core.discovery; graceful degradation via state.error when registry empty (Task 14, 21605f6). 4 baseline tests preserved + 1 new = 5/5.

- **v1-legacy (`diazMelgarejo/Perpetua-Tools` on `feat/ip-aware-discovery`):** tactical fix — perpetua/discovery/ with Backend dataclass (Task 1, 9b11e9d), async health_probe (Task 2, 7e4a40b), BackendRegistry autodetect + register_by_ip (Task 3, 06c1da3), tier+task selector (Task 4, 8d42f2e), orchestrator/agent_launcher.resolve_backend_for_spec (Task 4b, bf15d0d). Shape designed to match v2 canon (Task 13 copied it forward verbatim). 12/12 tests pass. New orchestrator/agent_launcher.py is additive — root agent_launcher.py untouched; a follow-up may consolidate.

- **cross-cutting (`orama-system/docs/`):** plan at docs/superpowers/plans/2026-05-17-salvage-translation-v1-discovery.md (1962 lines, 16 tasks), spec at docs/superpowers/specs/2026-05-17-salvage-translation-design.md (315 lines), PROGRESS.md ledger at perpetua-core repo root, this LESSONS append.

LangGraph concept map (CSV) mirrored 1:1 in v2-planning code: State=PerpetuaState · Node=async fn · Edge=string · ConditionalEdge=LabelRouter · Cycle=max_steps guard · START/END=sentinels · Checkpointer=plugin (shipped earlier) · Send()=parallel_dispatch · ToolNode=plugin · Validator=plugin · InterruptGuard=plugin.

### Race-condition LESSON

Wave 1A dispatched 7 parallel subagents on the same `oramasys/perpetua-core` branch. Three of them (C8/C9/C11) hit a `.git/index.lock` race and the serializing winner (C11) committed all three plugins under one SHA `8eaba56` mis-labeled "Task 11". **No work was lost** — each subagent verified its writes against the plan post-commit. But this is a pattern to avoid:

**Lesson:** for parallel dispatch on the SAME branch, the orchestrator should either (a) own commits — subagents write files only, orchestrator git adds + commits each — or (b) give each parallel subagent its own worktree. Option (a) is simpler. Option (b) is cleaner for very long-running work.

### Push policy

All three code branches stay **local** until user reviews end-to-end on Mac+Win hardware (Mac Ollama localhost:11434 + Win LM Studio 192.168.254.103:1234). Only cross-cutting docs (this LESSONS append + plan doc) push immediately to `orama-system`.

### Build philosophy reaffirmed

Per user direction: "simultaneous top-down + bottoms-up development." v2-planning bakes architectural decisions first (engine + plugins + canonical discovery), v1-legacy ships the first implementation (discovery wired into agent_launcher), then Track D copies v1 → v2 verbatim so the shape lives in one canonical home. v1 is the live sandbox; v2 absorbs what works.

---

---

## 2026-05-17 — Policy enshrinement (hardware + Node.js)

### HARD POLICY: Mac inference via Ollama only — LM Studio Mac is a MIRROR

This is a **non-negotiable hardware safety rule**, not a preference.

| Machine | Endpoint | Role | Inference? |
|---------|----------|------|-----------|
| Mac (Apple Silicon) | `localhost:11434` (Ollama) | Primary Mac inference | ✅ ALWAYS |
| Mac (Apple Silicon) | `localhost:1234` (LM Studio Mac) | **MIRROR ONLY** | ❌ NEVER dispatch here |
| Win (RTX 3080) | `192.168.254.103:1234` (LM Studio Win) | Primary Win inference + heavy models | ✅ ALWAYS |

**Why this is a hard rule:**
- `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2` physically runs on the RTX 3080.
- LM Studio Mac proxies all Win models over the LAN — they appear in `/v1/models` on Mac but Mac cannot actually run them.
- Dispatching the same heavy model to **both** LM Studio Mac and LM Studio Win simultaneously = "double barrel" = two concurrent requests funneled to one RTX 3080 = GPU contention → potential hardware damage.
- See also `docs/LESSONS.md` 2026-04-29 entry: `/v1/models` endpoint presence does NOT indicate physical home.

**Code enforcement (2026-05-17):**
- `perpetua/discovery/registry.py` (v1) and `perpetua_core/discovery/registry.py` (v2): `lmstudio-mac` seed annotated `# MIRROR — discovery only`.
- `perpetua/discovery/selector.py` (v1) and `perpetua_core/discovery/selector.py` (v2): added `_MIRROR_BACKENDS = frozenset({"lmstudio-mac"})`, filtered from ALL candidate selection including model_hint resolution. `_TIER_HOSTS["mac"]` now contains only `{"ollama-local"}`.

**Agents / future plans:** Before dispatching inference, check `b.name not in _MIRROR_BACKENDS`. Never route by model presence in `/v1/models` alone.

---

### HARD POLICY: Node.js — always resolve explicit full path

**Problem:** `node` in PATH resolves to system v14.21.3 (macOS bundled). Any script using `#!/usr/bin/env node` or bare `node` silently runs on v14 and fails with modern syntax (`??=`, optional chaining, top-level await, etc.) with cryptic errors.

**Rule:** Whenever invoking Node for scripts or CLI tools, resolve to the explicit full NVM path:

```bash
# Check available versions
ls ~/.nvm/versions/node/

# Use the pinned v22+ binary directly
~/.nvm/versions/node/v22.22.2/bin/node script.js

# For npm-installed CLIs (openclaw, gemini, etc.)
~/.nvm/versions/node/v22.22.2/bin/openclaw ...
~/.nvm/versions/node/v22.22.2/bin/npx ...
```

**Wrapper pattern** (for Gemini CLI and others that use shebang):
```bash
# ~/.local/bin/gemini  (must be on PATH before ~/.nvm shims)
#!/bin/bash
exec ~/.nvm/versions/node/v22.22.2/bin/node \
     ~/.nvm/versions/node/v22.22.2/bin/gemini "$@"
```

**Verification before any Node script:**
```bash
node --version   # if this returns v14.x.x → use explicit path
~/.nvm/versions/node/v22.22.2/bin/node --version  # should return v22.22.2
```

**Prior instances of this lesson:**
- 2026-04-xx: Gemini CLI broken because `#!/usr/bin/env node` resolved to v14 (wrapper fix applied).
- 2026-04-29: `openclaw` CLI requires Node ≥ v22; full path used: `~/.nvm/versions/node/v24.14.1/bin/openclaw`.

---

---

## 2026-05-20 — Claude — fix(docs): file:// link broke repo_hygiene test

### What was learned
- `docs/TDD.md` was added in commit `dba34d6` with a `file://` absolute hyperlink
  on line 5 pointing to a local plugin cache path.
- `scripts/review/repo_hygiene.py` has a strict rule: all markdown hyperlinks
  must be **repo-relative**. It rejects `file://`, `/absolute`, and drive-letter
  paths outright (line 152–153 of the script).
- The test `test_repo_hygiene_script_runs_clean` runs this script and asserts
  `returncode == 0`, so any new `file://` link introduced in a doc will fail CI.

### Root cause
External plugin/skill references that live outside the repo (e.g.
`~/.claude/plugins/...`) cannot be linked with a hyperlink in tracked docs.
They can only be referenced as plain text / backtick code spans.

### Decisions made
- Replaced the hyperlink with an inline `code` reference so the path is still
  human-readable but does not trigger the repo-relative link check.
- Pattern to follow for **any future external path reference** in tracked docs:

```
# Bad  — triggers hygiene checker:
[label](file:/home/user/.some/local/path)

# Good — plain backtick, not a hyperlink:
`~/.some/local/path`
```

### Prevention checklist
Before committing any markdown file that references a local filesystem path:
1. grep the diff for `file://` and `/absolute` and `~` inside `()` link syntax
2. Run `python scripts/review/repo_hygiene.py .` locally before committing
3. The TDD.md pre-commit checklist (docs/TDD.md) now covers this explicitly

### Related
- Failing test: `tests/test_repo_hygiene.py::test_repo_hygiene_script_runs_clean`
- Hygiene rule: `scripts/review/repo_hygiene.py` lines 152–153
- Fixed in: `fix/repo-hygiene-tdd-link`


<!-- Append entries below. Format:
## 2026-05-21 — Claude — RAG planning: answer search/memory questions via gbrain+CRG before designing

### What was learned

When asked "how are we implementing search/RAG?", ran gbrain + CRG queries BEFORE opening any files.
GBrain returned the authoritative answer in one query: `docs/v2/02-modules/rag-and-memory` was a
**stub** ("deferred from v2.0 kernel") — confirmed RAG was NOT yet implemented despite the repo
appearing mature. CRG returned 0 nodes (unbuilt/unindexed for this session). This saved ~10 inline
file reads and gave a more accurate architectural picture.

**Rules:**
1. For "what does this system do?" questions — gbrain query first, file reads second.
2. A stub doc is a complete answer: "not implemented" is as definitive as an implementation.
3. CRG returning 0 nodes = graph not built in current session. Fall back to gbrain. Never assume 0 = absent.

---

---

## 2026-05-21 — Claude — Spawning parallel agents: write plans first, implement second

### What was learned

User asked to "spawn the best agents suited to each subtask to finish this job soonest" for
a large planning session. The right approach:

1. **Brainstorm + design first** (single session) — get user agreement on architecture before spawning.
2. **Write ALL plan docs to a branch** before spawning implementation agents.
3. **Each agent gets one plan doc** — a well-scoped plan with exact file paths, failing test
   code, exact commands is a complete agent brief. No additional context needed.
4. **Use dispatching-parallel-agents** for tasks that are independent (FTS5 changes in
   perpetua-core are independent of gstack submodule changes in orama-system).
5. **Model selection by task complexity:**
   - Mechanical wiring (ContextNode, ContextEndpoint): Claude Haiku
   - Async + schema changes (GossipBus FTS5): Claude Sonnet
   - Multi-file with shell scripts (gstack submodule): Claude Sonnet
   - Tests + TDD compliance: Claude Sonnet

**Anti-patterns to avoid:**
- Spawning agents before plans are written — agents need exact file paths and failing tests, not vague goals.
- Using the same model for every task — wastes budget on mechanical tasks.
- Not writing v2 forward-plan docs during the brainstorm — v2 design is cheapest to capture during active design session.

---

---

## 2026-05-21 — Claude — GossipBus FTS5: zero-dep keyword recall for agents

### What was learned

The GossipBus `tail()` method returns recent-N events by time — no content search.
Adding FTS5 to SQLite requires only:
1. `CREATE VIRTUAL TABLE gossip_fts USING fts5(...)` with `content='gossip'` (backed by the gossip table)
2. Two triggers (AFTER INSERT, AFTER DELETE) to keep FTS in sync
3. One migration block in `init_db()` that populates FTS from existing rows if fts_count=0 and row_count>0

This is zero new Python dependencies — FTS5 is bundled in Python's `sqlite3`. It gives BM25 ranking
for free. Pattern: always check if SQLite FTS5 can solve a search problem before reaching for a
vector store.

**Key gotcha:** `gossip_fts MATCH ?` raises `OperationalError: fts5: syntax error` on empty query
string. Always guard with `if not query.strip(): return []`.

---

---

## 2026-05-21 — Claude — gstack optional submodule: detection order matters

### What was learned

For optional tools that may be installed via multiple paths (PATH, skill, submodule, OCI),
detection order must be explicit and idempotent:

1. Check `shutil.which("gbrain")` FIRST — respects user's existing install regardless of how it was done.
2. Check `~/.claude/skills/gstack` SECOND — covers Claude skill installs.
3. Check `tools/gstack/` THIRD — covers submodule installs.

Stop at the first hit. Never require all three to agree. Never raise on detection failure.

**Pattern:** Always write `detect_gstack() -> dict` style detection functions (return a dict,
never bool-only, never raise) so the caller can log the source and version alongside availability.
- 2026-05-17: General policy enshrined — applies to ALL Node tooling.

---

---

## 2026-05-21 — Claude — Hybrid LanceDB+FTS5 over FTS5-only: decision trail practice

### What was learned

**AI initial proposal:** FTS5-only retrieval (zero new dependencies). Rationale: YAGNI, maximum simplicity.

**User override:** Hybrid LanceDB+FTS5 with RRF k=60. Rationale: Ollama+bge-m3 is already a hard
system requirement (CLAUDE.md). LanceDB has nearly zero marginal cost. Semantic recall is worth one dep.

**Key insight:** When evaluating "add a new dep?", check if its runtime prerequisites are already required.
LanceDB alone is not free. LanceDB + bge-m3 on a machine that already requires bge-m3 is near-free.
The question is "incremental cost given current constraints" not "absolute cost from zero."

**Hybrid disaster recovery posture:** FTS5 always works (no Ollama, no LanceDB). LanceDB+bge-m3 is
opportunistic — wrapped in `try/except`. RRF falls back to `fts_hits` when `vec_hits=[]`. This means
the system degrades gracefully rather than failing hard when the embedding stack is down.

**Pattern: Document AI suggestion vs user override.** When the user makes a non-obvious architectural
choice that differs from the AI's recommendation, record both in the plan doc's decision trail table.
This preserves the reasoning for future sessions and prevents "why did we do this?" questions.
Format: `| # | Topic | AI Suggestion | User Decision | Rationale |` — one row per decision.

---

---

## 2026-05-21 — Claude — Fire-and-forget asyncio.create_task() + GC prevention

### What was learned

`asyncio.create_task()` creates a task that the event loop holds only via a **weak reference**.
If the calling code doesn't hold a strong reference, the task can be garbage-collected before
completion — silently. No exception, no warning.

**Fix (user-required):** module-level `_pending_embeds: set[asyncio.Task] = set()` + pattern:

```python
task = asyncio.create_task(self._embed_and_store(row_id, payload))
_pending_embeds.add(task)
task.add_done_callback(_pending_embeds.discard)
```

This creates a strong reference (set membership) that is automatically released when the task
completes (via `discard` callback). The set never grows unbounded.

**Why AI missed it initially:** the GC hazard is a Python-specific subtlety that requires knowing
CPython's weak-reference behavior for asyncio tasks. It's not obvious from the task's API.

**Rule:** Any `asyncio.create_task()` that is fire-and-forget MUST register the task in a
module-level strong-reference container with a done callback to clean up. No exceptions.


---

---

## 2026-05-22 — Claude — RAG v1 Backport shipped to Perpetua-Tools

**What shipped:** 4 RAG modules backported from `feat/rag-gstack-optional-v1` (this repo)
into `diazMelgarejo/Perpetua-Tools` on branch `feat/rag-backport-v1` (PR #28).
All 3 bug-class gaps from Gemini 3.5 Flash review applied. 345/345 tests pass.

**Key adaptation:** v2 plan targets `oramasys/perpetua-core` paths (`perpetua_core.gossip`, etc.).
v1 backport uses `orchestrator/` in PT. GossipBus is a NEW capability in v1 — PT had no
event log / SQLite before this backport.

**IMMUTABLE RULE re-confirmed:** `diazMelgarejo/*` = v1, implement code. `oramasys/*` = v2,
plan only via `/docs/v2/`. Override requires AskUserQuestion.

**Deferred items from v1 Backport Candidates table:**
- Items 5–7 (GbrainSearchTool, MemoryNode, dispatch_node wiring) deferred to next sprint
- v2.1 EmbeddingCircuitBreaker deferred — see `docs/v2/20-rag-and-memory-design.md`

**Evidence doc:** `docs/2026-05-22-rag-v1-backport-shipped.md`

---

---

## 2026-05-24 — Claude — CI hygiene blocks machine-specific OpenClaw paths

### What was learned

- `scripts/review/repo_hygiene.py` scans all tracked Markdown files, including plan
  docs under `docs/plans/`, for workstation-specific OpenClaw paths (the
  `$OPENCLAW_ROOT/...` pattern the scanner blocks).
- CI reports this only through `tests/test_repo_hygiene.py::test_repo_hygiene_script_runs_clean`,
  so inspect the hygiene script output directly for the exact file and line.
- PR #39 (Cursor DRAFT, closed 2026-05-24) was raised to fix this; the path scrub was
  already absorbed in commit `fd2accd` (main) before #39 was reviewed.

### Decision made

- Use `$OPENCLAW_ROOT/...` in docs and command snippets whenever a path needs to reference
  the parent OpenClaw checkout or any orama-system path beneath it.
- The `$OPENCLAW_ROOT` convention is enforced by the `OPENCLAW_WORKSTATION_LAYOUT`
  scanner in `repo_hygiene.py` (D9).

---

---

## 2026-05-25 — Claude (Cursor) — code-review pressure Test B (tool-order)

### What was learned

Pressure Test B (skill loaded, graph-first) was run as an empirical **dry-run** on `main` with delta `HEAD~5` (18 files; code-review touch: skill link fixes + new `docs/how-to/first-run-and-code-review.md`). The orama-system CRG index on disk is healthy (1417 nodes, 1257 bge-m3 embeddings via `graph.db`), but **this Cursor workspace does not expose `code-review-graph` MCP** — only `OpenClaw/.mcp.json` registers `uvx code-review-graph serve`. Observed investigator order was Read/git/Grep → sqlite proxy for stats → failed gbrain → hung `uvx` CLI; no `detect_changes` or `get_review_context` calls. Full matrix: `bin/orama-system/skills/code-review/references/pressure-test-notes.md` § Test B results 2026-05-25.

### Decisions made

- Treat Cursor sessions without CRG MCP as **documented partial compliance**; recommend registering the same server from `OpenClaw/.mcp.json` into the project/workspace MCP config before claiming full Test B pass.
- Align init examples in `SKILL.md` (`*_tool` suffix) with `mcp-tools-crg.md` tool names in a follow-up doc fix.

### Open questions

- Should pressure Test B script explicitly allow `git diff HEAD~N` when the tree is clean, or require a synthetic uncommitted edit?

---

## 2026-05-25 — Cursor (subagent) — CRG + gbrain verify on orama-system

### What was learned

- `move_agent_to_root` → `orama-system` succeeded; committed `.cursor/mcp.json` enables Cursor CRG when the user reloads MCP (tools still absent from this subagent session’s `mcps/` folder).
- **gbrain** `search` works from host shell with network (`first-run-install`, `crg-embed-mode` top hits).
- **CRG CLI** (`uvx code-review-graph`) works after cold install: `status --repo "$REPO"` → 1489 nodes; `detect-changes --repo "$REPO" --base 51816ce5` on session delta (risk 0.65, 4 bash functions without tests in graph). Use `--repo`, not `--repo-root`; MCP-only names like `list-graph-stats` are invalid on CLI.
- Fresh clone may show `nodes: 0` until `uvx code-review-graph build --repo <orama-system>` — not automatic in `first-run.done`.
- Sandbox `first-run-install.sh status` cannot write `~/.orama-system/first-run.json` (PermissionError) but probes still print; use non-sandbox for state file updates.

### Decisions made

- Mark fortify TODOs done for Cursor `.cursor/mcp.json` and `--help` vs `--version` probe; keep gbrain sandbox ENOTFOUND and graph-before-Read hook as open.
- No code fix required for merge; doc checklist updates only.

### Open items (2026-05-25 — do not duplicate here)

Tracked as checklists elsewhere (read the owner doc, not this log):

| Topic | Owner doc |
|-------|-----------|
| Fortify / Test B / MCP / policy gaps | [`bin/orama-system/skills/code-review/references/pressure-test-notes.md`](../bin/orama-system/skills/code-review/references/pressure-test-notes.md) § Fortify pass |
| CLAUDE-instru weaning + CI grep | [`docs/plans/2026-05-23-claude-instru-weaning-autoplan.md`](plans/2026-05-23-claude-instru-weaning-autoplan.md) § Open TODOs |
| Agent first-open surfaces (Cursor / Claude / OpenClaw) | [`docs/reference/agent-first-open-visibility.md`](reference/agent-first-open-visibility.md) |
| E2E bootstrap known gaps | [`docs/how-to/first-run-and-code-review.md`](how-to/first-run-and-code-review.md) § Known gaps |

---

## 2026-05-25 — Cursor — Official git identity + co-author policy (docs)

### What was learned

- **Canonical policy** lives in [`docs/wiki/08-git-hygiene-and-branching.md`](wiki/08-git-hygiene-and-branching.md#official-commit-identity-policy-2026-05-25): four approved primary authors (`cyre`a-circumflex+euro+quote (cp1252-misread em-dash)`Lawrence@cyre.me`, `Codex <codex@openai.com>`); `Co-authored-by` allows well-known public AI/vendor domains and only two Gmail addresses.
- **Enforcement:** `bash scripts/git/install-local-hooks.sh` → `check_identity.sh` (pre-commit) + `check_commit_message.sh` (commit-msg). Replaced the old “forbid all agent co-author substrings” hook with an allowlist model aligned with `repo_hygiene.py`.
- **Agent default:** sessions should not add `Co-authored-by` to their own commits even when hooks allow public AI attribution for human-authored merges.

### Decisions made

- Document-release sync: `CLAUDE.md` §3/§6, `CONTRIBUTING.md`, `agent-first-open-visibility.md`, `.cursor/rules/no-commit-attribution.mdc` point at the official section without removing prior approved identities.

---

## 2026-05-25 — Cursor — Security fixes 1–3 (orama + Perpetua-Tools)

### What was learned

- Fixes **1–3** from [`OpenClaw/v1/2026-05-23-security-markdown.md`](../../OpenClaw/v1/2026-05-23-security-markdown.md) are implemented: env-based Gemini key, `scan_tracked_secrets` in hygiene, bearer auth on portal/API/PT jobs, memory redaction before GossipBus persist.
- Fixes **4–6** (MCP path allowlist, remote endpoint URL policy, least-privilege MCP) stay **queued** — documented in [`docs/SECURITY-POLICY.md`](SECURITY-POLICY.md) and [`docs/v2/23-security-preconditions.md`](v2/23-security-preconditions.md).
- `ORAMA_CONTROL_PLANE_TOKEN` + `ORAMA_INSECURE_DEV=0` is the production posture; dev stacks can set `ORAMA_INSECURE_DEV=1` without a token.

### Decisions made

- Canonical policy: [`docs/SECURITY-POLICY.md`](SECURITY-POLICY.md); v1 index: [`OpenClaw/v1/README.md`](../../OpenClaw/v1/README.md).
- Perpetua-Tools mirrors orama git hooks via `scripts/git/check_identity.sh`.

---

---

## 2026-05-27 — Cursor Cloud — git attribution, AlphaClaw branch anchoring, push queue

### What was learned

**Cursor Cloud git (not fixable via `CURSOR_AGENT=0`):**

- Cloud VMs set `CURSOR_AGENT=1`; there is no supported user toggle to disable it.
- Cursor redirects `core.hookspath` to `~/.cursor/agent-hooks/<base64(workspace-path)>/` and may run `commit-msg.cursor.co-author` (injects unwanted `Co-authored-by` trailers).
- Mitigations that work: `chmod -x` on `commit-msg.cursor.co-author`, restore repo `.githooks` via `install-local-hooks.sh`, user-level `~/.cursor/openclaw/` + `sessionStart` hook (`install-user-git-environment.sh`), and hook-free `git commit-tree` via `commit-clean.sh`.
- Desktop **Agents → Attribution** does not reliably control cloud agent commits.

**Approved identity:** `cyre <diazMelgarejo@gmail.com>`; `repo_hygiene.py` / `check_commit_message.sh` block unattributable Gmail co-authors.

**AlphaClaw fork layout** ([`diazMelgarejo/AlphaClaw`](https://github.com/diazMelgarejo/AlphaClaw)):

| Branch | Role |
|--------|------|
| `main` | Upstream mirror only ([`origin/main`](https://github.com/diazMelgarejo/AlphaClaw/tree/main)) |
| `feature/MacOS-post-install` | Integration branch — must **contain** current `origin/main` |
| `cursor/sync-attribution-guards-6421` | Contrib — PR target is **integration**, not `main` |

Both integration and contrib branches must have **merge-base(branch, origin/main) = origin/main** (nearest common ancestor is upstream mirror tip). Shallow `git clone --depth 1` on a stale tip produced orphan roots (e.g. detached `a64d183`) — always run `bash scripts/git/alphaclaw-align-all.sh` after clone.

**Push order when credentials available:**

1. `bash scripts/cursor/push-openclaw-stack.sh` (orama branch + AlphaClaw)
2. Push `feature/MacOS-post-install` (includes `merge(upstream): sync origin/main…`)
3. Push `cursor/sync-attribution-guards-6421`
4. PR: `cursor/sync-attribution-guards-6421` → `feature/MacOS-post-install`
5. PR: `feature/MacOS-post-install` → `main` when integration is ready

### Decisions made

- Canonical automation in orama-system: `alphaclaw-sync-integration-with-main.sh`, `alphaclaw-align-all.sh`, `alphaclaw-realign-contrib-branches.sh`, `alphaclaw-contrib-checkout.sh`, `push-openclaw-stack.sh`.
- `.cursor/environment.json`: `ALPHACLAW_INTEGRATION_BRANCH`, `ALPHACLAW_CONTRIB_BRANCH`, cloud `install` calls `alphaclaw-align-all` after AlphaClaw clone.
- Wiki: `docs/wiki/12-cursor-cloud-commit-attribution.md`, `docs/wiki/13-alphaclaw-fork-contrib-branches.md`; rules: `.cursor/rules/cursor-cloud-environment.mdc`, `no-commit-attribution.mdc`.

### Prevention checklist

1. On every cloud session: `bash scripts/cursor/install-user-git-environment.sh` and `bash scripts/git/alphaclaw-align-all.sh`.
2. Before AlphaClaw commit: verify `git merge-base HEAD origin/main` equals `git rev-parse origin/main`.
3. Never open AlphaClaw feature PRs with base `main` when commits belong on integration/contrib lines.
4. Mandatory commit sequence: `git add <paths>` → `bash scripts/git/verify-staged-for-commit.sh` → `bash scripts/git/commit-clean.sh -m "..."`; confirm with `git show --stat HEAD` before push.

---

## 2026-05-27 — Claude (current session) — ❗️CRITICAL HITL VIOLATION & DOCTRINE

### TL;DR
A **Cursor agent on 2026-05-25 at 13:44** created `OpenClaw/_pt-merge-work/` as a throwaway `git clone` for security-fix-6 merge work. **A Claude agent in a later session (2026-05-27) autonomously promoted this scratch clone to "canonical Perpetua-Tools" status** — rewriting memory files, `CLAUDE-instru.md`, and PT-side docs to point there. **The user never authorized this.** Reverted today.

### The HITL Doctrine (NEW — must apply across all agents, all repos)

> **Rule: A tactical decision made by an agent in a single session MUST NEVER override a long-term architectural decision made by a human.**
>
> Examples of "long-term human decisions" agents may NEVER override silently:
> - Canonical repo paths / disk locations
> - Branch naming and ownership conventions
> - Commit identity / author allowlists
> - Org-level architecture (`diazMelgarejo/*` vs `oramasys/*` separation)
> - Directory layout in user-controlled folders (`OpenClaw/`, `~/code/oramasys/`)
> - Module name renames (e.g. `coordinator` → `orchestrator`)
>
> **Before any such decision, the agent MUST call `AskUserQuestion` (or stop and ask in plain prose) and wait for explicit approval.**
> Technical evidence (newer commits, fewer artifacts, "cleaner state") is NOT sufficient grounds to redesignate canonical paths.

### What went wrong (full trace)

| Step | Date | Agent | Action | HITL violation? |
|------|------|-------|--------|-----------------|
| 1 | 2026-05-25 10:05 | Cursor (workspace `e90fd68b…` on OpenClaw root) | Active in OpenClaw root folder | — |
| 2 | 2026-05-25 13:44 | Cursor agent | `git clone diazMelgarejo/Perpetua-Tools.git _pt-merge-work` at OpenClaw root | ⚠️ MINOR — created scratch clone with no convention for cleanup |
| 3 | 2026-05-25 13:44–13:51 | Cursor agent | merged `main` into `2026-05-25-005-security-fix-6-mcp-profiles`, pushed | — (committed under user's real identity, which IS approved) |
| 4 | 2026-05-27 (early in this session) | Claude (Sonnet 4.6, this conversation, pre-compaction) | Used `_pt-merge-work/` as working dir for RAG items 5–7 (afa4542) | ⚠️ MEDIUM — should have stopped and asked which repo to write to |
| 5 | 2026-05-27 (post-audit, pre-compaction) | Claude (same session) | Audited disk repos, noticed `_pt-merge-work` had newer commits, declared it "canonical", **rewrote** `project_perpetua_tools_path.md` + `CLAUDE-instru.md` + the RAG-shipped doc to reflect that | ❌ CRITICAL — autonomous architectural redesignation without `AskUserQuestion` |
| 6 | 2026-05-27 (this turn, post-compaction) | Claude (same session, user pushback) | User caught the violation; reverted all changes | ✅ resolved |

### Forensic evidence

- `_pt-merge-work/` reflog earliest entry: `clone: from https://github.com/diazMelgarejo/Perpetua-Tools.git` at `2026-05-25 13:44:12 +0800`
- Folder created at OpenClaw root level (not inside `perplexity-api/`) — consistent with Cursor having workspace access to OpenClaw root
- Cursor workspace `~/Library/Application Support/Cursor/User/workspaceStorage/e90fd68bd7c440906de9c318e4dbd282/workspace.json` opened on `file:///…/OpenClaw` at `2026-05-25 10:05`, retrieval index updated at `10:25`
- No Claude Code `.jsonl` session for OpenClaw on 2026-05-25 (confirmed — only May 22 and May 27 sessions exist for that project) → **Claude was not at the keyboard when the clone happened**
- All commits in `_pt-merge-work` are authored by `cyre <Lawrence@cyre.me>` (your real, approved identity), meaning the Cursor agent used your local git config — no identity violation, just a workspace pollution

### Decisions made (canonical, after revert)

1. **Canonical Perpetua-Tools = `OpenClaw/perplexity-api/Perpetua-Tools/`** — restored (this is the user's long-term decision since the directory was created)
2. **`_pt-merge-work/` is a one-off Cursor scratch clone** — should be cleaned up after the RAG items branch is pulled into canonical
3. **The `* 2` files** (e.g. `LESSONS 2.md`) in `perplexity-api/Perpetua-Tools/docs/` are **macOS APFS dedup artifacts**, not contamination — they are byte-identical to the originals and harmless. Previous agent claim that they marked the repo as "stale" was wrong.
4. **New rule for all future agents (Claude, Cursor, Codex, Conductor)**: before reorganizing canonical paths, branch conventions, or any long-term architectural attribute, call `AskUserQuestion` with a decision brief.

### Files reverted in this remediation

- `~/.claude/projects/-Users…OpenClaw/memory/project_perpetua_tools_path.md` — back to pointing at `perplexity-api/Perpetua-Tools/`
- `OpenClaw/CLAUDE-instru.md` line 96 — link restored to `perplexity-api/Perpetua-Tools/docs/openclaw-setup.md`
- `OpenClaw/CLAUDE-instru.md` directory-tree section — `perplexity-api/Perpetua-Tools/` shown as canonical, `_pt-merge-work/` flagged as scratch

### Outstanding cleanup (user-authorized in next step)

- Pull `origin/main` into canonical `perplexity-api/Perpetua-Tools/`
- Pull `origin/2026-05-27-006-rag-items-5-7` work into canonical (the RAG items 5–7 commits live on the remote; safe to re-fetch)
- `/sync-gbrain` to refresh the worktree-pinned source for the canonical path
- After verification: delete `_pt-merge-work/` entirely

### Open questions

- Should we add a pre-commit hook or wrapper to **block agent-initiated `git clone` into OpenClaw root** without a `.scratch-clone-justification` file?
- Should there be a `~/.claude/skills/hitl-major-decisions/` skill that any agent must invoke before path/architecture changes?

---

---

## 2026-05-31 — Claude (Opus 4.8) — Tri-repo migration audit + alignment plan + tooling stabilization

### What was learned
- **Tri-repo migration is Gate-2 partial, not complete.** A 3-agent audit mapped AlphaClaw capabilities → PT counterparts: PT controls AlphaClaw fully (adapter 25 methods + `alphaclaw_manager.py`); controls OpenClaw *via* AlphaClaw by design; but orama's `bin/mcp_servers/openclaw_bridge.py` still calls AlphaClaw **directly** (Gate-3 gap). 8 gaps remain. **Canonical roadmap now: [`Perpetua-Tools/docs/2026-05-31-tri-repo-alignment-completion-plan.md`](../../perplexity-api/Perpetua-Tools/docs/2026-05-31-tri-repo-alignment-completion-plan.md).**
- **gbrain fixed:** `prepare:true` against the Supabase pooler caused `prepared statement does not exist` write failures → set `prepare:false`. DB URL lives in `~/.gbrain/.env` (source it for CLI; MCP variant may need reconnect). Resynced all 3 per-repo sources. See [`bin/orama-system/gstack/SKILL.md` §GBrain Ops](../bin/orama-system/gstack/SKILL.md). **CRG registry is empty** — build per repo before relying on it.
- **macOS dup ` 2` files: ruled OUT OneDrive/iCloud** (both audited + cleared). Historical Finder/IDE keep-both, dormant. Repo-wide dedup: quarantined to `~/dup-quarantine-2026-05-31` (nothing deleted). Cross-ref the 2026-05-27 ghost-ref entry + AlphaClaw `wiki/07`.

### Decisions made
- `lib/mcp`+`lib/agents` retirement is **held until Gate 2 is green** (live authenticated smoke-test + local-agents tests). Code is superseded; ceremony is not done.
- `orama-system` local checkout is **volatile** (vanished twice this session; cause not OneDrive/iCloud). A background guardian auto-restores it (`~/.orama-guard.log`, mirror `~/.orama-system-backup.git`).

### Open questions
- What process deletes `orama-system`? (user running `sudo fs_usage` to catch it.) The 8 Gate-2/3 gaps remain (see alignment plan).

**Cross-repo:** [PT LESSONS](../../perplexity-api/Perpetua-Tools/docs/LESSONS.md) · [AlphaClaw Lessons](../../AlphaClaw/docs/Lessons.MD)

---

---

