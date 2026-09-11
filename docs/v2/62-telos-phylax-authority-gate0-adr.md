# ADR 62: Telos/Phylax Authority Split — Canonical Restoration

**Status:** accepted, corrected, and implementation-synchronized 2026-09-09 UTC
**Original Gate-0 date:** 2026-09-06  
**Canonical architecture date:** 2026-08-29

## Decision summary

The accepted 2026-08-29 architecture is and always was the canonical design.
The narrower September Telos scaffold was an implementation divergence, not a
superseding architectural decision. This ADR corrects that divergence and now
records the completed Gateway dedicated-dialer migration.

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
secure-dial/endpoint-policy implementations. That state is implementation drift
and is explicitly rejected by this correction.

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
14. reusable safe HTTP transport primitives for v2 consumers;
15. reusable async secure-dial primitives for non-HTTP/provider-connectivity
    consumers.

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

### Claude-Desktop-LLM transfer

`oramasys/Claude-Desktop-LLM/src/policy/endpoint-policy.ts` remains a
provider-facing compatibility facade; endpoint security executes behind Telos.
The exact verified consumer-transfer head is
`6a602e8786708dbe62a112360ddde4ba63b8c3ad`.

### Oramasys Gateway dialer — migration complete

The former `oramasys/oramasys/src/orama/gateway/dialer.py` security engine has
now been strangled into Telos rather than deleted.

The historical module survives as a **thin compatibility/application-policy
facade**. It retains:

- `ModelServerDialRequest`;
- `ModelServerDialResult`;
- `ModelServerDialer`;
- stable reason aliases;
- the Gate-4 provider/purpose/port capability matrix;
- `DialConnector` as a compatibility pointer to Telos `SecureDialConnector`.

It no longer owns DNS resolution, IP/address classification, SSRF policy,
public/private classification, endpoint-use authorization, pin selection,
peer-pin verification, redirect/proxy/TLS destination safety or decision
freshness/mismatch checks.

Telos now exposes `SecureDialer`, `SecureDialRequest`, `SecureDialResult`,
`SecureDialConnector`, and `ConnectedPeer`. The connector reports the actual
peer so Telos can verify the connection terminates at the vetted pin. This
closes the old compatibility contract gap where an opaque provider reference
alone could not prove connection-time pinning.

`GatewayLifecycle` no longer has a semantic-only preauthorization path against
a raw `EndpointRef` and no longer permits an optional/no-dialer bypass. Config
and health operations use mandatory Telos-backed secure dials, and the actual
Telos decision metadata from those dials becomes the routing-state policy
metadata.

Exact verified implementation evidence:

- Telos PR #1 head: `19810d0493344aa507c29c462f68afbc1b98ecf8`;
- Telos CI run `34409993139`: Python 3.11 and 3.12 success;
- Oramasys PR #5 head: `1eb191e99f0cc5d9604f103573aebaec2e5defc0`;
- Oramasys CI run `34410898142`: Python 3.11 and 3.12 success, 51 tests,
  94.27% total coverage, compile smoke success;
- fresh review-thread sweeps: zero threads on both PRs.

The v1 PT native dialer work remains valid inside the v1 regime because v1
never consumes v2 packages. That native implementation is independent parity
work, not authority leakage from v2 back into PT.

## Decision 3: Telos executable contracts and parity

`oramasys/telos` PR #1 restores the Tripwire/Telos authority and provides the
current v2 implementation evidence. Its clean-room parity sources include:

- `diazMelgarejo/Perpetua-Tools@a551da4fa97e5fbc6f908ad077c7b6d8030a3220`;
- `oramasys/Claude-Desktop-LLM@ba4f3910efc6496cd6476a274b93f4b877ba12b3`;
- historical Oramasys Gateway vectors at
  `oramasys/oramasys@8ad2574010013d9f5b40b193d316516872462130`.

The implementation covers endpoint identity, address policy, DNS/rebinding,
pinned transport, peer verification, redirect semantics, proxy isolation, TLS
Host/SNI identity, semantic authorization composition and bounded secure-dial
connectivity. Current Telos evidence head:
`19810d0493344aa507c29c462f68afbc1b98ecf8`.

Required project coverage is at least **80%**. A component that defines a
higher threshold keeps that higher threshold; it must never be lowered to
satisfy this floor.

## Decision 4: Phylax boundary

Phylax owns generic security/safety mechanisms, including compile/runtime
admission, provenance/integrity checks, capability admission, secrets or
filesystem safety mechanisms assigned to it, and monitorability/security
policy-pack infrastructure.

Phylax explicitly does **not** own endpoint parsing/canonicalization,
IP/CIDR classification, SSRF, DNS rebinding defense, redirect destination
policy, proxy isolation, TLS destination identity or safe dial/socket pinning.
Those are Telos concerns.

Telos and Phylax use Apache License 2.0.

## Decision 5: consumer contract rule

A v2 consumer MUST NOT maintain a permanent independent endpoint-security
implementation.

Consumers may contain thin language/process bridge adapters,
provider-specific request/response protocol code, provider readiness/lifecycle
logic, application-level routing/effect policy, compatibility names and
deterministic test doubles that do not duplicate Telos policy semantics.

Consumers may not independently own SSRF classification, DNS-rebinding policy,
endpoint allow/deny logic that competes with Telos, socket/IP pinning policy,
redirect destination security or proxy/TLS destination-security policy.

There is no silent direct-network fallback when Telos is unavailable. Failure
to obtain a valid Telos result is fail-closed.

## Decision 6: regime boundary

- PT v1 continues to own and run its existing v1 endpoint/security code.
- PT never imports v2 Telos.
- v2 never imports/runs PT endpoint-security code.
- parity is established by behavior/evidence comparison, not runtime reuse.
- migration into Telos is final clean-room ownership transfer, not a staged
  dual-authority runtime.

## Decision 7: documentation and provenance

Historical plans and preserved source documents remain historical evidence.
Where they describe the semantic-only September scaffold or a separate unnamed
SSRF/transport owner, this ADR supersedes that interpretation.

Repository-specific architectural claims must be grounded in repository files,
commits, PRs/reviews, PT `.agent` memory or explicit approved decisions.
Citation-contaminated secondary syntheses remain quarantined until claim-by-
claim provenance is restored.

## Consequences

- Telos is the only steady-state v2 endpoint-security authority.
- Claude-Desktop-LLM is a Telos consumer.
- Oramasys Gateway's dedicated dialer has been absorbed into Telos; the old
  module remains only as a thin compatibility/application-policy facade.
- Phylax stays generic and does not absorb endpoint semantics.
- PT remains authoritative only inside v1 and as read-only parity evidence for
  v2 clean-room work.
- Telos and Phylax use Apache-2.0.
- all projects maintain at least 80% test coverage unless an existing component
  threshold is stricter.

This Gateway-complete status does **not** claim that every unrelated historical
or legacy direct `curl`, `urllib` or `httpx` caller across the broader ecosystem
has already been migrated. Those remain separately auditable consumer paths.

## Current implementation evidence

- Telos restoration + secure dial: `oramasys/telos` PR #1,
  `19810d0493344aa507c29c462f68afbc1b98ecf8`.
- Gateway compatibility migration: `oramasys/oramasys` PR #5,
  `1eb191e99f0cc5d9604f103573aebaec2e5defc0`.
- Claude consumer transfer: `oramasys/Claude-Desktop-LLM` PR #1,
  `6a602e8786708dbe62a112360ddde4ba63b8c3ad`.
- Phylax boundary correction: `oramasys/phylax` PR #1,
  `9c5ad79e95c0400a0e24ef7c4f5d6fd90a9b27c5`.
- Original Orama reconciliation: merged PR #351,
  merge commit `101ad171444487bc186bbf8d0c6d6d67ac71d506`.
- PT native v1 hardening/memory: `diazMelgarejo/Perpetua-Tools` PR #382.

None of these references authorizes merge by itself. Merge remains a separate
human decision.
