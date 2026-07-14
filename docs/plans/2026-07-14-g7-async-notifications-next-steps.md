# G7 Async Notifications — Next Steps

Date: 2026-07-14  
Branch: `G7-Async-notifications`  
Source branch: `2026-07-12-001-gstack-safe-upgrade`

## Bucket

This branch preserves the G7-only planning work from the stale `2026-07-12-001-gstack-safe-upgrade` branch.

Included commits:

- `86c986f0 feat(skills,docs): add antigravity-agent fan-out skill + G7 async notifications analysis`

Included files:

- `docs/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md`
- `bin/orama-system/skills/antigravity-agent/SKILL.md`

Excluded on purpose:

- `e3abb562 feat(gstack): add gstack-safe-upgrade.sh, retire 2 upstream-absorbed fork patches` because that patch already landed via PR #148.
- General docs/security/shell-hygiene leftovers because they belong in the companion housecleaning PR.
- Perpetua-Tools `vendor/ecc-tools` submodule drift because it is non-G7 and points at commits not present locally; reconcile separately after verifying the submodule remote state.

## Current status

- G7 analysis exists and recommends a Portal Notification Hub MVP.
- Implementation is not included in this PR.
- The implementation checklist in `docs/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md` is still open.

## Next implementation branch

Create a follow-up implementation branch after this planning PR lands:

```text
G7-Async-notifications-mvp
```

## Implementation checklist left to do

- [ ] Define `EventType` enum and `Notification` dataclass.
- [ ] Implement `NotificationHub` with FIFO queue and subscription filtering.
- [ ] Add `/api/notifications/stream?types=...` SSE route.
- [ ] Wire the hub into existing portal monitors for agent state, topology, hardware, jobs, and phase transitions.
- [ ] Reuse existing redaction helpers for any agent, routing, or policy payloads.
- [ ] Add auth regression coverage for unauthenticated notification clients.
- [ ] Add `PORTAL_NOTIFICATIONS=1` feature flag, default off.
- [ ] Add an acceptance test proving an emitted event reaches an SSE client within 2 seconds.
- [ ] Document the route in the portal API reference.

## Review notes

This PR should be reviewed as a planning-preservation PR, not as an implementation PR. The key question is whether the G7 plan and Antigravity fan-out skill should be preserved on `main` before building the MVP.
