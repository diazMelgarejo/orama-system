# G7 Async Notifications — Next Steps

Date: 2026-07-14  
Branch: `G7-Async-notifications`  
Source branch: `2026-07-12-001-gstack-safe-upgrade`

## Bucket

This branch preserves the G7-only planning work from the stale `2026-07-12-001-gstack-safe-upgrade` branch.

Included commits:

- `86c986f0 feat(skills,docs): add antigravity-agent fan-out skill + G7 async notifications analysis`

Included files:

- `docs/next/fleet-mesh/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md` — Portal Notification Hub MVP analysis and implementation sketch.
- `bin/orama-system/skills/antigravity-agent/SKILL.md` — Antigravity `agy` fan-out skill guidance.
- `docs/next/fleet-mesh/2026-07-14-g7-async-notifications-next-steps.md` — this preservation branch's follow-up checklist.

Excluded on purpose:

- `e3abb562 feat(gstack): add gstack-safe-upgrade.sh, retire 2 upstream-absorbed fork patches` because that patch already landed via PR #148.
- General docs/security/shell-hygiene leftovers because they belong in the companion housecleaning PR.
- Perpetua-Tools `vendor/ecc-tools` submodule drift because it is non-G7 and points at commits not present locally; reconcile separately after verifying the submodule remote state.

## Current status

- G7 analysis exists and recommends a Portal Notification Hub MVP.
- Implementation is not included in this PR.
- The implementation checklist in `docs/next/fleet-mesh/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md` is still open.

## Next implementation branch

Create a follow-up implementation branch after this planning PR lands:

```text
G7-Async-notifications-mvp
```

## Cross-repo traceability

- Orama planning PR: `orama-system` PR #150, `G7-Async-notifications` → `main`, <https://github.com/diazMelgarejo/orama-system/pull/150>.
- Orama follow-up implementation branch: `G7-Async-notifications-mvp`, created from updated `orama-system/main` after PR #150 lands.
- Primary G7 analysis artifact: `docs/next/fleet-mesh/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md` in `orama-system`.
- Implementation checklist artifact: `docs/next/fleet-mesh/2026-07-14-g7-async-notifications-next-steps.md` in `orama-system`.
- Perpetua-Tools memory follow-up: add the cross-repo lesson through PT's canonical `.agent/tools/learn.py` pipeline on `Perpetua-Tools/main`; do not hand-edit generated `LESSONS.md` or `lessons.jsonl`.
- Remediation source reference: `$HOME/Library/Mobile Documents/iCloud~com~coteditor~CotEditor/Documents/restricted/amnesic-codex/Final-Remedy.md`.
- Cross-repo invariant: keep `orama-system` implementation code and `Perpetua-Tools` memory updates linked by repo names, PR numbers, and branch names only. Do not write workstation-specific absolute paths into tracked docs or memory.

## Implementation checklist left to do

- [ ] Define `EventType` enum and `Notification` dataclass.
- [ ] Implement `NotificationHub` with bounded per-session FIFO queues, explicit overflow semantics, subscription cleanup on disconnect, and subscription filtering.
- [ ] Add `/api/notifications/stream?types=...` SSE route gated by `PORTAL_NOTIFICATIONS=1`; disabled must mean no hub initialization, no monitor emission wiring, and `404` for the route.
- [ ] Wire the hub into existing portal monitors for agent state, topology, hardware, jobs, and phase transitions using edge-triggered diffs, not repeated full-snapshot spam.
- [ ] Reuse existing redaction helpers for any agent, routing, job, activity, or policy payloads before enqueueing events.
- [ ] Add auth regression coverage for unauthenticated notification clients, including enforced-auth `401` for `/api/notifications/stream`.
- [ ] Add `PORTAL_NOTIFICATIONS=1` feature flag, default off.
- [ ] Add an acceptance test proving an emitted event reaches an SSE client within 2 seconds.
- [ ] Add filter validation tests for valid comma-separated types, invalid types (`400`), empty filters, and disconnect cleanup.
- [ ] Document the route in the portal API reference, including auth, feature flag, event envelope, `types` filtering, best-effort delivery, and reconnect/no-durability semantics.

## Review notes

This PR should be reviewed as a planning-preservation PR, not as an implementation PR. The key question is whether the G7 plan and Antigravity fan-out skill should be preserved on `main` before building the MVP.

## Integrated action plan — oramasys-method + Final-Remedy pattern

Source: `$HOME/Library/Mobile Documents/iCloud~com~coteditor~CotEditor/Documents/restricted/amnesic-codex/Final-Remedy.md`.

The source plan is primarily a Perpetua-Tools PR recovery/remediation plan. Do **not** execute its destructive Git history steps from this G7 preservation branch. Import only the reusable remediation discipline into the follow-up `G7-Async-notifications-mvp` work:

1. **Freeze:** do not continue developing the MVP on `main`. Treat the reviewed G7 PR branch or its follow-up implementation branch as the only write target until review is complete.
2. **Root-cause clustering:** group review comments by invariant before patching. For this MVP the clusters are:
   - auth/security: route must use existing portal auth middleware and add enforced-auth regression coverage;
   - redaction/privacy: enqueue only already-redacted payloads, never raw agent/job/routing records;
   - lifecycle/concurrency: disconnect cleanup, bounded queues, overflow behavior, cancellation-safe SSE generator;
   - event semantics: edge-triggered state transitions, versioned envelope, stable `type`/`event_type` and `data`/`payload` aliases;
   - release discipline: `PORTAL_NOTIFICATIONS=1` default-off flag, docs, and tests before enabling operators.
3. **Branch discipline:** after this preservation PR lands, create the implementation branch from updated `main` as `G7-Async-notifications-mvp`. Keep commits cohesive by failure class (`schema+hub`, `route+auth`, `monitor wiring`, `tests+docs`). Preserve PR #150 scope and append updates instead of replacing the original analysis.
4. **Verify before merge:** run targeted portal tests and a new notification acceptance test. Existing relevant targets are `tests/test_portal_mutating_route_auth.py`, `tests/test_portal_dashboard.py`, `tests/test_fleet_topology_api.py`, plus new notification hub/route tests.

## Multi-agent review synthesis

Parallel reviewer bots were used as read-only reviewers for PR #150 and the follow-up MVP plan.

### CEO/strategy verdict

- Preserve PR #150 as a planning-preservation PR; do not expand it into implementation.
- The premise is sound if framed as **operator/control-plane event awareness**, not generic notification infrastructure.
- Avoid six-month regret by keeping the first milestone small: local portal SSE, default off, compatible envelope, no Redis/webhook/email/durable mesh in MVP.
- The follow-up implementation should prove one valuable path end-to-end before broad event coverage: an emitted portal state change reaches an authenticated SSE client within 2 seconds.

### Engineering verdict

- Feasible on existing `src/orama_system/portal_server.py` and `src/orama_system/lan_peer_channel.py` patterns.
- Do not reuse `/events/peer-stream` directly as the notification API: it is peer-transport-specific and currently a raw outbound queue. Add a separate `portal_notifications.py` service and `/api/notifications/stream` route.
- Tighten implementation details before coding: bounded queues, cleanup in `finally`, invalid filter handling, route feature-gating, auth tests, and edge-triggered monitor diffs.
- Treat the implementation estimate as a small MVP only after tests are scoped; monitor wiring and reliable acceptance tests are the likely time sinks.

### DX/security verdict

- API ergonomics should be simple: browser-native SSE, comma-separated `types`, documented envelope, and explicit reconnect/no-durability caveat.
- Security depends on inheriting portal auth middleware and redacting before enqueue. Add tests proving unauthenticated clients cannot subscribe when auth is enforced.
- Document operational behavior: default-off flag, how to enable, what happens when disabled, and how clients should handle reconnects or missed events.
- The `antigravity-agent` skill can be preserved, but keep it as direct CLI fan-out guidance only; do not register fabricated OpenClaw providers or include secrets in fan-out prompts/logs.

## Follow-up MVP acceptance criteria

- With `PORTAL_NOTIFICATIONS` unset or `0`, `/api/notifications/stream` returns `404` and no notification hub emits from monitor code.
- With `PORTAL_NOTIFICATIONS=1` and portal auth disabled for local dev, a test subscriber receives a redacted `agent_state_changed` or `job_completed` event within 2 seconds of `NotificationHub.emit()`.
- With portal auth enforced and no bearer token, `GET /api/notifications/stream` returns `401`.
- `?types=job_completed` receives `job_completed` and filters unrelated events; invalid types return `400`.
- Disconnecting an SSE client removes its queue/subscription and does not leak tasks or keep growing memory.
- Event JSON includes `version`, `type`, `event_type`, `ts`, `source`, `data`, and `payload` for GossipBus/GossipMesh adapter compatibility without implementing mesh replication in the MVP.
