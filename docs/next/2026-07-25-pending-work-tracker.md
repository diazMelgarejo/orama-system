# Pending & Partially-Implemented Work — orama-system

> **SUPERSEDED 2026-07-27** by
> [`2026-07-27-phase-0-master-plan.md`](2026-07-27-phase-0-master-plan.md) → PT canonical
> [`PHASE-0-MASTER-PLAN-2026-07-27.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/phase-0-specifications/PHASE-0-MASTER-PLAN-2026-07-27.md).
> Kept for history; HEAD was `5b05f545` — mesh #224 merged at `41b77300`.

**Purpose:** a single place to find every unfinished or partially-landed
plan across recent sessions. Cross-linked with
[`Perpetua-Tools/docs/next/2026-07-25-pending-work-tracker.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/next/2026-07-25-pending-work-tracker.md)
— several items span both repos; check both.

**Full scan (integrity + docs backlog):**
[`2026-07-25-docs-scan-and-integrity-report.md`](2026-07-25-docs-scan-and-integrity-report.md)

**Last updated:** 2026-07-25, re-verified against `origin/main` at
`5b05f545`.

---

## 1. Unified identity audit consolidation — Phases 1–2 done on `main`

**Merged:** PR **#220** (`0cce8110` on `main`; branch
`2026-07-24-005b-identity-audit-plan` deleted)
**Plan doc:** [`docs/plans/2026-07-24-unified-identity-audit-integrated-plan.md`](../plans/2026-07-24-unified-identity-audit-integrated-plan.md)

- [x] **Phase 1 — Policy and engine.** `scripts/git/identity-policy.json`,
      `scripts/git/identity-policy.schema.json`, `scripts/git/audit_engine.py`.
      Tests in `tests/test_audit_engine.py`.
- [x] **Phase 2 — consumer wiring on orama `main`:** `repo_hygiene.py`
      `check_identity()`, `check_identity.sh`, `audit_attribution.sh` →
      `audit_engine`.
- [ ] **Phase 3 — not started:** cross-repo sync to Perpetua-Tools (dedicated
      PT PR only — see PT tracker item 2).
- [ ] **Phase 4 — not started:** remove the 3 old hardcoded identity lists once
      every consumer is green; retain compatibility comments.

---

## 2. Peer-mesh auth + TLS (BUZZ/Twitter/Google) — plan complete, mostly not started

**Canonical doc:** [`docs/v2/49-peer-mesh-auth-tls-v2-plan.md`](../v2/49-peer-mesh-auth-tls-v2-plan.md)

- [x] v1 minimum: bearer tokens never sent over unauthenticated HTTP
      (`query_peer_topology.py`, `lan_peer_assign.py`, `_is_authenticated_transport()`)
- [x] **AlphaClaw HTTPS — done on PT `main`.** PR **#276** merged (`f120239e`);
      Windows ACL PR **#278** merged (`e331aaf1`). Opt-in via
      `ALPHACLAW_TLS_ENABLED`. Details: PT tracker item 1.
- [ ] **Not started (orama peer-mesh surface):** `src/secure_transport.py`
- [ ] **Not started:** `src/peer_cert_manager.py` (peer-mesh certs — separate
      from PT AlphaClaw TLS proxy cert manager)
- [ ] **Not started:** `src/auth/` — `AuthProvider`, `AuthManager`, Bearer/BUZZ/
      Twitter/Google providers (Bearer remains permanent fallback)
- [ ] **Not started:** audit logging (`.orama/audit.log`, HMAC-chained)
- [ ] **Not started:** `orama auth status` CLI, upgrade-prompt UI

**For an agent picking this up:** implement against the plan doc "Decisions"
table — questions are pre-answered.

---

## 3. Fleet mesh / G7 — Phase 7 MVP still open

**Index:** [`docs/next/fleet-mesh/README.md`](fleet-mesh/README.md)

- [x] G7 pre-v2 backlog closure (rate-limit reuse, React Query invalidation)
- [ ] Portal Notification Hub MVP — [`G7-ASYNC-NOTIFICATIONS-ANALYSIS.md`](fleet-mesh/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md) +
      [`docs/superpowers/plans/2026-07-14-g7-authenticated-sse-mvp.md`](../superpowers/plans/2026-07-14-g7-authenticated-sse-mvp.md)
- [ ] Phases 8–10+ (recovery, topology learning, Byzantine/GossipMesh) — deferred
      per fleet-mesh README

---

## How to use this file

Before starting work, verify `main` HEAD and check for review comments newer
than this summary. Update checkboxes in the **same commit** as the completing
work. For v2 deferrals see
[`2026-07-25-docs-scan-and-integrity-report.md`](2026-07-25-docs-scan-and-integrity-report.md) §3.
