# Pending & Partially-Implemented Work — orama-system

**Purpose:** a single place to find every unfinished or partially-landed
plan across recent sessions. Cross-linked with
[`Perpetua-Tools/docs/next/2026-07-25-pending-work-tracker.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/next/2026-07-25-pending-work-tracker.md)
— several items span both repos; check both.

**Last updated:** 2026-07-25, from the branch each item's code actually
lives on.

---

## 1. Unified identity audit consolidation — Phase 1 of 4

**Branch:** `2026-07-19-002-fleet-mesh-oob-fixes` (PR #197)
**Plan doc:** [`docs/plans/2026-07-24-unified-identity-audit-integrated-plan.md`](../plans/2026-07-24-unified-identity-audit-integrated-plan.md)

- [x] **Phase 1 — Policy and engine.** `scripts/git/identity-policy.json`,
      `scripts/git/identity-policy.schema.json`, `scripts/git/audit_engine.py`.
      17/17 tests in `tests/test_audit_engine.py`. Fail-closed on missing/
      malformed/wrong-version policy. No vendor-domain wildcard, no
      universal bot wildcard, private identities excluded from the tracked
      file (existing `private_literal_values()` mechanism preserved via
      dependency injection).
- [ ] **Not started — Phase 2, one consumer at a time** (plan section 10):
  1. Switch `scripts/review/repo_hygiene.py`'s `check_identity()` to call
     `audit_engine.is_approved_identity()` instead of its own hardcoded
     `APPROVED_IDENTITIES` set + duplicated case-normalization logic
     (currently marked with a `# LEGACY` comment pointing at this plan).
  2. Switch `scripts/git/check_identity.sh` to shell out to (or otherwise
     consume) the engine.
  3. Switch `scripts/git/audit_attribution.sh` to the engine, preserving
     every existing contract listed in plan section 2.2 (banned-attribution
     scanning, co-author policy, `GIT_AUDIT_RANGE`/`GIT_AUDIT_STRICT`, exit
     codes) — golden-output tests first (plan Phase 0), each consumer
     migrated and its own suite re-run green before the next.
- [ ] **Not started — Phase 3:** cross-repo sync to Perpetua-Tools (a
      dedicated PT PR, explicitly NOT bundled into PT PR #276 — see PT's
      own tracker, item 2).
- [ ] **Not started — Phase 4:** remove the 3 old hardcoded identity lists
      once every consumer is green; retain compatibility comments.
- **Acceptance criteria:** full checklist in the plan doc's own §11 — none
  yet checked off beyond the Phase 1 subset above.

---

## 2. Peer-mesh auth + TLS (BUZZ/Twitter/Google) — plan complete, implementation not started

**Branch:** `security/02-peer-mesh-auth-tls-v2-plan` (stacked on PR #197)
**Canonical doc:** [`docs/v2/49-peer-mesh-auth-tls-v2-plan.md`](../v2/49-peer-mesh-auth-tls-v2-plan.md)
(ingests 3 design docs; updated 2026-07-25 to reflect actual code, not
just the original sketch)

- [x] v1 minimum: bearer tokens never sent over unauthenticated HTTP
      (`query_peer_topology.py`, `lan_peer_assign.py`, both via
      `_is_authenticated_transport()`)
- [x] **AlphaClaw HTTPS gap — done, but on the PT side.** See
      Perpetua-Tools' tracker item 1 for the actual implementation
      (`orchestrator/alphaclaw_tls_proxy.py` + `alphaclaw_manager.py`
      wiring). This repo makes zero gateway decisions by design; nothing
      to implement here for that part.
- [ ] **Not started:** `src/secure_transport.py` (peer-mesh TLS enforcement,
      separate from AlphaClaw's — this is for `query_peer_topology.py`/
      `probe_lan_peer.py`'s peer-to-peer connections specifically)
- [ ] **Not started:** `src/peer_cert_manager.py` (peer-mesh cert
      provisioning — a different surface from AlphaClaw's cert manager,
      which already exists on the PT side)
- [ ] **Not started:** `src/auth/` — the full `AuthProvider` protocol,
      `AuthManager`, and all 4 provider implementations (Bearer/BUZZ/
      Twitter/Google). Bearer Token must remain the permanent, never-
      forced-to-migrate fallback per the plan's own explicit requirement.
- [ ] **Not started:** audit logging (`.orama/audit.log`, HMAC-chained)
- [ ] **Not started:** `orama auth status` CLI, the upgrade-prompt UI
- **For an agent picking this up:** the plan doc's own "Decisions" table
  has pre-answered all 13 open questions — implement against that table,
  don't re-litigate the questions.

---

## How to use this file

Before starting work referenced here, verify the branch tip matches what's
listed above and check for review comments newer than what's summarized.
Update this file's checkboxes in the same commit as the work that
completes them, on the same branch — never a separate tracking-only
commit elsewhere (see `SECURITY.md` § "Lessons and action must land on
the same branch").
