<!-- markdownlint-disable MD013 -->
# SSRF Defense in Depth (three layers, one job each)

> Companion to
> [`53-maestro-swarm-v2-redesign-critique.md`](../53-maestro-swarm-v2-redesign-critique.md). Pointer
> from
> [`../../plans/2026-07-02-endpoint-policy-standardization-execution.md`](../../plans/2026-07-02-endpoint-policy-standardization-execution.md).
> Source: `Defense-in-Depth SSRF Prevention in 2025-2026_ Limits of Application-Layer Python Validators.md` (restricted/for-Perplexity research, not
> tracked in this repo, covering CVE-2025-8267 multicast, CVE-2026-27826 TOCTOU, CVE-2026-27795 redirect, IMDSv2 hop limit 1 vs 2 for containers, and forward vs output iptables chain rules). **Unverified guidance** — this source has not gone through this repo's
> verifier/approval gate; the conclusions below are treated as informative reference, not as an
> approved-provenance requirement, until that source is either tracked and verified or its claims
> are independently re-derived from primary references (OWASP SSRF Cheat Sheet, AWS IMDSv2 docs,
> etc., already cited inline where used).

## The three layers

| Layer | What it stops | What it cannot stop | Owner | Status |
| --- | --- | --- | --- | --- |
| 1 Pre-flight | Bad schemes, userinfo, control chars, octal/hex/dword, IPv4-mapped IPv6, RFC1918, loopback, link-local, CGNAT, multicast, reserved | Rebinding, redirects | PT `src/utils/ssrf_fetch_policy.py` | **Shipped** — 22 tests (unit + hypothesis property), 2026-08-20 |
| 2 Pinning transport | Rebinding (resolve → validate **all** A/AAAA → connect to that IP, SNI = hostname); each redirect hop re-validated; split-identity pool partitioning (`host_params["host"] = pinned_ip`) | A process that bypasses the HTTP client | New PT adapter, every user-URL fetch | **Shipped (2026-08-22)** — `src/utils/ssrf_pinned_adapter.py` and `tests/test_ssrf_pinned_adapter.py` (commits `351bad1e`, `5a6a4ae7`, PT PR #359); all listed fetchers wired, split-identity concurrency & reuse verified |
| 3 Network / IMDS | Anything that still dials metadata | Nothing in-app | Operator runbook (below), not Python | **This doc** |

**Validator cannot pin.** Layer 1 (PT `src/utils/ssrf_fetch_policy.py`) is a pure string/IP-literal
check with no network I/O — non-allowlisted hostnames are denied outright, not resolved and then
checked. This is a separate module and test path from `src/utils/model_endpoint_url.py`, which
intentionally _allows_ loopback/RFC1918 addresses for trusted LAN model servers (opposite polarity,
different threat model — do not conflate the two). Closing DNS-rebinding TOCTOU and redirect-based
SSRF requires Layer 2 (a connection-time-pinning transport); do not add DNS resolution to the
Layer-1 module to "fix" this — that reintroduces the exact validate-then-reconnect gap the whole
class of 2025-2026 CVEs exploited.

Opposite-polarity (LAN-trusting) callers still need redirect hardening even though they don't
route through the deny-by-default Layer 2 transport: `connectivity.py`'s `_probe_local` and
`orchestrator/autoresearch_bridge.py`'s `probe_lm_studio_http()` both validate the target via
`model_endpoint_url.py` before fetching, but validating the _initial_ URL doesn't protect against
a redirect from that already-validated target (see "Outbound HTTP transport hardening" in
[`32-agentic-security-controls.md`](../32-agentic-security-controls.md) for the general pattern).
`_probe_local` accepted this as a documented, low-risk tradeoff (fixed, code-reviewed local
endpoints); `probe_lm_studio_http()` was hardened on 2026-08-22 to refuse redirects outright via a
custom `urllib.request.HTTPRedirectHandler` (a health-check probe has no legitimate reason to
follow one), since `urllib.request`'s default opener auto-follows redirects with zero
revalidation.

**HITL note.** If any future job needs to fetch a genuinely arbitrary user-supplied URL (not one of
the outbound fetchers below), that is a Stage-3/isolation case per the source research, not a
Layer-1/Layer-2 case — flag for human review before wiring it into any fetch path.

**Open gap — `scripts/discover.py` mesh probes.** `discover_endpoints()` calls `probe_models()`
against `$MAC_IP`, `$WIN_PEER_IPS`, cached last-known-good addresses, and fresh subnet-scan
results, using `validate_model_endpoint_url()` (the RFC1918-permitting, LAN-trusting validator
noted above — correct for its intended purpose, discovering LM Studio on the local network).
`filter_endpoints_for_trust()` (`mesh/discovery_trust.py`) only runs afterward, on the already-
probed results — so an untrusted or spoofed peer on the subnet still receives a real HTTP request
before mesh trust/ACK verification happens, and `validate_model_endpoint_url()` provides no
connection-time pinning against DNS-rebinding on whatever it does accept. This should route
through the Stage-3 PT adapter or an equivalent pinned transport ahead of `filter_endpoints_for_trust()`
rather than relying on `validate_model_endpoint_url()` alone — **not implemented in this pass**,
tracked as follow-up work; understanding `discovery_trust.py`'s ack/trust semantics fully before
changing the probe flow is a separate design task, not a same-PR doc-text fix.

## Denylist single source of truth

`src/utils/ssrf_fetch_policy.py` (Perpetua-Tools) is the SSOT for the Layer-1 denylist: loopback,
IPv4 private ranges (RFC1918, `10.0.0.0/8`/`172.16.0.0/12`/`192.168.0.0/16`), IPv4 link-local
(`169.254.0.0/16`), IPv6 link-local (`fe80::/10`, RFC4291), IPv6 unique local addresses
(`fc00::/7`, RFC4193 — `fd00:ec2::254`, the AWS IMDS IPv6 address, lives in this ULA space, not
IPv6 link-local), ECS metadata (`169.254.170.2`), CGNAT (`100.64.0.0/10`), multicast
(`224.0.0.0/4`, `ff00::/8`), `0.0.0.0/8`, IPv4-mapped IPv6. Do not fork this list into a second
module or repo — extend the one file.

Fetchers that must route through Layer 2 (not raw `httpx`/`requests`):
`connectivity.py`, `orama_bridge.py`, `perplexity_client.py`. **The Layer-1 vendor-host allowlist
exemption (below) does not override this list.** It is a Layer-1-only exemption — `api.perplexity.ai`
and `api.x.ai` skip Layer 1's pre-flight hostname denial because they're fixed, hardcoded,
code-reviewed hosts, not because their calls are exempt from Layer 2 pinning. A fetcher in the list
above must route through Layer 2 even when it happens to call one of these allowlisted vendor hosts;
the allowlist only ever waives Layer 1, never Layer 2, for a listed fetcher.

The vendor-host exemption only ever applies to a caller that is **not** one of the fetchers listed
above (e.g. a future one-off fixed-host caller outside this list) — and even then, skipping Layer 2 is
only safe if that caller's own HTTP client independently enforces TLS certificate validation, does not
follow redirects without revalidating each hop's target, and connects only to the IP it validated (not
a re-resolved one). If the client used for such a call doesn't guarantee that, route it through Layer 2
too rather than trusting the vendor-host exemption alone.

**Resolved (2026-08-22):** `perplexity_client.py` is hardened, but via a different mechanism than
`connectivity.py`/`orama_bridge.py` — it's on the `openai` SDK, which is built on `httpx`, not
`requests`/`urllib3`, so `ssrf_pinned_adapter`'s connect-time IP pinning (which subclasses urllib3's
connection/pool classes) cannot be reused directly. `src/utils/ssrf_pinned_adapter.py` now also
exposes `build_pinned_httpx_client()`, passed as `http_client=` to both `OpenAI()` and
`AsyncOpenAI()`: it forces `follow_redirects=False` (the `openai` SDK's own default httpx client
construction sets `follow_redirects=True` — confirmed directly, **not** `httpx.Client`'s own `False`
default, and a real gap on its own) and adds a "request" event hook that validates every resolved
A/AAAA for the request's host via `address_checker` immediately before httpx's connection attempt.
This is **not** true IP pinning (that needs a custom `httpcore` network backend — out of scope,
tracked as a follow-up if httpx-based clients proliferate) but it does satisfy the vendor-host
exemption's three conditions above for this fixed, hardcoded host: TLS verification stays on
(httpx's own default), redirects are never auto-followed, and the pre-flight hook closes the
"this fixed hostname now resolves somewhere it shouldn't" TOCTOU gap the exemption's third
condition is really about. `orchestrator/autoresearch_bridge.py`'s `probe_lm_studio_http()` had
the same class of gap on a third transport (`urllib.request`'s default opener auto-follows
redirects) — fixed by refusing redirects outright via a custom `HTTPRedirectHandler` (a
fixed-purpose health-check probe has no legitimate reason to follow one). `connectivity.py` and
`orama_bridge.py` remain the only two with true connect-time pinning (PT PR #359 remediation,
`_probe`/`_probe_local` split; `ssrf_request` via `asyncio.to_thread`). `gbrain_search.py` and
`orama_mcp_client.py` were checked and found **not applicable** — both are pure local-subprocess
callers (CLI binary / stdio JSON-RPC), neither makes an outbound HTTP request at all.

## Operator runbook — Layer 3 (network / IMDS)

Owned by infra/platform, not application code. Nothing here is enforced by Python.

1. **IMDSv2 required, hop limit 1 as the isolation baseline** on every AWS instance
   (`HttpTokens=required`, `HttpPutResponseHopLimit=1`). Hop limit 1 is correct when no container
   on the host needs IMDS; a container adds its own network-namespace hop, consuming one hop of TTL
   independent of any proxy, so a container that genuinely needs IMDS reads needs hop limit 2 — but
   this is deployment-specific, not a blanket container rule. **EKS Auto Mode enforces hop limit 1**
   and requires a pod to set `hostNetwork: true` to reach IMDS at all (it shares the host's network
   namespace, so it never takes the extra hop). Standalone hosts (self-managed EKS nodes, plain
   EC2 running containers) default according to the AMI's `ImdsSupport` setting — AL2023's default
   can be 2 — and are not overridden by any Auto-Mode enforcement. Treat hop limit 1 as the default
   for every deployment, and hop limit 2 as an explicit, reviewed exception scoped to the specific
   non-host-network workload that needs it — never a host-wide default "because containers."
2. **Block metadata IPs at egress, precedence-safe**: `-A` (append) is not enough by itself — it
   adds the DROP rule after whatever is already in the chain, so a pre-existing broad `ACCEPT` rule
   earlier in the chain still matches first and the metadata traffic never reaches the DROP.
   Manage these rules in a dedicated chain jumped to early (or use `-I` to insert at the top of
   `OUTPUT`/`FORWARD`), and persist the rule set across reboots with the distro's standard
   mechanism (`iptables-persistent`, `netfilter-persistent`, or the cloud image's boot-time rule
   loader) rather than a one-shot `-A` that vanishes on restart. Block `169.254.169.254` (IPv4),
   `169.254.170.2` (ECS), and `fd00:ec2::254` (AWS IMDS IPv6, in ULA space) — an IPv4-only rule set
   leaves the IPv6 endpoint open. On a host running containers, a **hostNetwork pod's** traffic to
   the metadata IP uses the host's `OUTPUT` chain (it shares the host's network namespace, per
   point 1's EKS Auto Mode note), while **ordinary pod traffic** traverses the host's `FORWARD`
   chain and the pod network namespace — cover both, either with matching precedence-safe `OUTPUT`
   and `FORWARD` rules or the CNI's own network-policy mechanism (Calico `GlobalNetworkPolicy`,
   Cilium `CiliumNetworkPolicy`, etc.), and validate both paths are actually blocked, not just one.
   Do not rely on route tables or security groups for this block; see point 4 for why.
3. **Prefer IRSA / Workload Identity** over instance-wide IMDS-issued credentials. IMDS-issued
   credentials are already temporary and auto-rotating, not long-lived — the benefit of
   IRSA/Workload Identity is narrower, workload-specific role scope instead of the whole instance
   sharing one role, not credential lifetime.
4. **Deny-by-default egress control** blocking IPv4 RFC1918 private ranges, IPv4 link-local
   (`169.254.0.0/16`), IPv6 link-local (`fe80::/10`), IPv6 ULA (`fc00::/7` — where AWS's IPv6 IMDS
   address lives), and metadata ranges, for any service reachable from outside the trust boundary.
   AWS security groups are
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

## PR sequence & commit SHA evidence

- **PR-O1 / PR-O2** (this doc & operator runbook) — `docs/v2/plans/2026-08-20-ssrf-defense-in-depth.md` (orama-system). **Shipped** — initial commit `1b463d1f`, updated to shipped status via commit [`c841ed31`](https://github.com/diazMelgarejo/orama-system/commit/c841ed31718d35a2e592abec07de06ec5b00ae55) (`c841ed31718d35a2e592abec07de06ec5b00ae55`).
- **PR-P1** (PT, Layer-1 module) — `src/utils/ssrf_fetch_policy.py` + `tests/test_ssrf_fetch_policy.py`. **Shipped (2026-08-20)** — 22 tests (unit + hypothesis property) via commit [`5152288e`](https://github.com/diazMelgarejo/Perpetua-Tools/commit/5152288ea56f9168b9f69b1fa0bc9b37c02b29eb) (`5152288ea56f9168b9f69b1fa0bc9b37c02b29eb`).
- **PR-P2** (PT, pinning transport) — Layer 2. **Shipped (2026-08-22)** — Split-identity `SSRFPinnedHTTPAdapter` (`src/utils/ssrf_pinned_adapter.py`):
  - Implementation: commit [`351bad1e`](https://github.com/diazMelgarejo/Perpetua-Tools/commit/351bad1e5a5a1f6a1523450917e754bb762149b1) (`351bad1e5a5a1f6a1523450917e754bb762149b1`).
  - 6-test regression matrix: commit [`5a6a4ae7`](https://github.com/diazMelgarejo/Perpetua-Tools/commit/5a6a4ae7bfba463e26bb17f8a7e09641973cf873) (`5a6a4ae7bfba463e26bb17f8a7e09641973cf873`).
  - Eliminates shared `connection_pool_kw` mutation race via `build_connection_pool_key_attributes()` and partitions connection pools on the pinned IP literal (`host_params["host"] = pinned_ip`) while preserving TLS SNI/Host headers on the domain. Verified with 6-test matrix in `tests/test_ssrf_pinned_adapter.py` (concurrent two-pin, sequential A-to-B reuse, zero adapter-state mutation, HTTPS pin+SNI, target-based redirect denial, and multi-threaded shared session).
- **PR-P3** (PT, wire + fail closed) — wire outbound fetchers (`connectivity.py`, `orama_bridge.py`, `perplexity_client.py`) through Layer 2. **Shipped (2026-08-22)** — commit [`24bc3490`](https://github.com/diazMelgarejo/Perpetua-Tools/commit/24bc34903efd700b0ac6738de42ef9246f499035) (`24bc34903efd700b0ac6738de42ef9246f499035`). `connectivity.py` and `orama_bridge.py` have true connect-time pinning (PT PR #359); `perplexity_client.py` is hardened via `build_pinned_httpx_client()` (redirect-disabled + pre-flight address validation, not true pinning — httpx's transport layer doesn't support connect-time IP pinning the way `ssrf_pinned_adapter` does for `requests`/`urllib3`; documented as a deliberate scope boundary above, not an oversight). `autoresearch_bridge.py`'s LM Studio probe (a `model_endpoint_url`-validated LAN target, opposite polarity — not a Layer 2 candidate) was separately hardened to refuse redirects. `gbrain_search.py` and `orama_mcp_client.py` checked and found not applicable (pure local-subprocess callers, no outbound HTTP). All changes have passing tests with a RED-GREEN verification pass, not just a self-reported claim.

Out of scope: adopting Smokescreen in-process, disabling IPv6 globally, rewriting MCP.
