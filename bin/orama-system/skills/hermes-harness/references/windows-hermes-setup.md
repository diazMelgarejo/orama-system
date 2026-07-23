# Windows Hermes Setup — Operator Playbook

> **Role:** Canonical Windows bring-up, PATH hygiene, ECC install/validate, and
> partner-CLI wiring for Hermes on Windows 11 + LM Studio.
> **Absorbed from:** Hermes self-improve skill `windows-hermes-setup` (2026-07-23).
> **Paths:** `%USERPROFILE%`-relative or env-var form only (LINT-006).

---

## Triggers

- Any task requiring Hermes, `cursor-agent`, `node`, `npm`, `git`, or ECC on Windows.
- Questions about how Hermes talks to other agents on this machine.
- Post-install validation after ECC `--target hermes` or `start.ps1` rehab.

---

## Golden Rule: Probe First, Do Not Duplicate

1. Before adding shims or PATH entries, prove current tool state with exact paths.
2. If a working command exists, do not reinvent it.
3. If `cursor-agent` is installed, run `--version` / `--help` before reinstalling.
4. If `~/.hermes/ecc-install-state.json` exists, run doctor before full reinstall.

---

## Canonical Windows Paths

Prefer stable user-level paths over versioned app-install folders.
See also [`windows-onboarding-config.md`](windows-onboarding-config.md).

| Tool | Stable path | Notes |
|------|-------------|-------|
| **node** | `%USERPROFILE%\.lmstudio\.internal\utils\node.exe` | LM Studio bundled runtime |
| **npm** | `%USERPROFILE%\.lmstudio\bin` (User PATH) | Use `npm.cmd` in Git Bash if bare `npm` fails |
| **git** | Resolve dynamically from Git for Windows / GitHub Desktop | Never hardcode `app-<ver>` paths |
| **cursor-agent** | `%LOCALAPPDATA%\cursor-agent\cursor-agent.cmd` | |
| **Hermes** | `%LOCALAPPDATA%\hermes\bin` + `%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts` | |
| **Codex** | `%LOCALAPPDATA%\Programs\OpenAI\Codex\bin` (preferred) or `%USERPROFILE%\.lmstudio\bin` | |
| **AGY** | `%LOCALAPPDATA%\agy\bin` | |

**Rule (AlphaClaw wiki §11):** Anchor shims in `%USERPROFILE%\.lmstudio\bin` — not
versioned LM Studio app-data folders.

**Verify:**

```powershell
$env:Path = "$env:USERPROFILE\.lmstudio\bin;$env:Path"
node --version
npm --version
git --version
```

---

## Partner PATH Hygiene

**Preferred:** `platform/windows/ensure-partner-cli-paths.ps1` (idempotent; called from `install.ps1` and `start.ps1`).

Candidate directories (add to User PATH only when missing; prepend so newer CLIs shadow older shims):

- `%LOCALAPPDATA%\Programs\OpenAI\Codex\bin`
- `%LOCALAPPDATA%\cursor-agent`
- `%LOCALAPPDATA%\agy\bin`
- `%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts`
- `%LOCALAPPDATA%\hermes\bin`
- `%USERPROFILE%\.lmstudio\bin`

After refresh:

```powershell
Get-Command hermes, codex, agy, cursor-agent -ErrorAction SilentlyContinue |
  Format-Table Name, Source
```

---

## Hermes ECC Install / Validate (Windows)

**Install root:** `~/.hermes` (Windows: `%USERPROFILE%\.hermes`)

**Expected post-install artifacts:**

- `~/.hermes/skills`, `~/.hermes/rules`, `~/.hermes/commands`
- `~/.hermes/ecc-install-state.json`

**Install (from Perpetua-Tools ECC vendor):**

```powershell
cd $env:PERPETUA_TOOLS_PATH\vendor\ecc-tools
.\install.ps1 --target hermes --profile minimal
```

**Validate:**

```powershell
node scripts/ecc.js doctor --target hermes
# or: node scripts/ecc.js doctor --target hermes --json
```

Do **not** use `npx ecc doctor` as the preferred path — `npx` may be absent even when `npm.cmd` works.

If `install.sh` fails with `npm: command not found` despite `npm.cmd` working in Git Bash,
patch the ECC clone bootstrap to call `npm.cmd install` (temporary shim, not a permanent rewrite).

Details: [`ecc-doctor-and-cursor-smoke-checks.md`](ecc-doctor-and-cursor-smoke-checks.md)

### CRG / Cursor MCP (Windows)

After ECC `--target cursor` or any vendor MCP drop, set CRG to LM Studio — **not** Ollama `:11434`:

```powershell
# Preferred: platform-aware sync
cd $env:ORAMA_SYSTEM_PATH
bash bin/orama-system/scripts/sync-cursor-mcp.sh --profile readonly

# Or manual patch in .cursor/mcp.json → code-review-graph.env:
# "CRG_OPENAI_BASE_URL": "http://localhost:1234/v1"
```

Reload MCP in Cursor Settings. Full rule:
[`../../code-review/references/crg-platform-endpoints.md`](../../code-review/references/crg-platform-endpoints.md).

### ECC idempotency

- If `ecc-install-state.json` exists and ECC directories are present → **validate, skip full reinstall**.
- Partial artifacts → targeted reinstall of missing modules only.
- Do **not** delete non-ECC skills/rules/commands in `~/.hermes`; ECC installs are additive.

---

## start.ps1 Partner PATH Wiring

`start.ps1` loads `.paths.ps1`, then sources `platform/windows/ensure-partner-cli-paths.ps1`
so Hermes/Codex/AGY/cursor-agent resolve in-session without manual PATH edits.

Without this step, partner CLIs may be installed but not callable from the `start.ps1` session.

```powershell
cd $env:ORAMA_SYSTEM_PATH
.\platform\windows\start.ps1 --lan-peer --no-open   # LAN + peer drop flush
.\platform\windows\start.ps1 --status
```

---

## Agent Comms (what start.ps1 does and does not do)

`start.ps1` does **not** provide a universal Hermes→cursor-agent message bus.

| Mechanism | Purpose |
|-----------|---------|
| **GossipBus log** | `python $env:PERPETUA_TOOLS_PATH\scripts\agent_coordination.py log <agent_id> "<msg>"` |
| **Peer-inbox drop** | `lan_peer_assign.py drop --peer --file ... --assignee mac` |
| **Update all agents** | [`update-all-agents-comms.md`](update-all-agents-comms.md) — fanout + GossipBus recipe |
| **Flush on LAN start** | `start.ps1 --lan-peer` → `flush-outbox --peer` |
| **coord_pulse.ps1** | Scheduled Cursor dispatch inside this repo |
| **Direct cursor-agent** | `cursor-agent --print --model <model> "<prompt>"` |

Session close-out: see [`../SKILL.md`](../SKILL.md) § Update the Board.

---

## cursor-agent Steering / Handoff

When handing work to cursor-agent, do **both**:

1. Write `.cursor/state/<handoff-name>.md` (verified state, gaps, explicit asks).
2. Invoke cursor-agent pointing at that file.

Details: [`cursor-agent-steering-handoff.md`](cursor-agent-steering-handoff.md)

---

## Windows One-Liner Probe Pitfall

Avoid inline interpreter probes on Windows (`node -e`, `python -c`, `php -r`, `perl -e`).
MSYS/Git Bash quoting often fails silently. Prefer a script file or a direct command probe.

---

## Pitfalls

| Pitfall | Fix |
|---------|-----|
| Hardcoded GitHub Desktop `app-<ver>` git path | Resolve dynamically or use `%USERPROFILE%\.lmstudio\bin` shim |
| `npx` missing but `npm.cmd` present | Use `npm.cmd` or call Node scripts directly |
| Symlinks into LM Studio app folders | Anchor in `%USERPROFILE%\.lmstudio\bin` |
| Assuming all partner CLIs required | `start.ps1` starts local daemons; missing partners reduce capability only |
| coord scripts missing `.env.local` vars | Persist tokens/MAC_IP as User-level env vars |

---

## Output Expectations

Report validated state: paths found/not found, processes running, health-check results.
Distinguish "not wired yet" from "already wired correctly".

---

## Related

- [`windows-onboarding-config.md`](windows-onboarding-config.md) — env vars + partner CLI table
- [`hermes-windows-partner-readiness.md`](hermes-windows-partner-readiness.md) — canary matrix
- [`win-localhost-runtime-checklist.md`](win-localhost-runtime-checklist.md)
- [`../commands/windows-hermes-setup/SKILL.md`](../commands/windows-hermes-setup/SKILL.md) — Hermes command card
- AlphaClaw wiki `11-windows-dev.md` — node/npm/git anchor policy
- Workspace reference: `win-rtx5080-windows-dev-reference.md` (ultrathink root)
