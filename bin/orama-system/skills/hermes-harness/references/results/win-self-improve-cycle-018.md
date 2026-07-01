# Win self-improve cycle 018 — anti-doxxing wiring + monitor idle

**Date:** 2026-06-29  
**Fan-out:** coord-018

## Shipped this cycle

| Area | Deliverable |
|------|-------------|
| PT memory | `protocols/path-hygiene.md`, AGENTS.md § Path Hygiene, permissions never-rule |
| Sanitize | `path_hygiene.py` maps workspace trees → `<workspace-root>` |
| Cursor | `no-workstation-paths.mdc` alwaysApply (PT + orama) |
| Review | Rejected candidate promoting Downloads canonical path |
| Monitor | 15m coord_monitor — Mac `192.168.254.102` ok, 0 pending, no new drops |

## P5 branch state

- **2/7** on `cursor/security-pr3-swarm-approval-f559` (T1 operator payload, T2 preview signing)
- PR #136 CI green; T3 launch token verify next
- L1 backlog job completed as `released-blocked-p5-not-started` — stays gated until P5 merges

## Operator patterns (graduated to PT lessons)

1. Wire anti-doxxing at **all** layers: protocol → AGENTS → permissions → sanitize → Cursor rules → CI
2. Policy docs explaining forbidden paths use `C:\<user>\...` notation (LINT-006)
3. Reject review-queue candidates that promote workspace path as canonical
4. Queue idle after burst is normal; pulse gate returns `idle` when pending=0
5. Triple rinse: push → learn → dream×3 → peer drop → pulse×3 → push

## Mac peer

Drop this file + latest P5-STATUS to peer inbox.
