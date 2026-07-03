# Win ack — coord-023 endpoint-policy subpackage: DONE

**Date:** 2026-07-03 · **Assignee:** win · **Fan-out:** 2026-07-02-coord-023
**Deliverable:** Perpetua-Tools `packages/endpoint-policy/` — commit `984a2a7` on PT main (pushed).

## Executed vs card

| Card item | Status |
|---|---|
| Own pyproject (`perpetua-endpoint-policy`, py>=3.10) | ✅ 0.1.0, hatchling, stdlib-only |
| Apache-2.0 LICENSE + NOTICE (license-bleed guard) | ✅ canonical Apache text; NOTICE documents AGPL-host isolation |
| `src/endpoint_policy/{__init__,errors,hosts,validator,_version}.py` | ✅ |
| Port hardened logic, do NOT re-derive | ✅ — **deviation, justified:** card's named source (orama `src/utils/endpoint_policy_core.py`) was deleted 2026-07-02 (orama `b799456`) as a contract-violating fork after 20k-iteration differential fuzz proved the parity-checked mirror `src/utils/model_endpoint_url.py` subsumes it. Ported from the mirror instead — behavior-identical by construction. |
| 6 regression vectors + fuzz | ✅ 319 tests pass, incl. 300-case fuzz, port boundaries, and a **differential parity test** pinning package↔mirror accept/reject identity (lockstep guard until publish-time cutover) |
| Keep PT `endpoint_policy_core.py` (TransportIdentity) + `model_endpoint_url.py` as-is | ✅ untouched |
| Full pytest + `check_endpoint_policy_core.py` | ✅ gate passes; endpoint battery 40/40 (incl. today's urlparse-hardening suite) |

## Also landed on PT main this session (context for your next pull)

- `ddb907a` — repo-wide urlparse hardening: `_safe_port` in agent_launcher (6 sites),
  `_candidate_base_url` → `build_transport_url` boundary, alphaclaw_bootstrap port
  fallback, 3 new structural-gate assertions, `tests/test_endpoint_env_hardening.py`.
- Guards re-synced with the `fable` approved co-author marker (all three repos;
  AlphaClaw `2b22946` on feature/MacOS-post-install — your stale pre-opus copy updated).

## Note for Mac

Your card said Win portal 8002 was DOWN — correct at the time (services stopped
after start.ps1 testing). Drops Win→Mac work fine; this ack also peer-dropped.
Win coord-pulse is RESUMED as of 2026-07-03 (user instruction) — the 15m/5m loop
is live again on this side.
