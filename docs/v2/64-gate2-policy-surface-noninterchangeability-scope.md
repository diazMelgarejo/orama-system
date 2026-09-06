# Gate 2: Policy-Surface Non-Interchangeability — Scope and Candidate Finding

**Status:** v2 evidence + dispatch brief, 2026-09-07
**Authority:** [ADR 62](62-telos-phylax-authority-gate0-adr.md), [Doc 63](63-gate1-endpoint-observation-and-conformance-evidence.md)
**Regime boundary:** read-only v1 (PT) analysis only. No PT file changes authorized
by this document. Any fix lands in v2 or as a PT PR reviewed separately by the
human operator — this scopes and evidences the problem, it does not implement.

## Gate 2 requirement (from the gap-closure plan)

Document and enforce three call-site choices — model endpoint validation,
transport identity, SSRF fetch — as non-interchangeable, and add test cases
proving a hostname that merely *looks* harmless still gets rejected by the
SSRF layer if it resolves to a prohibited address. Exit evidence: a call-site
inventory assigns every network use to one policy surface; mixed or
bypassing callers fail tests/review.

## Extended importer inventory (beyond Doc 63's per-module list)

Doc 63 listed representative consumers per module. This document adds the
cross-tabulation Gate 2 actually needs: which call sites import **more than
one** policy-surface module, and whether that composition is a correct
layered design or an actual gap.

| File | Surfaces imported | Verdict |
| --- | --- | --- |
| `orchestrator/connectivity.py` | `model_endpoint_url` + `ssrf_pinned_adapter` | Correct layering — inline comment states intent explicitly ("never weakens ssrf_request's own policy"); model-endpoint check first, then the actual fetch goes through `ssrf_request`. |
| `orchestrator/orama_bridge.py` | `model_endpoint_url` + `ssrf_pinned_adapter` | Correct layering — same pattern, `validate_model_endpoint_url(url, allow_public=False)` then `ssrf_request` for the real network call. |
| `src/perpetua_tools/agent_launcher.py` | `endpoint_policy_core` (transport) + `model_endpoint_url` (validation) | **Candidate gap — see below.** The actual network call bypasses `ssrf_pinned_adapter` entirely. |
| `orchestrator/fastapi_app.py` | `endpoint_policy_core` + `model_endpoint_url` | Needs the same check as `agent_launcher.py` — not yet traced to its actual call site in this pass. |

## Candidate finding: `agent_launcher.py`'s model-server override path has no DNS-resolution check

Traced concretely, not assumed:

1. `src/utils/model_endpoint_url.py::_host_allowed()` — for any hostname that
   is not a literal IP address and not `localhost`/`.localhost`/`127.*`, the
   function does **not** resolve DNS. It falls straight to
   `except ValueError: return allow_public` — i.e. once
   `ALLOW_PUBLIC_MODEL_ENDPOINTS=1` is set (a real, documented operational
   mode for remote/LAN model servers, not a misconfiguration), **any**
   hostname is accepted with zero address-class checking.
2. `src/perpetua_tools/agent_launcher.py` uses exactly this function
   (`validate_model_endpoint_url`) to validate a model-server override URL
   (lines ~353, ~367), then makes the actual request via a raw
   `httpx.AsyncClient()` (lines ~542, ~571, ~611, ~620) — **never** through
   `utils.ssrf_pinned_adapter.ssrf_request()`, which is the only module in
   this codebase that actually resolves DNS and rejects prohibited address
   classes (`ssrf_fetch_policy.py`'s job).
3. Net effect: with `ALLOW_PUBLIC_MODEL_ENDPOINTS=1` set, a model-server
   override hostname that resolves to `169.254.169.254` (cloud metadata) or
   any other prohibited address is accepted by `validate_model_endpoint_url`
   and then fetched by raw `httpx`, with no DNS-resolution check anywhere in
   that path. This is precisely the scenario Gate 2's own text names:
   *"a hostname resolving to a prohibited address must be rejected by the
   SSRF layer even if its text appears harmless."*

**This is a candidate, not a confirmed exploit** — it needs two things this
document does not do: (a) confirming `ALLOW_PUBLIC_MODEL_ENDPOINTS=1` is a
realistic, reachable operational configuration (not dead/test-only code),
and (b) tracing whether any other layer downstream (network policy, firewall,
container egress rules) already closes this gap out-of-band. Both are Gate 2
dispatch work, not resolved here.

## Dispatch scope for the next agent

1. Confirm or refute the `agent_launcher.py` candidate finding above with
   actual reachability tracing (who sets `ALLOW_PUBLIC_MODEL_ENDPOINTS`, in
   what deployment, and does anything else intercept the `httpx` call).
2. Complete the same mixed-surface trace for `orchestrator/fastapi_app.py`
   (flagged above as not yet traced).
3. Write the call-site inventory conclusion as **read-only v2 evidence**
   (this repo, `docs/v2/`), the same pattern as Doc 63 — no PT file edits.
4. If the finding is confirmed, do **not** fix it directly in PT. Write up
   the concrete fix (route `agent_launcher.py`'s actual request through
   `ssrf_pinned_adapter.ssrf_request()` instead of raw `httpx`) as a proposed
   PT PR description in this repo's docs, for the human operator to review
   and decide whether to land in PT on PT's own timeline — this is exactly
   the "v1 gets zero implementation changes from v2 work" boundary from
   ADR 62's Regime boundary section, applied to a security finding, not just
   an architecture one.
5. Add the "hostname resolves to prohibited address, text looks harmless"
   test case Gate 2 requires — as a v2-side test against `ssrf_pinned_adapter`
   behavior (already exists?) or a written PT-PR proposal test if it's the
   confirmed gap above, never a same-repo edit to PT test files directly.

## Explicitly out of scope for Gate 2

- Any actual PT code change (regime boundary).
- Gate 4's Telos wiring into the Gateway Lifecycle.
- Layer 2 pinned-transport redirect/DNS-rebinding vectors already deferred
  to the future transport authority in Doc 63.
