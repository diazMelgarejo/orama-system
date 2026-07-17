# Preserve-Branch Cleanup Manifest

Status: Phase 1 complete on 2026-07-17. This record evaluates the 27 open
`Preserve unmerged branch:` PRs from
[`2026-07-17-preserve-branch-pr-cleanup-plan.md`](2026-07-17-preserve-branch-pr-cleanup-plan.md).

## Decision

No rebase, replay, merge, or force-update is appropriate. The current `main`
already preserves the useful behavior for 25 branches, generally through a
post-rewrite tree twin or an independently landed, stronger follow-up. Replaying
them would create duplicate historical work and risk regressing the current
implementation. Two oversized branches remain deliberately untouched for human
review.

The table is ordered newest branch activity first. `git cherry -v origin/main
origin/<branch>` provided the patch-equivalence signal; selected behavior and
canonical artifacts on `main` were then checked for every `B` entry. `D` means
the branch was intentionally not judged by a superficial file comparison.

| PR | Branch | Bucket | Disposition | Evidence on current `main` |
| --- | --- | --- | --- | --- |
| #155 | `2026-07-12-001-gstack-safe-upgrade` | B | delete after approval | All ten patches are equivalent; the safe-upgrade helper and follow-on G7 work are present. |
| #154 | `2026-07-11-002-gossip-bus-skill` | B | delete after approval | Exact equivalent landed as `8745044c` (PR #147). |
| #170 | `feat/agent-coordination-heartbeat-skill` | B | delete after approval | PR #146 (`04c8dd15`) landed the capability; later heartbeat cadence hardening supersedes it. |
| #156 | `coderabbitai/utg/7e543a4` | B | delete after approval | GLM fallback remediation and its tests landed in `e0fe1ae7` with later opt-in hardening. |
| #176 | `skillify-pr2-followup` | B | delete after approval | Its launcher/path hygiene is represented by `5fae2e88` and stronger later startup hardening. |
| #182 | `subagent/win-orchestrator/doc-sync-peer-inbox` | B | delete after approval | Exact equivalent patch is already in `main` (`e0c44f47`). |
| #181 | `subagent/win-coder/mac-co-orchestrator-playbook` | B | delete after approval | The three playbook artifacts and later integrations are present in `main`. |
| #180 | `subagent/win-autoresearcher/h5-gpu-harness` | B | delete after approval | The harness and its results are consolidated in canonical H5 cross/final reports. |
| #178 | `subagent/mac-researcher/h4-mac-benchmark` | B | delete after approval | Exact equivalent patch and later H4 synthesis are in `main`. |
| #175 | `skillify-pr1-standards-validator-plan` | B | delete after approval | The validator, tests, and later warning/field refinements are in `main`. |
| #171 | `feat/vitest-tdd-gate-scratch` | B | delete after approval | Its tree matches #165; the TDD gate, hooks, and stronger tests are in `main`. |
| #165 | `cursor/review-vitest-tdd-scratch-c4ae` | B | delete after approval | Same tree as #171; the behavior is represented by the canonical TDD gate. |
| #163 | `cursor/review-peer-inbox-docs-c4ae` | B | delete after approval | Exact equivalent patch is in `main`. |
| #162 | `cursor/review-h4-mac-benchmark-c4ae` | B | delete after approval | H4 artifacts and the integrative doctrine are preserved by current canonical docs. |
| #161 | `cursor/oramasys-integrative-merge-c4ae` | B | delete after approval | The current integrative-merge guide is the same or a stronger successor. |
| #157 | `cursor/ci-autofix-automation-1da6` | B | delete after approval | All branch patches are equivalent to `main`. |
| #153 | `2026-06-30-start-windows-implementation` | B | delete after approval | All branch patches are equivalent to `main`. |
| #152 | `2026-06-30-start-macos-implementation` | B | delete after approval | All branch patches are equivalent to `main`. |
| #151 | `2026-06-27--windows-eol-turf-normalize` | B | delete after approval | All branch patches are equivalent to `main`. |
| #164 | `cursor/review-self-reflection-c4ae` | B | delete after approval | All branch patches are equivalent to `main`. |
| #158 | `cursor/ci-autofix-automation-b566` | B | delete after approval | All branch patches are equivalent to `main`. |
| #159 | `cursor/ci-autofix-automation-d7b3` | B | delete after approval | All branch patches are equivalent to `main`. |
| #160 | `cursor/fix-ci-hygiene-hermes-c4ae` | B | delete after approval | All branch patches are equivalent to `main`. |
| #179 | `subagent/mac-researcher/h5-ollama-parallel` | B | delete after approval | All branch patches are equivalent to `main`; current H5 synthesis is canonical. |
| #172 | `fix/pr135-lint006-windows` | B | delete after approval | All branch patches are equivalent to `main`. |
| #169 | `experiment/pt-orama-self-reflection` | D | leave for human | 430 files and three unmatched commits; branch contains an oversized copied-skill/config stack. |
| #166 | `cursor/security-hardening-pre-v2-c4ae` | D | leave for human | 617 files and eight unmatched commits; manual architectural review is required. |

## Execution Guardrail

Before deleting a `B` branch, create and push a `safety/preserve-pr-<number>-20260717`
tag at its current head. Then use
[`scripts/git/delete-preserve-branch-prs.sh`](../../scripts/git/delete-preserve-branch-prs.sh)
with `--execute`. The helper is deliberately inert without that explicit flag,
and its order matches this manifest. GitHub branch deletion closes each related
Preserve PR without merging it.

Do not delete, rebase, replay, or force-update #166 or #169. They are the only
remaining human-review items after the approved `B` set is processed.
