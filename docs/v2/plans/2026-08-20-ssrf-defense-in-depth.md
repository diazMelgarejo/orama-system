# SSRF Defense in Depth (three layers, one job each)

> Companion to [`53-maestro-swarm-v2-redesign-critique.md`](../53-maestro-swarm-v2-redesign-critique.md).
> Pointer from [`../../plans/2026-07-02-endpoint-policy-standardization-execution.md`](../../plans/2026-07-02-endpoint-policy-standardization-execution.md).
> Source: Defense-in-Depth SSRF Prevention in 2025-2026 (restricted/for-Perplexity research, not tracked in this repo).

## The three layers

| Layer | What it stops | What it cannot stop | Owner | Status |
|---|---|---|---|---|
| 1 Pre-flight | Bad schemes, userinfo, control chars, octal/hex/dword, IPv4-mapped IPv6, RFC1918, loopback, link-local, CGNAT, multicast, reserved | Rebinding, redirects | PT `src/utils/ssrf_fetch_policy.py` | **Shipped** — 22 tests (unit + hypothesis property), 2026-08-20 |
| 2 Pinning transport | Rebinding (resolve → validate **all** A/AAAA → connect to that IP, SNI = hostname); each redirect hop re-validated | A process that bypasses the HTTP client | New PT adapter, every user-URL fetch | **Not started** — assigned to codex-execution-bridge / agnes-antigravity-claude via PT-T5-APPROVAL-002 / PT-T5-LEDGER-003 / PT-T5-SETTLE-004 / PT-T5-API-005 |
| 3 Network / IMDS | Anything that still dials metadata | Nothing in-app | Operator runbook (below), not Python | **This doc** |

**Validator cannot pin.** Layer 1 (`ssrf_fetch_policy.py`) is a pure string/IP-literal check with no network I/O. It fails closed on any hostname it can't resolve itself — bare hostnames outside the vendor allowlist are denied, not silently passed through. Closing DNS-rebinding TOCTOU and redirect-based SSRF requires Layer 2 (a connection-time-pinning transport); do not add DNS resolution to the Layer-1 module to "fix" this — that reintroduces the exact validate-then-reconnect gap the whole class of 2025-2026 CVEs exploited.

**HITL note.** If any future job needs to fetch a genuinely arbitrary user-supplied URL (not one of the four known fetchers below), that is a Stage-3/isolation case per the source research, not a Layer-1/Layer-2 case — flag for human review before wiring it into any fetch path.

## Denylist single source of truth

`src/utils/ssrf_fetch_policy.py` (Perpetua-Tools) is the SSOT for the Layer-1 denylist:
loopback, RFC1918, link-local (`169.254.0.0/16`, `fe80::/10`, `fd00:ec2::254`, ECS `169.254.170.2`), CGNAT (`100.64.0.0/10`), multicast (`224.0.0.0/4`, `ff00::/8`), `0.0.0.0/8`, IPv4-mapped IPv6. Do not fork this list into a second module or repo — extend the one file.

Fetchers that must route through Layer 2 once it lands (not raw `httpx`/`requests`): `perplexity_client.py`, `gbrain_search.py`, `autoresearch_bridge.py`, `orama_mcp_client.py`. Fixed vendor hosts (`api.perplexity.ai`, `api.x.ai`) stay on the Layer-1 hostname allowlist and skip DNS/pinning entirely.

## Operator runbook — Layer 3 (network / IMDS)

Owned by infra/platform, not application code. Nothing here is enforced by Python.

1. **IMDSv2 required, hop limit 1** on every AWS instance (`HttpTokens=required`, `HttpPutResponseHopLimit=1`; hop limit 2 only for a container that must read IMDS through a proxy layer, e.g. EKS/AL2023 pod access).
2. **Block metadata IPs at egress**: `169.254.169.254`, `169.254.170.2` (ECS), `fd00:ec2::254` (AWS IMDS IPv6) — route table / security group / `iptables -A OUTPUT -d 169.254.169.254 -j DROP` on any host that doesn't need IMDS.
3. **Prefer IRSA / Workload Identity** over long-lived IMDS-issued credentials, so a stolen metadata response is low-value.
4. **Deny-by-default egress firewall** (security groups / K8s NetworkPolicies) blocking RFC1918 + link-local + metadata ranges cluster-wide, for any service reachable from outside the trust boundary.
5. **Optional, not required for first PRs**: Stripe Smokescreen (or equivalent CONNECT proxy) as a network-layer backstop that re-validates the resolved IP at connect time, narrowing the same rebinding window Layer 2 closes at the app level.

None of the above is achievable from `ssrf_fetch_policy.py` or any future pinning transport — an app-layer control cannot enforce IMDSv2 token requirements or route-table rules. Treat this checklist as the actual authoritative IMDS defense; Layer 1's link-local/metadata denial is backup only.

## PR sequence (for reference)

- **PR-O1** (this doc) — orama, docs only. Done 2026-08-20.
- **PR-P1** (PT, Layer-1 module) — `src/utils/ssrf_fetch_policy.py` + `tests/test_ssrf_fetch_policy.py`. Done 2026-08-20.
- **PR-P2** (PT, pinning transport) — Layer 2. Not started; PT-T5-APPROVAL-002/LEDGER-003/SETTLE-004/API-005.
- **PR-P3** (PT, wire + fail closed) — wire the four fetchers through Layer 2 once it exists. Blocked on PR-P2; wiring them to Layer-1-only now would falsely imply rebinding/redirect protection they don't have yet.
- **PR-O2** (this doc's runbook section) — operator IMDS/egress checklist. Done 2026-08-20 (folded into this file rather than split, since both are orama-docs-only and small).

Out of scope: adopting Smokescreen in-process, disabling IPv6 globally, rewriting MCP.
