# SSRF Defense in Depth (three layers, one job each)

> Companion to
> [`53-maestro-swarm-v2-redesign-critique.md`](../53-maestro-swarm-v2-redesign-critique.md). Pointer
> from
> [`../../plans/2026-07-02-endpoint-policy-standardization-execution.md`](../../plans/2026-07-02-endpoint-policy-standardization-execution.md).
> Source: Defense-in-Depth SSRF Prevention in 2025-2026 (restricted/for-Perplexity research, not
> tracked in this repo). **Unverified guidance** — this source has not gone through this repo's
> verifier/approval gate; the conclusions below are treated as informative reference, not as an
> approved-provenance requirement, until that source is either tracked and verified or its claims
> are independently re-derived from primary references (OWASP SSRF Cheat Sheet, AWS IMDSv2 docs,
> etc., already cited inline where used).

## The three layers

| Layer               | What it stops                                                                                                                      | What it cannot stop                     | Owner                                | Status                                                                                                                                                       |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1 Pre-flight        | Bad schemes, userinfo, control chars, octal/hex/dword, IPv4-mapped IPv6, RFC1918, loopback, link-local, CGNAT, multicast, reserved | Rebinding, redirects                    | PT `src/utils/ssrf_fetch_policy.py`  | **Shipped** — 22 tests (unit + hypothesis property), 2026-08-20                                                                                              |
| 2 Pinning transport | Rebinding (resolve → validate **all** A/AAAA → connect to that IP, SNI = hostname); each redirect hop re-validated                 | A process that bypasses the HTTP client | New PT adapter, every user-URL fetch | **Not started** — assigned to codex-execution-bridge / agnes-antigravity-claude via PT-T5-APPROVAL-002 / PT-T5-LEDGER-003 / PT-T5-SETTLE-004 / PT-T5-API-005 |
| 3 Network / IMDS    | Anything that still dials metadata                                                                                                 | Nothing in-app                          | Operator runbook (below), not Python | **This doc**                                                                                                                                                 |

**Validator cannot pin.** Layer 1 (PT `src/utils/ssrf_fetch_policy.py`) is a pure string/IP-literal
check with no network I/O — non-allowlisted hostnames are denied outright, not resolved and then
checked. This is a separate module and test path from `src/utils/model_endpoint_url.py`, which
intentionally _allows_ loopback/RFC1918 addresses for trusted LAN model servers (opposite polarity,
different threat model — do not conflate the two). Closing DNS-rebinding TOCTOU and redirect-based
SSRF requires Layer 2 (a connection-time-pinning transport); do not add DNS resolution to the
Layer-1 module to "fix" this — that reintroduces the exact validate-then-reconnect gap the whole
class of 2025-2026 CVEs exploited.

**HITL note.** If any future job needs to fetch a genuinely arbitrary user-supplied URL (not one of
the four known fetchers below), that is a Stage-3/isolation case per the source research, not a
Layer-1/Layer-2 case — flag for human review before wiring it into any fetch path.

## Denylist single source of truth

`src/utils/ssrf_fetch_policy.py` (Perpetua-Tools) is the SSOT for the Layer-1 denylist: loopback,
RFC1918, link-local (`169.254.0.0/16`, `fe80::/10`, `fd00:ec2::254`, ECS `169.254.170.2`), CGNAT
(`100.64.0.0/10`), multicast (`224.0.0.0/4`, `ff00::/8`), `0.0.0.0/8`, IPv4-mapped IPv6. Do not fork
this list into a second module or repo — extend the one file.

Fetchers that must route through Layer 2 once it lands (not raw `httpx`/`requests`):
`perplexity_client.py`, `gbrain_search.py`, `autoresearch_bridge.py`, `orama_mcp_client.py`. Fixed
vendor hosts (`api.perplexity.ai`, `api.x.ai`) stay on the Layer-1 hostname allowlist and skip
DNS/pinning — but skipping Layer 2 is only safe if the HTTP client used for these hosts
independently enforces TLS certificate validation, does not follow redirects without revalidating
each hop's target, and connects only to the IP it validated (not a re-resolved one). If the client
used for these calls doesn't guarantee that, route them through Layer 2 too rather than trusting the
vendor-host exemption alone.

## Operator runbook — Layer 3 (network / IMDS)

Owned by infra/platform, not application code. Nothing here is enforced by Python.

1. **IMDSv2 required, hop limit 1** on every AWS instance (`HttpTokens=required`,
   `HttpPutResponseHopLimit=1`). Hop limit 1 applies only when no container needs IMDS; a container
   adds its own network-namespace hop, consuming one hop of TTL independent of any proxy, so any
   host running a container that must read IMDS (e.g. EKS pods, AL2023's own default) needs hop
   limit 2 — treat 1 as the default and 2 as an explicit, reviewed exception, not the other way
   around.
2. **Block metadata IPs at egress**: `169.254.169.254` (IPv4) via
   `iptables -A OUTPUT -d 169.254.169.254 -j DROP`, `169.254.170.2` (ECS) the same way, and
   `fd00:ec2::254` (AWS IMDS IPv6) via the IPv6 equivalent
   (`ip6tables -A OUTPUT -d fd00:ec2::254 -j DROP`) if IPv6 IMDS is enabled — an IPv4-only rule
   leaves the IPv6 endpoint open. Apply at the route table / security group layer too, on any host
   that doesn't need IMDS.
3. **Prefer IRSA / Workload Identity** over instance-wide IMDS-issued credentials. IMDS-issued
   credentials are already temporary and auto-rotating, not long-lived — the benefit of
   IRSA/Workload Identity is narrower, workload-specific role scope instead of the whole instance
   sharing one role, not credential lifetime.
4. **Deny-by-default egress control** blocking RFC1918 + link-local + metadata ranges (IPv4 and
   IPv6) for any service reachable from outside the trust boundary. AWS security groups are
   allow-only and cannot layer a metadata-specific deny on top of a broader outbound allow — if a
   workload needs general egress, enforce the deny with a network ACL, AWS Network Firewall,
   host-level firewall, or K8s NetworkPolicy instead, and confirm each covers both IPv4 and IPv6
   metadata/link-local ranges.
5. **Optional, not required for first PRs**: Stripe Smokescreen (or equivalent CONNECT proxy) as a
   network-layer backstop that re-validates the resolved IP at connect time, narrowing the same
   rebinding window Layer 2 closes at the app level.

None of the above is achievable from `ssrf_fetch_policy.py` or any future pinning transport — an
app-layer control cannot enforce IMDSv2 token requirements or route-table rules. Treat this
checklist as the actual authoritative IMDS defense; Layer 1's link-local/metadata denial is backup
only.

## PR sequence (for reference)

- **PR-O1** (this doc) — orama, docs only. Done 2026-08-20.
- **PR-P1** (PT, Layer-1 module) — `src/utils/ssrf_fetch_policy.py` +
  `tests/test_ssrf_fetch_policy.py`. Done 2026-08-20.
- **PR-P2** (PT, pinning transport) — Layer 2. Not started;
  PT-T5-APPROVAL-002/LEDGER-003/SETTLE-004/API-005.
- **PR-P3** (PT, wire + fail closed) — wire the four fetchers through Layer 2 once it exists.
  Blocked on PR-P2; wiring them to Layer-1-only now would falsely imply rebinding/redirect
  protection they don't have yet.
- **PR-O2** (this doc's runbook section) — operator IMDS/egress checklist. Done 2026-08-20 (folded
  into this file rather than split, since both are orama-docs-only and small).

Out of scope: adopting Smokescreen in-process, disabling IPv6 globally, rewriting MCP.
