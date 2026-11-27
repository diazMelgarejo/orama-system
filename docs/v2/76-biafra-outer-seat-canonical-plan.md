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
| Effort and models | Two tiers, both explicit. **Preferred, human-gated:** Biafra (MetaResearcher) on Claude Fable 5.2 high or GPT-6.2 Astra high; the AutoResearcher seat on Claude Opus 5.5 medium or GPT-6.2 Sol medium. These stay preferred as planned and run only after explicit human approval before execution. **Default, automatic:** the standing rule, medium, else high, else low, never xhigh or max, runs on free W&B turns with no human approval and is the fallback whenever no paid permission has been granted. Clarified 2026-11-17; an earlier version of this row said the draft's table was superseded, which was wrong. Updated 2026-11-25 by operator ruling: the durable OpenAI pair is GPT-6.2 Astra high (outer) and GPT-6.2 Sol medium (inner), subject to change when OpenAI updates its frontier models; GPT-6.2 Astra and Sol were first publicly available on 2026-11-17 (see the paired offline review reference for sources). |
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
| G3 | The evaluator digest is computed by `evaluator_digest()`, and `validate_mechanism_card` did not compare a card's digest with its dry-run receipt. Accepted before this change: (1) a graduated card whose receipt has no `trace`; (2) a graduated card whose receipt `trace.evaluator_digest` differs from the card's; (3) a graduated card whose digest was never pinned by anything. | Resolved 2026-11-17, decided by the operator's request in this change. The digest covers exactly the verifier files given to `evaluator_digest(paths)`, bound by file name and bytes. `pin_evaluator(pin_path, verifier_paths)` (operator or gate, at run start) writes `{version, evaluator_digest, covers}` once with exclusive create and, if the pin exists, returns it only when the recomputed digest and covered names are identical, else `ValueError`; `read_pin` validates and returns the digest. `validate_mechanism_card(card, pinned_digest=None)`: reviewed and graduated need a receipt `trace` that is a valid trace entry whose `evaluator_digest` equals the card's and whose `metric_after - metric_before` equals the card's `delta` (tolerance 1e-9); graduated requires `pinned_digest`; a given `pinned_digest` must equal the card's digest. All three cases are refused. |
| G4 | Stall window defaults to 3 consecutive reverts. | Operator to confirm or change. |
| G5 | The 2026-06-05 rule that `oramasys/*` is reference-only versus later direct PRs there. | Not touched here; no `oramasys/*` repository is mutated. |
| G6 | Persona elaboration beyond the operator's wording. | Draft, for review. One boundary was added: Biafra questions the work's assumptions and does not diagnose the person. Later decision (2026-11-23): accepted as written; see section 15. |
| G8 | `_finite` accepts integers up to about 1.8e308, including the band above 2**53 where conversion to float loses precision. A transport that serialises the raw integer (JSON can carry 10**400) may accept a value this validator refuses. | Assumption recorded; the docstring states it. Operator to confirm that every consumer computes in doubles. |
| G9 | The fixed-wall card check runs only when a caller passes `mechanism_card`. A caller that omits it is not checked. | Resolved 2026-11-17, decided by the operator's request in this change: no card, no promotion. Cycles stay usable without a card, because a proposal turn produces the card afterwards, and report `card_checked: false`. When a valid card is passed, `dry_cycle` and `live_cycle` results also carry `card_id` (`<mechanism_id>@<revision>`). A reviewed or graduated card needs a receipt with `card_checked: true` and a `card_id` equal to its own, so promotion follows a dry run that checked this card, fixed walls included. `dry_cycle` receives measured values; the proposing agent must call `validate_mechanism_card` before measuring. |
| G7 | Provider state for the live cycle (W&B model order and effort acceptance, BigModel balance) was last seen on 2026-11-12. | Must be re-probed before arming. |

Note (2026-11-17, section 13): an independent review led to an addition to the G3 binding, now
implemented and tested: a receipt is also compared with the card's `delta` (the trace's
`metric_after - metric_before`), so a receipt for `X@1` cannot promote a card reusing that id
with a different delta. At that revision the receipt bound identity, evaluator digest and delta,
but did not bind `owner_slices`, `targets`, `hypothesis` or metric names. This section records the
decision at that time; consult the current validator for the current binding.

Review follow-up (2026-11-21): new card-bearing dry receipts also bind a SHA-256
fingerprint of canonical card content. Only `status`, `reverted` and the receipt
itself are excluded; the trace decision separately binds `reverted`. Run and
card evaluator digests must agree, and graduated cards need an independently
recorded pin. Existing unbound receipts must be regenerated before promotion.
This is content binding, not proof that the caller performed the measurement;
the proposing agent still validates the card before measuring.

## 5. Live cycle (one, bounded, not armed by this change)

Preconditions, all required: the operator names provider, budget, request limit and deadline (given
as W&B free-first, 2 requests, no paid credits); the model order and effort acceptance are re-probed
the same day; the evaluator digest is pinned with `pin_evaluator` before the cycle;
`BIAFRA_ORCHESTRATOR_GATE=approved` and `BIAFRA_ALLOW_LAUNCH=1` are set by the operator for that one
run and unset afterwards. Stop and report,
without retry, if the provider needs paid credit, rejects the requested effort, or the marker file
already exists. The result is data until a non-maker reviews it.

Note (2026-11-17, after the lockstep remediation, section 13): the live cycle does not read the pin
itself yet, so the operator or gate must call `pin_evaluator` first; and the spend gate refuses the
launch without a fresh attestation or with an exhausted budget, holding the reservation for the
launcher timeout plus a settle margin.

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
| Model order | `deepseek-ai/DeepSeek-V4.1-Flash-1017`, then `deepseek-ai/DeepSeek-V4.1-Flash`, then `deepseek-ai/DeepSeek-V4-Flash-0731` | [launcher](../../bin/orama-system/skills/cline-wandb/scripts/launch_cline_wandb.py), [stale-reference ledger](../stale-reference-ledger-2026-11-12.md) |
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
Later decision (2026-11-23): the route is split by role; see section 15.

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

## 13. Lockstep remediation (2026-11-17) dispositions

> Numbering note: the request called this section 10, but sections 10 to 12 already exist and are
> historical, so it is section 13. Nothing earlier is renumbered.

Perpetua-Tools (PT, producer and state authority) PR #516 and orama-system (stateless consumer)
PR #519, both on branch `2026-11-17-001-biafra-seat-canonical`, were reviewed in the "2026-11-17
Restack Review": request changes, seven findings (P1: 1 and 2; P2: 3 to 7), with G3 and G9 called
out as open design gaps. The record of inputs, commit subjects, verification and both independent
review verdicts is
[`references/biafra/lockstep-remediation-2026-11-17.md`](references/biafra/lockstep-remediation-2026-11-17.md).

### 13.1 Dispositions

| Item | Disposition | Owning repo and module |
| --- | --- | --- |
| Finding 1 (P1) | Fixed. The PT W&B path refuses before dispatch on a missing or stale attestation or an exhausted budget, settles on success, and settles the full reservation after a possibly sent failure. | PT: `orchestrator/spend_gate.py`, `.agent/harness/llm.py` |
| Finding 2 (P1) | Fixed. `CostGuard` is shared and atomic across instances and processes that use one budget file: one private SQLite store, every operation in BEGIN IMMEDIATE. | PT: `orchestrator/cost_guard.py` (`CostGuard`), `orchestrator/private_sqlite.py` |
| Finding 3 (P2) | Fixed. Declared holds `reserve(cost, hold_seconds)`; a late commit for a swept reservation still records the spend (`late_commit`). Orama's live cycle holds for `timeout_s` plus `SETTLE_MARGIN_S`. | PT: `orchestrator/spend_gate.py`; orama: `bin/agents/biafra_cycle.py` |
| Finding 4 (P2) | Fixed. A decode failure after the launcher ran no longer looks like an unsent request: the launcher is started with Popen and awaited with `communicate`, output is decoded afterwards with `errors="replace"`, only a failed Popen releases, and a timeout, pipe error or interrupt settles the full reservation (unavailable output is not evidence of zero billed output). | orama: `bin/agents/biafra_cycle.py` |
| Finding 5 (P2) | Fixed. The leader is never reaped before the process group is signalled; cleanup is armed right after Popen; the exit probe order is `waitid`, `kqueue`, `/proc`, else fail closed. | orama: `bin/agents/sandbox_run.py` |
| Finding 6 (P2) | Fixed by additive memory records: `lesson_d4ac6209ce38` supersedes `lesson_762380426dc7`; `lesson_7240bbe31030` supersedes the original over-claim `lesson_15733a3316ad`. | PT: memory records |
| Finding 7 (P2) | Fixed. The runbook's attest command no longer shows `--confirm`; the operator types the phrase at the interactive prompt. | orama: `live-pair-loop-runbook.md` |
| G3 | Resolved (section 4): evaluator pin and receipt binding; the receipt's `delta` is also compared (decision 13 below). | orama: `bin/agents/seat_contracts.py` |
| G9 | Resolved (section 4): no card, no promotion. | orama: `bin/agents/seat_contracts.py`, `bin/agents/biafra_cycle.py` |

Two further changes are recorded without a finding number: the live cycle's abnormal-exit and
reservation handling (decisions 5, 11 and 12) and the sandbox cleanup (decisions 6 and 15), both in
orama.

### 13.2 Decisions

| # | Decision | Rationale |
| --- | --- | --- |
| 1 | G3: `pin_evaluator` writes a one-time pin at run start (exclusive create; re-pin only for the same digest and covers, else "evaluator changed"); `read_pin` validates shape; a reviewed or graduated card needs a receipt `trace` carrying its digest; graduated also needs `pinned_digest`. | Closes the three accepted G3 cases. |
| 2 | G9: cycles stay usable without a card; a validated card adds `card_id = "<mechanism_id>@<revision>"`; a reviewed or graduated card needs a receipt with `card_checked: true` and its own `card_id`. Reversible. | A mandatory input card would break the real flow, because the outer dry run produces the receipt the card is built from. |
| 3 | One spend gate owned by PT: `SpendGate` (preflight, settle, settle_unknown, release, classify, snapshot); shared atomic `CostGuard`; private-file checks extracted to `orchestrator/private_sqlite.py`; legacy budget JSON imported once and renamed `<name>.migrated`, and a missing store beside a `.migrated` file fails closed; orama's `spend_guard.py` is a thin forwarder with no ledger. | PT is the runtime and state authority; orama adds no ledger. |
| 4 | W&B outcome mapping: an HTTP status below 500 is a definitive refusal and releases; 5xx, transport errors, timeouts, interrupts and malformed responses settle the full reservation; if settle fails after a paid answer, the answer is kept and the charge falls back to `settle_unknown`. | The first design charged every HTTP error; unavailable output is not evidence of zero billed output. |
| 5 | Live cycle: hold = `timeout_s` + `SETTLE_MARGIN_S` (120 s); launcher started with Popen and awaited with `communicate`; only a failed Popen releases; output decoded afterwards with `errors="replace"`. | A running launch must never be swept; a bad byte must not make a spent request look unsent. |
| 6 | Sandbox cleanup: never reap the leader before signalling the group; cleanup armed right after Popen; exit probe order `waitid`, kqueue, `/proc`, else fail closed (`SandboxUnavailable`). A per-poll `ps` probe was rejected. | Cost; CPython exposes `os.waitid` on macOS only from 3.13, so older macOS Pythons use kqueue. |
| 7 | Memory correction by additive records. Accurate wording: a same-user process can write a valid attestation file; the guard checks contents and age and cannot prove who wrote it; only the interactive `attest` command asks a human. | The original wording over-claimed. |
| 8 | Runbook: the attest command no longer shows `--confirm`. | The parser has no such argument. |
| 9 | Memory changes ship in PR #516 although accepted `lesson_94a6ff5363ae` says PT memory commits belong on main only. Flagged to the operator. | The defect was introduced there. |
| 10 | Publish order: push PT once, set orama `.github/pt-dispatch-test-ref` to the pushed PT head, push orama once; no merges; reply on the open PT thread with the fixing commit; update PT #516's description. | Orama pins PT; #516 now changes runtime and budget code, not only docs. |
| 11 | Implemented and tested: the live-cycle launcher starts with `start_new_session=True`; on timeout, pipe error or interrupt the whole group is SIGKILLed before a bounded reap. | A grandchild holding the pipes cannot hang the cycle past `timeout_s`. |
| 12 | Implemented and tested: after Popen succeeds the request counts as sent; the `finally` never releases a sent reservation; if settling fails after send, the reservation is left to its declared hold and the error is surfaced. | A sent request is never recorded as zero spend. |
| 13 | Implemented and tested: receipt binding also compares the card's `delta` with the trace's `metric_after - metric_before` (float-rounding tolerance). | A receipt for `X@1` must not promote a different card that reuses the id `X@1`. |
| 14 | Implemented and tested: `pin_evaluator` uses a unique temp file (`mkstemp` in the pin's directory). | Concurrent pinning in one process cannot collide. |
| 15 | Implemented and tested: the sandbox checks that an exit probe exists before starting the child. | A platform with no probe fails closed before any model-written code runs. |

Decisions 11 to 15 came from the independent orama review (request changes). All five are
implemented with failing-first tests on PR #519's branch (affected suites: 428 passed, 18 skipped
macOS-only); the PR is not merged.

### 13.3 Operator-facing behaviour changes

- `CostGuard`'s default store fails closed when its directory or an ancestor fails the private-store
  checks. Previously it degraded to an in-memory budget.
- Spend recorded after migration lives only in the SQLite store; reverting does not move it back.
- The 600 s openai client timeout is per HTTP phase, not a total deadline. A request can outlive the
  900 s hold; the late commit still records the spend.
- Live-cycle precondition (section 5): the evaluator pin is recorded with `pin_evaluator` before the
  cycle, and graduating a card needs it. The live cycle does not itself read the pin yet (see
  Later TODOs). The spend gate refuses the launch on a missing or stale attestation or an exhausted
  budget, and the reservation is held for the launcher timeout plus the settle margin.
- The runbook's attest command is run without `--confirm`; the operator types the phrase.

### 13.4 Publication state

Both PRs are open and not merged. The operator believed them merged, but their heads were still
the reviewed `c90feebb` (PT #516) and `bd5931a2` (orama #519); no merge was made. Lockstep order:
push PT once, set orama's `.github/pt-dispatch-test-ref` to the pushed PT head, push orama once;
reply to the open PT thread with the fixing commit; update PT #516's description. Nothing is
armed: live gates and serving stay off. By the operator's ruling, every change from this
remediation, memory included, is consolidated on these two PRs; no new PR is opened.

### 13.5 Later TODOs

From the remediation source (not done; owner decisions or follow-up work):

- Native macOS verification of the kqueue probe and the 18 macOS-only sandbox tests; Windows was not
  exercised.
- The live cycle reads no pin itself. Enforcing `read_pin` inside `live_cycle` before launch is a
  follow-up (graduation already requires the pin).
- `lesson_371473e17ad0` remains accepted as a redundant shorter correction (its `supersedes` holds
  one id).
- Generic filler docstrings ("Test helper or fixture: ...") in older test helpers could be
  rewritten.
- A hard wall-clock deadline for the W&B request instead of the per-phase timeout.
- `AGENT_PROVIDER=openai` with `OPENAI_BASE_URL` pointed at W&B bypasses the gate (operator
  environment); route or refuse it.
- Decide whether PR-carried memory is acceptable versus `lesson_94a6ff5363ae`.
- Live gates and serving stay off; arming one bounded live cycle remains a separate operator act.

Still open in this document, unchanged by this remediation: G1 (Anamnesis ledger), G2 (Kungfu),
G4 (stall window), G6 (persona draft), G7 (re-probe provider state before arming), G8 (`_finite`
integer precision), G10 (metric registry) and G11 (Wanda's soul card versus the Cline W&B route,
see 8.4). Tri-level stays off.

## 14. Open-gap source continuation (2026-11-17)

The current implementation request continues the source work without claiming
new operator ratification. The
[implementation receipt](references/biafra/open-gaps-implementation-2026-11-17.md)
records the migration, caller compatibility and residual gates. Sections 4 and
13 retain their historical cutoff; the following dispositions supersede only
their statements about these source gaps.

| Gap | Current disposition |
| --- | --- |
| G1 | Still dependency-blocked on provisioned Anamnesis; no replacement Orama ledger. |
| G2 | Still dependency-blocked on published Kungfu atoms and evaluable O1–O3. |
| G4 | Existing three-revert behavior retained as `STALL_WINDOW`; not new policy ratification. |
| G6 | Persona remains a draft; no agent has accepted it for the operator. |
| G7 | Live preflight now requires same-day local probe evidence and matching evaluator pin before reservation or marker; an actual provider re-probe remains an operator prerequisite. |
| G8 | Source guard rejects integers beyond ±2**53 without requiring the unverified all-consumers-double assumption. |
| G10 | One declared metric registry governs cards, trace entries and cycles; existing `metric` default remains declared for compatibility. |
| G11 | Still an operator choice; conflicting Wanda and PT records remain preserved. |

The live-cycle pin TODO is implemented. The generic OpenAI W&B bypass now
refuses before SDK construction. PT bounds the W&B SDK request in a killable
worker with parent-owned spending; process creation and bounded cleanup limits
are documented rather than represented as hard real-time guarantees.
Armed legacy `run_program` refuses: live callers must use the governed interface.
Nothing here arms a cycle, enables serving, approves a paid model, qualifies a
host or authorizes a merge. Publication remains held for the existing PR pair.

**2026-11-20 update:** the user released the publication hold for existing
PT #516 and Orama #519, with logical commits and one push per repository.
The [deferred-failure catalogue](references/biafra/unrelated-failure-catalogue-2026-11-20.md)
classifies every recorded unrelated failure and warning, with baseline evidence
and owner-specific next steps. Publication does not waive the seven current
baseline-reproducible failures, close G1/G2/G6/G11 or authorize a merge.

## 15. Operator rulings on G6 and G11 (2026-11-23)

The operator ruled on both gaps on 2026-11-23. These are later decisions: sections 4, 8.4, 13 and
14 keep their historical wording, and where they call G6 or G11 open, this section applies.

| Gap | Ruling |
| --- | --- |
| G6 | The outer-seat persona in `bin/agents/metaresearch-outer/SOUL.md` is accepted as written, including the added boundary: Biafra questions the work's assumptions and does not diagnose the person. |
| G11 | The W&B route is split by role. Wanda keeps the OpenAI client and Weave, and her soul card stands. The Biafra seats are designated to use Cline through `launch_cline_wandb.py` (`lesson_8d873e4e2f73`) under the shared spend gate, once the launcher can bound total output and request count. |

Neither earlier record is invalid. The soul card's prohibition binds Wanda, and the lesson
describes the Biafra route. Wanda's soul card states that scope.

**What runs today (historical — 2026-11-23, superseded by 2026-11-27 closure below).**
`live_cycle()` refuses with `launcher-output-bound-unsupported`. The legacy `run_program` path
refuses with `legacy-live-path-disabled` **only when armed** (`launch_allowed()` returns true);
when the gate and arm variables are unset, `run_program()` calls `dry_cycle()` and sets
`called_launcher=False` instead. Neither path launches Cline. The launcher has no spend gate
of its own, so any Cline caller must go through `bin/agents/spend_guard.py`, as the live cycle
is designed to. Wanda's W&B calls are made directly with the OpenAI client by
`bin/orama-system/skills/wanda-wandb/scripts/wanda_chat.py`. That client stays outside the
spend gate in this change and is not an authorized unattended or paid path. The "generic OpenAI
route refuses W&B" rule in section 14 belongs to Perpetua-Tools' `.agent/harness/llm.py`, a
different consumer, so it does not conflict with Wanda's path.
`tests/test_biafra_designation_docs.py` keeps this wording tied to the launcher's refusal.
The Perpetua-Tools record is its `DECISIONS.md` entries of 2026-11-23, with a correction of the
same date.

Nothing here arms a live cycle, enables serving, approves a paid model or authorizes a merge. G1
and G2 stay dependency-blocked, and arming one bounded live cycle remains a separate operator act.

### 15.1 Bounded-launcher contract checkpoint (2026-11-26, superseded by 2026-11-27 closure below)

This is an additive Lane 1B status note. The 2026-11-23 ruling and the historical sections stand;
**implementation is incomplete**, and "bounded-capable" remains an acceptance gate rather than a
claim about the route today.

The governed Biafra Cline contract requires all of the following:

- A finite, positive `--max-requests` and a finite, positive `--max-total-output` must both be
  supplied. Missing, malformed, non-finite or non-positive bounds must refuse before dispatch and
  before any spend-gate reservation.
- Request-count and cumulative-output accounting must enforce both caps and terminate or refuse
  fail-closed when either cap would be exceeded. Once a request may have been sent, its reservation
  must settle as unknown spend; it must never be silently released.
- `live_cycle()` must validate and pass both bounds before reservation, and
  `_launcher_boundary_problem()` may return `None` only when both bounds are verified active.
- The legacy path stays fail-closed: armed `run_program()` returns
  `legacy-live-path-disabled` without launching; unarmed `run_program()` remains a dry cycle with
  `called_launcher=False`.
- Wanda's Cline CLI prohibition remains intact and scoped to her W&B route. It does not grant
  Wanda a bounded-launcher exception.

The launcher requires positive integer values and forwards both flags, and `live_cycle()` passes them,
but installed-client aggregate output enforcement remains unverified (`BOUND_CONTRACT` remains false).
`_launcher_boundary_problem()` still returns `launcher-output-bound-unsupported`, so neither live
path dispatches Cline. Implementation is incomplete: the route remains a designation, not
bounded-capable. The remaining gate is proof of client-level request-count and cumulative-output
termination, before any spend-gate reservation, followed by client qualification and boundary lift.
No live activation is authorized.

**2026-11-27 Phase 1B BOUND_CONTRACT closure update.** Launcher-side boundary enforcement is
implemented in `launch_cline_wandb.py` via a stdlib loopback HTTP accounting proxy:

- `POST` requests whose parsed URL path (ignoring query strings) ends in `/chat/completions` are
  authenticated via a per-launch random session token, serialized, and counted; all other `POST` routes
  are refused with HTTP `403`.
- Before forwarding each `/chat/completions` request, the proxy clamps `max_tokens` (and
  `max_completion_tokens`, if present) to the remaining output budget and injects
  `stream_options: {"include_usage": true}` for streaming calls.
- Every forwarded chat request ends in exactly one classified outcome: `ACCOUNTED` (verified
  `usage.completion_tokens`), `REJECTED` (definitive rejection status code in
  `{400, 401, 403, 404, 405, 413, 415, 422}` proving 0 output tokens generated), or `UNACCOUNTED`.
  An `UNACCOUNTED` outcome debits the full clamped reservation, records a boundary breach, terminates
  the child fail-closed, and exits `124`.
- The launcher terminates fail-closed with exit code `124` (and `live_cycle()` settles via
  `_settle_unknown`) whenever `request_count > max_requests`, `remaining_tokens <= 0` when the
  next chat completion arrives, cumulative `usage.completion_tokens > max_total_output`, a chat request
  results in `UNACCOUNTED` spend (including missing usage, non-definitive upstream errors, or upstream
  transport/read errors on chat completions), or admitted in-flight handlers fail to drain within the
  bounded shutdown window (transport/read errors on non-chat routes return HTTP 502/504 without recording
  a boundary error or triggering exit 124).
- On shutdown, `stop_and_drain()` moves the proxy lifecycle `RUNNING -> DRAINING` and waits for admitted
  handlers. It has two distinct outcomes: if every admitted handler finishes before the deadline it
  returns `True` and the phase stays `DRAINING` (the normal completion state); only if the deadline
  passes does the phase become `CLOSED` under lock (timeout-only) and the launcher exits `124`. `CLOSED`
  fences every upstream dispatch, chat and non-chat, so a late worker cannot start a new request.
- Offline harness tests in `tests/test_launch_cline_wandb.py` and `tests/test_launch_cline_wandb_lifecycle.py`
  verify that exceeding bounds triggers fail-closed termination.

`BOUND_CONTRACT` is verified and flipped to `{"max_requests": True, "max_total_output": True}`,
allowing `_launcher_boundary_problem()` to return `None` for valid positive bounds while continuing
to refuse missing or non-positive bounds with `invalid-launcher-bounds`. The Biafra Cline route is
now bounded-capable. The legacy path stays fail-closed (`legacy-live-path-disabled`), Wanda's soul
card prohibition remains intact and scoped to her W&B route, and no live cycle is armed.
