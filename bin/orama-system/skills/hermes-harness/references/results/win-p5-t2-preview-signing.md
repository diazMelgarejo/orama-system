# Win result — P5 T2 swarm preview signing

**Branch:** `cursor/security-pr3-swarm-approval-f559`  
**Date:** 2026-06-29

## Shipped

- `_swarm_assignments_hash` + `_sign_swarm_preview` in `portal_server.py`
- `POST /api/swarm/preview` returns `preview_id`, `approval_token`, `expires_at`
- HMAC via `sign_operator_payload` with assignments_hash in canonical payload
- Tests: 7/7 `test_swarm_preview.py` (incl. round-trip verify)

## Next

T3 — launch requires tokens; deprecate `approved: true`
