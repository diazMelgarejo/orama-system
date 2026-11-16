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

## To reuse

1. Put the evaluators in a `verifier/` folder beside the drivers; set `ORAMA_REPO` to the checkout.
2. Choose a real task from existing feedback and write the cases from the reviewer's own inputs.
3. Measure the baseline, and check that a reference answer scores 0 before any request.
4. Export the provider key variable in the shell for that command only, and set the gate and arm
   variables on the same command line.
5. Pass `spend_ledger` and `budget_usd` to `run_live` so the monthly guard applies.

The scoring must go through `bin/agents/sandbox_run.py`. Never run a candidate with the provider key
in its environment. See the runbook at
`bin/orama-system/skills/metaresearcher/references/live-pair-loop-runbook.md`.
