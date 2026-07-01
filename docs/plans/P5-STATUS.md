# P5 — Server-side swarm approval — status tracker

> **Last updated:** 2026-06-30 (CR fixes resolved: server-only operator signing secret, type-safe verify_operator_payload, test-vector noqa)  
> **Overall:** Planning **done** · Implementation **done** · CodeRabbit **3/3 findings resolved** · **100%** (T1 sign/verify_operator_payload landed with 24/24 tests passing, ruff clean)

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
> **Last updated:** 2026-06-30 (CR fixes resolved: server-only operator signing secret, type-safe verify_operator_payload, test-vector noqa)  
> **Overall:** Planning **done** · Implementation **done** · CodeRabbit **3/3 findings resolved** · **100%** (T1 sign/verify_operator_payload landed with 24/24 tests passing, ruff clean)
```

---

## Task checklist (T1–T7)

| Task | Description | Status | Evidence |
|------|-------------|--------|----------|
> **Last updated:** 2026-06-30 (CR fixes resolved: server-only operator signing secret, type-safe verify_operator_payload, test-vector noqa)  
> **Overall:** Planning **done** · Implementation **done** · CodeRabbit **3/3 findings resolved** · **100%** (T1 sign/verify_operator_payload landed with 24/24 tests passing, ruff clean)

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
> **Last updated:** 2026-06-30 (CR fixes resolved: server-only operator signing secret, type-safe verify_operator_payload, test-vector noqa)  
> **Overall:** Planning **done** · Implementation **done** · CodeRabbit **3/3 findings resolved** · **100%** (T1 sign/verify_operator_payload landed with 24/24 tests passing, ruff clean)
| Target branch | `main` |
| Blocked downstream | L1 comms, PR4 P6 discovery approval |

---

## Next operator action

> **Last updated:** 2026-06-30 (CR fixes resolved: server-only operator signing secret, type-safe verify_operator_payload, test-vector noqa)  
> **Overall:** Planning **done** · Implementation **done** · CodeRabbit **3/3 findings resolved** · **100%** (T1 sign/verify_operator_payload landed with 24/24 tests passing, ruff clean)

Mac: review branch PR when T3+ tests pass; merge unblocks L1 and P6 stack.
