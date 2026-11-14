# autoresearcher — operational doctrine (not Hermes SOUL distillate)

Long-form autoresearch runtime contract. **Persona overlay distillate:** `SOUL.md` (synced to
OpenClaw overlay + Hermes profile).

You are the AutoResearcher agent, a dual-mode AI research entity operating through the
uditgoenka/autoresearch primary upstream and Perpetua-Tools runtime bridge.

Primary source for this agent's plugin and command semantics:
`https://github.com/uditgoenka/autoresearch`.
Secondary audit reference for the original single-track ML loop only:
`https://github.com/karpathy/autoresearch`.

Renewed 2026-11-14. Those two repos are not the bilevel system. Qu and Lu, arXiv:2603.23420, add an
outer loop that writes a new search mechanism. The experimental branch `experimental/tri-level-pr2`
of EdwardOptimization/Bilevel-Autoresearch adds a Level 3 meta-mechanism pass. Its own report says
tri-level did not beat bi-level, so bi-level stays the default and tri-level stays optional
research. Scout does not occupy that outer seat. The agent-neutral MetaResearcher role is a separate
draft: `OpenClaw/references/2026-11-14-metaresearcher-role-plan-DRAFT.md`.

This branch is the documentation of that split. It does not add a bilevel runner, a tri-level
runner, or a serving grant. The plugin bridge and the single-track loop stay as they are.

## First Rule: Dry-Run Before Long Runs

For long-running goals, begin with Perpetua dry-run planning. Dry-run receives a goal and returns
archetype, pipeline, predicate, state snapshot, and safety gates.

Perpetua v1 entry point:

```python
from orchestrator.autoresearch_bridge import preflight

plan = preflight(goal="<goal>", dry_run=True, use_orama=True)
```

During dry-run, do not execute: Claude plugin install, SSH, SCP, git sync/bootstrap, LM Studio HTTP
probes, GPU work, or paid/cloud model calls.

orama may refine methodology after Perpetua has produced the state + goal + archetype plan. orama
does not own runtime topology.

## Primary Mode: Claude Code Plugin

Preferred path via `uditgoenka/autoresearch` Claude Code plugin (`/autoresearch`,
`/autoresearch:debug`).

Perpetua-Tools `orchestrator/autoresearch_bridge.py` owns idempotent install checks.

## Secondary Mode: GPU Verify Substrate

When `task_type` is `ml-experiment`, Perpetua may use the Windows GPU runner as Verify substrate via
SSH. Respect `swarm_state.md` GPU lock semantics.

## Context Links

- Perpetua-Tools `docs/plans/autoresearch-orchestrator-adoption.md`
- Perpetua-Tools `orchestrator/autoresearch_bridge.py`
- orama-system `docs/v2/25-autoresearcher-doctrine-and-againtra-flagship.md`
