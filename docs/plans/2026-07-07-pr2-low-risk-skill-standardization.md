# PR 2 — Low-Risk Skill Standardization Initial Input

Date: 2026-07-07
Branch: `skillify-pr2-low-risk-skills`
Base: `main` after PR #141 squash merge
Scope: PR 2 from the merged skill upgrade roadmap, with ADR-045 added as Planning Gstack input

## Original PR 2 purpose

Upgrade the low-risk skills identified by PR 1 without changing high-risk execution behavior.

Target skills, in the revised priority order:

- `bin/orama-system/gstack/SKILL.md` — first priority for Planning Gstack alignment
- `bin/orama-system/skills/first-run-setup/SKILL.md`
- `bin/orama-system/skills/shell-hygiene/SKILL.md`

This PR should reduce validator warnings for the target skills, improve metadata precision, and preserve or improve existing operational guidance. It should not touch high-risk execution skills, MCP dispatch, OpenClaw/Hermes execution paths, or canonical skill-source roots.

## Oramasys AutoPlan gate

AFRP classification:

```text
AFRP: Type C | Level Expert | Mode 2
Scope: PR 2 planning and low-risk skill standardization
```

AutoPlan decision: proceed as a draft PR, but keep the work planning-first until the three target skills are patched and validated.

Review model applied:

- CEO review: keep the PR small and start with Planning Gstack because it sets the routing surface for later ADR-045 rollout.
- Engineering review: link to ADR-045 as the source of truth instead of duplicating its framework in every skill.
- DX review: make the next agent path obvious: gstack for planning, first-run for bootstrap, shell-hygiene for shell discipline.
- Final gate: repo docs remain source of truth; any Margin page is a review projection only.

Security alignment from `SECURITY.md`:

- keep stacked PR discipline,
- keep this as one logical workstream,
- preserve prior security records and plan context additively,
- maintain safe defaults and explicit boundaries,
- avoid introducing new sensitive examples or runtime artifacts.

## ADR-045 alignment

ADR-045 Phase 1 completed the foundation for gstack, gbrain, and CRG error resilience. It defines the shared safe-default framework, implementation guide, diagnostics convention, and Phase 2 rollout target list.

PR 2 should now start with Planning Gstack because gstack is the routing and planning surface that can point later skill updates toward the ADR-045 framework without duplicating it.

Relevant ADR-045 Phase 2 inputs:

- priority rollout includes gstack routing and `first-run-setup`,
- skills should route to the shared resilience framework instead of inventing local variants,
- verification should consider happy path, offline, lock, and timeout cases where applicable,
- the implementation guide is the source of truth for applying the shared framework.

## Roadmap requirements

| Skill | Metadata moves |
|---|---|
| `gstack` | `when_to_use`, `effort: medium`, Planning Gstack priority, ADR-045 routing alignment |
| `first-run-setup` | explicit invocation, argument hint, arguments, bounded system-state checks, ADR-045 bootstrap routing |
| `shell-hygiene` | `when_to_use`, `effort: low`, `paths` for shell-relevant files, portable script references |

## Current inventory

### `gstack`

- Has long `description` with trigger phrases embedded.
- Body is under the hard ceiling but above the preferred compact target.
- Contains many hard-won operational details; do not delete them.
- Should reference ADR-045 as the shared source for gstack/gbrain/CRG resilience instead of re-implementing the framework locally.

### `first-run-setup`

- Has `name` and `description` only.
- Body is compact and idempotent.
- Because it can invoke install/config scripts, it should become explicit-invocation only.
- MCP-specific work should route to `mcp-install`.
- Should point bootstrap hardening toward ADR-045 rather than duplicating policy.

### `shell-hygiene`

- Has `name` and a long `description`.
- Lacks separate `when_to_use`, `effort`, and `paths`.
- Body is compact and useful; preserve the no-sleep-chain and zsh word-splitting rules.
- Should stay focused on shell execution hygiene, not ADR-045 ownership.

## Execution plan

1. Patch `gstack` first with Planning Gstack and ADR-045 Phase 1/2 alignment.
2. Patch `first-run-setup` second, keeping install actions explicit and routing bootstrap hardening to ADR-045.
3. Patch `shell-hygiene` third, keeping it compact and focused.
4. Run the skill validator baseline against the three touched roots.
5. Run the validator unit tests.
6. Open the PR with this original purpose preserved at the top and later changes appended below.

## Non-goals

- Do not touch `mcp-orchestration`.
- Do not touch `hermes-harness`.
- Do not change MCP runtime dispatch behavior.
- Do not change OpenClaw/Hermes execution paths.
- Do not move canonical skill sources into non-orama roots.
- Do not delete or compress existing gstack operational knowledge without an equivalent canonical reference.
- Do not duplicate ADR-045 inside every skill; link to it as the canonical source.

## Margin projection note

This repo document is the source of truth. A Margin page, if published later, is only a review projection. Fold any Margin comments back into this file or the PR body before approval.

## Append-only update log

### 2026-07-07 — ADR-045 added to PR 2 scope

Planning Gstack is now the first PR 2 priority. The pass should align with ADR-045 Phase 1 foundation and Phase 2 rollout by treating gstack as the routing and planning surface for gstack/gbrain/CRG resilience. `first-run-setup` remains in scope because ADR-045 lists it as a priority bootstrap skill; `shell-hygiene` remains in scope as a low-risk shell convention cleanup, but it is no longer the first edit.

### 2026-07-07 — oramasys AutoPlan and SECURITY.md alignment added

Applied the oramasys AutoPlan gate to PR 2. The plan now records AFRP classification, CEO/engineering/DX review, final-gate framing, and `SECURITY.md` alignment. The next edit remains Planning Gstack first, with ADR-045 as the canonical resilience source and Margin treated only as a projection.
