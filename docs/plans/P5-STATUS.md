# P5 — Server-side swarm approval — status tracker

> **Last updated:** 2026-06-29 (coord-023)  
> **Overall:** Planning **done** · Implementation **in progress on branch** · **~35%** (T1–T2 on branch; main unchanged)

---

## Where to see progress

| Surface | What it shows | Link / path |
|---------|---------------|-------------|
| **This file** | Living checklist T1–T7 + acceptance criteria | `docs/plans/P5-STATUS.md` |
| **Execution plan** | Full TDD spec, files to touch, test commands | [`2026-06-28-security-pr3-p5-swarm-approval-execution-plan.md`](2026-06-28-security-pr3-p5-swarm-approval-execution-plan.md) |
| **Decisions lock** | `/autoplan` amendments A1–A6 | [`P5-DECISIONS-LOCKED.md`](P5-DECISIONS-LOCKED.md) |
| **SECURITY.md** | P5 listed under "Remaining toward zero open queue" until merge | `SECURITY.md` §B / line ~131 |
| **Portal code (`main`)** | Still `approved: true` client bool | `portal_server.py` ~2075–2079 |
| **Branch** | T1–T2 implemented | `cursor/security-pr3-swarm-approval-f559` |
| **Win drops** | T1/T2 results in inbox | `win-p5-t1-operator-payload.md`, `win-p5-t2-preview-signing.md` |
| **L1 gate** | `l1_dispatch.py` exits 2 until P5 merges to `main` | `bin/.../scripts/l1_dispatch.py` |

---

## Phase breakdown

```text
[████████████████████] PR1–PR2 merged (auth hardening baseline)
[████████████████████] PR3 planning merged (#128, 2026-06-28)
[███████░░░░░░░░░░░░░] P5 implementation (T1–T2 on branch; T3–T7 pending)
[░░░░░░░░░░░░░░░░░░░░] PR4 P6 discovery (blocked on P5 merge to main)
[░░░░░░░░░░░░░░░░░░░░] L1 /api/l1/* (blocked on P5 merge to main)
```

---

## Task checklist (T1–T7)

| Task | Description | Status | Evidence |
|------|-------------|--------|----------|
| **T1** | `sign_operator_payload` / `verify_operator_payload` in `control_plane_auth.py` | ✅ On branch | `tests/test_control_plane_auth.py` |
| **T2** | Preview returns `preview_id`, `approval_token`, `expires_at` | ✅ On branch | `tests/test_swarm_preview.py` 7/7 |
| **T3** | Launch requires tokens; rejects bare `approved` | ❌ Pending | `main` + branch tip |
| **T4** | Auth regression tests (bearer + no token → 422) | ❌ Pending | — |
| **T5** | React SwarmComposer holds tokens | ❌ Pending | `swarm.ts` still `approved: true` on `main` |
| **T6** | SECURITY.md P5 remediated note | ❌ Pending | After merge |
| **T7** | Full pytest + repo_hygiene | ❌ Pending | — |

**Score: 2 / 7 tasks complete (on branch; 0 / 7 on `main`)**

---

## Acceptance criteria (execution plan)

- [ ] Launch with bearer but **no** `approval_token` → **422**
- [ ] Valid preview → launch with tokens → dispatches 5 PT jobs
- [ ] Tampered objective → **403**
- [ ] Expired token → **403**
- [ ] Wrong `preview_id` → **403**
- [x] Unauthenticated launch → **401** (PR1 on `main`)
- [ ] React cannot launch without prior preview
- [ ] SECURITY.md P5 annotated remediated

**Score: 1 / 8 on `main`** (401 only)

---

## Branch / PR state

| Item | State |
|------|-------|
| Planning branch | `cursor/security-pr3-planning-f559` → **MERGED** (#128) |
| Implementation branch | `cursor/security-pr3-swarm-approval-f559` → **on remote** (Win active) |
| Open PR | none yet — operator merge when T3–T7 green |
| Target branch | `main` |
| Blocked downstream | L1 comms, PR4 P6 discovery approval |

---

## Next operator action

Win coder: **T3** on `cursor/security-pr3-swarm-approval-f559` — launch requires tokens; hard 422 without `approval_token`.

Mac: review branch PR when T3+ tests pass; merge unblocks L1 and P6 stack.
