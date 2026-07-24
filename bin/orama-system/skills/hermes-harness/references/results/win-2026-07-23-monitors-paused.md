# Monitors paused — operator session end

**Fan-out:** coord-028
**Status:** OPERATOR RULE
**From:** win-cursor
**Date:** 2026-07-23

## Audience

| Lane | Action |
|------|--------|
| win-cursor | Monitors paused; resume manually next session |
| win-coder | Do not expect coord_pulse dispatches until resumed |
| win-autoresearcher | Idle; no scheduled pulse jobs |
| mac-orchestrator | **Unload all coord/scheduled monitors listed below** |
| mac-researcher | Idle until Mac orchestrator resumes |
| hermes | No background coord_comms_board until re-enabled |

## Windows (this host) — DONE

| Monitor | State |
|---------|-------|
| `OramaCoordPulse` (Task Scheduler, 900s) | **Disabled** |
| `OramaCoordCommsBoard` (5-min, if installed) | Not installed |
| `OramaServiceWatchdog` | Not installed |
| Running `coord_pulse` / `coord_monitor` processes | None |

## Mac — ACTION REQUIRED

Unload these launchd jobs (do not delete plists — resume next session):

```bash
launchctl bootout "gui/$(id -u)/com.orama.coord-pulse" 2>/dev/null || launchctl unload ~/Library/LaunchAgents/com.orama.coord-pulse.plist 2>/dev/null || true
launchctl bootout "gui/$(id -u)/com.orama.network-watch" 2>/dev/null || launchctl unload ~/Library/LaunchAgents/com.orama.network-watch.plist 2>/dev/null || true
launchctl bootout "gui/$(id -u)/com.orama.lm-link-watch" 2>/dev/null || launchctl unload ~/Library/LaunchAgents/com.orama.lm-link-watch.plist 2>/dev/null || true
launchctl unload -w ~/Library/LaunchAgents/com.gbrain.autopilot.plist 2>/dev/null || true
pkill -f cline_autoresearcher_watch 2>/dev/null || true
```

Verify paused:

```bash
launchctl list | grep -E 'orama|gbrain' || echo 'no orama/gbrain launchd jobs loaded'
```

## Resume next session

**Windows:**

```powershell
Enable-ScheduledTask -TaskName OramaCoordPulse
# or reinstall: .\scripts\install_coord_pulse.ps1
```

**Mac:**

```bash
cd $ORAMA_SYSTEM_PATH
./scripts/install_coord_pulse.sh
./scripts/install_network_watch.sh   # if previously installed
./scripts/install_lm_link_watch.sh   # if previously installed
# gbrain autopilot: launchctl load ~/Library/LaunchAgents/com.gbrain.autopilot.plist
```

## Open / deferred

- Operator will resume all monitors manually at start of next session.
- Do not auto-reinstall coord pulse via `start.sh --lan-peer` until operator confirms.
