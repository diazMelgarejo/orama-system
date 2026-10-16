# Contract — production foreign-provider transport

**Status:** approved design contract under [D-LG-7](ADR-D-LG-7-R4-SAFETY-COMPATIBILITY-PLATFORM.md).
Design only. Plan slice: [T4](PLAN-R4-EXECUTION.md#t4--one-qualified-foreign-provider-transport).
Depends on the [HITL/effect contract](CONTRACT-DURABLE-HITL-EFFECTS.md) and on
[ADR 62](../../62-telos-phylax-authority-gate0-adr.md), under which Telos owns all
endpoint-specific security.

## 1. Start with one cell

Enable one named provider/version **capability cell**, never a framework family. Its
manifest states:

| Manifest field | Meaning |
| --- | --- |
| Effect classes | Which operations the cell may perform |
| Endpoint purposes | Telos-recognized purposes it may reach |
| Credential requirements | What it needs and how it is supplied |
| Deadlines | Request and total-run limits |
| Stream/error semantics | Partial-stream and error classification |
| Idempotency | Key scope, retention window, collision behaviour |
| Reconciliation | Whether and how an outcome can be queried |

One passing provider path does not enable another. Unsupported cells stay refused.

## 2. Every network path

Enumerate all SDK paths: model calls, tool calls, retries, redirects, authentication
refresh, discovery and telemetry. Then:

1. Prefer an injectable Telos-backed transport.
2. If injection cannot contain every path, use a **contained worker** whose OS/network
   boundary permits only the authorized Telos-mediated channel.
3. A Python socket monkeypatch is a **test tripwire**, not production containment.
4. A semantic-only precheck followed by a raw SDK connection does not qualify (this is
   the failure mode erratum E10 records).
5. If Telos, admission or containment is unavailable, **fail closed**. No direct-network
   fallback exists.

Telos owns destination security, peer pinning and credential handling across redirects.
The adapter owns serialization and provider-specific outcomes and never copies Telos
security semantics.

## 3. Worker model

The worker executes one declared provider operation. It is not the graph scheduler. It
receives only required credentials and data, a scoped capability and a fencing epoch.
Before each I/O it rechecks permit, cancellation, fencing and endpoint admission.
This check cannot be atomic with the remote socket write: if fencing changes after
handoff, the request is recorded as in flight and its provider outcome is reconciled.

## 4. Outcomes

Cancellation is a request, not proof of rollback. Every operation ends as one of
`confirmed_applied`, `confirmed_not_applied` or `unknown`. A partial model stream may
have incurred cost and is never "no effect". Retry budgets and total run cost survive
restart. Paid egress needs explicit opt-in and spend limits; tests default offline.

## 5. Evidence tiers for enabling a cell

1. Local controlled-server integration (offline).
2. Explicitly authorized sandbox credentials and spend, for named cells only.
3. Review of actual network evidence and provider limitations before opt-in enablement.

Default CI stays offline. Publishing the cell's contract and evidence is part of the
slice; enablement is a separate operator decision.

## 6. Acceptance tests (named, to fail first)

Bypass-socket attempt; mixed DNS answers; redirect carrying credentials; proxy path;
retry after acceptance; partial stream then crash; cancellation race; stale fencing
epoch; acceptance-before-crash recovered by reconciliation, not resend.
