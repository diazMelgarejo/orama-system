# Win assignment — endpoint-policy shared subpackage (coord-023)

**Date:** 2026-07-02
**Fan-out:** `2026-07-02-coord-023`
**Assignee:** win (coder / Hermes or ClinePass)
**Topic:** security/endpoint-policy
**Transport:** git commits (Win orama portal 8002 DOWN; peer-file drops unavailable)

## Division of labor (Win 27B co-orchestrator: VERDICT ACCEPT, no blockers)

| Node | Owns | Status |
|------|------|--------|
| Mac | orama-system `main` | CI contract checker restored (`dea6b20`, run 28563937736 GREEN); validator verified hardened (ipv4-mapped unwrap + wrapped `urlparse().port`, 1019 tests pass); distill-fable-5 pilot docs |
| Win | Perpetua-Tools `main` | THIS CARD — author `packages/endpoint-policy/` |

## Win executes

1. Create `packages/endpoint-policy/` in Perpetua-Tools: own `pyproject.toml`
   (name `perpetua-endpoint-policy`, py>=3.10), own Apache-2.0 `LICENSE` + `NOTICE`
   (host repo is AGPL — license bleed guard), `src/endpoint_policy/{__init__,errors,hosts,validator,_version}.py`.
2. Port the hardened logic from orama-system `src/utils/endpoint_policy_core.py`
   (it already satisfies the invariant: single `ModelEndpointPolicyError`, wrapped
   `parsed.port`, `ipv4_mapped` unwrap, link-local block) — do NOT re-derive.
3. Regression suite: all 6 vectors — localhost:port, `notaport`, `99999`,
   `169.254.169.254`, `[::ffff:169.254.169.254]`, skip-invalid list — plus
   hypothesis fuzz (mirror orama `tests/test_endpoint_policy_fuzz.py`).
4. Keep `src/utils/endpoint_policy_core.py` (transport identity) and
   `src/utils/model_endpoint_url.py` as-is; they are DIFFERENT modules
   (filename collision — see lesson in orama `docs/distill-fable-5/2026-07-02-pilot/LESSONS.md`).
5. Run PT full pytest + `scripts/security/check_endpoint_policy_core.py`; commit to PT main.

## Ack filename

`win-coord-023-ack.md` (git commit or peer drop once portal 8002 is back)
