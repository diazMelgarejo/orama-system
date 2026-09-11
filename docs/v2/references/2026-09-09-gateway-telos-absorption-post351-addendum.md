# Gateway → Telos absorption — post-PR-351 addendum (2026-09-09 UTC)

## Purpose

PR #351 merged before the Oramasys Gateway dedicated-dialer consumer migration
was completed. This addendum preserves the chronology: the merged restoration
handoff remains correct evidence of the state at merge time, and this document
records the later verified completion of that explicitly remaining dependency.

The recorded completion commit is timestamped **2026-09-09T22:14:53Z**.
UTC is the primary date basis for this evidence; no local-time date is used as
the canonical record.

## Completed migration

The former `oramasys/oramasys/src/orama/gateway/dialer.py` security engine has
been absorbed into `oramasys/telos` **additively, not deleted**.

The Gateway module remains as a thin compatibility/application-policy facade
retaining the historic public names and Gate-4 provider/purpose/port policy.
Endpoint-security mechanics now execute in Telos.

### Telos additions

Telos now owns a reusable async secure-dial contract:

- `SecureDialRequest`;
- `SecureDialResult`;
- `SecureDialer`;
- `SecureDialConnector`;
- `ConnectedPeer`.

It resolves and validates every DNS answer, derives destination classification,
authorizes the Telos-produced `EndpointIdentity`, passes only a vetted pin to
the connector and verifies the connector-reported peer equals that pin.
Decision endpoint mismatch, expiration, DNS/address failure, timeout, connector
failure and peer mismatch all fail closed.

HTTP-specific redirect, proxy, credential and TLS Host/SNI behavior remains in
Telos's safe transport implementation under the same endpoint-security
authority.

### Gateway compatibility retained

Oramasys retains:

- `ModelServerDialRequest`;
- `ModelServerDialResult`;
- `ModelServerDialer`;
- stable Gateway reason aliases;
- provider/purpose/port capability policy;
- `DialConnector` as a compatibility pointer to Telos `SecureDialConnector`;
- lifecycle/progress/idempotency/readiness/routing-state ownership.

The connector compatibility contract is intentionally strengthened from an
opaque provider-ref-only result to `ConnectedPeer(provider_ref, peer_address)`
so Telos can prove connection-time pinning rather than merely preflight it.

### Lifecycle integration

`GatewayLifecycle` no longer performs a duplicate semantic-only Telos
preauthorization against a raw `EndpointRef`, and the secure dialer is no longer
optional.

Config and health secure dials are mandatory. Their real Telos decision/policy
metadata becomes the source persisted in routing state. There is no silent
non-Telos path when the dialer is absent or Telos fails.

## Exact verified evidence

### Telos

- repository: `oramasys/telos`;
- PR: #1;
- exact head: `19810d0493344aa507c29c462f68afbc1b98ecf8`;
- CI run: `34409993139`;
- Python 3.11: success;
- Python 3.12: success;
- coverage gate: success;
- compile smoke: success;
- fresh review threads: zero.

### Oramasys Gateway

- repository: `oramasys/oramasys`;
- PR: #5 — `refactor(gateway): absorb endpoint security into Telos`;
- branch: `2026-09-10-gateway-dialer-telos-absorption`;
- exact head: `1eb191e99f0cc5d9604f103573aebaec2e5defc0`;
- Telos dependency pin: `19810d0493344aa507c29c462f68afbc1b98ecf8`;
- `oramasys/perpetua-core` dependency pin:
  `86225fa5c974ab2fe0b65d228a2b31888aaa440c`;
- CI run: `34410898142`;
- Python 3.11: success;
- Python 3.12: success;
- **51 tests passed**;
- **94.27% total Oramasys coverage**;
- compile smoke: success;
- fresh review threads: zero.

The immutable Core pin also closes a pre-existing clean-runner installation
hole: `perpetua-core>=2.0.0-alpha.1` was not resolvable from PyPI.

## Preserved security vectors

No useful Gateway vector was discarded. The migration map in Oramasys records
where each vector now lives, including:

- mixed DNS-answer denial;
- metadata endpoints;
- IPv4-mapped IPv6 normalization;
- CGNAT;
- 6to4 relay anycast `192.88.99.0/24`;
- Teredo `2001::/32`;
- 6to4 `2002::/16`;
- public endpoint opt-in;
- endpoint-decision identity/freshness;
- bounded dial timeout;
- vetted pin selection;
- post-connect peer-pin verification.

## Ownership versus global enforcement

This closes the **Oramasys Gateway dedicated-dialer** migration that was still
pending in the merged PR #351 handoff.

It does not retroactively claim that every unrelated historical or legacy
`curl`, `urllib` or `httpx` call site elsewhere in the broader ecosystem is
already Telos-enforced. Those call sites remain individually auditable consumer
paths.

The architectural rule is unchanged: permanent reusable v2 endpoint-security
mechanisms belong only in Telos.

## Memory follow-up gate

PT `.agent` durable memory/coordination evidence may now be synchronized to the
exact Telos and Oramasys heads above because both v2 heads are independently
verified.

Rendered PT semantic memory such as `LESSONS.md` must continue to be produced by
the canonical memory tooling rather than hand-edited.

## Merge governance

This addendum records verification and architecture state. It does not authorize
merging Telos PR #1, Oramasys PR #5, or any other open PR.
