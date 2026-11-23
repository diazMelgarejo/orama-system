# Verify-before-claiming — coordination protocol reference (PT 489)

Source of authority: Perpetua-Tools PR 489 (merged; head verified ancestor of
PT origin/main) - the operating checklist lives at
`Perpetua-Tools/.agent/protocols/verify-before-claiming.md` with the dated
miss catalogue in `memory/semantic/HANDWAVING_CATALOGUE_AND_AVOIDANCE_2026-11-10.md`.
This file ports the checklist for orama-system peer agents so the rule is
readable where coordination work happens.

## The checklist (ported)

1. **First contact with a tool or API**: read the documentation or entry
   point before running; a script can ignore `--help` and execute its normal
   (possibly mutating) action - treat an unknown-flag invocation as a real
   run and control its effects. Record version and flags. List the defaults
   that act or spend (mode, auto-approval, workdir, network, credits) and
   override or accept each explicitly.
2. **Existing code**: a path that only runs under a rare condition is
   dormant - run it once for real or label it UNTESTED; never build on top
   of it. "It has always worked" needs the last run that proves it.
3. **Answering a reviewer**: copy every finding into a numbered checklist;
   reply item by item (done / not done / disagree) with the commit or output
   that shows it; a reply shorter than the list needs a reason per missing
   item. Never write "done" for a bundle.
4. **Negative claims**: "not found" needs two differently worded searches
   (synonym, exact phrase, path), named. "Not installed" needs the command
   and its output, or a question to the operator.
5. **Experiments**: learn syntax from `--help` or a throwaway target; never
   probe the real append-only board, queue, outbox, or log.
6. **Claims and receipts**: an assignment or a merged PR is not a result; a
   reviewer disposition or an owner go needs its own record. Claim only what
   you can evidence; state identity_verified=false and endorsement=none on
   self-reported notes.

## Application to orama-system peer coordination

- Board notes and LAN drops follow items 3 and 6: every status line carries
  the artifact filename and its sha256.
- Task claims (task_claims rows) follow item 6: claim only after reading the
  enqueue payload and the referenced evidence; state blockers with the
  missing-input owner.
- Cross-references: PT 489 (Perpetua-Tools), D-0 decision record
  (docs/v2/queue-fencing-and-recovery/decision-record.md), the Q-68b
  numbering clarification.
