# 76 — Biafra, the outer seat: canonical plan and retrofit readiness

> **Status:** operator-approved 2026-11-17 for implementation. This document records what was
> decided, what this change implements, and what is still open. It adds no tri-level runner, no
> serving grant and no live run by itself. It extends
> [`25-autoresearcher-doctrine-and-againtra-flagship.md`](25-autoresearcher-doctrine-and-againtra-flagship.md);
> nothing in 25 is rewritten.

## 1. Decisions (from the operator, 2026-11-17)

| Topic | Decision |
| --- | --- |
| Role | The MetaResearcher role is approved. The seat name **Biafra** is ratified as a canonical agent. |
| Naming | Additive. Display name `Biafra` and a separate `canonical_agent: biafra` record. `openclaw_id`, `hermes_profile`, `soul_id` and the folder stay `metaresearch-outer` / `perpetua.autoresearch.outer`. |
| Persona | Operator wording: a stern but very helpful thesis adviser, disarming, thorough, specific, direct, evidence-first, non-intrusive, nudging toward stated goals, exposing assumptions. Pronouns she/her, operator-supplied. The rest of the personification in `bin/agents/personas/biafra.yaml` is a draft for review. |
| Retrofit scope | Seat contracts plus a Mechanism Card schema, in orama-system. |
| Card home | The contract lives in orama-system now. Anamnesis is the future record store and Kungfu the future reference holder; neither unpublished repository is changed. |
| Effort and models | Two tiers, both explicit. **Preferred, human-gated:** Biafra (MetaResearcher) on Claude Fable 5.2 high or GPT-6 Astra high; the AutoResearcher seat on Claude Opus 5.5 medium or GPT-6.1 Sol medium. These stay preferred as planned and run only after explicit human approval before execution. **Default, automatic:** the standing rule, medium, else high, else low, never xhigh or max, runs on free W&B turns with no human approval and is the fallback whenever no paid permission has been granted. Clarified 2026-11-17; an earlier version of this row said the draft's table was superseded, which was wrong. |
| Live gate | Opened in principle for one bounded cycle: W&B free-first, 2 requests (one inner, one outer), no retry, no paid credits. Nothing is armed by this change. See section 5. |
| PR shape | One PR in each mutated repository. |

## 2. What exists (verified on main at `ad5ca541`)

Seats `autoresearch-inner` and `metaresearch-outer` with programs, `bin/agents/biafra_cycle.py` (dry
cycles with a one-cycle marker, verifier-protected paths, gate plus arm), the `metaresearcher` skill
and `tests/test_biafra_seats.py`. Scout (`autoresearcher`) is the original inner-seat AutoResearcher.

## 3. What this change adds

| Item | Where |
| --- | --- |
| Trace entry contract, `stall_report`, `evaluator_digest`, Mechanism Card validator | `bin/agents/seat_contracts.py` |
| Shape-only schema and fixtures (3 invalid, 2 valid) | `docs/v2/references/biafra/mechanism-card.schema.json`, `tests/fixtures/mechanism_card/` |
| Dry cycle emits a validated trace entry when given an evaluator digest; non-finite metrics are refused | `bin/agents/biafra_cycle.py`, both programs |
| Biafra canonical, additive: registry display and `canonical_agent`, `seat` on all three research rows | `bin/agents/REGISTRY.yml` |
| Persona and soul card | `bin/agents/personas/biafra.yaml`, `bin/agents/metaresearch-outer/SOUL.md` |
| Scout and inner-seat cards gain the seat contract | `bin/agents/autoresearcher/`, `bin/agents/autoresearch-inner/SOUL.md` |
| Skill and task-type reference | `bin/orama-system/skills/metaresearcher/SKILL.md`, `bin/orama-system/references/autoresearch-task-type.md` |

Fixed walls: a card whose `owner_slices` names Phylax, Telos or Agate is refused with `E_OWNER` before
any measurement. The Python validator is the authority; the schema is shape-only, because a schema
that cannot encode ownership must not be mistaken for safety.

## 4. Gaps, conflicts and uncertainties (not assumed)

| # | Item | State |
| --- | --- | --- |
| G1 | Biafra has no ledger to read. Anamnesis is a scaffold and its runtime capture fails closed. | Open. Trace entries are specified, not stored. A reader adapter waits for Anamnesis. |
| G2 | Kungfu is an unpublished local draft with an unevaluable O1–O3 gate. | Open. Mechanism Cards reference atoms by id only. |
| G3 | The evaluator digest is computed by `evaluator_digest()` but nothing yet pins it at run start, and `validate_mechanism_card` never compares a card's digest with its dry-run receipt. Accepted today although it should not be: (1) a graduated card whose receipt has no `trace`; (2) a graduated card whose receipt `trace.evaluator_digest` differs from the card's; (3) a graduated card whose digest was never pinned by anything. | Open. Needs a place the operator or gate writes the pin, and a decision on what the digest covers. Not implemented on purpose. |
| G4 | Stall window defaults to 3 consecutive reverts. | Operator to confirm or change. |
| G5 | The 2026-06-05 rule that `oramasys/*` is reference-only versus later direct PRs there. | Not touched here; no `oramasys/*` repository is mutated. |
| G6 | Persona elaboration beyond the operator's wording. | Draft, for review. One boundary was added: Biafra questions the work's assumptions and does not diagnose the person. |
| G8 | `_finite` accepts integers up to about 1.8e308, including the band above 2**53 where conversion to float loses precision. A transport that serialises the raw integer (JSON can carry 10**400) may accept a value this validator refuses. | Assumption recorded; the docstring states it. Operator to confirm that every consumer computes in doubles. |
| G9 | The fixed-wall card check runs only when a caller passes `mechanism_card`. A caller that omits it is not checked. | Reported as `card_checked: false` so checked and unchecked are distinguishable. Making the card mandatory is a decision for the operator. |
| G7 | Provider state for the live cycle (W&B model order and effort acceptance, BigModel balance) was last seen on 2026-11-12. | Must be re-probed before arming. |

## 5. Live cycle (one, bounded, not armed by this change)

Preconditions, all required: the operator names provider, budget, request limit and deadline (given
as W&B free-first, 2 requests, no paid credits); the model order and effort acceptance are re-probed
the same day; the evaluator digest is recorded; `BIAFRA_ORCHESTRATOR_GATE=approved` and
`BIAFRA_ALLOW_LAUNCH=1` are set by the operator for that one run and unset afterwards. Stop and report,
without retry, if the provider needs paid credit, rejects the requested effort, or the marker file
already exists. The result is data until a non-maker reviews it.

## 6. Retrofit map (later, each its own decision)

| When | What |
| --- | --- |
| Anamnesis provisioned | A read-only adapter feeds trace entries to Biafra; Mechanism Cards become ledger records. |
| Kungfu published and O1–O3 evaluable | Cards reference atom revisions; the manifest validator becomes the second ownership check. |
| Tri-level | Stays off. Needs a human approval record at the top-level orchestrator gate. |

## 7. Verification

`python3 -m pytest tests/test_seat_contracts.py tests/test_biafra_seats.py tests/test_agent_frugality_tiers.py`
and the repository hygiene and markdown checks named in the PR.

## 8. Correct W&B defaults, references and live check log (2026-11-17)

### 8.1 Defaults used from now on

| Item | Default | Source |
| --- | --- | --- |
| Model order | `deepseek-ai/DeepSeek-V4.1-Flash-1017`, then `deepseek-ai/DeepSeek-V4.1-Flash`, then `deepseek-ai/DeepSeek-V4-Flash-0731` | [launcher](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/cline-wandb/scripts/launch_cline_wandb.py), [stale-reference ledger](https://github.com/diazMelgarejo/orama-system/blob/main/docs/stale-reference-ledger-2026-11-12.md) |
| Effort | Ladder medium, else high, else low, never xhigh or max. The V4.1 models reject `medium` (HTTP 400 "Invalid request") and accept `high` and `low`, so the free default turn is V4.1-Flash-1017 at **high**. V4-Flash-0731 accepts `medium`. | `lesson_d4ff6f4278ad` |
| Absent ids | The bare `DeepSeek-V4-Flash` id is 404; W&B serves no `deepseek-flash` alias | launcher docstring, `lesson_d4ff6f4278ad` |
| Cline provider entry | `tokenSource` `manual`; `updatedAt` in milliseconds with a trailing `Z`. A "invalid model ID" error from Cline 3.0.74 is stale metadata, not a bad model | `lesson_8e02c7fd391d`, ledger |
| Key handling | Shell-source the operator env file before reading `DEEPSEEK_V4_FLASH_WANDB`; a raw parse gives 401. No CoreWeave team or project string | `lesson_e6e7c89409ea`, `lesson_2c1aad86632a` |
| Cline flags | Plan mode, `--auto-approve false`, positional prompt (no `task` subcommand) | `lesson_d581163a2d66`, launcher |
| Route | `launch_cline_wandb.py`; ClinePass DeepSeek keeps its own wrapper | `lesson_8d873e4e2f73`, [PR 496](https://github.com/diazMelgarejo/orama-system/pull/496) |

Lessons are in the Perpetua-Tools
[LESSONS.md](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/.agent/memory/semantic/LESSONS.md)
(source rows in `lessons.jsonl` beside it). `plan_turn` and `default_wandb_turn` in
`bin/agents/seat_contracts.py` encode these defaults, and a test pins them to the launcher.

### 8.2 How Cline on W&B reached parity with Wanda

2026-11-10 positional prompt, plan mode, `cline-pass` provider id; 2026-11-12 model churn, the
medium-effort 400 and the strict 3.0.74 provider entry were isolated by bisecting an isolated
config; 2026-11-13 key sourcing and the launcher fix (PR 496). `lesson_8d873e4e2f73` records one
identical-prompt probe: Cline answered four tasks and was faster on each; Wanda matched the format
on three and returned a `second_largest` function that stopped mid-line. That is one probe of
four tasks, not a benchmark.

### 8.3 Live check log

- Models listed live from W&B Inference (read-only, HTTP 200, 24 models): `V4.1-Flash-1017`,
  `V4.1-Flash`, `V4-Flash-0731`, `V4-Pro-0813` and `GLM-5.3-Flash` are present; the bare
  `V4-Flash` id is absent. The Codex CLI lists `gpt-6-astra` and `gpt-6.1-sol`.
- Aliases that break the effort rule and must not be used: `claude-ultra` (default effort `max`)
  and `codex-ultra` (default effort `ultra`).
- First effort probe: `V4.1-Flash-1017` at `medium` returned `error: Invalid request`, no retry.
  This repeated the deterministic 400 already recorded in `lesson_d4ff6f4278ad`; the request was
  avoidable. One of the two approved requests was used.
- The same pass found three validator defects (a fixed-wall owner hidden in a longer name, a crash
  on non-object input, a bare string read as a set of letters), fixed test-first. A later security
  review found the first owner fix incomplete (accents, glued names, Cyrillic look-alikes); it was
  hardened to normalize first, then match substrings, and to refuse non-ASCII names.

### 8.4 Open

Wanda's soul card lists the Cline CLI as forbidden for the W&B route, while `lesson_8d873e4e2f73`
routes W&B DeepSeek through Cline. Which governs is the operator's decision; neither is edited here.

## 9. Pair dogfood, free dry run (2026-11-17)

`tests/test_pair_dogfood.py` runs the pair end to end with no model call, no gate, no arm and no
network. The inner seat makes three recorded attempts that revert, Scout reports a fourth on its own
seat (`inner-scout`), and all four carry distinct attempt ids and the same pinned evaluator digest.
Biafra reads the ledger, `stall_report` names a three-revert stall, her outer cycle keeps a better
metric, and a Mechanism Card candidate citing the stalled entry ids validates with no errors. The
evaluator digest is unchanged afterwards, and an outer-seat attempt on a test path is refused as
`verifier-protected`. A second cycle in the same directory is refused as `already-ran` with zero
retries. This proves the contracts and seat boundaries. It does not prove that a model proposes a
good search rule; that needs a live cycle, which needs the operator gate, a named budget and a
same-day provider re-probe.

The first version of this dogfood surfaced no new defect. The eight review defects it depends on
(Scout's seat id, constant attempt ids, silent no-trace default, marker claimed before validation,
metric guard, digest pinning, card consistency, owner and field checks) were fixed first, test-first.

## 10. First real-world live pair turn (2026-11-17)

After the operator pointed out that live turns exist to test real-world situations, the loop was
aimed at the four real CodeRabbit comments on pull request 519 instead of an invented corpus. The
inner seat fixed comment 2, the outer seat triaged comments 3 and 4 and proposed a rule, and the
useful parts were incorporated after vetting. Details, the vetting table and the saved ledger and
card are in `docs/v2/references/biafra/live-cycle-2026-11-17/`.

Request accounting, stated plainly: two requests earlier in the day (the first failed on a known
400, the second produced the review), possibly one cut-off request from a synthetic first attempt
that was stopped (its marker existed), and two in the real loop. The operator approved one live
pair loop; the cut-off attempt is the only count that is uncertain.

## 11. Turns 2 and 3, the sandbox and the runbook (2026-11-17)

Two further real turns ran on defects the first turn exposed. The inner seat fixed a sentence being
accepted as `owner_slices` (turn 2) and degenerate identifiers such as `a/../b` (turn 3b); turn 3
was reverted because the prompt did not show a helper's return type, and the prompt now includes
helper source. A side agent and an automated security review found that candidates were scored
on the operator's machine with the provider key in the scorer's environment, guarded only by a name
denylist. `bin/agents/sandbox_run.py` now provides a scrubbed environment, a deny-by-default
kernel sandbox, an allowlist vet and refusal of broad read roots, with tests for each denial. The
interim runbook is `bin/orama-system/skills/metaresearcher/references/live-pair-loop-runbook.md`.
Request count for the real loop: eight, plus two review requests and one cut-off attempt earlier.

## 12. Billing basis and the shared spend guard (2026-11-17, corrected)

A side agent noted the live requests had been called free-tier without checking billing. The
official documentation was read: Free-plan inference stops when its allowance is used up until
pay-as-you-go is activated, billing is monthly and only after activation, and limits that apply
are concurrency (`429`) and location (`403`). A `402` has two causes: the allowance is used up
while pay-as-you-go is inactive, or the spending cap was reached. An earlier version of this
section said only that the cap was reached; CodeRabbit caught that, and it is corrected here.

"Free with no payment method charged" is not enough, because a Free account can have pay-as-you-go
active without a card yet charged. The operator must attest that the plan is Free, pay-as-you-go
is inactive and allowance remains (`python3 -m orchestrator.provider_limits attest ...`, operator
only, valid seven days); without it the guard refuses every live request.

The guard is shared. Perpetua-Tools, the runtime and state authority, owns the logic: the provider
policy (`config/provider-policies/wandb-inference.json`, official references that `python3 -m
orchestrator.provider_limits verify wandb-inference` re-checks live), `CostGuard` in monthly mode,
the classifier for 402 and 429, and the corrected `_call_wandb` (no SDK retries). Orama uses it
through `bin/agents/spend_guard.py` and `PERPETUA_TOOLS_ROOT`, and adds no spend logic of its own.
Full text and the stop rules are in the runbook,
`bin/orama-system/skills/metaresearcher/references/live-pair-loop-runbook.md`, under Billing
basis. The Billing page is the only place the plan state can be confirmed, and an agent cannot
open it.
