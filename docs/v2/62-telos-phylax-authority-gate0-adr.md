# ADR 62: Telos/Phylax Authority Split — Canonical Restoration

**Status:** accepted and corrected, 2026-09-10  
**Original Gate-0 date:** 2026-09-06  
**Canonical architecture date:** 2026-08-29

## Decision summary

The accepted 2026-08-29 architecture is and always was the canonical design.
The narrower September Telos scaffold was an implementation divergence, not a
superseding architectural decision. This ADR corrects that divergence.

- **Telos** is the single v2 authority for **all endpoint-specific security**.
- **Phylax** is the generic compile/runtime security, safety, admission and
  monitorability authority and does not own endpoint-specific policy.
- **Agate** owns hardware capability/fit/placement evidence.
- **Oramasys** owns application/workflow composition, routing, budgets,
  effects, lifecycle and progress.
- **Perpetua Core** owns dependency-minimal execution mechanics.
- provider owners retain provider protocol/readiness/lifecycle semantics but
  must consume Telos for endpoint security rather than maintain independent
  secure connectors.

Telos and Phylax are Apache-2.0. Oramasys and Perpetua Core remain MIT.

## Why this correction is necessary

The original Tripwire design and the accepted 2026-08-29 Telos/Phylax split
assigned the whole endpoint-security problem to one authority: endpoint
identity, SSRF, DNS/rebinding defense, dial/socket pinning, redirect safety,
proxy isolation, TLS destination identity and purpose-scoped endpoint use.

The initial September `oramasys/telos` scaffold incorrectly narrowed Telos to
semantic endpoint-use authorization and described DNS, pinning and transport
safety as somebody else's lower layer. That created an unnamed v2 owner and
caused `oramasys/oramasys` and `oramasys/Claude-Desktop-LLM` to carry their own
secure-dial/endpoint-policy implementations. That state is implementation
drift and is explicitly rejected by this correction.

## Decision 1: repository shape

Telos and Phylax remain standalone `oramasys/*` repositories. Their repository
existence is not the disputed point; the disputed point was Telos's narrowed
scope. The standalone repositories are retained while their boundaries are
restored to the accepted architecture.

## Decision 2: single executable endpoint-security authority

**Canonical owner: `oramasys/telos`.**

Telos owns, end to end:

1. URL parsing and canonical endpoint identity;
2. scheme/host/port normalization, including IDNA/canonical host handling;
3. IP/CIDR and special-use destination classification;
4. cloud-metadata and SSRF protections;
5. DNS resolution and validation of every A/AAAA answer;
6. DNS rebinding / TOCTOU resistance;
7. connection-time IP/socket pinning;
8. post-connect peer-pin verification;
9. redirect revalidation on every hop;
10. proxy isolation;
11. TLS destination identity and original Host/SNI preservation;
12. credential/header hygiene across redirects;
13. purpose-scoped semantic endpoint-use authorization;
14. reusable safe transport primitives for v2 provider/application consumers.

A semantic allow decision is not transport-safety evidence. A transport-safe
endpoint is not purpose-authorized by itself. Telos composes both decisions
before network use.

### Canonical endpoint identity

Caller-provided booleans such as `is_public` are not trusted security evidence.
Telos derives normalized endpoint identity and destination classification from
its own parsing/resolution path. Consumers may provide operator intent such as
whether remote endpoints are enabled and which configured endpoints are
eligible, but they do not classify the destination on Telos's behalf.

### v1 evidence versus v2 authority

The following v1 PT surfaces are **read-only golden evidence**, not v2 runtime
dependencies:

- `packages/endpoint-policy/`;
- `src/utils/endpoint_policy_core.py`;
- `src/utils/ssrf_fetch_policy.py`;
- `src/utils/ssrf_pinned_adapter.py`;
- their associated endpoint/SSRF/pinning tests and prior design records.

The v2 implementation is a clean-room reimplementation. No v2 runtime may
import, execute, locate, or silently fall back to PT endpoint-security code.

### Claude-Desktop-LLM evidence and transfer

`oramasys/Claude-Desktop-LLM/src/policy/endpoint-policy.ts` was valuable v2
implementation evidence, especially for direct-provider behavior, connection
pinning, redirect revalidation and cancellation. It is not a permanent
endpoint-security authority.

The consumer-transfer implementation is tracked in
`oramasys/Claude-Desktop-LLM` PR #1. Its provider-facing `guardedFetch()`
becomes a compatibility facade over the Telos bridge; endpoint security runs
inside Telos. Exact verified consumer-transfer head at the time of this ADR
correction: `29aa88cb4191669a575b4ba7b9734c4e98482995`.

### Oramasys Gateway dialer

`oramasys/oramasys/src/orama/gateway/dialer.py` is likewise transitional
implementation evidence/compatibility code, not a second endpoint-security
authority. Its DNS/address-classification/dial behavior must be strangled into
Telos and reduced to an application/provider consumer adapter. Oramasys keeps
application policy and lifecycle semantics; Telos owns the endpoint-security
primitive.

The v1 PT native dialer work remains valid inside the v1 regime because v1
never consumes v2 packages. That native implementation is independent parity
work, not authority leakage from v2 back into PT.

## Decision 3: Telos executable contracts and parity

`oramasys/telos` PR #1 restores the Tripwire/Telos authority and provides the
current v2 implementation evidence. Its clean-room parity sources are pinned:

- `diazMelgarejo/Perpetua-Tools@a551da4fa97e5fbc6f908ad077c7b6d8030a3220`;
- `oramasys/Claude-Desktop-LLM@ba4f3910efc6496cd6476a274b93f4b877ba12b3`.

The implementation covers endpoint identity, address policy, DNS/rebinding,
pinned transport, peer verification, redirect semantics, proxy isolation,
TLS Host/SNI identity and semantic authorization composition. The exact Telos
PR #1 head recorded by this ADR is
`aee02988955c6abc181cd24b29e640c8891f928a`.

Required project coverage is at least **80%**. A component that defines a
higher threshold keeps that higher threshold; it must never be lowered to
satisfy this floor.

## Decision 4: Phylax boundary

Phylax owns generic security/safety mechanisms, including compile/runtime
admission, provenance/integrity checks, capability admission, secrets or
filesystem safety mechanisms assigned to it, and monitorability/security
policy-pack infrastructure.

Phylax explicitly does **not** own:

- endpoint parsing/canonicalization;
- IP/CIDR endpoint classification;
- SSRF policy;
- DNS rebinding defense;
- redirect destination policy;
- proxy isolation;
- TLS destination identity;
- safe dial/socket pinning.

Those are Telos concerns.

The initial MIT scaffold was incorrect. Telos and Phylax use Apache License
2.0, matching the endpoint-policy authority being replaced.

## Decision 5: consumer contract rule

A v2 consumer MUST NOT maintain a permanent independent endpoint-security
implementation.

Consumers may contain:

- thin language/process bridge adapters;
- provider-specific request/response protocol code;
- provider readiness/lifecycle logic;
- application-level routing and effect policy;
- deterministic test doubles that do not duplicate Telos policy semantics.

Consumers may not independently own:

- SSRF classification;
- DNS-rebinding policy;
- endpoint allow/deny logic that competes with Telos;
- socket/IP pinning policy;
- redirect destination security;
- proxy/TLS destination-security policy.

There is no silent direct-fetch fallback when Telos is unavailable. Failure to
obtain a valid Telos result is fail-closed.

## Decision 6: regime boundary

v1 and v2 are separate regimes.

- PT v1 continues to own and run its existing v1 endpoint/security code.
- PT never imports v2 Telos.
- v2 never imports/runs PT endpoint-security code.
- parity is established by behavior/evidence comparison, not runtime reuse.
- migration into Telos is final clean-room ownership transfer, not a staged
  dual-authority runtime.

## Decision 7: documentation and provenance

Historical plans and preserved source documents remain historical evidence.
Where they describe the semantic-only September scaffold or a separate unnamed
SSRF/transport owner, this ADR and the current PR #351 errata supersede that
interpretation.

Repository-specific architectural claims must be grounded in repository files,
commits, PRs/reviews, or PT `.agent` memory. Unrelated external pages are not
valid evidence for ADR contents, project epochs, contract names, or commit
history. Citation-contaminated secondary syntheses remain quarantined until
claim-by-claim provenance is restored.

## Consequences

- Telos is the only steady-state v2 endpoint-security authority.
- Claude-Desktop-LLM becomes a Telos consumer.
- Oramasys Gateway's dedicated dialer is transitional and must be outsourced
  into Telos rather than becoming a second permanent authority.
- Phylax stays generic and does not absorb endpoint semantics.
- PT remains authoritative only inside v1 and as read-only parity evidence for
  v2 clean-room work.
- Telos and Phylax use Apache-2.0.
- all projects maintain at least 80% test coverage unless an existing component
  threshold is stricter.

## Current implementation evidence

- Telos restoration: `oramasys/telos` PR #1.
- Claude consumer transfer: `oramasys/Claude-Desktop-LLM` PR #1.
- Orama reconciliation: `diazMelgarejo/orama-system` PR #351.
- PT native v1 dedicated-dialer hardening/evidence: `diazMelgarejo/Perpetua-Tools` PR #382.

None of these references authorizes merge by itself. Merge remains a separate
human decision.
