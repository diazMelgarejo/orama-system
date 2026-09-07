# Gate 2: Policy-Surface Evidence and PT Remediation Boundary

**Status:** evidence complete; PT remediation proposal requires separate human-reviewed work
**Date:** 2026-09-07
**Authority:** [ADR 62][adr-62], [Gate 1 evidence][gate-1-evidence], and
[Gate 2 scope][gate-2-scope]

[adr-62]: 62-telos-phylax-authority-gate0-adr.md
[gate-1-evidence]: 63-gate1-endpoint-observation-and-conformance-evidence.md
[gate-2-scope]: 64-gate2-policy-surface-noninterchangeability-scope.md
**Regime boundary:** this is read-only v1 evidence. It neither changes Perpetua-Tools nor
authorizes a v1 change. A future PT pull request must start from this evidence and be
reviewed on PT's own timeline.

## Decision

The three endpoint-policy surfaces are intentionally non-interchangeable:

| Surface | Authority | Intended input | What it must not replace |
| --- | --- | --- | --- |
| Transport identity | `endpoint_policy_core` | Known provider identity and URL construction | Host authorization or DNS safety |
| Model endpoint policy | `model_endpoint_url` | Model-server URL grammar and permitted address classes | DNS resolution, connection pinning, or arbitrary-fetch SSRF policy |
| SSRF fetch policy | `ssrf_fetch_policy` plus `ssrf_pinned_adapter` | Arbitrary remote fetches and fixed reviewed hosts | The LAN model-server policy, which intentionally permits local/private targets |

No caller may infer DNS safety merely because it passed model endpoint validation.
Conversely, routing LAN model servers through the generic arbitrary-fetch policy would
silently reject a supported deployment shape. The missing capability is a
model-server-specific, DNS-aware transport policy, not a reason to weaken the existing
SSRF policy.

## Read-only evidence

Three independent read-only source reviews reached the same material conclusions.

### 1. Public-host validation is a real runtime opt-in, not test-only code

`ALLOW_PUBLIC_MODEL_ENDPOINTS` is read at runtime by
`src/utils/model_endpoint_url.py`, documented by that module and the published
endpoint-policy package, and exercised by tests. When enabled, a non-literal hostname
is accepted without DNS resolution. Literal prohibited address classes remain rejected,
but hostname text is not evidence of the address ultimately dialed.

The repository contains optional host egress controls, but this review found no source
evidence that a particular deployment has installed and enforced one. They remain
defense in depth, not proof that an in-process gap is closed.

### 2. The original launcher chain is refuted; a separate configuration boundary remains

Doc 64 correctly identified raw HTTPX model probes, but its asserted path through
`resolve_local_or_remote()` is not live: the function has no production caller. The
actual launcher path derives remote model probe URLs directly from operator-controlled
environment configuration and sends raw HTTPX requests without either model endpoint
validation or the SSRF adapter.

This is **not** evidence of a public request-to-fetch exploit. The input is local
operator configuration, so its threat classification depends on the configuration
authority and deployment boundary. It is nevertheless a policy-conformance gap: a
future PT review must decide whether remote model configuration is trusted inventory or
must receive model-server DNS-aware validation before use. That decision must also
address credentials sent to a configured remote endpoint and the use of cleartext
transport where applicable.

### 3. The FastAPI health route is a confirmed mixed-surface gap

The control-plane auth policy deliberately exempts `/health`. FastAPI binds the route's
three model-host arguments from query parameters. Existing tests demonstrate this
binding for rejected literal metadata-like addresses.

The reachable path is:

```text
unauthenticated GET /health?{model-host parameter}
  -> validate_model_endpoint_url()
  -> backend_health_map()
  -> check_{backend}()
  -> _probe_local()
  -> raw httpx.get()
```

`_probe_local()` repeats the same syntactic model-endpoint validation, but neither call
resolves a hostname before raw HTTPX connects. Therefore, when the documented
public-model-host opt-in is enabled, a caller can supply a hostname that passes the
model policy while resolving to an address class that policy would otherwise forbid.

This is a **confirmed reachable policy gap under the explicit opt-in**, not a claim
that every deployment is exploitable: a deployment must expose the public health route
and enable public model hosts. The source review establishes the request-to-raw-fetch
path and does not claim deployment-specific network reachability.

### 4. Other probe paths are distinct decisions

The orchestration candidate probes use raw HTTPX for catalog/configuration-derived
local endpoints. Cloud connectivity probes use the existing SSRF adapter. These paths
must not be collapsed into the health-route finding: the former rely on trusted
inventory, while the latter already use the arbitrary-fetch policy.

## Proposed PT remediation, for separate review

The smallest safe first change is to remove caller-supplied model endpoint overrides
from the unauthenticated `/health` route. It should probe only server-owned configured
endpoints and retain a minimal liveness response. If operator diagnostics genuinely
need ad hoc endpoints, add a separately protected diagnostic route with an explicit
authorization decision and rate limiting; do not reintroduce them as public health
query parameters.

Before allowing remote model-server hostnames in any runtime path, a PT proposal must
also define and implement a dedicated model-server dialer that:

1. resolves every A/AAAA result before dispatch and applies a model-server address
   policy to every result;
2. preserves intentional loopback/private LAN support while rejecting link-local,
   metadata-like, multicast, reserved, and other prohibited classes;
3. rechecks or pins the resolved connection across redirects and retries, with
   redirects disabled until that behavior is implemented and tested;
4. has an async-compatible client contract, timeouts, and no credential forwarding to
   an unverified remote origin; and
5. is used by all remote model-server callers, including launcher configuration, rather
   than treating `ssrf_request()` as a drop-in replacement for async LAN probes.

The existing generic SSRF adapter is valuable evidence, but its default policy rejects
the LAN targets that model serving intentionally supports. A blind substitution would
be a regression and is not proposed here.

## Required test evidence for a future PT PR

| Case | Expected result |
| --- | --- |
| Public health query supplies a custom model host | Ignored because health reads server-owned configuration only, or rejected before any network call |
| Hostname resolves to a prohibited address | Rejected before dispatch; assert the HTTP client was never called |
| Hostname has multiple answers, one prohibited | Rejected before dispatch |
| Intentional loopback/private configured model server | Allowed only by the dedicated model-server policy |
| Public configured model server without opt-in | Rejected |
| Public configured model server with opt-in | Allowed only after DNS-aware policy checks; redirects remain disabled or are independently revalidated |
| Launcher configuration uses a remote model endpoint | Parses and validates through the same dedicated policy before probes or credential-bearing requests |

The test suite must use controlled DNS and HTTP-client fakes. It must not contact a
metadata service or rely on a workstation's resolver, firewall, or egress policy.

## Gate 2 completion and follow-on ownership

Gate 2's documentation and evidence obligation is complete: the call-site choices are
classified, the Doc 64 candidate is corrected, and the genuine public input path has a
bounded remediation proposal. Implementation belongs to a separately reviewed PT PR;
it is not v2 work and is not authorized by this record.

Remaining related work is deliberately separate:

- Gate 4 owns Telos enforcement wiring.
- Future transport work owns real connection pinning and redirect/rebinding vectors.
- PT operators own deployment-specific egress enforcement evidence.
