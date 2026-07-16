# G7 Pre-v2 Backlog Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the three G7 follow-ups in `TODOS.md` with one reused backend rate limit, one opt-in React cache-invalidation stream, and an archived trust-risk disposition before broader `docs/v2/` migration work begins.

**Architecture:** This is a dependent fast-follow to `2026-07-14-g7-authenticated-sse-mvp.md`, not a parallel replacement. Reuse the portal's process-local limiter, keep React Query polling as the fallback, and treat SSE events only as prompts to refetch the authoritative redacted snapshot. Preserve the existing single-operator-LAN threat-model text unchanged; archive the resolved backlog record instead of deleting it.

**Tech Stack:** FastAPI, the existing in-process portal limiter, pytest, React 18, TypeScript, TanStack React Query, native `EventSource`, Vitest, React Testing Library.

## Global Constraints

- Complete and merge Tasks 1-5 of `docs/superpowers/plans/2026-07-14-g7-authenticated-sse-mvp.md` before starting Task 1 here.
- `docs/v2/` remains authoritative. This plan may link to it but must not rewrite its threat-model claims.
- Keep `PORTAL_NOTIFICATIONS` default-off and add no Redis, NATS, durable replay, mesh transport, or new dependency.
- Authenticate before consuming rate-limit capacity so unauthenticated requests cannot exhaust the operator's quota.
- Never put a bearer token in a URL, browser storage, event payload, log, fixture, or tracked file.
- Keep the existing 5-second `/api/app/state` poll as a fallback; notifications only invalidate the React Query cache.
- Follow strict RED -> GREEN TDD. Preserve RED/GREEN commands and results in `docs/testing/2026-07-16-g7-pre-v2-todo-closure.tdd.md`.
- For resolved documentation, move the original backlog text into `docs/archive/`; do not delete historical rationale.
- Run `python3 scripts/review/repo_hygiene.py .` before every commit.

---

## Dependency Order

```text
G7 Tasks 1-5 (Claude-owned implementation)
  -> Task 1: session rate limit
  -> Task 2: 204-safe API helper and typed EventSource adapter
  -> Task 3: React Query invalidation hook
  -> Task 4: evidence and archival closure
```

Tasks 1 and 2 may run in parallel after G7 lands. Task 3 consumes Task 2. Task 4 runs only after Tasks 1-3 are green.

### Task 1: Reuse the Portal Rate Limit for Session Bootstrap

**Files:**
- Modify: `src/orama_system/portal_server.py`
- Test: `tests/test_portal_notifications.py`

**Interfaces:**
- Consumes: `create_notification_session(request: Request, response: Response) -> None`, `_check_rate_limit(key: str) -> bool`, `_CONFIGURE_MAX_CALLS == 5` from the landed G7 code and current portal limiter.
- Produces: authenticated per-client session bootstrap capped at five successful attempts per 60-second process-local window.

- [ ] **Step 1: Write the failing integration test**

Add this test after the G7 session tests:

```python
def test_notification_session_rate_limits_authenticated_client(monkeypatch):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "0")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "test-notification-token")
    monkeypatch.setattr("utils.control_plane_auth.persisted_control_plane_token", lambda: "")
    portal_server._CONFIGURE_RATE.clear()
    try:
        with TestClient(portal_server.app, base_url="http://localhost") as client:
            denied = client.post("/api/notifications/session")
            allowed = [
                client.post(
                    "/api/notifications/session",
                    headers={"Authorization": "Bearer test-notification-token"},
                )
                for _ in range(portal_server._CONFIGURE_MAX_CALLS)
            ]
            blocked = client.post(
                "/api/notifications/session",
                headers={"Authorization": "Bearer test-notification-token"},
            )
    finally:
        portal_server._CONFIGURE_RATE.clear()

    assert denied.status_code == 401
    assert [response.status_code for response in allowed] == [204] * 5
    assert blocked.status_code == 429
```

- [ ] **Step 2: Run the test and verify RED**

Run: `uv run --extra test pytest tests/test_portal_notifications.py::test_notification_session_rate_limits_authenticated_client -q`

Expected: FAIL because all six authenticated requests return 204.

- [ ] **Step 3: Add the minimal authenticated rate-limit check**

In `create_notification_session`, place this block after `verify_control_plane_auth(request)` and before `response.set_cookie(...)`:

```python
    client_host = request.client.host if request.client is not None else "unknown"
    if not _check_rate_limit(f"notifications-session:{client_host}"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded - max 5 sessions/min")
```

Do not add a second limiter, dependency, timer, or token-derived key. The current portal is process-local and single-operator; this is the narrow pre-migration plug.

- [ ] **Step 4: Run GREEN and affected auth tests**

Run: `uv run --extra test pytest tests/test_portal_notifications.py tests/test_portal_mutating_route_auth.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the TDD slice**

```bash
git add src/orama_system/portal_server.py tests/test_portal_notifications.py
git commit -m "fix(g7): rate limit notification session bootstrap"
```

Commit body: `_check_rate_limit` and its 5/60 constants are reused unchanged; agents must re-read `create_notification_session`; the notification auth baseline now includes an authenticated 429 case.

### Task 2: Add a 204-safe Typed EventSource Adapter

**Files:**
- Modify: `web/src/api/client.ts`
- Test: `web/src/api/client.test.ts`
- Create: `web/src/api/notifications.ts`
- Test: `web/src/api/notifications.test.ts`

**Interfaces:**
- Consumes: `apiFetch<T>()`, `POST /api/notifications/session` returning 204, and named SSE events from the G7 plan.
- Produces: `bootstrapNotificationSession(signal?: AbortSignal): Promise<void>` and `openPortalNotificationStream(onNotification, onDisconnect): () => void`.

- [ ] **Step 1: Write the failing 204 test**

Add to `web/src/api/client.test.ts`:

```typescript
it("returns undefined for a successful 204 response", async () => {
  vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 204 }));

  await expect(
    apiFetch<void>("/api/notifications/session", { method: "POST" }),
  ).resolves.toBeUndefined();
});
```

- [ ] **Step 2: Run the test and verify RED**

Run: `cd web && npm test -- src/api/client.test.ts`

Expected: FAIL with an end-of-JSON-input parse error.

- [ ] **Step 3: Make `apiFetch` handle no-content success**

Insert before the final `res.json()` call in `web/src/api/client.ts`:

```typescript
  if (res.status === 204) {
    return undefined as T;
  }
```

Run: `cd web && npm test -- src/api/client.test.ts`

Expected: PASS.

- [ ] **Step 4: Write failing named-event adapter tests**

Create `web/src/api/notifications.test.ts` with a fake `EventSource` that records constructor options and listeners. Assert all of these behaviors in separate tests:

```typescript
expect(fake.url).toBe("/api/notifications/stream");
expect(fake.withCredentials).toBe(true);
expect([...fake.listeners.keys()]).toEqual([
  "agent_state_changed",
  "fleet_topology_changed",
  "hardware_status_changed",
  "job_completed",
  "phase_transition",
]);
fake.dispatch("job_completed", JSON.stringify({
  version: 1,
  event_id: "event-1",
  type: "job_completed",
  event_type: "job_completed",
  timestamp: "2026-07-16T00:00:00Z",
  data: { job_id: "redacted-job" },
  payload: { job_id: "redacted-job" },
}));
expect(onNotification).toHaveBeenCalledWith(
  expect.objectContaining({ event_id: "event-1", type: "job_completed" }),
);
fake.onerror?.(new Event("error"));
expect(fake.close).toHaveBeenCalledOnce();
expect(onDisconnect).toHaveBeenCalledOnce();
```

Run: `cd web && npm test -- src/api/notifications.test.ts`

Expected: FAIL because `notifications.ts` does not exist.

- [ ] **Step 5: Implement the smallest typed adapter**

Create `web/src/api/notifications.ts`:

```typescript
import { apiFetch } from "./client";

export const portalNotificationTypes = [
  "agent_state_changed",
  "fleet_topology_changed",
  "hardware_status_changed",
  "job_completed",
  "phase_transition",
] as const;

export type PortalNotificationType = (typeof portalNotificationTypes)[number];

export interface PortalNotification {
  version: 1;
  event_id: string;
  type: PortalNotificationType;
  event_type: PortalNotificationType;
  timestamp: string;
  data: Record<string, unknown>;
  payload: Record<string, unknown>;
}

export async function bootstrapNotificationSession(signal?: AbortSignal): Promise<void> {
  await apiFetch<void>("/api/notifications/session", { method: "POST", signal });
}

export function openPortalNotificationStream(
  onNotification: (notification: PortalNotification) => void,
  onDisconnect: () => void,
): () => void {
  const source = new EventSource("/api/notifications/stream", { withCredentials: true });
  for (const type of portalNotificationTypes) {
    source.addEventListener(type, (event) => {
      onNotification(JSON.parse((event as MessageEvent<string>).data) as PortalNotification);
    });
  }
  source.onerror = () => {
    source.close();
    onDisconnect();
  };
  return () => source.close();
}
```

Run: `cd web && npm test -- src/api/client.test.ts src/api/notifications.test.ts`

Expected: PASS.

- [ ] **Step 6: Commit the TDD slice**

```bash
git add web/src/api/client.ts web/src/api/client.test.ts web/src/api/notifications.ts web/src/api/notifications.test.ts
git commit -m "feat(g7): add typed notification stream client"
```

Commit body: `apiFetch<void>` now accepts 204; agents must re-read `notifications.ts`; frontend API tests now cover named events, credentials, close, and disconnect.

### Task 3: Invalidate React Query While Retaining Polling

**Files:**
- Create: `web/src/features/command-center/usePortalNotifications.ts`
- Test: `web/src/features/command-center/usePortalNotifications.test.tsx`
- Modify: `web/src/features/command-center/CommandCenter.tsx`
- Test: `web/src/features/command-center/CommandCenter.test.tsx`

**Interfaces:**
- Consumes: Task 2's bootstrap and stream adapter plus the existing `QueryClient` key `['appState']`.
- Produces: `usePortalNotifications(enabled: boolean): void`; every notification invalidates `['appState']`, disconnects re-bootstrap after one second, and unmount cancels the stream and timer.

- [ ] **Step 1: Write failing hook tests**

Mock `bootstrapNotificationSession` and `openPortalNotificationStream`, render the hook under a `QueryClientProvider`, and assert:

```typescript
expect(bootstrapNotificationSession).toHaveBeenCalledOnce();
expect(openPortalNotificationStream).toHaveBeenCalledOnce();
onNotification({ type: "job_completed" } as PortalNotification);
expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["appState"] });
onDisconnect();
await vi.advanceTimersByTimeAsync(1_000);
expect(bootstrapNotificationSession).toHaveBeenCalledTimes(2);
unmount();
expect(closeStream).toHaveBeenCalled();
```

Also render with `enabled=false` and assert neither API function is called.

Run: `cd web && npm test -- src/features/command-center/usePortalNotifications.test.tsx`

Expected: FAIL because the hook does not exist.

- [ ] **Step 2: Implement the hook**

Create `web/src/features/command-center/usePortalNotifications.ts`:

```typescript
import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  bootstrapNotificationSession,
  openPortalNotificationStream,
} from "@/api/notifications";

const RECONNECT_DELAY_MS = 1_000;

export function usePortalNotifications(enabled: boolean): void {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!enabled) return;
    let stopped = false;
    let closeStream: (() => void) | undefined;
    let reconnectTimer: number | undefined;

    const connect = async () => {
      try {
        await bootstrapNotificationSession();
        if (stopped) return;
        closeStream = openPortalNotificationStream(
          () => void queryClient.invalidateQueries({ queryKey: ["appState"] }),
          () => {
            if (!stopped) reconnectTimer = window.setTimeout(connect, RECONNECT_DELAY_MS);
          },
        );
      } catch {
        if (!stopped) reconnectTimer = window.setTimeout(connect, RECONNECT_DELAY_MS);
      }
    };

    void connect();
    return () => {
      stopped = true;
      closeStream?.();
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
    };
  }, [enabled, queryClient]);
}
```

- [ ] **Step 3: Integrate without removing polling**

In `CommandCenter.tsx`, import the hook and call it immediately after component state setup:

```typescript
  usePortalNotifications(import.meta.env.VITE_PORTAL_NOTIFICATIONS === "1");
```

Do not change `refetchInterval: 5_000` or `refetchIntervalInBackground: false`.

Extend `CommandCenter.test.tsx` by mocking `usePortalNotifications`, rendering once, and asserting it was called. This catches a future integration deletion while the hook tests own behavior.

- [ ] **Step 4: Run frontend GREEN gates**

Run: `cd web && npm test`

Expected: all Vitest tests PASS.

Run: `cd web && npm run typecheck && npm run lint`

Expected: both commands exit 0.

- [ ] **Step 5: Commit the TDD slice**

```bash
git add web/src/features/command-center/usePortalNotifications.ts web/src/features/command-center/usePortalNotifications.test.tsx web/src/features/command-center/CommandCenter.tsx web/src/features/command-center/CommandCenter.test.tsx
git commit -m "feat(g7): refresh command center from notifications"
```

Commit body: `VITE_PORTAL_NOTIFICATIONS=1` enables cache invalidation; agents must re-read the new hook; the 5-second polling baseline is intentionally unchanged.

### Task 4: Preserve Evidence and Move the Resolved Backlog

**Files:**
- Create: `docs/testing/2026-07-16-g7-pre-v2-todo-closure.tdd.md`
- Create: `docs/archive/2026-07-16-g7-pre-v2-todo-closure.md`
- Modify: `TODOS.md`
- Modify: `docs/next/fleet-mesh/README.md`

**Interfaces:**
- Consumes: RED/GREEN output and commits from Tasks 1-3.
- Produces: durable execution evidence, an archived copy of the original three-item backlog, and a short active pointer with no lost rationale.

- [ ] **Step 1: Run the complete focused gate**

Run: `uv run --extra test pytest tests/test_portal_notifications.py tests/test_portal_mutating_route_auth.py tests/test_portal_dashboard.py tests/test_fleet_topology_api.py -q`

Run: `cd web && npm test && npm run typecheck && npm run lint && npm run build`

Expected: every command exits 0.

- [ ] **Step 2: Write the TDD evidence report**

Record, for each task, the exact RED command and intended failure, GREEN command and result, changed interfaces, commit SHA, and coverage command/result. State explicitly that the trust-model item required no behavior change.

- [ ] **Step 3: Move, do not delete, the backlog history**

Create `docs/archive/2026-07-16-g7-pre-v2-todo-closure.md` by moving the three original G7 bullets from `TODOS.md` into it verbatim, then append each outcome and evidence link. Replace the moved section in `TODOS.md` with one line linking the archive and this plan. Preserve any unrelated or newly added backlog entries in place.

Do not modify `docs/v2/45-single-operator-lan-threat-model-descope.md`. Its D23 administrative-identity boundary remains the accepted authority until a separately approved security plan supersedes it.

- [ ] **Step 4: Validate documentation hygiene**

Run: `python3 scripts/review/repo_hygiene.py .`

Expected: `OK: repo hygiene checks passed` and no broken local links.

- [ ] **Step 5: Commit the closure record**

```bash
git add TODOS.md docs/archive/2026-07-16-g7-pre-v2-todo-closure.md docs/testing/2026-07-16-g7-pre-v2-todo-closure.tdd.md docs/next/fleet-mesh/README.md
git commit -m "docs(g7): archive completed pre-v2 follow-ups"
```

Commit body: no runtime interface changes; agents must re-read the archive and evidence report; test baselines are recorded, not changed by this documentation commit.

## Acceptance Gate

- The G7 implementation plan is merged and its targeted backend suite is green.
- The sixth authenticated session bootstrap returns 429; unauthenticated calls still return 401 without consuming the authenticated quota.
- `apiFetch<void>` resolves on 204.
- The client listens to named events with credentials and never puts a token in the URL.
- A notification invalidates `['appState']`; the existing 5-second poll remains.
- Disconnect re-bootstrap occurs before a new `EventSource` is opened.
- The original three backlog entries exist in `docs/archive/` with outcomes and evidence.
- No `docs/v2/` threat-model claim is changed.
- Backend, frontend, typecheck, lint, build, and repository hygiene gates pass.
