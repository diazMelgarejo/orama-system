# P5 — Server-side swarm approval — status tracker

> **Last updated:** 2026-06-29 (`/autoplan` on implementation branch)  
> **Overall:** Planning **done** · `/autoplan` **APPROVED** · Implementation **ready** · **~20%** (plan + review on branch)

---

## Where to see progress

| Surface | What it shows | Link / path |
|---------|---------------|-------------|
| **This file** | Living checklist T1–T7 + acceptance criteria | `docs/plans/P5-STATUS.md` |
| **Execution plan** | Full TDD spec, files to touch, test commands | [`2026-06-28-security-pr3-p5-swarm-approval-execution-plan.md`](2026-06-28-security-pr3-p5-swarm-approval-execution-plan.md) |
| **SECURITY.md** | P5 listed under "Remaining toward zero open queue" until remediated | `SECURITY.md` §B / line ~131 |
| **Portal code** | Current gap: `approved: true` client bool | `portal_server.py` ~2075–2079 |
| **React UI** | Hardcoded `approved: true` on launch | `web/src/features/command-center/SwarmComposer.tsx` ~112 |
| **Win preflight drop** | Mac peer artifact from coord-016 | `bin/.../results/win-p5-preflight-gap.md` |
| **PT backlog** | L1 blocked on P5 | `Perpetua-Tools/.agent/memory/working/V1_DEFERRED_BACKLOG_2026-06-28.md` |
| **GitHub** | PR #128 merged = **planning only**; no implementation PR open | `gh pr list --search swarm` |
| **L1 gate** | `l1_dispatch.py` exits 2 until P5 helpers exist | `bin/.../scripts/l1_dispatch.py` |

---

## Phase breakdown

```text
[████████████████████] PR1–PR2 merged (auth hardening baseline)
[████████████████████] PR3 planning merged (#128, 2026-06-28)
[████░░░░░░░░░░░░░░░░] /autoplan review on impl branch (2026-06-29)
[░░░░░░░░░░░░░░░░░░░░] P5 implementation (T1–T7) — READY TO START
[░░░░░░░░░░░░░░░░░░░░] PR4 P6 discovery (blocked on P5 merge)
[░░░░░░░░░░░░░░░░░░░░] L1 /api/l1/* (blocked on P5 merge)
```

---

## Task checklist (T1–T7)

| Task | Description | Status | Evidence |
|------|-------------|--------|----------|
| **T1** | `sign_operator_payload` / `verify_operator_payload` in `control_plane_auth.py` | ✅ Done (branch) | `tests/test_control_plane_auth.py` 5 new cases |
| **T2** | Preview returns `preview_id`, `approval_token`, `expires_at` | ❌ Not started | `api_swarm_preview` unsigned |
| **T3** | Launch requires tokens; rejects bare `approved` | ❌ Not started | Still `approved: true` gate only |
| **T4** | Auth regression tests (bearer + no token → 422) | ❌ Not started | Tests expect `approved` bool |
| **T5** | React SwarmComposer holds tokens | ❌ Not started | `swarm.ts` still `approved: true` |
| **T6** | SECURITY.md P5 remediated note | ❌ Not started | Still in "Remaining" queue |
| **T7** | Full pytest + repo_hygiene | ❌ Not started | — |

**Score: 1 / 7 tasks complete** (T1 on branch)

---

## Acceptance criteria (execution plan)

- [ ] Launch with bearer but **no** `approval_token` → **422**
- [ ] Valid preview → launch with tokens → dispatches 5 PT jobs
- [ ] Tampered objective → **403**
- [ ] Expired token → **403**
- [ ] Wrong `preview_id` → **403**
- [ ] Unauthenticated launch → **401** (already PR1)
- [ ] React cannot launch without prior preview
- [ ] SECURITY.md P5 annotated remediated

**Score: 1 / 8** (401 only)

---

## Branch / PR state

| Item | State |
|------|-------|
| Planning branch | `cursor/security-pr3-planning-f559` → **MERGED** (#128) |
| Implementation branch | `cursor/security-pr3-swarm-approval-f559` → **on remote** (`/autoplan` review) |
| `/autoplan` | ✅ APPROVED with amendments A1–A6 |
| Open PR | **None yet** — create draft or after T1–T7 |
| Target branch | `main` |
| Blocked downstream | L1 comms, PR4 P6 discovery approval |

---

## Next operator action

```bash
git fetch origin
git checkout cursor/security-pr3-swarm-approval-f559
# Implement T1 → T7 per execution plan (see GSTACK REVIEW REPORT + amendments A1–A6)
gh pr create --draft --title "fix(security): P5 server-side swarm approval tokens (PR3)"
```

After merge: re-run `win-p5-preflight-gap` checks; unblock `win-coder-l1-comms-autoplan-backlog`.
