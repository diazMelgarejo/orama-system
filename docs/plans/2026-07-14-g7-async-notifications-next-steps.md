# G7 Async Notifications — Next Steps

Date: 2026-07-14
Branch: `G7-Async-notifications-mvp`
Source branch: `2026-07-12-001-gstack-safe-upgrade`

## Canonical precedence

- `docs/v2/*` is authoritative over every other plan before or after it.
- These G7 notes exist to implement the already-reviewed MVP inside the v1 portal boundary.
- If any G7 sentence conflicts with v2, treat the G7 sentence as stale and rewrite it to match v2.
- Do not expand this branch into mesh replication, v2.5 safety enforcement, or a new trust boundary.

## Bucket

This branch preserves the G7-only planning work from the stale `2026-07-12-001-gstack-safe-upgrade` branch and continues it as the MVP implementation branch.

Included commits:

- `86c986f0 feat(skills,docs): add antigravity-agent fan-out skill + G7 async notifications analysis`

Included files:

- `docs/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md` — Portal Notification Hub MVP analysis and implementation sketch.
- `bin/orama-system/skills/antigravity-agent/SKILL.md` — Antigravity `agy` fan-out skill guidance.
- `docs/plans/2026-07-14-g7-async-notifications-next-steps.md` — this preservation branch's follow-up checklist.

Excluded on purpose:

- `e3abb562 feat(gstack): add gstack-safe-upgrade.sh, retire 2 upstream-absorbed fork patches` because that patch already landed via PR #148.
- General docs/security/shell-hygiene leftovers because they belong in the companion housecleaning PR.
- Perpetua-Tools `vendor/ecc-tools` submodule drift because it is non-G7 and points at commits not present locally; reconcile separately after verifying the submodule remote state.

## Current status

- G7 analysis exists and recommends a Portal Notification Hub MVP.
- The implementation scaffold is already present in this branch.
- Remaining work is to harden the scaffold against auth, redaction, lifecycle, and compatibility requirements.
- The checklist in `docs/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md` is now the source of remaining work, not a blank-slate spec.
- Research-backed implementation decisions are recorded in `docs/superpowers/references/2026-07-14-g7-sse-production-patterns.md`. They are subordinate to `docs/v2/*`.

## Next implementation branch

This is the follow-up implementation branch:

```text
G7-Async-notifications-mvp
```

## Cross-repo traceability

- Orama planning PR: `orama-system` PR #150, `G7-Async-notifications` → `main`, <https://github.com/diazMelgarejo/orama-system/pull/150>.
- Orama follow-up implementation branch: `G7-Async-notifications-mvp`, created from updated `orama-system/main` after PR #150 lands.
- Primary G7 analysis artifact: `docs/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md` in `orama-system`.
- Implementation checklist artifact: `docs/plans/2026-07-14-g7-async-notifications-next-steps.md` in `orama-system`.
- Perpetua-Tools memory follow-up: add the cross-repo lesson through PT's canonical `.agent/tools/learn.py` pipeline on `Perpetua-Tools/main`; do not hand-edit generated `LESSONS.md` or `lessons.jsonl`.
- Remediation source reference: `$HOME/Library/Mobile Documents/iCloud~com~coteditor~CotEditor/Documents/restricted/amnesic-codex/Final-Remedy.md`.
- Cross-repo invariant: keep `orama-system` implementation code and `Perpetua-Tools` memory updates linked by repo names, PR numbers, and branch names only. Do not write workstation-specific absolute paths into tracked docs or memory.

## Implementation checklist left to do

- [ ] Verify the existing `EventType` enum and `Notification` dataclass still match the reviewed contract.
- [ ] Confirm `NotificationHub` behavior: bounded per-session FIFO queues, overflow semantics, subscription cleanup on disconnect, and subscription filtering.
- [ ] Keep `/api/notifications/stream?types=...` gated by `PORTAL_NOTIFICATIONS=1`; disabled must mean no hub initialization, no monitor emission wiring, and `404` for the route.
- [ ] Wire the hub into existing portal monitors for agent state, topology, hardware, jobs, and phase transitions using edge-triggered diffs, not repeated full-snapshot spam.
- [ ] Reuse existing redaction helpers for any agent, routing, job, activity, or policy payloads before enqueueing events.
- [ ] Add auth regression coverage for unauthenticated notification clients, including enforced-auth `401` for `/api/notifications/stream`.
- [ ] Close the browser-auth gap: native `EventSource` cannot attach `Authorization`; issue the existing control-plane cookie only through a same-origin, bearer-authenticated bootstrap and never accept a bearer query parameter.
- [ ] Keep `PORTAL_NOTIFICATIONS=1` as the default-off feature flag.
- [ ] Keep the acceptance test proving an emitted event reaches an SSE client within 2 seconds.
- [ ] Keep filter validation tests for valid comma-separated types, invalid types (`400`), empty filters, and disconnect cleanup.
- [ ] Document the route in the portal API reference, including auth, feature flag, event envelope, `types` filtering, best-effort delivery, and reconnect/no-durability semantics.
- [ ] Emit standard SSE `id` and `event` fields alongside the JSON envelope; add immutable `event_id` to the envelope, but keep `Last-Event-ID` replay explicitly out of G7.
- [ ] Test overflow as drop-oldest, retain-newest, observable loss; test cookie-authenticated same-origin browser streaming and cross-origin bootstrap rejection.
- [ ] Preserve `/docs/v2` alignment: keep the envelope compatible with v2.1 GossipMesh and the route compatible with v2 security gates, but do not implement v2.1 mesh replication or v2.5 safety overlays in this MVP.

## `/docs/v2` compatibility plan

This branch should be reviewed as the first G7 implementation step after the planning PR. It should not fork the v2 roadmap. It should create a seam future v2 work can consume.

### v2.0 kernel compatibility

- Keep G7 local to `orama-system` v1 portal code. Do not import `perpetua-core` or change the v2 kernel boundary.
- Use stable event names that can later map into `PerpetuaState.metadata` or a local `GossipBus` append-only event without rewriting clients.
- Preserve small, redacted deltas rather than full dashboard snapshots.

### v2.1 GossipMesh compatibility

- Required envelope fields: `version`, `type`, `event_type`, `ts`, `source`, `data`, `payload`.
- G7 adds `event_id` as a stable opaque adapter identity. It is not a durable sequence and does not imply replay.
- Required filter semantics: comma-separated `types` maps to future `event_type` interest filters.
- Explicit deferrals: no `/api/gossip/tail`, no `/api/gossip/ingest`, no cross-particle replication, no Redis/NATS, no durable replay, no peer scoring.

### v2/v2.5 security compatibility

- Treat `/api/notifications/stream` as a control-plane `read` route under `docs/v2/23-security-preconditions.md` and `docs/v2/24-security-first-platform.md`.
- Default-off is mandatory: disabled means `404` and no monitor emission wiring.
- Redaction-before-enqueue is mandatory. Do not emit raw agent state, job records, prompts, transcripts, bearer tokens, or model endpoint secrets.
- v2.5 safety stays future work. G7 may emit audit-friendly events, but must not claim MAESTRO/SWARM enforcement, HITL injection, risk scoring, cryptographic attestation, witness quorum, or equivocation detection.
- Apply `docs/v2/45-single-operator-lan-threat-model-descope.md`: bounded queues and monotonic event fields are useful under honest flakiness; adversarial P2P controls require a fresh Q1-Q3 threat-model check.

## Review notes

This branch should be reviewed as the G7 MVP implementation branch. The key question is whether the notification scaffold preserves the reviewed G7 plan while staying inside the v1 portal MVP boundary and leaving clean adapter seams for `/docs/v2`.

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
- Align implementation docs with `/docs/v2` by naming the future adapter contract and by warning future agents not to silently expand MVP scope into v2.1 mesh or v2.5 safety enforcement.

## Follow-up MVP acceptance criteria

- With `PORTAL_NOTIFICATIONS` unset or `0`, `/api/notifications/stream` returns `404` and no notification hub emits from monitor code.
- With `PORTAL_NOTIFICATIONS=1` and portal auth disabled for local dev, a test subscriber receives a redacted `agent_state_changed` or `job_completed` event within 2 seconds of `NotificationHub.emit()`.
- With portal auth enforced and no bearer token, `GET /api/notifications/stream` returns `401`.
- `?types=job_completed` receives `job_completed` and filters unrelated events; invalid types return `400`.
- Disconnecting an SSE client removes its queue/subscription and does not leak tasks or keep growing memory.
- Event JSON includes `version`, `type`, `event_type`, `ts`, `source`, `data`, and `payload` for GossipBus/GossipMesh adapter compatibility without implementing mesh replication in the MVP.
- Tests or constants lock the future-spec references so later edits cannot accidentally remove the v2 kernel, v2.1 mesh, or v2.5 safety alignment without review.
