# G7 SSE Production Patterns Research

Date: 2026-07-14
Depth: Quick, time-boxed to five minutes
Scope: authenticated, browser-consumed SSE notifications for the Orama portal.

## Executive Summary

The G7 MVP should stay a local, default-off, best-effort notification stream. The
browser protocol already gives us named events, reconnection, and `Last-Event-ID`;
it does not give us authorization headers, durable replay, or a safe reason to put
a bearer token in a URL. The current G7 scaffold has the right local-process queue
and redaction boundary, but the browser authentication path is incomplete when
control-plane auth is enabled: `EventSource` cannot set `Authorization`, and the
existing control-plane cookie is accepted but is not issued by the portal.

Adopt the SSE wire conventions now: emit `id`, `event`, and `data` fields; make the
JSON `data` an immutable versioned envelope; use a bounded per-subscriber queue;
drop the oldest queued event for a slow subscriber; and make reconnect mean
snapshot re-synchronization, not replay. Do not add a ten-day store or a thirty-day
retention rule to G7. Both are durable-event-system work and conflict with the
documented MVP boundary.

## Authority And Comparison Set

Primary sources were preferred. A FastAPI tutorial, the HTML living standard,
MDN, OWASP, and the maintained `sse-starlette` implementation met the bar. Search
hits for FastAPI notification applications were demos or discussions, not a
production reference implementation; they were deliberately excluded from adopted
patterns.

| Concern | Source used | Adopted conclusion |
| --- | --- | --- |
| SSE protocol and reconnect | [HTML Living Standard](https://html.spec.whatwg.org/multipage/server-sent-events.html) | Send `event`, `id`, and JSON `data`; clients reconnect and may send `Last-Event-ID`. |
| Browser behavior | [MDN: Using server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) | Use native same-origin `EventSource`; do not expect custom request headers. |
| FastAPI integration | [FastAPI SSE tutorial](https://fastapi.tiangolo.com/tutorial/server-sent-events/) | Use the framework-supported SSE response path rather than hand-maintaining HTTP stream details. |
| Operational stream behavior | [`sysid/sse-starlette`](https://github.com/sysid/sse-starlette) | Use its disconnect handling, periodic ping, send timeout, and optional bounded memory-channel patterns if the dependency is already acceptable. |
| Browser auth and CSRF | [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) | Never pass a bearer in a query string; cookie-authenticated browser traffic needs a same-origin policy and CSRF defenses for state-changing routes. |

## Decisions

### 1. Authentication and CSRF

- Keep control-plane authentication for the stream. A `401` test is necessary but
  insufficient: it only proves denial, not that an authenticated browser can use
  the route.
- Do not put `ORAMA_CONTROL_PLANE_TOKEN` in `?token=`. URLs leak through history,
  proxy logs, referers, and diagnostics.
- For browser-native SSE, add a narrowly scoped same-origin session bootstrap that
  receives an existing `Authorization: Bearer` credential and issues the already
  supported `orama_control_plane_token` cookie as `HttpOnly`, `Secure` outside
  local HTTP development, `SameSite=Strict`, and `Path=/api/notifications`.
  The bootstrap must reject cross-origin callers and never put the bearer into HTML
  or JavaScript.
- Cookie authentication makes the read-only stream usable through `EventSource`.
  It does not make mutation safe. Existing state-changing portal routes must keep
  their origin/CSRF protection; do not extend a read-stream exception to them.
- If an operator needs cross-origin streaming, use a fetch-based streaming client
  with the bearer header, explicit origin allowlisting, and a separate threat-model
  decision. It is not an MVP convenience switch.

### 2. Queue and Backpressure Semantics

- Retain one bounded FIFO queue per subscriber. `NotificationHub(queue_size=100)`
  is a sensible starting point for an operator portal, not a delivery guarantee.
- On overflow, drop the oldest queued event then enqueue the newest. This preserves
  the current state transition over stale intermediate changes and bounds memory.
- Increment a per-subscription drop counter and emit or expose it as a local metric
  for operator diagnosis. Do not turn queue overflow into a producer-wide block.
- Preserve `finally` cleanup and cancellation behavior. Add a keepalive comment
  (about 15 seconds) and a bounded send timeout if the response implementation
  supports them, because proxies and dead clients otherwise retain resources.

### 3. Envelope and Replay Semantics

The JSON envelope remains the future mesh adapter seam. Add a stable `event_id`
now, then project fields into standard SSE lines:

```text
id: <event_id>
event: <event_type>
data: {"version":1,"event_id":"...","type":"job_completed",...}

```

- `event_id` is an opaque UUID or UUIDv7-style identifier, not a timestamp.
- `ts` remains metadata, not ordering or an authorization input.
- The server accepts `Last-Event-ID` syntactically but G7 does not replay from it.
  On reconnect, clients fetch the redacted portal snapshot and resume live events.
- There is no ten-day durable replay and no thirty-day retention in G7. The allowed
  tradeoff is loss across disconnect/process restart in exchange for a simple,
  bounded, default-off MVP. Durable replay belongs to the later v2.1 event/mesh
  design and needs its own storage, retention, eviction, authorization, and audit
  decisions.

## File-By-File Implementation Plan

### `src/orama_system/portal_notifications.py`

Extend `Notification` with an immutable ID, document overflow as best effort, and
make dropped-event telemetry observable. Keep producer-side redaction outside this
module so the module does not need to understand every sensitive payload shape.

```python
event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

def to_dict(self) -> dict[str, Any]:
    return {
        "version": self.version,
        "event_id": self.event_id,
        "type": self.type.value,
        "event_type": self.type.value,
        "ts": self.ts,
        "source": self.source,
        "data": dict(self.data),
        "payload": dict(self.data),
    }
```

### `src/orama_system/portal_server.py`

Use the portal's existing auth verifier for a bootstrap endpoint, issue a
path-scoped cookie only after successful bearer authentication, and add a
same-origin check before issuing it. Use an SSE-native response implementation or
preserve the equivalent headers, pings, timeout, and cancellation behavior.

```python
yield (
    f"id: {notification.event_id}\\n"
    f"event: {notification.type.value}\\n"
    f"data: {json.dumps(notification.to_dict())}\\n\\n"
)
```

Set `Cache-Control: no-cache` on the stream. Do not add a `retry:` value without a
measured reconnect policy; browser defaults are adequate for this local MVP.

### `tests/test_portal_notifications.py`

Add focused tests for:

- authenticated bootstrap sets the path-scoped cookie and the cookie can open the
  stream when auth is enforced;
- a cross-origin bootstrap attempt is rejected;
- stream bytes contain matching SSE `id`, `event`, and JSON `event_id` values;
- queue overflow drops oldest, keeps newest, and records the drop;
- reconnects do not claim replay: `Last-Event-ID` produces a fresh live stream and
  the client must re-fetch a snapshot.

### `docs/api-reference.md` and G7 plan

Document `PORTAL_NOTIFICATIONS`, default-off `404`, same-origin browser setup,
comma-separated `types`, per-subscriber overflow, typed SSE fields, and the
explicit no-replay contract. Link the contract to v2.1 as a future adapter seam,
not an implementation claim.

## Acceptance Criteria Added By This Research

1. With enforced auth, an operator can establish a browser-native same-origin
   `EventSource` without exposing a bearer in HTML, JavaScript, or the URL.
2. A caller cannot obtain that cookie from a cross-origin request.
3. Every notification has one matching SSE `id`, SSE `event`, and envelope
   `event_id`.
4. A slow subscriber cannot grow memory without bound; its newest event survives
   overflow and the loss is observable.
5. A reconnect never implies missed events were replayed; the documented client
   recovery path is snapshot then live stream.

## Deferred Work

- durable storage, replay windows, retention or compaction;
- cross-process fan-out, Redis/NATS, webhooks, email, or mobile push;
- v2.1 mesh replication and v2.5 safety enforcement;
- cross-origin browser EventSource support.

## Captured Evidence Archive

The raw Firecrawl responses used for this time-boxed research are retained in
[the G7 Firecrawl evidence archive](2026-07-14-g7-firecrawl/README.md). The
archive is evidence for review and reruns, not an additional source of design
authority; the decisions above remain bounded by the cited primary sources and
the canonical `docs/v2/*` plans.

## Rerun Inputs

```text
workflow: firecrawl-deep-research
topic: production conventions for authenticated FastAPI SSE notifications
depth: quick (five-minute cap)
authority: official docs, standards, maintained production libraries; blogs secondary only
output: cited research plus repository-specific implementation plan
```
