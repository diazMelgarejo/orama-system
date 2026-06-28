# Mac self-improve assignment

**Assignee:** mac (mac-researcher / Hermes)  
**Topic:** self-improve/lessons  
**Fan-out:** 2026-06-28-self-improve-001

## Objective

Crystallize session learnings from LAN peer + file-inbox coordination into proposed `docs/LESSONS.md` entries. **Do not commit** until user approves (self-improve gate).

## Scope (Mac)

1. File-based peer handoff (`lan_peer_assign.py`, `~/.openclaw/state/lan_peer/inbox/`)
2. Joint-account auth (`auth_mode: joint` vs `orama_only`)
3. `pid_on_port` LISTEN-only fix (portal skipped on outbound probe)

## Deliverable

- `mac-lessons-draft.md` in local inbox with dated entries (Fact / Pattern / Rationale)
- Drop summary to Win peer inbox when ready for cross-review

## Read peer

After Win completes its assignment:

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py --peer list
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py --peer read --name win-self-improve-runtime.md
```
