# PR 2 — Low-Risk Skill Standardization Initial Input

Date: 2026-07-07
Branch: `skillify-pr2-low-risk-skills`
Base: `main` after PR #141 squash merge
Scope: PR 2 from the merged skill upgrade roadmap

## Original PR 2 purpose

Upgrade the low-risk skills identified by PR 1 without changing high-risk execution behavior.

Target skills:

- `bin/orama-system/skills/shell-hygiene/SKILL.md`
- `bin/orama-system/skills/first-run-setup/SKILL.md`
- `bin/orama-system/gstack/SKILL.md`

This PR should reduce validator warnings for the target skills, improve metadata precision, and preserve or improve existing operational guidance. It should not touch high-risk execution skills, MCP dispatch, OpenClaw/Hermes execution paths, or canonical skill-source roots.

## Roadmap requirements

| Skill | Metadata moves |
|---|---|
| `shell-hygiene` | `when_to_use`, `effort: low`, `paths` for shell-relevant files, portable script references |
| `first-run-setup` | explicit invocation, argument hint, arguments, bounded system-state checks |
| `gstack` | `when_to_use`, `effort: medium`, forked QA/review context where appropriate, no mid-review user questions for automated QA |

## Current inventory

### `shell-hygiene`

- Has `name` and a long `description`.
- Lacks separate `when_to_use`, `effort`, and `paths`.
- Body is compact and useful; preserve the no-sleep-chain and zsh word-splitting rules.

### `first-run-setup`

- Has `name` and `description` only.
- Body is compact and idempotent.
- Because it can invoke install/config scripts, it should become explicit-invocation only.
- MCP-specific work should route to `mcp-install`.

### `gstack`

- Has long `description` with trigger phrases embedded.
- Body is under the hard ceiling but above the preferred compact target.
- Contains many hard-won operational details; do not delete them.
- If modularization is too large for PR 2, preserve the content and leave a clear follow-up note rather than compressing away knowledge.

## Execution plan

1. Patch `shell-hygiene` first.
2. Patch `first-run-setup` second.
3. Patch `gstack` last.
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

## Append-only update log

Future PR 2 commits should be summarized below this line without replacing the original purpose above.
