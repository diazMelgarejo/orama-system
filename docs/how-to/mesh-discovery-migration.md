# Discovery Trust and Migration Recovery

Discovery is not serving authorization. Model-endpoint liveness and peer-portal
reachability are distinct observations; a migration updates address eligibility,
not certificate trust, credentials, firewall rules, or serving activation.

## Transport and credential boundaries

- Discovery authentication and migration POSTs use a configured CA with chain
  and hostname validation. Redirects are rejected, including same-origin ones.
- The shared outbound resolver tries the explicit peer credential first, then
  supported Orama and PT lane candidates. Only authentication refusals permit
  trying another credential. Migration signing keys remain a separate lane.
- A `401` followed by `200` measures access behavior, not server possession of a
  secret. Verified TLS authenticates the server.

## Admission and removal

Strict configuration mode refuses automatic migration to an address that has
not been explicitly configured or approved. Signature validity does not override
this policy. Explicit revocation overrides every positive source, including
archives, discovery state, environment configuration, and relaxed admission.

`scripts/mesh/discovery_trust.py --remove-ip <address>` revokes effective trust.
Only explicit `--trust-ip <address>` or an affirmative interactive approval can
lift that revocation. Automatic rediscovery cannot undo it.

## Delivery and acknowledgement

The receiver acknowledges a migration only after verification and atomic trust
state persistence. Its reply contains `ok: true` and the SHA-256 of the exact
canonical announcement. Invalid signatures, policy rejection, or storage failure
produce a negative application result; HTTP success alone is insufficient.

The sender saves outstanding recipients before delivery and after each verified
acknowledgement. Retries read that state from disk, skip acknowledged recipients,
and use a fresh signed announcement for remaining recipients. The prior committed
address remains unchanged until all recipients acknowledge. Empty recipient lists
are respected and never expanded implicitly.

Pending recipients are never retired automatically by age or failure count.
An operator must explicitly reconcile a permanently retired recipient in the
local self-identity state, preserving a local backup and evidence of the decision.
A second address change while another migration is pending stops automatic
notification until that outstanding migration is reconciled. No bulk queue flush
or live topology rewrite is implied by this workflow.

## Regression evidence

Run `tests/test_discovery_migration_boundaries.py` for redirect refusal, strict
policy, revocation, canonical credential selection, partial-delivery recovery,
and the producer-to-authenticated-route-to-persistence-to-sender acknowledgement
path. These are synthetic tests, not evidence of a live LAN round trip.
