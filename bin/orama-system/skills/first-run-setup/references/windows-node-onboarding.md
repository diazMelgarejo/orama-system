# Windows Node Onboarding — Fresh-Machine Handoff

> **Audience:** a brand-new Windows box joining the LAN fleet as an
> AutoResearcher/coder node (e.g. a 2nd/3rd/Nth Windows RTX GPU machine).
> Never had these repos, Git, Node, Python, or LM Studio installed before.
> **Owner:** orama-system `bin/orama-system/skills/first-run-setup/`
> **Canonical install path this doc wraps:** [`../../../references/first-run-install.md`](../../../references/first-run-install.md)
> **Written from a real 2nd-Windows-node bring-up (RTX 3080), reused for the 3rd node (RTX 5080).**

Give this single file to the new machine. Every command below is idempotent —
safe to re-run after a partial failure, reboot, or interrupted download.

---

## 0. What you're joining

Three repos, one LAN fleet:

```
AlphaClaw (L1 — infra) → Perpetua-Tools (L2 — middleware) → orama-system (L3 — orchestration)
```

- Runtime/state lives in **Perpetua-Tools**. orama-system is stateless methodology.
- Every Windows node's **hard requirement**: LM Studio running and reachable —
  no fallback, the system fails loudly without it. (Mac nodes require Ollama
  instead; not your concern on Windows.)
- Coordination between machines happens over LAN via a peer-inbox pulse
  (`coord_pulse.ps1`, installed as a Task Scheduler job in step 6) — not a
  cloud service, not SSH. Get on the same LAN/subnet as the other nodes first.

## 1. Prerequisites (do these before anything below)

| Tool | Check | Install if missing |
|------|-------|---------------------|
| Git for Windows | `git --version` | `winget install --id Git.Git` |
| PowerShell 5.1+ | built into Windows 10/11 | — |
| NVM for Windows | `nvm version` | `winget install --id CoreyButler.NVMforWindows` |
| Python 3.13+ | `python --version` | `winget install --id Python.Python.3.13` |
| winget itself | `winget --version` | ships with modern Windows; update via Microsoft Store "App Installer" if missing |

GPU driver: install the vendor driver for your card (RTX 5080 → latest
NVIDIA Game Ready or Studio driver) **before** installing LM Studio, so it
picks up CUDA correctly on first launch.

## 2. Clone both repos

Pick a parent directory (this doc assumes `C:\code`, adjust freely — nothing
below hardcodes it beyond this step):

```powershell
mkdir C:\code
cd C:\code
git clone https://github.com/diazMelgarejo/orama-system.git
git clone https://github.com/diazMelgarejo/Perpetua-Tools.git
```

Set the path env vars every skill/script in both repos expects. Add to your
PowerShell profile (`notepad $PROFILE`) so they persist across reboots:

```powershell
[Environment]::SetEnvironmentVariable("ORAMA_SYSTEM_PATH", "C:\code\orama-system", "User")
[Environment]::SetEnvironmentVariable("PERPETUA_TOOLS_PATH", "C:\code\Perpetua-Tools", "User")
```

Restart the PowerShell session (or `refreshenv` if you have Chocolatey) so
both vars are live before continuing.

## 3. Hard requirement: LM Studio

```powershell
cd $env:ORAMA_SYSTEM_PATH
.\scripts\ensure_requirements.ps1
```

This is idempotent and does three things, in order:
1. Installs LM Studio via `winget` if the binary isn't found under
   `%LOCALAPPDATA%\Programs\LM-Studio` / `%PROGRAMFILES%\LM-Studio`.
2. Probes `http://localhost:1234/v1/models` (override port via
   `LM_STUDIO_WIN_PORT` env var if you run a non-default port).
3. Creates/updates a Python `.venv` at the repo root and installs
   `requirements.txt`, skipping reinstall if the hash-stamp already matches.

If step 2 warns that the server isn't reachable: open LM Studio manually →
**Server tab → Start Server** → load a model → re-run
`.\scripts\ensure_requirements.ps1 -CheckOnly` to confirm green.

Run with `-CheckOnly` any time to probe without installing/mutating anything.

## 4. First-run install (Node, Python deps, CRG, gbrain, embeddings)

This is the shared cross-platform installer both Mac and Windows nodes use —
canonical spec: [`../../../references/first-run-install.md`](../../../references/first-run-install.md).

```powershell
cd $env:ORAMA_SYSTEM_PATH
bash bin/orama-system/scripts/first-run-install.sh status   # fast, read-only — see what's missing
bash bin/orama-system/scripts/first-run-install.sh install  # idempotent — only touches what status flagged
```

(Requires Git Bash, which ships with Git for Windows from step 1.) Re-running
`install` after a Ctrl+C or crash resumes from the last incomplete
component — it does not restart from zero. Confirm success:

```powershell
Test-Path "$HOME\.orama-system\first-run.done"   # should be True
```

MCP orchestration workers are a separate, optional step — not part of
`first-run.done`:

```bash
bash bin/orama-system/scripts/install-mcp-stack.sh
```

## 5. Perpetua-Tools side

```powershell
cd $env:PERPETUA_TOOLS_PATH
git pull origin main
# Perpetua-Tools has no separate Windows installer today — it rides on the
# Python venv + Node toolchain first-run-install.sh already set up in
# orama-system. If PT ever grows its own requirements.txt, install it the
# same way ensure_requirements.ps1 did in step 3.
```

## 6. Join LAN coordination (Hermes Gateway pulse)

```powershell
cd $env:ORAMA_SYSTEM_PATH
.\scripts\install_coord_pulse.ps1              # installs a 15-min Task Scheduler job
.\scripts\install_coord_pulse.ps1 -Status       # confirm it's registered + check last log lines
```

This registers `OramaCoordPulse` in Task Scheduler, running
`bin/orama-system/skills/hermes-harness/scripts/coord_pulse.ps1` on an
interval (default 900s / 15min, override with `-IntervalSec`). It is what
lets this machine see and respond to peer-dropped task cards from the Mac
orchestrator and other Windows nodes without a human in the loop.

To drop this machine's presence into another node's inbox manually (e.g. to
announce yourself to the Mac co-orchestrator on first boot):

```bash
python bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py drop \
  --peer --peer-ip <mac-or-other-node-ip> \
  --file <path-to-an-announcement-doc.md>
```

## 7. Start the stack

```powershell
cd $env:ORAMA_SYSTEM_PATH
.\platform\windows\start.ps1
```

`start.ps1` delegates all gateway/routing decisions to Perpetua-Tools'
`orchestrator/alphaclaw_manager.py` — it does not contain routing logic
itself. If LM Studio isn't reachable, this fails loudly by design (§0 hard
requirement) rather than silently degrading.

## 8. Verify you're actually in the fleet

```powershell
python3 -m pytest tests/ -k "win_job_queue or mac_job_queue" -q   # queue routing logic sane
bash scripts/git/check_identity.sh                                 # commit identity configured correctly
python3 scripts/review/repo_hygiene.py .                           # no workstation-path leaks in tracked files
```

Then check `.\scripts\install_coord_pulse.ps1 -Status` again after ~15
minutes to confirm the scheduled pulse actually ran once (non-empty log
tail, no error lines).

## 9. What to learn / feed back after this node's first week

Log anything genuinely new (not already covered above) to
`docs/LESSONS.md` in orama-system — GPU-specific quirks (e.g. RTX 5080
driver/CUDA version pins LM Studio needed), winget package name drift,
timing differences in `ollama pull`-equivalent LM Studio model downloads on
this hardware, or any step above that turned out to be stale. That's how
this doc — and `first-run-install.sh` itself — gets better for the next
Windows node instead of every machine rediscovering the same gaps.
