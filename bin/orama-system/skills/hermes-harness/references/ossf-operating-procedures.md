# Hermes harness — operating procedures

Progressive-disclosure body extracted from `SKILL.md` for OSSF-1 line budget.

## Operating Thesis

1. **Durable source:** orama-system and ECC own reusable skills and rules.
2. **Harness edge:** Hermes and other tools adapt loading/invocation only at the edge.
3. **No private imports:** never ship raw `~/.hermes`, secrets, personal memory, or account tokens.
4. **Parallel to OpenClaw:** `openclaw-skills` owns OpenClaw config; this
   skill owns Hermes onboarding and partner prompts.

## Persistent Pulse Cadence

The Mac OpenClaw orchestrator stays persistent and self-resuming across gateway
restarts via an `openclaw cron` job (`mac-orchestrator-pulse`), not a manual loop.

- **Base heartbeat: every 15 minutes.** Probes the Win Hermes co-orchestrator +
  Win coder (LM Studio) via `probe_lan_peer.py --json`, checks the LAN-peer job
  queue (`lan_peer_assign.py list` / `list --peer`), and dispatches if both
  sides are idle and work is queued.
- **Fast loop while busy: self-reschedules to +5 minutes.** After a successful
  dispatch, the pulse schedules a one-shot `openclaw cron add --at +5m` follow-up
  that repeats the same check. Each successful dispatch re-arms the next +5m
  follow-up; an idle check (nothing queued) lets the chain end naturally and
  the base 15m heartbeat takes back over. This gives fast iteration while jobs
  are flowing without polling every 15m when there is nothing to do.
- **Failure handling:** retry a failing dispatch up to 10x with exponential
  backoff (~5min cap), then log a FAILURE summary to
  [`.agent/memory/working/REVIEW_QUEUE.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/.agent/memory/working/REVIEW_QUEUE.md) and stop — never
  schedule a follow-up on failure, never crash the pulse or the gateway.
- **Resumable by construction:** the job lives in `openclaw.json`'s
  `.cron.jobs` (persisted config, not ephemeral state), so it survives gateway
  restarts and resumes on its own — no manual re-arm needed.
- **Setup/edit:** use `openclaw cron add` / `openclaw cron edit` — never hand-edit
  `.cron.jobs` via `jq`; the job schema (`schedule.kind`/`everyMs`, `payload.kind`,
  etc.) differs from what a raw JSON example might suggest and an invalid shape
  silently breaks the live gateway (see `lesson_67ddcb4837f2` in PT's semantic
  memory). Full cadence rationale + commands:
  [`../../../../docs/how-to/openclaw-hermes-cross-harness-wiring.md`](../../../../docs/how-to/openclaw-hermes-cross-harness-wiring.md)
  § 11.

## Universal Invocation Protocol

Hermes and OpenClaw are co-equal harness adapters over one canonical skill corpus.
All dispatch must normalize to the cross-harness contract in
[`references/hermes-universal-invocation-protocol.md`](references/hermes-universal-invocation-protocol.md)
(harmonized with `openclaw-skills/references/universal-skill-protocol.md`).

### Core envelope (L3 intent — required)

```json
{
  "skill_id": "pt-orama-council",
  "args": {},
  "agent_id": "hermes"
}
```

### Dispatch envelope (L2 — Hermes + partners)

Committed examples use env placeholders only; runners expand paths at runtime.

```json
{
  "skill_id": "pt-orama-council",
  "args": {"task": "review security checklist"},
  "agent_id": "hermes",
  "executor_id": "codex",
  "harness": "hermes",
  "orama_system_root": "$ORAMA_SYSTEM_PATH",
  "canonical_skill_root": "bin/orama-system/skills",
  "transport": {
    "partner": "codex",
    "profile": "fanout"
  }
}
```

| Field | Rule |
| ------- | ------ |
| `agent_id` | Audit owner (who initiated) |
| `executor_id` | Runner (`codex`, `agy`, `hermes`); required when delegating |
| `transport` | Opaque L2 dispatch intent for OTel/Periscope audit (v2 schema in `/docs/v2`) |
| `orama_system_root` | Placeholder in docs; absolute only inside runners |

L1 transport (CLI flags) stays internal to `dispatch_codex_partner.py` and AGY scripts.

### Core result (required)

```json
{
  "status": "ok",
  "files_modified": [],
  "follow_up_actions": []
}
```

Hermes may add optional fields: `output`, `warnings`, `errors`, `checks`, echoes.
`blocked` is a Hermes alias for `needs_input`. Path casing mismatches → `warnings[]`, not `blocked`.

## Session Close-Out: Update the Board (mandatory for significant landed work)

**Trigger phrase:** "update all agent comms" (or "update the board" /
"post to the whiteboard" / "notify all peers") means run **both**
mechanisms below together, in one pass — not one or the other. This is
the standing invocation for "tell every other agent/peer what happened,"
whether said explicitly by the user or inferred from context (e.g. after
resolving a multi-agent conflict, after verifying another agent's
concurrent work, after landing anything a peer would otherwise have to
rediscover).

Not just for `coord-N` fan-outs — **any** session that lands substantive
work (a real code change, a closed plan, a fix that other agents/peers
would want to know about) updates both mechanisms before ending, so a
peer checking the board mid-work doesn't rediscover it independently:

1. **GossipBus whiteboard log** ([`scripts/agent_coordination.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/scripts/agent_coordination.py)
   `log <agent_id> "<message>"`) — one line, states
   what landed, the commit(s)/PR(s), and anything still open that a peer
   with different access (push rights, a different host, etc.) could
   help unblock. Cheap, always do it.
2. **Peer-inbox drop** (`references/results/<peer>-<date>-<topic>.md`,
   this directory) — for anything substantial enough to need more than
   one line: what shipped, what's still open and why, what's explicitly
   deferred and to where. Follow the existing drop format (see any file
   in `references/results/` for the shape — status line, what-landed
   table, open/needs-a-peer section, not-touched-explicitly-deferred
   section). This is the persistent record; the whiteboard log is the
   pointer to it.

Established 2026-07-22 during a frugality/privacy-gate + repo-hygiene
close-out session — see `references/results/mac-2026-07-22-frugality-p3-
and-repo-closeout-status.md` for a worked example of both mechanisms used
together. **Step-by-step Hermes recipe:**
[`references/update-all-agents-comms.md`](references/update-all-agents-comms.md).
Corollary: check the board while waiting on any background
process (a push, a test run, another agent's job) — don't idle.

## Subskill Registry (Hermes-facing)

Thin local wrappers point at canonical command cards. Never cache full skill bodies.

| Wrapper slug | Canonical target | Harness | Notes |
| -------------- | ------------------ | --------- | ------- |
| `pt-orama-council` | `commands/pt-orama-council/SKILL.md` | Hermes / Codex | 5-model council |
| `pt-orama-review` | `commands/pt-orama-review/SKILL.md` | Hermes / Codex | Findings-first review |
| `pt-orama-delegate` | `commands/pt-orama-delegate/SKILL.md` | Hermes / AGY | Bounded delegation |
| `pt-hardware-policy` | `commands/pt-hardware-policy/SKILL.md` | Hermes | `hardware-affinity-gate` edge |
| `lan-peer-self-talk` | `commands/lan-peer-self-talk/SKILL.md` | Hermes | Mac↔Win LAN peer — [operator playbook](references/lan-peer-self-talk.md#operator-playbook) |
| `windows-hermes-setup` | `commands/windows-hermes-setup/SKILL.md` | Hermes | Windows PATH, ECC doctor, partner CLI — [playbook](references/windows-hermes-setup.md) |
| `pt-orama-lesson-mining` | `commands/pt-orama-lesson-mining/SKILL.md` | Hermes / Codex | **Optional** — session insight graduation; not installed by default |
| `hermes-harness` | `SKILL.md` (this file) | Hermes | Install / provider / import |
| `local-inference` | `../local-inference/SKILL.md` | Hermes | Redirect stub |
| `openclaw-status` | `../openclaw-skills/skills/openclaw-status/SKILL.md` | Hermes | Mac fabric primary |
| `openclaw-restart` | `../openclaw-skills/skills/openclaw-restart/SKILL.md` | Hermes | Mac fabric primary |
| `openclaw-add-secret` | `../openclaw-skills/skills/openclaw-add-secret/SKILL.md` | Hermes | Mac-only; Win → `blocked` |

Paths are relative to `bin/orama-system/skills/`. Install thin wrappers:

```powershell
python bin\orama-system\skills\hermes-harness\scripts\install_hermes_thin_skills.py --install
```

## Hermes Bootstrap Gate

Idempotent check before non-trivial dispatch on Windows. Return JSON health envelope
(core result + optional `checks` / `output`):

```powershell
$env:HERMES_HOME = if ($env:HERMES_HOME) { $env:HERMES_HOME } else { "$env:LOCALAPPDATA\hermes" }
$installDir = Join-Path $env:HERMES_HOME "hermes-agent"
if (-not (Test-Path "$installDir\.git")) { throw "HERMES_NOT_INSTALLED" }
& $env:HERMES_GIT_BASH_PATH --noprofile --norc -lc 'echo hermes-bash-ok'
```

```json
{
  "status": "ok",
  "files_modified": [],
  "follow_up_actions": [],
  "harness": "hermes",
  "checks": ["hermes-bash-ok", "install_dir_present"],
  "output": {"bash": "hermes-bash-ok", "install_dir": "$HERMES_HOME/hermes-agent"}
}
```

Partner canaries: `python bin\orama-system\skills\hermes-harness\scripts\verify_partner_canaries.py`

## Windows Bring-Up

Canonical setup playbook (absorbed from Hermes self-improve `windows-hermes-setup`):
[`references/windows-hermes-setup.md`](references/windows-hermes-setup.md).
Install thin wrapper:
`python bin\orama-system\skills\hermes-harness\scripts\install_hermes_thin_skills.py --install`.

**CRG on Windows:** `.cursor/mcp.json` must use `CRG_OPENAI_BASE_URL=http://localhost:1234/v1`
(LM Studio, not Ollama `:11434`). Run `bash bin/orama-system/scripts/sync-cursor-mcp.sh` or see
[`../code-review/references/crg-platform-endpoints.md`](../code-review/references/crg-platform-endpoints.md).

Use PowerShell with explicit UTF-8 when writing files:

```powershell
[Console]::InputEncoding=[System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$OutputEncoding=[System.Text.UTF8Encoding]::new($false)
```

Default `HERMES_HOME` to `$env:LOCALAPPDATA\hermes`; the repo lives at
`$env:HERMES_HOME\hermes-agent`, managed uv at `$env:HERMES_HOME\bin\uv.exe`,
and `HERMES_GIT_BASH_PATH` points at Git Bash.

Before using one-shot or agent modes, put the installed venv launcher on
`PATH` and set `HERMES_GIT_BASH_PATH` to a literal `bash.exe`. Detailed Windows
recipe: `docs/wiki/15-hermes-windows-harness.md`.

`HERMES_GIT_BASH_PATH` must point to a literal `bash.exe`. Prefer full Git for
Windows. If reusing GitHub Desktop's bundled Git, a `bash.exe` hardlink beside
`usr\bin\sh.exe` is acceptable only if this passes:

```powershell
& $env:HERMES_GIT_BASH_PATH --noprofile --norc -lc 'echo hermes-bash-ok'
```

### Bare `python` vs venv — a recurring, hard-to-notice class of bug

Any `.ps1` script in this skill (or elsewhere on Windows) that invokes
`python <script.py>` bare — instead of the repo's `.venv\Scripts\python.exe`
— is silently at the mercy of whatever `python` resolves to first on PATH
at that moment. That is **not guaranteed to be the venv with this repo's
own `requirements.txt` installed**, especially under Task Scheduler, a
freshly-opened shell, or a script invoked from a different working
directory than expected.

**Symptom pattern:** a script that works fine when run manually from the
repo root fails elsewhere with `ModuleNotFoundError` for a package that
*is* actually installed — just in a different interpreter than the one
that ran. Confirmed live, repeatedly, this session:

- `coord_pulse.ps1` — false "missing websockets" (it was installed, just
  not in the interpreter that ran)
- `service_watchdog.ps1` — same class, `lan_peer_assign.py` peer-drop calls
- `coord_comms_board.ps1` — `agent_coordination.py heartbeat pulse` failed
  with `ModuleNotFoundError: No module named 'aiosqlite'` (installed in
  Perpetua-Tools' venv, not the system Python bare `python` resolved to)

**Fix:** dot-source the shared resolver and use its result instead of bare
`python`:

```powershell
. (Join-Path $env:ORAMA_SYSTEM_PATH 'scripts\lib\get-best-python.ps1')
$PythonExe = Get-BestPython $env:ORAMA_SYSTEM_PATH
& $PythonExe some_script.py --arg
```

**Cross-repo scripts need their own resolution per repo** — a script that
calls into both orama-system and Perpetua-Tools python files (e.g.
`coord_comms_board.ps1` calling PT's `agent_coordination.py`) needs
`Get-BestPython $env:ORAMA_SYSTEM_PATH` for one and
`Get-BestPython $env:PERPETUA_TOOLS_PATH` for the other — they are
different venvs with different installed packages, not interchangeable.

**Exception — legitimate bare `python` before a venv exists:** bootstrap
scripts that *create* the venv itself (`ensure_requirements.ps1`,
`install.ps1`'s `python -m venv ...` calls) correctly use bare `python`,
since the venv doesn't exist yet at that point in execution. Don't "fix"
those.

**Related gotcha — cwd-dependent state resolution across repos.** Even
with the correct venv python, a script in orama-system invoking a
Perpetua-Tools Python file can still resolve state to the wrong repo:
`agent_coordination.py`'s `GossipBus` falls back to
`git rev-parse --git-common-dir` against the *current process cwd* when no
explicit state dir is set. A PowerShell script running from
orama-system's directory that calls into PT's `agent_coordination.py`
silently anchors PT's coordination database inside orama-system's own
`.git`, not PT's -- confirmed live as `ERROR: failed to initialize the
coordination database: unable to open database file`. Fix: set
`$env:PT_STATE_DIR = Join-Path $env:PERPETUA_TOOLS_PATH '.state'`
explicitly before any such call, bypassing the cwd-dependent fallback.

## Procedure

### 1. Clone or Repair Hermes

```powershell
$env:HERMES_HOME = if ($env:HERMES_HOME) { $env:HERMES_HOME } else { "$env:LOCALAPPDATA\hermes" }
$target = Join-Path $env:HERMES_HOME "hermes-agent"

if (Test-Path "$target\.git") {
  git -C $target fetch origin --prune
  git -C $target pull --ff-only origin main
} else {
  git clone --branch main https://github.com/NousResearch/hermes-agent.git $target
}
```

Then let the installer validate the checkout — only after a pinned digest
check. Do **not** execute a floating remote installer on visual inspection
alone:

```powershell
$installer = Join-Path $env:TEMP "hermes-install.ps1"
$expected = $env:HERMES_INSTALL_PS1_SHA256
if (-not $expected) {
  throw "Refusing mutable remote installer: set HERMES_INSTALL_PS1_SHA256 to a vendor-published or operator-pinned SHA-256 digest first."
}
Invoke-WebRequest -Uri https://hermes-agent.nousresearch.com/install.ps1 -OutFile $installer
$actual = (Get-FileHash -Algorithm SHA256 -Path $installer).Hash.ToLowerInvariant()
if ($actual -ne $expected.ToLowerInvariant()) {
  throw "Hermes installer digest mismatch: expected $expected, got $actual"
}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installer `
  -Stage repository -NonInteractive -Json -HermesHome $env:HERMES_HOME -InstallDir $target
```

This avoids piping into `Invoke-Expression` when the installer needs parameters.
Prefer a **vendor-published** digest or Authenticode signature when one
exists. As of 2026-06-19 NousResearch does not publish either for
`install.ps1` — until they do, operators must pin a SHA-256 from a
first-party trusted acquisition (record it in `HERMES_INSTALL_PS1_SHA256`)
or skip the remote installer and stay on the git-clone path above. Saving
the script and skimming it is optional operator hygiene; it is **not** a
substitute for the digest gate.

### 2. Configure Provider Defaults

Recommended Nous Portal default for coding work: `qwen/qwen3-coder:free`.
For local LM Studio, use OpenAI-compatible local settings:

```text
Base URL: http://127.0.0.1:1234/v1
API key: lm-studio
```

Use a real API key only for hosted providers. Never commit keys.

### 3. Install Coding Partner CLIs on Windows

Permanent **User PATH** entries (idempotent — safe to re-run):

```powershell
.\platform\windows\ensure-partner-cli-paths.ps1
```

| CLI | Windows path | Verify |
| ----- | -------------- | -------- |
| Codex | `%LOCALAPPDATA%\Programs\OpenAI\Codex\bin` (WinGet) **preferred**; fallback `%USERPROFILE%\.lmstudio\bin` | `codex --version` |
| AGY | `%LOCALAPPDATA%\agy\bin` | `agy --version` |
| cursor-agent | `%LOCALAPPDATA%\cursor-agent` | `cursor-agent --version` |
| Hermes | `%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts` | `hermes --version` |

Use the LM Studio Node/npm toolchain for Codex install when needed:

```powershell
$env:PATH = "$env:USERPROFILE\.lmstudio\.internal\utils;$env:PATH"
npm install -g @openai/codex@latest --audit=moderate
npm install -g @google/gemini-cli --audit=moderate
```

`--audit=moderate` flags known-vulnerable transitive packages at install time
without pinning to a version number that will immediately go stale in this
doc. If `npm audit` reports a moderate-or-higher finding, stop and review
before continuing.

Install Antigravity CLI with the same fail-closed digest gate — save the
bootstrap script, verify a pinned SHA-256, then execute (never pipe into
`Invoke-Expression`):

```powershell
$agyInstaller = Join-Path $env:TEMP "antigravity-install.ps1"
$expected = $env:ANTIGRAVITY_INSTALL_PS1_SHA256
if (-not $expected) {
  throw "Refusing mutable remote installer: set ANTIGRAVITY_INSTALL_PS1_SHA256 to a vendor-published or operator-pinned SHA-256 digest first."
}
Invoke-WebRequest -Uri https://antigravity.google/cli/install.ps1 -OutFile $agyInstaller
$actual = (Get-FileHash -Algorithm SHA256 -Path $agyInstaller).Hash.ToLowerInvariant()
if ($actual -ne $expected.ToLowerInvariant()) {
  throw "Antigravity installer digest mismatch: expected $expected, got $actual"
}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $agyInstaller
codex --version; gemini --version; agy --version
```

The Antigravity installer itself downloads the `agy` binary and verifies a
SHA-512 checksum against its release manifest before extracting it — that
covers the payload binary, not the bootstrap `install.ps1`. Prefer a
vendor-published digest/signature for the bootstrap script when available;
otherwise pin `ANTIGRAVITY_INSTALL_PS1_SHA256` from a trusted acquisition
before any run. Visual inspection alone is not an integrity check.

If `agy` is absent, or if `agy --print "Reply with exactly: AGY_READY"`
exits with empty stdout, skip it and continue with Hermes/Gemini/Codex. To
differentiate a shell problem from a hosted-model problem, rerun once with
`--log-file <path>`; silent auth followed by quota exhaustion means AGY is
installed but not dispatchable.

### 4. Import Skills Safely

Import only reusable skill text or thin pointers into Hermes. Do not mirror
private workspace state. Hermes local commands must be thin wrappers that point
back to canonical command cards under `commands/<slug>/SKILL.md`.

Create or refresh Hermes local commands from the canonical repo:

```powershell
python bin\orama-system\skills\hermes-harness\scripts\install_hermes_thin_skills.py --install
```

The expected slash commands are `/pt-orama-council`, `/pt-orama-review`, and
`/pt-orama-delegate`. Optional: `/pt-orama-lesson-mining` (pass `--include-optional`
to the thin-skill installer). Never paste a full canonical skill body into Hermes.

### 5. Use Hermes as a Coding Partner

For bounded non-interactive review on this Windows host, prefer explicit
provider/model routing because the default LM Studio model can be reachable but
slow enough for `hermes chat` to appear hung.

```powershell
hermes chat --query "Reply with exactly: HERMES_READY" --quiet --safe-mode `
  --provider nous --model stepfun/step-3.7-flash:free --max-turns 1
```

Prompt Hermes with a bounded, evidence-first contract: state the goal, forbid
commits/deletes/deploys/secrets, forbid copying private harness state, cite the
canonical skills to inspect, and request JSON with assumptions, findings,
proposed edits, tests, and risks.

Use AGY for non-interactive Gemini-style partner work only after the visible
canary passes, Gemini CLI only for authenticated Gemini-Analyzer use-cases, and
Codex CLI for approved mechanical repo edits. The main orama agent keeps
judgment.

## Verification

```powershell
Test-Path "$env:HERMES_HOME\hermes-agent\.git"
& $env:HERMES_GIT_BASH_PATH --noprofile --norc -lc 'echo hermes-bash-ok'
hermes chat --query 'Reply with exactly: HERMES_READY' --quiet --safe-mode `
  --provider nous --model stepfun/step-3.7-flash:free --max-turns 1
codex --version
cursor-agent --version
gemini --version
git -C "$env:HERMES_HOME\hermes-agent" status --short --branch
```

Pass criteria: Hermes repo exists, Bash prints `hermes-bash-ok`, one-shot
prints `HERMES_READY`, provider keys stay outside git, imported skills are
sanitized, and OpenClaw operations still route through `openclaw-skills`.

## Plan integration

When synthesizing multiple plans into one canonical document, follow
[`references/plan-integration.md`](references/plan-integration.md):

1. Read source plans, then target plan.
2. Reframe missing absorption targets as no-ops; enrich canonical assets.
3. Repo-relative paths only; parametrize IPs; preserve provenance.
