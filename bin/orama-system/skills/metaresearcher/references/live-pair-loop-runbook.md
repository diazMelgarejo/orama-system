# Live pair loop runbook (interim, 2026-11-17)

Status: interim. It is written from four live turns on one day and will change. Every rule below
names the evidence it came from. Where the evidence is thin, it says so.

## Billing basis

The spend guard is shared: the logic, the provider policy and the budget state live in Perpetua-Tools
(the runtime and state authority) and every agent uses them. Provider facts are not trusted from memory:
`python3 -m orchestrator.provider_limits verify wandb-inference` fetches the official references named in
`config/provider-policies/wandb-inference.json` and reports each fact as confirmed, drift or
unreachable (13 of 13 confirmed on 2026-11-17).

What the official pages say ([Usage information and limits](https://docs.coreweave.com/products/inference/serverless/usage-limits),
last modified 2026-11-09, and the
[402 article](https://docs.coreweave.com/support/inference/articles/api-error-code-402-you-exceeded-your-cur)):
Serverless Inference is priced per token; the plan allowance is used first; on the Free plan inference stops
when the allowance is used up until pay-as-you-go is activated; billing is monthly and only after activation;
activation does not charge a card; the default Free cap is 100 dollars a month once active. A `402`
("You exceeded your current quota") has two causes: the allowance is used up while pay-as-you-go is inactive
(Free and Academic plans), or the spending cap was reached. Concurrency limits per project and user return
`429`; location limits return `403`. No per-hour or per-day request limits are documented.

A Free account can have pay-as-you-go active without a card yet charged, and then turns can bill up to the
cap. So "free with no payment method charged" is not enough. Before any live request the operator must
**attest** that the plan is Free, pay-as-you-go is inactive and allowance remains. Only the operator can read
the Billing page, so the `attest` command asks for an interactive terminal and a typed confirmation.
The guard itself checks only the file's contents, so a process running as the same user could write it:
the attestation is a speed bump, not an access control. Run:
`python3 -m orchestrator.provider_limits attest wandb-inference --plan-free --payg-inactive
--allowance-remaining --by <name>`, then type the confirmation at the interactive prompt (the parser
has no `--confirm` argument and refuses it). It expires after seven days. An agent must never run it.
Without a fresh attestation the guard refuses every live request
(`attestation-required`).

Rules: never activate pay-as-you-go; stop the loop on any `402` or `429`; one call is one request, so the
provider client is built with `max_retries=0` (the OpenAI SDK retries a 429 twice by default).
`live_cycle` reports a failed launch matching either code as `provider-payment-required` or
`provider-rate-limited` with `stop: true`, spends the attempt and never retries; the shared classifier decides.

### Monthly budget and the shared guard

The operator set an estimated ceiling of 90 dollars a month of "free" use, kept under the 100-dollar cap. The
guard is Perpetua-Tools' `orchestrator/cost_guard.py` `CostGuard` in its monthly mode (atomic reserve, commit
and rollback), configured by the provider policy and used from orama through `bin/agents/spend_guard.py`:
set `PERPETUA_TOOLS_ROOT`, build `SpendGuard()`, pass it as `live_cycle(..., spend_guard=guard)`. `live_cycle`
refuses before any launch with the guard's reason (`attestation-required`, `budget-exhausted`; `stop: true`),
reserves a conservative projection, and settles the estimated actual cost afterwards, including for failed and
timed-out requests. With no checkout, no policy or no attestation, it fails closed. Only sizes are stored in
the audit rows, never prompts or answers. Sizes are characters over four; the rates are an upper bound (0.50
input and 1.50 output dollars per million tokens, the highest non-Pro DeepSeek rates on the pricing page), and
the projection assumes 40 thousand output tokens because the reasoning stream is billed. The estimate is not
billing: the Billing page is the truth.

Position on 2026-11-17: the live requests made so far are estimated at about 0.15 dollars (0.17 percent of the
budget), reconstructed as an upper bound and seeded into the guard's state.

## Principles

1. **Test on real work with the real evaluator.** A live turn exists to meet real-world conditions:
   real reviewer comments, real failing CI, the repository's own tests, and cases taken from the
   reviewer's stated inputs. A corpus and answer key you wrote yourself tests your assumptions.
2. **Show each seat what it is graded on.** Hidden cases made the outer seat misjudge an evaluator
   it never saw. Show the expectations, the helper source and the return types.
3. **The evaluator is fixed and pinned.** Neither seat edits it; its digest goes in the trace.
4. **Model output is untrusted data.** Reproduce every claim against the code. Run candidates only
   in the sandbox. Read a candidate before you incorporate it.
5. **One attempt per request, no retry of the same attempt.** Fixing the cause of a failure and
   making a new attempt is not a retry; say which it is.
6. **Every refusal happens before a side effect.** The attempt marker is claimed last.
7. **Report faithfully.** Count requests honestly, including cut-off ones, and name claims that did
   not hold.

## Before a live turn

| Check | How |
| --- | --- |
| A real task exists | `gh api repos/<owner>/<repo>/pulls/<n>/comments` and `/reviews`; open issues; failing CI |
| The defect reproduces | Run the reviewer's own input against the current code and see it fail |
| The evaluator is fixed | Repository tests plus reviewer-derived cases; baseline measured; a reference answer scores 0 |
| The evaluator is safe | Candidates run through `bin/agents/sandbox_run.py` only |
| Gate and arm | `BIAFRA_ORCHESTRATOR_GATE=approved` and `BIAFRA_ALLOW_LAUNCH=1` set for that one command only |
| Provider re-probe | Same-day read-only model list; abort before any completion if the model is missing |
| Budget | Operator ceiling: an estimated 90 dollars a month of list-price usage, under the Free plan's 100-dollar cap; pass `spend_guard` (the adapter to the shared guard in Perpetua-Tools) to `live_cycle`; see Billing basis |
| Effort | Explicit; medium, else high, else low; the V4.1 models reject `medium`, so `high` |

## What goes in a seat's prompt

The task from the real feedback, quoted as data; the target function; the **source of every helper
it calls** (turn 3 reverted because the model assumed `_text` returned the text, and it returns a
bool); the exact required behaviour, matching the evaluator; the output format (one code block, one
function, three sentences naming the assumption); and "do not call tools". Tell the outer seat which
numbers are real: she caught that one count in a prompt was wrong.

## Safety for model-written code

- A name denylist is a filter, not a sandbox: it accepted a `getattr`-built dunder walk.
- `sandbox_run.run_isolated`: empty environment (no key, no gate variable), deny-by-default kernel
  profile (no network, writes only in the scratch root, reads only the interpreter, system libraries
  and scratch root, exec only of the interpreter), a timeout that kills the process group, and a
  refusal to run when no sandbox exists or a read root is broad.
- `sandbox_run.vet_allowlist`: one function, listed constructs only, no parameter defaults or
  variadics, no name that shadows a builtin. It is a first gate; the sandbox is the isolation.
- In an automated loop the scorer runs a candidate before anyone reads it. Reading is a vetting step,
  not the control.

## Run order

Measure the baseline and check a reference answer scores 0. Run the inner seat live. Score it in the
sandbox and record the trace. Vet the candidate and incorporate it test-first. Run the outer seat
live on the real trace and vet her claims. Commit named files locally. Push only when the operator
says so.

## Choosing a target and ordering a turn

Distilled by the Crystal pass over the 2026-11-17 event log (one request, about 0.009 dollars).

- **Make the target a pure decision function.** The allowlist vet bans `try` and attribute calls by
  design, so a lifecycle (try/finally, I/O, adapter calls) can never be a pair target. Extract a
  function that takes facts and returns a decision, prove the extraction with the existing tests, give
  that to the seat, and write the lifecycle by hand in the caller. `_launch_decision` is the example.
- **Score against a measured baseline.** If a harness change leaves existing tests failing (a permissive
  test guard did, 8 of them), count only failures beyond that baseline, comparing failed test identities, not counts (a candidate
  that fixes one baseline failure and breaks another keeps the count and must still score as a
  regression; the archived evaluator compares counts and is kept unchanged), and run a known-good reference
  answer through the evaluator before the live request, so evaluator bugs are not charged to the model.
- **Start the seat in the background, then edit only what it does not import.** Incorporate its output
  test-first afterwards.

## Vetting what a model returns

- **Reproduce each claim.** Turn 2's outer review had true points (a misleading message, degenerate
  identifiers), false ones (non-string elements raising, wiring untested) and a fabricated
  reproducer (a `delta()` helper that does not exist). Only reproduced claims drive work.
- **Claims about code the seat was not shown are suspect.** Show it, or discount them.
- **Look for what the evaluator cannot see.** Examples found: a dead `try/except` that would report
  a misleading reason; an unbounded diagnostic message.
- **Check what the candidate assumes.** Turn 1's accepts integers up to about 1.8e308; that is now a
  stated, recorded assumption, not an accident.
- **Check the card.** The validator checks shape and fixed-wall names, not meaning: a sentence as an
  owner and an invented metric both passed until the validator was tightened.

## Incorporating

Write the reviewer's own inputs as tests first and watch them fail. Apply the candidate with the
edit the vetting called for, run the touched suites, stage named files, commit, and check
`git log -1` (a hook can reject a commit silently).

## Results so far (all on the operator-certified W&B Free plan, `DeepSeek-V4.1-Flash-1017`, high effort)

| Turn | Seat | Task | Result |
| --- | --- | --- | --- |
| 1 | inner | Huge integers raise `OverflowError` (CodeRabbit) | 6 to 0, kept |
| 1 | outer | Triage comments 3 and 4, propose a rule | card valid, grounded |
| 2 | inner | Sentence accepted as `owner_slices` (observed in turn 1) | 10 to 0, kept |
| 2 | outer | Judge turn 2, choose the next task | card valid; her chosen task rested on a fabricated reproducer and was rejected |
| 3 | inner | Degenerate identifiers, blank-entry message | reverted: wrong assumption about a helper |
| 3b | inner | Same task, helper source shown | 10 to 0, kept |

Not proven: that the outer seat's rule improves later attempts. Turn 2 used her rule and passed, but
the prompt also contained the exact requirements, so the effect cannot be separated.

## Git, PR and push discipline

One pull request per mutated repository; commit locally and push once, on the operator's word;
name files when staging (`git add -A` staged a generated file); a rejected hook means no commit;
never push to learn whether the remote is ahead. Replies to a bot reviewer wait for the push and
the operator's authorization, and cite the fixing commit.

## Shell and tooling gotchas

`npm install` needs `--prefix` or it acts on the nearest ancestor project; a bare `cat > file`
blocks on stdin; zsh does not word-split a variable, so a loop over `set -- $var` fails; `echo ====x`
expands as a command in zsh; a replace-to-end-of-file edit deletes later code; the plugin hook that
blocks commands naming `node_modules` or `.venv` paths is not to be worked around.

## Open decisions

The stall window; Wanda's soul card versus the W&B Cline route; a registry of declared metrics (G10).

## Saved harness

Sanitized copies of the evaluators and drivers used in the live turns are in
`docs/v2/references/biafra/live-cycle-2026-11-17/harness/`, with a README on how to rebuild a turn.
