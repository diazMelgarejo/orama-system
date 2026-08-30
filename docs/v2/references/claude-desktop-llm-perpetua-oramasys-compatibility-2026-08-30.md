# Reference: Claude-Desktop-LLM, Perpetua, and Oramasys Compatibility

**Status:** Approved architecture  
**Date:** 2026-08-30  
**Baseline:** `diazMelgarejo/orama-system` PR #333 at `08ad6c6f99f44aad41cfdc64c404a125c053724c`  
**Implementation plan:** [2026-08-30-001-claude-pt-orama-compatibility-plan.md](2026-08-30-001-claude-pt-orama-compatibility-plan.md)

## Purpose

Define the migration-safe compatibility architecture for
`oramasys/Claude-Desktop-LLM`, `diazMelgarejo/Perpetua-Tools`, and the
Oramasys v2 family. The goal is not to copy Perpetua implementation into the
Claude MCP server. It is to establish one semantic policy model, prove it with
portable vectors, and give each repository a narrow adapter owned by the right
domain.

Claude-Desktop-LLM is the application-side local-provider adapter. It operates
Ollama and LM Studio. It is not the generic egress-security authority,
runtime-check substrate, graph-execution engine, hardware-placement authority,
or observability authority.

## Evidence-Based Audit

| Area | Current Claude behavior | Perpetua baseline | Gap |
| --- | --- | --- | --- |
| DNS results | Resolves and pins one address. | Resolves every A/AAAA address, validates each, and rechecks the connected peer. | A multi-address hostname can contain a denied address that Claude never evaluates. |
| Address classes | Rejects DNS-mediated loopback but can allow a configured private/LAN address. | Generic SSRF transport denies loopback, private, link-local, CGNAT, multicast, reserved, and unspecified ranges. | The two mechanisms serve different purposes but are not explicitly modeled as different modes. |
| Endpoint ownership | A TypeScript policy is local to the Claude repository. | Python Layer 1/Layer 2 policy is the current implementation authority. | Semantics can drift across languages. |
| Policy proof | Native `node:test` covers loopback, redirects, and selected DNS cases. | PT has a shared deny predicate and transport-level validation. | No portable conformance-vector suite exists. |
| Runtime integration | Claude connects directly to Ollama and LM Studio only. | PT provides generic runtime, SSRF, and orchestration capabilities. | No approved versioned live integration interface exists. |
| Observability | Provider-native state is authoritative; local JSONL is secondary. | PT observability and coordination remain separate runtime concerns. | Do not introduce an OTLP or generic event dependency into Claude. |
| Core execution | Not consumed by Claude. | `oramasys/perpetua-core` PR #1 is merged, green, and review-clean. | No remediation belongs in Claude for the former state-alias or checkout-token findings. |

The current TypeScript policy's claim that it simply mirrors PT is therefore too
broad. It mirrors connection-time pinning, but not PT's full all-address,
address-class, and peer-recheck contract.

## Locked Ownership

| Owner | Owns | Does not own |
| --- | --- | --- |
| `oramasys/perpetua-core` | Dependency-minimal generic execution mechanics. | Orama policy, provider routing, endpoint policy. |
| `oramasys/agate` | Hardware capability, model affinity, and placement. | Provider health or security policy. |
| `oramasys/telos` | Endpoint/network policy semantics, portable vectors, and language-specific policy adapters. | Generic runtime-check mechanism. |
| `oramasys/phylax` | Generic runtime-check substrate and security/safety packs. | Endpoint-policy semantics or provider routing. |
| `oramasys/oramasys` | Application orchestration, routing, and provider integration. | A generic cross-domain contracts package. |
| `oramasys/Claude-Desktop-LLM` | Claude/Desktop-facing Ollama and LM Studio adapter. | A second security-policy authority or generic telemetry pipeline. |
| `diazMelgarejo/Perpetua-Tools` | Existing Python runtime/security implementation until each capability is extracted. | Permanent ownership of every extracted concern. |

There must be no generic `oramasys/contracts` repository or package. Each
contract remains with its semantic owner. Claude consumes Telos endpoint-policy
contracts, Phylax runtime-check contracts, and provider-routing contracts from
their owner-specific locations.

## Endpoint-Policy Model

Telos defines the vocabulary and conformance vectors. Implementations may be
TypeScript or Python, but they must produce the same allow/deny decision for a
given mode and evidence set.

### Modes

| Mode | Intended caller | Default | Explicit allowance |
| --- | --- | --- | --- |
| `untrusted_egress` | PT tools fetching arbitrary external URLs. | Deny all non-public, unsafe, or unresolved targets. | No private/LAN exception. |
| `provider_local` | Claude talking to a local model runtime. | Permit direct loopback only. | None required. |
| `provider_trusted_lan` | Claude talking to a deliberate operator-managed LAN model runtime. | Deny. | Exact hostname allowlist, operator opt-in, HTTPS for non-loopback, and address-class policy specifically allowing the trusted LAN range. |
| `provider_public_remote` | Claude talking to an operator-approved public provider. | Deny. | Exact hostname allowlist, operator opt-in, HTTPS, and public resolved addresses only. |

A hostname resolving to loopback is never equivalent to a caller directly
specifying loopback. It is rejected in every non-loopback mode, even when it is
allowlisted. A redirect is a new hop and must repeat the full process.

### Required Decision Inputs

Every adapter evaluates:

1. URL structure: `http` or `https` only; no userinfo, controls, or empty host.
2. Caller-supplied host identity: direct loopback, configured hostname, or IP literal.
3. All A/AAAA results for the hostname.
4. Normalized address class for every result: loopback, private, link-local,
   CGNAT, multicast, reserved, unspecified, or public.
5. The policy mode and its exact configured authority.
6. The connected peer address after the socket is opened.
7. Redirect hop count and the same inputs for every subsequent hop.

The default safe behavior is deny. DNS failure, an empty answer set, a
mixed-safe-and-denied answer set, an unexpected peer, or an unknown mode is a
deny result with a stable machine-readable code.

### Portable Contract

Telos publishes a versioned vector file, for example
`endpoint-policy-v1.json`, containing inputs and expected decision codes.
Each language adapter runs the same vector corpus without network access by
injecting resolver and connector fakes.

Minimum codes:

```text
url_invalid
scheme_disallowed
userinfo_present
hostname_missing
dns_resolution_failed
dns_answer_denied
host_not_allowlisted
remote_opt_in_required
remote_https_required
peer_address_denied
redirect_limit
allowed
```

The vector corpus must cover IPv4, IPv6, bracketed IPv6, canonical mapped IPv6,
multiple A/AAAA answers, direct loopback, DNS-to-loopback, CGNAT, IMDS,
link-local, private LAN, public remote, redirect transitions, and peer mismatch.

## Runtime Checks and Live Integration

Phylax owns a generic runtime-check envelope and pack execution. Claude does
not create its own generic check framework. Its adapter reports only
Claude-owned facts, such as selected provider, configured endpoint mode,
connection decision code, provider health, and redacted latency/error class.

A live PT/Oramasys connection starts only after the semantic owner publishes a
versioned API. The first interface must be read-only and fail closed:

```text
ProviderRouteRequest  -> resolve provider/runtime route
ProviderRouteDecision -> allowed | denied | unavailable, reason code, policy version
RuntimeCheckRequest   -> evaluate named owner-defined check
RuntimeCheckResult    -> pass | fail | unavailable, evidence references only
```

No raw prompts, model responses, credentials, endpoint secrets, or unrestricted
telemetry events cross this boundary. A missing service, incompatible version,
or unrecognized decision code leaves Claude in its local fail-closed behavior;
it never silently falls back to an unverified remote route.

## Delivery Sequence

1. **Telos foundation:** publish endpoint-policy v1 vocabulary, mode matrix,
   vectors, and Python/TypeScript adapter requirements.
2. **PT parity:** make PT's generic egress adapter consume the v1 vectors
   without broadening its untrusted-egress allowance.
3. **Claude adaptation:** replace Claude-local classification drift with the
   Telos v1 TypeScript adapter; retain the explicitly approved
   `provider_trusted_lan` mode.
4. **Phylax foundation:** publish the generic runtime-check envelope and
   security/safety pack behavior. No endpoint-policy duplication.
5. **Claude live-integration adapter:** consume versioned owner APIs behind an
   optional, fail-closed client; keep direct Ollama/LM Studio provider-native
   operations authoritative.
6. **Differential evidence and retirement:** prove vectors and live decisions
   are consistent before deleting or deprecating any duplicated policy logic.

Each step is independently reviewable. No dual writable authority is allowed.

## Acceptance Gates

- Telos v1 contains the mode matrix and deterministic vectors.
- Python PT and TypeScript Claude adapters pass the identical vector corpus.
- Claude rejects every unsafe resolved address outside the selected, explicit
  trusted-LAN exception.
- A connection peer is validated after connect and before request use.
- All redirect hops are independently classified and pinned.
- Claude continues to support direct local Ollama and LM Studio operation
  without a PT, Telos, or Phylax service being present.
- Any optional live service integration is version-negotiated, redacted,
  read-only for the first slice, and fail closed.
- No new generic `oramasys/contracts`, OTLP dependency, or duplicate
  runtime-check framework is introduced.
