# Steeled Lockstep Fleet Remediation Plan (2026-11-13)

**Status:** executable residual plan after harsh review  
**Supersedes for execution:** Agnes `lockstep_fleet_remediation_and_optimization_plan_20261108.md`
v3
**Absorbs:** `references/2026-11-13-lockstep-fleet-remediation-plan-review.md`
(do-not-execute-as-written)
**Board:** GossipBus topic `LOCKSTEP_FLEET_PLAN_REVIEW_20261113` + LAN peer L-1a / PR495–497 notes  

Serving stays **OFF**. `ORAMA_GRANT_SERVING` stays unset. Green CI, bot replies, and this document
do **not** authorize merge, host qualification, C6, or activation.

---

## 1. Authority (required by review)

- Claim class - Canonical location - Not here
- Closure register, C6/C8 ordering, dispositions - `orama-system/docs/v2/` especially `MASTER-
  CLOSURE-AND-IMPLEMENTATION-PLAN-2026-11-06.md`, `closure/c1-orama-dispositions-2026-11-06.md`,
  `closure/c3d-operator-review-procedure-2026-11-06.md`, `references/r0-r2-contract-
  freeze-2026-10-26.md` - Oramasys product docs, PT plans
- Serving activation, Release 1–2 post-merge, revocation capacity, C6 Mac/Windows -
  `oramasys/oramasys/docs/` (`serving-activation-runbook.md`, `release12-postmerge-
  qualification-2026-11-04.md`, `revocation-capacity-handoff-2026-11-03.md`,
  `closure/c6-qualification-runbook.md`, `closure/c6-windows-handoff.md`) - `orama-system/docs/v2/`
  alone
- PT Part 3, multi-agent remediation, phase-0 disposition - `Perpetua-
  Tools/docs/next/2026-08-23-coordination-consolidation-part3-plan.md` (2026-11-06 ratification: PT
  stays manual, no daemon, automatic expiry is v2-only), `docs/plans/`, `docs/references/phase0-and-
  orama-open-work-closure-plan-2026-07-18.md` - Orama or Oramasys
- Review methodology (finding matrix, single-edit, bot SHA replies) - `orama-system/bin/orama-
  system/references/post-review-micro-remediation.md` + `SKILL.md` link - Product gates

**Dropped citation:** `VERIFIED-HANDOFF-AND-NEXT-SLICE-2026-11-08.md` (not in tree). Use the
Oramasys C6 runbooks + Orama master closure instead.

**Phase 4 from Agnes v3 is not part of this steeled plan.** Dual-platform / SQLite ≥ 3.51.3 / p95 ≤
60 ms / zero fail-open belong to a **separate Oramasys-owned C6 execution plan** after phylax
portability and operator-authorized volume evidence. CodeRabbit remediation never closes C6, R6–R8,
or serving.

---

## 2. Board reality (re-home off merged tips)

- Former plan target - State - Consequence
- `oramasys/phylax#32` - **MERGED** - Phase 1 (C1 reserved names / publication refusal) treated
  closed on main
- `diazMelgarejo/orama-system#481` - **MERGED** - Phase 2 (aiosqlite CI, subreaper, portal
  ModelGovernance mapping) closed on main
- `diazMelgarejo/Perpetua-Tools#484` - **MERGED** - Phase 3 (state_dir, episodic IO, memory_search,
  HANDOFF) closed on main
- Phase 0 methodology - On main (`post-review-micro-remediation.md` + SKILL link) - Do not re-open

**Live residual tips (GossipBus + gh, 2026-11-13):**

- PR - Head (at synthesis) - Role
- PT `#496` - `0f57c4eb` (steeled L-1a floor/presence) - L-1a interim cleanup fence (canonical
  Mac/POSIX; Windows Cline `cc57cd14` = cross-evidence only per LAN `QF-L1A-DELTA-REPORT`)
- PT `#495` - `de325709` (base `#496` @ `0f57c4eb`) - Memory lessons; Agnes noted prior
  remediations; residual CR on mtime CAS + LF vs byte identity
- PT `#497` - `f38634a6` / stacked tip - Discovery-endpoints lesson; board
  `PR495_497_LESSONS_FIX_COMPLETE` — no open CR threads
- Orama `#493` - `e3c68ef5` (+ steelman doc) - Queue-fencing D-0 docs; residual CR on Q-68b replay
  wording, atomic stage, V1-2/V2-2 hold split, markdown lint

Stack: `#496` (main) → `#495` → `#497`. Merge bottom-up only under operator authority.

---

## 3. What the harsh review kept (steel, not discard)

1. Serving off / grant unset.  
2. One edit per file, one push per repo after local verification.  
3. Codify methodology before apply (already on main).  
4. Phylax Windows reserved-name ownership (already merged).  
5. Mandatory bot replies with exact SHAs.  
6. Agnes C1–C5 technical fixes were the right *shape*; re-verify on **current** tips, not stale
`#32/#481/#484` comments.

---

## 4. Finding matrix (residual only)

- PR - Thread / finding - File - Fix - Owning tip
- PT 496 - CR `4558150122` — `agent_killed` must not count as renewed liveness -
  `orchestrator/coordination/task_queue.py` - Liveness `MAX(ts)` restricted to presence kinds
  (`agent_register`, `agent_pulse`, `agent_claim`, `agent_release`); exclude `agent_killed` - `#496`
- PT 496 - CR `4558150125` — floor must be dead-classification boundary, not only `captured_at` -
  `task_queue.py` + `heartbeat_monitor.py` - Pass `liveness_floor_by_agent` from
  `find_agent_heartbeats` `last_heartbeat_ts` into capture; store per-row floor; release uses that
  floor - `#496`
- PT 496 - CR `4558150131` — empty capture still folds full history - `task_queue.py` - Early
  `return []` when capture empty before `release_captured_queue_claims` - `#496`
- PT 495 - CR `4557491086` — mtime-only CAS unsafe - `.agent/memory` via `learn.py`/`graduate.py
  --supersedes lesson_8d06f91c13bd` - Require shared lock or content-hash/revision CAS; ban mtime-
  only - `#495`
- PT 495 - CR `4557491096` — LF-normalized ≠ byte identity - supersede `lesson_7db1ec37e5d8` - State
  digest form; raw-byte vs normalized-equivalence labels - `#495`
- PT 497 - (none open) - — - Rebase only if `#495` moves; no content change required - `#497`
- Orama 493 - CR `4533389934` / `4533389971` — two-stage replay + attempt numbering -
  `docs/v2/queue-fencing-and-recovery/{README,amendment-drafts,decision-record}.md` - Align README +
  decision record; define attempt 1 = first verified retry after initial grant - `#493`
- Orama 493 - CR `4545895750` — atomic durable stage advance - `decision-record.md` - Persist stage
  before returning token; concurrent retries ≤ one token - `#493`
- Orama 493 - CR `4545895775` — split V1-2 vs V2-2 holds - `decision-record.md` - Separate
  prerequisite lists - `#493`
- Orama 493 - CI markdownlint MD013/MD047 - same docs - Wrap to 100 cols; trailing newline - `#493`

---

**Orama #493 note:** remote tip `e3c68ef5` already aligned Q-68b attempt numbering, durable stage
advance, V1-2/V2-2 hold split, and schema-1 replay gate; this PR tip only adds the steeled fleet
synthesis document.

## 5. Gossip / LAN integrations folded in

- **L-1a Mac canonical** remains `49bda5d2` shape (two-phase capture/release, `REFUSED`,
unknown-task hold). This steeled edit **tightens** the floor and presence filter without reverting
Delta 1–4 agreements.
- **PR495/497 lessons fix complete** (Agnes outbox 2026-11-12): prior supersessions kept; only
residual CR rows above.
- **Cline W&B route / TLS front-end / pin notes:** coordination context only; not merge or serving
authority.
- **Part 3 ratification:** no PT daemon; no automatic claim-expiry on PT in this batch.

---

## 6. Execution rules

1. Edit only the owning tip worktree; re-read file from tip before edit.  
2. TDD for `#496` fence changes; run `tests/test_l1a_interim_cleanup_fence.py` (+ related
coordination tests).
3. Memory changes only through `.agent/tools/learn.py` + `graduate.py --supersedes` (never hand-edit
`LESSONS.md`).
4. Reply to each CR thread with `@{Bot} we fixed this in commit {SHA}` after the tip lands.  
5. **One push per repository** at the end (PT stack branches + orama `#493`). No force-push. No
merge. No serving.

---

## 7. Explicit non-goals

- Re-opening merged `#32` / `#481` / `#484`.  
- Inventing or editing Oramasys C6/serving runbooks from this remediation.  
- Treating local pytest as host qualification or SQLite floor evidence.  
- Concurrent Ollama + LM Studio heavy load on this Mac.
