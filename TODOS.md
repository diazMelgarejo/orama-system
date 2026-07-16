# TODOS

Deferred scope from plan reviews. Not implementation-ready — each item needs its own scoping pass before it becomes a plan.

## From /autoplan review of `docs/superpowers/plans/2026-07-14-g7-authenticated-sse-mvp.md` (2026-07-15)

- **Rate-limit `POST /api/notifications/session`** — deferred (CEO Decision #4). Outside the G7 MVP's blast radius; no rate-limit infra exists in the portal yet. Endpoint already requires a valid bearer credential, so abuse surface is small today, but a dedicated rate-limit layer should exist before this route sees real external traffic.

- **Wire the G7 notification stream into the already-built React Command Center** — deferred (CEO Decision #6, corrected 2026-07-16). Initially mis-scoped as "reconcile two competing frontends" — that's wrong. `docs/v2/16-web-app-orchestration-plan.md` (2026-05-16, marked RESOLVED 2026-06-14) already planned and shipped this exact migration: React SPA (`web/src/`) is the primary UI, `portal_server.py:3245` serves `web/dist` when built and falls back to the legacy `_render_html` dashboard only when it isn't — not two permanent parallel surfaces. The SPA already polls `/api/app/state` (`web/src/api/appState.ts:33`). So there's no reconciliation project needed — just a small, well-scoped follow-up: add an `EventSource`/fetch-stream client to the Command Center that consumes `/api/notifications/stream` (once G7 ships) instead of, or alongside, the existing poll. Much smaller than originally estimated — likely S/M effort, not 1-2 weeks. Still out of scope for the G7 MVP itself (its own Global Constraints bar UI work in this PR) — a natural fast-follow, not a fresh planning cycle.
