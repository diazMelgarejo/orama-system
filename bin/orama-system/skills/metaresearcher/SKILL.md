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
