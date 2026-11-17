# Live pair loop harness (saved copies, 2026-11-17)

These are sanitized copies of the evaluators and drivers that ran the live turns. The originals sat in
a session scratch directory that does not persist. They are examples to rebuild a turn from, not a
supported tool.

| File | Role |
| --- | --- |
| `evaluator_turn3.py` | Fixed evaluator for the inner seat: vets a candidate with the allowlist, splices it into a scratch copy of the repository, runs reviewer-derived cases and the existing tests through the sandbox, and returns a metric |
| `evaluator_outer_turn2.py` | Fixed evaluator for the outer seat: validates her Mechanism Card and checks it is grounded in the real ledger |
| `driver_inner_turn3b.py` | Builds the inner prompt (task, target function, helper source, required behaviour), re-probes the model list, runs `run_live`, saves the trace |
| `driver_outer_turn2.py` | Builds the outer prompt from the real trace, the candidate and the real open items, runs `run_live` |
| `evaluator_prelaunch.py` | Turn 5 inner evaluator: reviewer cases for the pure pre-launch decision table `_launch_decision`, existing live-cycle tests scored against a measured baseline, a reference answer checked first |
| `driver_inner_prelaunch.py` | Turn 5 inner driver; passes the real shared `SpendGuard()` and `ledger_path` (7 failed cases to 0, kept) |
| `evaluator_review.py` | Turn 5 outer evaluator: scores only the review's form and grounding in the diff; content is vetted by reproduction |
| `driver_outer_review.py` | Turn 5 outer driver: Biafra reviews the redesigned launch lifecycle; three findings, all reproduced and fixed |

## To reuse

1. Put the evaluators in a `verifier/` folder beside the drivers; set `ORAMA_REPO` to the checkout.
2. Choose a real task from existing feedback and write the cases from the reviewer's own inputs.
3. Measure the baseline, and check that a reference answer scores 0 before any request.
4. Export the provider key variable in the shell for that command only, and set the gate and arm
   variables on the same command line.
5. Set `PERPETUA_TOOLS_ROOT`, build `SpendGuard()` from `bin/agents/spend_guard.py` and pass it to `run_live`
   as `spend_guard`; the operator must have attested (see the runbook) or every request is refused.

## Known limitations of these saved copies

- `driver_inner_turn3b.py` and `driver_outer_turn2.py` ran before the spend guard was mandatory and call
  `run_live` without `spend_guard`. `live_cycle` now refuses that call (`spend-guard-required`); add
  `spend_guard=SpendGuard()` to rebuild a turn (step 5 above).
- `evaluator_outer_turn2.py` reads the live ledger, which now holds later records than the prompt named,
  and assumes the card parses to an object. `evaluator_turn3.py` scores an unavailable pytest as 999.
  They are kept exactly as run, as evidence of what was measured. A new turn should use a fixed evidence
  snapshot, reject non-object cards, and stop (not score) when the test launch itself fails.

The scoring must go through `bin/agents/sandbox_run.py`. Never run a candidate with the provider key
in its environment. See the runbook at
`bin/orama-system/skills/metaresearcher/references/live-pair-loop-runbook.md`.
