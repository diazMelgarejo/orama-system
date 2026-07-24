# G7 Pre-v2 TODO Closure TDD Evidence

Date: 2026-07-16

Plan: [`../superpowers/plans/2026-07-16-g7-pre-v2-todo-closure.md`](../superpowers/plans/2026-07-16-g7-pre-v2-todo-closure.md)

## Scope

This evidence closes the pre-v2 fast-follow around the authenticated G7 SSE MVP:

- Reuse the existing portal process-local limiter for notification session bootstrap.
- Add a typed browser `EventSource` adapter using the actual server envelope (`ts: number`, not `timestamp`).
- Invalidate the existing React Query `["appState"]` cache on notifications while preserving the 5-second polling fallback.
- Archive the accepted trust-model debt without changing `docs/v2/45-single-operator-lan-threat-model-descope.md`.

## RED / GREEN Log

| Task | RED command | RED result | GREEN command | GREEN result |
|---|---|---|---|---|
| Session bootstrap rate limit | `uv run --offline --extra test pytest tests/test_portal_notifications.py::test_notification_session_rate_limits_authenticated_client -q` | Failed as expected: sixth authenticated request returned `204`, not `429`. | `uv run --offline --extra test pytest tests/test_portal_notifications.py::test_notification_session_requires_bearer_and_sets_scoped_cookie tests/test_portal_notifications.py::test_notification_session_rejects_cross_origin_bootstrap tests/test_portal_notifications.py::test_notification_session_rate_limits_authenticated_client -q` | Passed: `3 passed`. |
| Typed EventSource adapter | `npm test -- src/api/notifications.test.ts` | Failed as expected: `./notifications` did not exist. | `npm test -- src/api/client.test.ts src/api/notifications.test.ts` | Passed: `9 passed`. |
| React Query invalidation hook | `npm test -- src/features/command-center/usePortalNotifications.test.tsx` | Failed as expected: `./usePortalNotifications` did not exist. | `npm test -- src/features/command-center/usePortalNotifications.test.tsx` | Passed: `4 passed`. |
| Command Center integration | N/A, covered by the hook integration smoke test added to `CommandCenter.test.tsx`. | N/A | `npm test -- src/api/client.test.ts src/api/notifications.test.ts src/features/command-center/usePortalNotifications.test.tsx src/features/command-center/CommandCenter.test.tsx` | Passed: `17 passed`. |

## Interface Changes

- `POST /api/notifications/session` now rate-limits successful authenticated bootstrap attempts with `_check_rate_limit("notifications-session:<client_host>")`.
- `web/src/api/notifications.ts` exports `bootstrapNotificationSession`, `openPortalNotificationStream`, `portalNotificationTypes`, and `PortalNotification`.
- `PortalNotification` matches the backend wire contract: `ts: number` is the event time field.
- `usePortalNotifications()` performs capability discovery by attempting same-origin session bootstrap; `401`, `403`, and `404` disable the stream for the current hook lifetime.
- Temporary disconnects use bounded reconnect delays and do not create concurrent reconnect timers.
- `CommandCenter` still polls `/api/app/state` every 5 seconds; notifications only invalidate that existing cache key.

## Coordination Notes

- Claude completed the G7 backend implementation and reported the `ts` versus `timestamp` contract mismatch through the PT coordination board.
- The frontend adapter and plan were corrected to use `ts: number`.
- `uv.lock` changed during local `uv run`; the lock churn was preserved under ignored local state and the tracked lockfile was restored because this task did not intentionally change dependencies.

## Full Validation

Final focused validation results:

```text
uv run --offline --extra test pytest tests/test_portal_notifications.py tests/test_portal_mutating_route_auth.py tests/test_portal_dashboard.py tests/test_fleet_topology_api.py -q
55 passed, 2 warnings

cd web && npm test
27 passed

cd web && npm run typecheck
PASS

cd web && npm run lint
PASS

cd web && npm run build
PASS

python3 scripts/review/repo_hygiene.py .
OK: repo hygiene checks passed
```
