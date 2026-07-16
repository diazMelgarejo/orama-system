# TODOS

Deferred scope from plan reviews. Not implementation-ready — each item needs its own scoping pass before it becomes a plan.

## From /autoplan review of `docs/superpowers/plans/2026-07-14-g7-authenticated-sse-mvp.md` (2026-07-15)

- **Rate-limit `POST /api/notifications/session`** — deferred (CEO Decision #4). Outside the G7 MVP's blast radius; no rate-limit infra exists in the portal yet. Endpoint already requires a valid bearer credential, so abuse surface is small today, but a dedicated rate-limit layer should exist before this route sees real external traffic.

- **Reconcile the two portal frontends and wire the SPA to the G7 notification stream** — deferred (CEO Decision #6, raised mid-review 2026-07-16). Two consumer surfaces exist for the same backend: the legacy server-rendered HTML dashboard (`_render_html` in `src/orama_system/portal_server.py`, own `setInterval` polling loops at `/` and `/dashboard`) and a newer React SPA (`web/src/`, Vite-built, proxied through the portal per `130e631c`). The SPA has the active tooling investment (Vitest gate, dev-recalib commits) — evidence points to an in-progress migration off the legacy dashboard, not two permanent surfaces. Neither currently consumes `/api/notifications/stream` (zero `EventSource` references repo-wide as of this review). Properly scope as its own plan (`/office-hours` or `/autoplan`) before implementing — likely 1-2 weeks, touches most of `web/src/` and the dashboard's route surface. Out of scope for the G7 MVP by its own Global Constraints (no UI work).
