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
this policy. Strict mode trusts environment allowlists and the `approved_ips`
entries recorded by explicit operator approval. Legacy `ips` entries have no
approval provenance and are therefore automatic-admission candidates only;
operators must explicitly reapprove any legacy entries required in strict mode.
Explicit revocation overrides every positive source, including archives,
discovery state, environment configuration, and relaxed admission.

`scripts/mesh/discovery_trust.py --remove-ip <address>` revokes effective trust.
Only explicit `--trust-ip <address>` or an affirmative interactive approval can
lift that revocation. Automatic rediscovery cannot undo it.

Trust admission, revocation, and migration-recipient updates share one
cross-process local transaction lock. The lock covers only local
read-validate-write state transitions; TLS delivery and other network waits run
outside it, then an acknowledgement is revalidated against freshly loaded state
before it can settle a recipient. A malformed or unreadable `known-peers.json`
or `self-identity.json` is not an empty first run: the affected operation stops
without overwriting the file, and an operator must repair the authority state.
The shibboleth probe rejects non-finite or non-positive timeouts and caps each
network operation at 0.5 seconds; this is not a whole-probe deadline.

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
An explicit `--remove-ip` revocation retires that address from both the current
retry list and the durable audience used by any later superseding migration, so
it cannot receive a bearer or block completion. Other permanent retirements
require an explicit local reconciliation with a backup and evidence of the
decision.
If the local address changes again while a migration is still pending, the
sender supersedes the stale pending entry and announces `last_known_ip` to the
newest address to the union of fresh targets and **all** original recipients,
including recipients that acknowledged the previous address. Their previous
acknowledgements do not apply to a newer address. Returning to the last committed
address is also a new notification, not permission to drop pending work.

The pending record retains `all_recipients` until notification completes. Legacy
pending records that predate this field cannot reconstruct previously removed
recipients. Automatic notification stops without changing those records; an
operator must supply the full original audience in `all_recipients` when
reconciling such a record. No bulk queue flush or live topology rewrite is implied.

## Regression evidence

Run `tests/test_discovery_migration_boundaries.py` for redirect refusal, strict
policy, revocation, canonical credential selection, partial-delivery recovery,
the transaction/corruption failure paths, and the
producer-to-authenticated-route-to-persistence-to-sender acknowledgement path.
These are synthetic tests, not evidence of a live LAN round trip or serving
activation.
