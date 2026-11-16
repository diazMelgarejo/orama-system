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
| G3 | The evaluator digest is computed by `evaluator_digest()` but nothing yet pins it at run start. | Open. Needs a place the operator or gate writes it. Proposal, not decided. |
| G4 | Stall window defaults to 3 consecutive reverts. | Operator to confirm or change. |
| G5 | The 2026-06-05 rule that `oramasys/*` is reference-only versus later direct PRs there. | Not touched here; no `oramasys/*` repository is mutated. |
| G6 | Persona elaboration beyond the operator's wording. | Draft, for review. One boundary was added: Biafra questions the work's assumptions and does not diagnose the person. |
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
