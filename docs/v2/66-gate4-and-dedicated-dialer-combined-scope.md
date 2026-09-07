# Gate 4 + Dedicated Model-Server Dialer — Combined Scope for the Next PR

**Status:** scope only, 2026-09-07 — no implementation in this document
**Authority:** [ADR 62](62-telos-phylax-authority-gate0-adr.md), [Gate 2 scope](64-gate2-policy-surface-noninterchangeability-scope.md), [Gate 2 evidence](65-gate2-policy-surface-evidence.md)
**Regime boundary:** unchanged from ADR 62. Gate 4 work lands in `oramasys/*`.
The dedicated dialer's PT-facing half is a human-reviewed PT PR, exactly like
PT PR #380 was — never a same-repo PT edit landed by an agent.

## Why these two are one PR, not two

PT PR #380 deliberately shipped the smallest safe fix: remove caller-supplied
model-host overrides from the unauthenticated `/health` route. Doc 65's own
"Required test evidence" table named 4 cases that fix does not cover, because
they belong to a broader remediation it explicitly deferred:

- Hostname resolves to a prohibited address → rejected before dispatch
- Hostname has multiple DNS answers, one prohibited → rejected before dispatch
- Public configured model server *with* opt-in → allowed only after
  DNS-aware policy checks
- Launcher configuration uses a remote model endpoint → same dedicated
  policy, not `agent_launcher.py`'s current raw `httpx` path

All four require the same missing primitive: a **DNS-resolving, address-class-aware
model-server dialer** — doc 65's "Proposed PT remediation" second part, not yet
built anywhere. Gate 4 (the first real Telos vertical slice: wiring
`TelosPort` for `config_read`/`health_probe` into `GatewayLifecycle.run()`)
needs a real endpoint-authorization decision to sit in front of *something* —
today there is no v2-side model-server dial primitive for it to authorize
before use. Building the dialer as part of Gate 4, instead of separately,
means Telos authorizes the actual dial path from day one instead of
authorizing a placeholder that gets swapped out later.

## Two halves, two owners, one PR

### Half A — v2: the dedicated dialer + Telos wiring (this repo's normal path)

Lives in `oramasys/oramasys` (the dialer, since it's a provider-adapter-level
concern per ADR 62's authority map) and consumes `oramasys/telos`'s canonical
`EndpointRef`/`EndpointUseRequest` types (already wired into `TelosPort` by
PR #2 on this repo).

**Dialer contract (first cut):**

```python
class ModelServerDialRequest:
    endpoint: EndpointRef          # already-normalized, from the canonical primitive
    purpose: EndpointPurpose       # config_read | health_probe (Gate 4 scope only)
    allow_public: bool             # caller's own opt-in state, not inferred

class ModelServerDialResult:
    allowed: bool
    reason_code: str
    resolved_address: str | None   # the specific IP actually dialed, for audit
    provider_ref: str | None
```

1. Resolve every A/AAAA record for `endpoint.host` before any connection is
   opened.
2. Classify every resolved address; reject link-local, metadata-like (e.g.
   `169.254.169.254`), multicast, and other prohibited classes — allow
   loopback/RFC1918 only when the purpose's policy permits it.
3. Do **not** follow redirects by default; if a future purpose needs them,
   revalidate every hop's resolved address independently, never trust the
   first hop's classification for subsequent hops.
4. No credential forwarding to an address that failed classification, even
   transiently before rejection.
5. `Telos.authorize()` is the decision gate; the dialer is what *executes*
   an already-allowed dial. The dialer must not reimplement authorization
   logic Telos already owns — it enforces DNS/address safety, Telos
   enforces purpose/actor authorization. Keep these ports distinct, per
   ADR 62 Decision 2's own warning against re-creating "two canonical
   sources" drift.

**Gate 4 exit evidence, reused unmodified from ADR 62:** bind a concrete
in-process `TelosPort` adapter via dependency injection; require endpoint
reference and purpose, reject absent/unknown purpose; persist or emit a
redacted, correlated decision record; deny by default when the policy
adapter cannot decide; do not yet authorize arbitrary general egress,
provider dispatch, or hardware placement.

**Telos scope stays exactly `config_read` + `health_probe`, per Gate 4 as
already ratified.** `model_egress` (the third `EndpointPurpose` the scaffold
already defines) is explicitly **not** in this PR — it needs the paid-dispatch
accounting gate the gap-closure plan keeps separate, and pulling it in here
would silently widen Gate 4's own exit evidence beyond what was decided.

### Half B — PT: the actual `agent_launcher.py`/health call sites adopting the dialer

This is the part that touches PT, and it is a **human-reviewed PT PR**,
prepared the same way PR #380 was:

1. `agent_launcher.py`'s remote model-server override path currently
   validates with `model_endpoint_url.py` (no DNS resolution) then dials
   raw `httpx` directly. Route it through the new dialer instead — this is
   the "launcher configuration uses a remote model endpoint" test case from
   doc 65's matrix.
2. `/health`, once PT PR #380 lands, has no caller-supplied host path left to
   secure — nothing further needed there. Confirm this explicitly rather
   than assuming; if a future PT change reintroduces caller-supplied hosts,
   it must go through the dialer, not `validate_model_endpoint_url` alone.
3. Do **not** touch `ssrf_pinned_adapter.py` or `ssrf_fetch_policy.py` — Gate
   2's own conclusion was these stay a distinct Layer 2 surface for
   arbitrary remote fetches, not model-server dialing. Reusing them here
   would be exactly the interchangeability Gate 2 rejected.

## Required test evidence (carried forward from Doc 65, now assignable)

| Case | Where it's proven |
| --- | --- |
| Hostname resolves to a prohibited address | v2 dialer unit test (controlled DNS fake) |
| Hostname has multiple answers, one prohibited | v2 dialer unit test |
| Public configured model server with opt-in | v2 dialer unit test + PT integration test on the adopting call site |
| Launcher configuration uses a remote model endpoint | PT integration test (`agent_launcher.py` routed through the dialer) |
| Telos denies an unknown purpose | v2 `TelosPort` adapter unit test |
| Telos decision is redacted and correlated to the lifecycle run | v2 `GatewayLifecycle` integration test |

Test suites must use controlled DNS and HTTP-client fakes, matching doc 65's
own constraint — no test may contact a real metadata service or depend on a
workstation's resolver, firewall, or egress policy.

## Sequencing

1. Wait for PT PR #380 to merge (human decision, not automatable) — Half B's
   diff needs #380's already-landed `/health` shape as its base, not a
   moving target.
2. Build Half A (v2 dialer + Telos wiring) first; it has no PT dependency
   and can start immediately.
3. Build Half B once #380 is merged, as one PT PR reviewed the same way
   #380 was — not landed directly by any agent.
4. Both halves ship in the same overall change window, but as two separate
   PRs in two separate repos (this was never going to be literally one PR
   across two GitHub orgs) — "the same next PR" means the same planned unit
   of work, not one GitHub pull request spanning `oramasys/oramasys` and
   `Perpetua-Tools`.

## Explicitly out of scope for this combined PR

- `model_egress` purpose authorization (needs the paid-dispatch accounting
  gate first).
- Redirect/DNS-rebinding vectors for the *existing* SSRF Layer 2 adapter
  (`ssrf_pinned_adapter.py`) — that stays a separate, already-deferred
  future transport-authority item per doc 63.
- Any change to `ssrf_fetch_policy.py`'s own arbitrary-remote-fetch policy.
- Gate 5 (`ResolvedRoute`) and Gate 6 (Core strangler migration) — both
  still gated on Gate 4 landing first.
