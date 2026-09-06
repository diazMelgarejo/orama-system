# Gate 1 Endpoint Observation And Conformance Evidence

**Status:** v2 evidence baseline, 2026-09-06
**Authority:** [ADR 62](62-telos-phylax-authority-gate0-adr.md)
**Implementation home:** `oramasys/telos` behavior vectors and tests

## Purpose

This document records the read-only v1 observations that Gate 1 needs without
changing a v1 repository. It also assigns the v2 conformance evidence to the
successor authority that owns it.

v1 and v2 are separate regimes. This is not a migration patch for
Perpetua-Tools or orama-system. The observations below are a portable baseline
for new v2 consumers; they do not authorize a dependency from either v1
repository into `oramasys/*`.

## Authority Map

| Boundary | Observed v1 authority | v2 evidence and future authority | Not interchangeable with |
| --- | --- | --- | --- |
| Transport identity parse/build | `src/utils/endpoint_policy_core.py` | Read-only golden observations; a future v2 transport authority may recertify against them | Model endpoint validation and Telos authorization |
| Model endpoint allow/deny | `src/utils/model_endpoint_url.py` | Separate model-endpoint policy parity work | Transport reconstruction and SSRF pinning |
| SSRF preflight | `src/utils/ssrf_fetch_policy.py` | Separate Layer 2 security vector set | Telos purpose rules |
| SSRF pinned transport | `src/utils/ssrf_pinned_adapter.py` | Separate Layer 2 redirect, DNS-rebinding, and connection-pinning proof | Telos purpose rules |
| Purpose-scoped endpoint use | No v1 equivalent selected by this evidence | `oramasys/telos`: `EndpointRef`, `EndpointUseRequest`, `EndpointUseDecision`, and `EndpointPolicy.version` | URL parsing, DNS resolution, provider selection |

Telos receives an already-normalized `EndpointRef` with trusted public/private
classification. It does not parse raw URLs, resolve DNS, follow redirects, or
open network connections.

## Read-Only Importer Inventory

The observed importer categories are evidence of boundary separation, not a
request to edit those callers.

| Observed module | Boundary | Representative observed consumers |
| --- | --- | --- |
| `utils.endpoint_policy_core` | transport reconstruction | FastAPI app, LAN discovery, model registry, agent launcher, SSRF pinned adapter |
| `utils.model_endpoint_url` | model endpoint allow/deny | FastAPI app, connectivity, routing, supervisor, worker registry, discovery registry, agent launchers |
| `endpoint_policy` package | published package compatibility | package validator and fuzz tests |
| `utils.ssrf_fetch_policy` | SSRF preflight | pinned adapter and SSRF tests |
| `utils.ssrf_pinned_adapter` | SSRF pinned transport | connectivity, bridge clients, telemetry exporter, and transport tests |

The observed transport vectors cover qualified and bare hosts, IPv6 forms,
backend-port replacement, normalization, malformed schemes and ports, and
credential-bearing URL rejection. They are transport identity evidence only.
SSRF redirects, DNS rebinding, and connection pinning remain explicitly out of
scope for that vector family.

## Telos Conformance Contract

ADR 62 requires JSON vectors checked into `oramasys/telos`. The initial suite
must prove:

1. Exact allowed endpoint and purpose succeeds.
2. Exact non-member endpoint denies.
3. Unknown purpose denies.
4. A public endpoint denies without explicit `allow_public` opt-in.
5. Policy-version rollover fails closed until the consumer re-certifies
   against vectors generated for that version.

The vector file separately declares URL parsing, DNS classification, redirect
following, and connection pinning out of scope. A future consumer must use the
policy version in the vector artifact as its certification key. On mismatch it
must deny rather than falling back to compatibility mode.

## Gate 1 Exit Evidence

- [x] v1 importer inventory captured as read-only v2 evidence.
- [x] Transport/model/SSRF/Telos responsibilities distinguished.
- [x] Telos JSON vector schema and fixture-driven test suite created in the
  successor repository.
- [ ] A concrete Gateway consumer adopts the typed Telos contract. This is
  Gate 4 work and must not begin until its own dependency gate is satisfied.
- [ ] Layer 2 pinned-transport redirect and rebinding vectors are specified by
  the future transport authority; they are deliberately not Telos fixtures.
