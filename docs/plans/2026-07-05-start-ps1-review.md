# /steer — `start.ps1` review (2026-07-05)

## Finding 1: `ORAMA_SYSTEM_PATH` double-nesting breaks `coord_pulse.ps1`
**Severity:** High  
**Current behavior:** `.paths.ps1` writes `$env:ORAMA_SYSTEM_PATH = Join-Path $PWD 'bin\orama-system'`. `coord_pulse.ps1` reads that env var as `$Repo`, then resolves script paths like `bin\orama-system\skills\hermes-harness\scripts\win_job_queue.py` relative to it. Result: `...\bin\orama-system\bin\orama-system\skills\...` — nonexistent.  
**Evidence:** `start_lan_peer_final.log` and `start_lan_peer_rerun.log` show WARN `probe script missing` / `assignment script missing` followed by `usage: win_job_queue.py pulse-gate` failures.  
**Proposed change:** Update `.paths.ps1` generation to set `ORAMA_SYSTEM_PATH` to repo root (`$PWD` / `$RepoRoot`), not `bin\orama-system`. Ensure `coord_pulse.ps1` and any other consumers treat it as repo root.

## Finding 2: GLM-5.2 setup hint uses macOS/Linux path on Windows
**Severity:** Low  
**Current behavior:** Message suggests `bash ~/.alphaclaw/.openclaw/workspace/skills/glm52-fallback/setup-glm52.sh` regardless of OS.  
**Proposed change:** Detect Windows and either suppress the setup hint or reference Windows docs/runbook path.

## Finding 3: Stale premerge `.bak` files
**Severity:** Low  
**Current behavior:** `.claude/skills/git-history-surgery/SKILL.md.premerge-20260703.bak` and siblings are untracked.  
**Proposed change:** Remove these cleanup artifacts from repo workspace; keep them out of git.

## No changes needed now
- Broadened `win_job_queue.py` Mac→Win acceptance already synced in commit `9089f5b`
- LAN probe shows healthy Mac connectivity
- PT orama-system `main` branches synchronized to remote

## Review/approval needed
- Approve P1 rewrite of `.paths.ps1` `ORAMA_SYSTEM_PATH` generation
- Approve P2 GLM52 path messaging adjustment
- Approve P3 removal of `.claude/skills/*.premerge-20260703.bak`
- Leave `.hermes/` untracked local directory alone
