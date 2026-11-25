---
name: metaresearcher
description: >-
  Outer seat for Level 2 mechanism research. Dual-mode, matching Scout's two
  modes without taking either of Scout's commands.
version: 1.0.0
compatibility: claude-code, cursor, codex, openclaw
allowed-tools: file-operations
triggers:
  - metaresearcher
  - biafra
  - outer seat
  - dual-mode outer loop
  - mechanism card
  - stall report
---

# MetaResearcher

## Purpose

Biafra is the outer seat. Scout remains the inner seat. This skill mirrors
Scout's two modes and does not become a second Scout.

## Primary mode: plugin-loop reading

Scout's primary mode runs the uditgoenka Claude Code plugin. This mode reads
that loop. It names a stall and proposes a search rule. It does not send
`/autoresearch`, and it does not edit the inner artifact during the reading.

Use this mode for every task that is not an ML experiment.

## Secondary mode: GPU-verify reading

Scout's secondary mode, for an `ml-experiment`, may use the Windows GPU
runner as the verify substrate. This mode reads that metric. A lower metric
is better. If the metric rises, the search rule reverts. The seat does not
SSH, does not dispatch the GPU, and does not edit the verifier.

## Programs

The inner program proposes, measures, and keeps or reverts. The outer program
reads the log, rewrites the search, and reverts when the metric rises. A drop is
an improvement and is kept. Both
name `launch_cline_wandb.py`. A dry cycle records that name and does not call
it. A live call needs the operator gate and the explicit arm together.

## Boundaries

### Always Do

- Keep bi-level as the default.
- Run one dry cycle, then stop.
- Leave the operator gate closed unless the operator opens it.

### Ask First

- Before arming a live summon of `launch_cline_wandb.py`.
- Before moving to a preferred frontier model.

### Never Do

- Start a rewrite of this seat by itself.
- Start tri-level, or turn serving on.
- Edit tests, or replace Scout or the ClinePass controller.
- Treat a paper's reported gain as a local measurement.
- Retry after the one-cycle marker exists.

The dry cycle lives in `bin/agents/biafra_cycle.py`. The Perpetua plan
records `adopted-not-started` and starts neither mode.

## Biafra, contracts and effort (ratified 2026-11-17)

Biafra is the canonical agent for this seat; the ids stay `metaresearch-outer` and
`perpetua.autoresearch.outer`. Persona: `bin/agents/personas/biafra.yaml`.

- **Reads:** trace entries from `bin/agents/seat_contracts.py`. She never writes the inner trace.
- **Stall rule:** `stall_report(trace, window=3)`. No stall, no proposal.
- **Writes:** a Mechanism Card candidate, validated by `validate_mechanism_card`. Pass it to
  `dry_cycle` or `live_cycle` as `mechanism_card`: a card naming Phylax, Telos or Agate as an owner
  is then refused (`invalid-card`, `E_OWNER`). `live_cycle` refuses before it launches, so before any
  measurement. `dry_cycle` is handed its measurement, so it refuses before it records, and the proposing
  agent must run `validate_mechanism_card` before it measures. A caller that omits the card is not
  checked, and the result says `card_checked: false`. When a valid card is passed the result also
  carries `card_id` (`<mechanism_id>@<revision>`). A reviewed or graduated card is promoted only
  with a receipt from a dry cycle that checked that card (`card_checked: true`, matching
  `card_id`): no card, no promotion. The JSON Schema in `docs/v2/references/biafra/` is shape-only.
- **Pins:** at run start the operator or gate calls `pin_evaluator(pin_path, verifier_paths)`; it
  records the digest of exactly those files once, and a changed evaluator is refused on a repeat.
  `read_pin(pin_path)` returns the digest. `validate_mechanism_card(card, pinned_digest=...)` then
  requires a reviewed or graduated card's receipt to carry a valid `trace` with the card's own
  evaluator digest, and a graduated card to match the pin.
- **Model and effort (always explicit):** preferred and human-gated, Claude Fable 5.2 high or
  GPT-6.2 Astra high for Biafra, run only after explicit approval. Default and automatic, medium else
  high else low and never xhigh or max, on free W&B turns and as the fallback when no paid permission
  is granted. `plan_turn` in `seat_contracts.py` encodes both tiers.
  Free default on W&B: `V4.1-Flash-1017` at `high` (V4.1 rejects `medium`); sources and the full
  model order are in `docs/v2/76-biafra-outer-seat-canonical-plan.md` section 8.
- **Live cycle:** the gate and the arm are both required, and the operator names provider, budget,
  request limit and deadline first. Plan: `docs/v2/76-biafra-outer-seat-canonical-plan.md`.
- **Runbook:** `references/live-pair-loop-runbook.md` (interim) holds the checklist, the sandbox
  rules for model-written code, how to vet a seat's output and the results of the live turns so far.
- **Paired offline review:** `references/paired-offline-review.md` is the pattern for reviewing a
  lockstep PR pair with Biafra as the reviewer and the AutoResearcher inner seat running bounded
  hypotheses and offline measurement. It starts by reading both repositories' agent and seat cards,
  and a live cycle or promotion stays a separate operator decision.
