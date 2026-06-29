# P5 — Locked decisions (implementation branch)

> **Branch:** `cursor/security-pr3-swarm-approval-f559`  
> **Locked:** 2026-06-29 · Change via explicit amendment on this branch  
> **Source:** `/autoplan` GSTACK REVIEW REPORT

## Locked (v1)

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | HMAC secret = `ensure_control_plane_token()` | Stack plan; rotation invalidates in-flight previews (acceptable) |
| D2 | `expires_at` inside signed canonical JSON | Amendment A1 — no trusted unsigned expiry field |
| D3 | Canonical JSON: `sort_keys=True`, `separators=(',', ':')` | Stable `assignments_hash` contract |
| D4 | Launch flow: verify MAC → rebuild preview → hash compare → dispatch rebuilt assignments | Amendment A2 |
| D5 | Deprecate `approved: bool` — hard 422 if tokens absent | Closes P5 |
| D6 | Stateless tokens; 15m TTL; **accept** double-launch within TTL | No nonce store in v1 |
| D7 | Docs: "preview–launch integrity binding" not "true HITL" | Honest threat model |
| D8 | `sign_operator_payload` / `verify_operator_payload` in `control_plane_auth.py` | Reused by swarm, L1, PR4 discovery |
| D9 | `ORAMA_INSECURE_DEV=1` still requires tokens when signing | HITL not optional |
| D10 | Status codes: missing token → **422**; tamper/expiry → **403** | Acceptance criteria |

## Deferred (change later without breaking D1–D10)

- Single-use token consume / nonce store
- Audit log on launch (operator fingerprint, preview_id)
- PT `/v1/jobs` attestation
- CSRF / session cookie (PR5)
- `contextProfile` UI wiring

## Amendment process

Edit this file + execution plan `GSTACK REVIEW REPORT` amendments table; note in PR description.
