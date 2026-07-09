# Gstack AutoPlan Review — PR1/PR2 Post-Merge Audit and PR3 Scope

Date: 2026-07-09
Status: phone-review draft
Source artifact reviewed: `2026-07-09-orama-pr1-pr2-postmerge-code-review-autoplan.md` (uploaded)
AutoPlan source: `garrytan/gstack/autoplan/SKILL.md` on `main`
Margin source: `https://margin.fieldspan.ai/skill.md`
Scope: orama-system planning document only

## AutoPlan Method Applied

The local Gstack skill is not installed in this session, so the review was applied from the canonical `autoplan/SKILL.md` text:

1. CEO review: challenge premise, ownership, sequencing, business risk.
2. Design review: skipped — this is planning/process, not UI.
3. Engineering review: architecture, code paths, tests, failure modes, deployment risk.
4. DX review: developer workflow, error quality, review ergonomics.
5. Final gate: auto-decide routine choices, surface user challenges, leave a reviewable artifact.

Unlike the source document's own self-audit, this review re-verified the source document's factual claims directly against the live `orama-system` repo (Phase 0 evidence gate, applied to the reviewer's own inputs, not just the target scope) — see **Evidence Corrections** below.

## Final Gate Verdict

Decision: **approve the overall verdict, correct two factual claims, narrow the PR3 scope before opening it.**

The source document's executive summary and goal audits are accurate: PR1 and PR2 did land, did meet their stated goals, and PR #144 did surpass PR2's original low-risk scope in a legitimate way (interactive provider setup, GLM52 consolidation). The recommended sequence — verify, close the security decision, then a narrowly-scoped PR3 — is the right shape. But the PR3 file inventory proposed in "Action 3" names two paths that do not exist in the repo, and one "Critical" gap claim is contradicted by live evidence. Both must be fixed before this becomes an execution plan.

## What The Attached Plan Gets Right

1. Correctly separates "core implementation failures" (none found) from "post-merge assurance gaps" (real, and worth tracking).
2. Correctly identifies GLM52 credential rotation as an operator decision, not something an agent should silently resolve.
3. Correctly proposes PR3 as medium-risk-only, explicitly excluding `mcp-orchestration` and `hermes-harness`.
4. Correctly flags CodeRabbit rate-limiting on PR #142 and PR #144 as an observability gap requiring manual compensation — this matches this session's own independent finding of one stale-but-since-fixed unresolved thread on PR #141.
5. Correctly proposes a strict-mode deferral until the legacy skill corpus is staged, rather than forcing global strict validation immediately.
6. The append-only PR-body discipline callout is grounded — this repo has had exactly this failure mode before (the PR #141 "Codex clobber" incident), so flagging it as an ongoing risk is warranted, not boilerplate.

## Evidence Corrections

### 1. "Fresh workflow runs were not observed" — contradicted by live evidence

The source document lists this as a **Critical** gap: *"The connector returned no workflow runs for the merge commits checked."* Re-querying the GitHub Checks API directly against a recent main commit (`cd50804`) returns **14 check runs**, including `lint-and-test`, `Git hygiene`, `SKILL.md Version Gate`, and CodeQL analysis jobs — all present and queryable. This was a connector-session limitation in the source document's own environment, not a property of the repository. Downgrade from Critical to Minor: *"the reviewing agent's session lacked workflow-run visibility; a fresh session does not."*

### 2. PR3 scope paths `cidf/**` and `afrp/**` do not exist

Verified directly:

| Proposed path | Status | Actual location |
|---|---|---|
| `bin/orama-system/skills/cidf/**` | Does not exist | `bin/orama-system/skills/orama-cidf/SKILL.md` + `bin/orama-system/references/content-insertion-framework.md` + `bin/orama-system/skills/oramasys-method/references/cidf-and-mcp.md` |
| `bin/orama-system/skills/afrp/**` | Does not exist | `bin/orama-system/skills/orama-afrp/SKILL.md` |
| `bin/orama-system/skills/code-review/SKILL.md` | Exists (332 lines) | as proposed |
| `bin/orama-system/skills/git-history-surgery/SKILL.md` | Exists (161 lines) | as proposed |

CIDF doctrine is also partially duplicated across three locations (`orama-cidf/SKILL.md`, the standalone reference, and `oramasys-method/references/cidf-and-mcp.md`) — this is itself a candidate PR3 finding (de-duplicate to one canonical source), not just a path-naming fix.

### 3. `gstack/SKILL.md` is 497 lines — a near-miss, not a clean pass

The source document marks the 500-line ceiling as "Met" for PR2. True at present (497 lines), but with only 3 lines of headroom. Any future gstack edit risks tripping the ceiling immediately. Recommend flagging this file for extraction-to-reference before it is touched again, rather than treating "under 500" as a stable resting state.

## Ruthless Criticism

### 1. The PR3 acceptance criteria are self-referential

"Metadata aligned with PR1 standards" and "repo hygiene and baseline validator pass" are necessary but not sufficient. Neither criterion checks whether CIDF's three-location duplication gets resolved or re-duplicated a fourth time. A PR3 that passes the stated acceptance criteria could still leave the CIDF fragmentation problem worse, not better, if the standardization pass edits all three copies independently instead of consolidating them.

**Required refinement:** add an explicit PR3 acceptance criterion: *"CIDF doctrine has exactly one canonical body; the other two locations become thin pointers or are removed."*

### 2. "No runtime dispatch changes" is asserted, not verified

Same failure mode the source document itself criticizes in the original endpoint-policy plan it references stylistically (Phase 0 evidence over deduction) — but the PR3 proposal doesn't apply that standard to itself. `code-review` and `git-history-surgery` are process/methodology skills, low risk of runtime dispatch involvement, but this should be a Phase-0-style verification step in PR3, not an assumed non-goal.

**Required refinement:** add a Phase 0 task: `grep -rn "dispatch\|execute\|subprocess" bin/orama-system/skills/{code-review,orama-cidf,orama-afrp}/` and confirm zero hits touch MCP/OpenClaw/Hermes entrypoints before editing.

### 3. The credential-rotation gap has no owner or deadline

"Action 2" correctly identifies that GLM52 credential rotation is an outstanding operator decision, but the plan does not assign a deadline or a blocking relationship to PR3. If the exposed value was ever real, leaving this open while PR3 work proceeds is a sequencing risk the plan itself would flag if applied to someone else's work.

**Required refinement:** Action 2 becomes a hard gate on Action 3, not a parallel track. State explicitly: *"PR3 does not open until Action 2's operator decision is recorded (rotated, or confirmed non-sensitive)."*

### 4. "Strict mode limited to scope of new skills only" is under-specified

Good instinct, but the plan doesn't define what makes a skill "new" for this purpose — by directory creation date, by absence from the PR1 baseline snapshot, or by explicit allowlist entry. Without a mechanical definition, this becomes a judgment call each PR re-litigates.

**Required refinement:** define "new skill" as *"not present in the `/tmp/orama-skill-baseline.json` snapshot generated by Action 1."* This makes the strict-mode boundary mechanically checkable rather than a matter of agent discretion each time.

## Steelman

The best version of the attached plan is not "run four more actions in sequence." It is a single governing rule that makes the four actions fall out naturally:

**No new skill work proceeds until (a) the security decision is closed, and (b) the file inventory for the next PR has been verified against the live tree, not deduced from prior planning documents.**

That rule is strong because it prevents the exact failure class this repository has already experienced twice in this session's own audit history: a plan naming paths or claims that don't match the current tree, applied faithfully anyway. PR1's validator and PR2's standardization both succeeded specifically because they stayed grounded in the actual corpus. PR3 should inherit that discipline, not just inherit the roadmap's next line item.

## Refined Execution Plan

### Phase 0 — Evidence Correction (supersedes the source document's Action 1, same commands)

```bash
git clone https://github.com/diazMelgarejo/orama-system.git && cd orama-system
git checkout main && git pull --ff-only
python3 scripts/review/repo_hygiene.py .
python3 scripts/review/check_orama_skills.py --mode baseline --format json > /tmp/orama-skill-baseline.json
python3 -m pytest tests/test_check_orama_skills.py -v
```

Additional Phase 0 task not in the source document: confirm the corrected PR3 file inventory (below) before branching.

### Phase 1 — Security Closure Gate (blocks Phase 2)

Run the source document's Action 2 command (`git grep` sweep) and record the operator's rotate/no-rotate decision in this file before proceeding. This phase has no code changes.

### Phase 2 — PR3, Corrected Scope

**Branch:** `refactor/pr3-medium-risk-skill-standardization`

**Corrected file inventory:**

- `bin/orama-system/skills/code-review/SKILL.md`
- `bin/orama-system/skills/git-history-surgery/SKILL.md`
- `bin/orama-system/skills/orama-cidf/SKILL.md`
- `bin/orama-system/references/content-insertion-framework.md`
- `bin/orama-system/skills/oramasys-method/references/cidf-and-mcp.md` (consolidation target, not independent edit)
- `bin/orama-system/skills/orama-afrp/SKILL.md`

**Non-goals (unchanged from source document, still correct):**

- No `mcp-orchestration` or `hermes-harness` changes.
- No runtime dispatch changes (now verified via Phase 0 grep, not assumed).
- No strict-mode global enablement.

**Acceptance criteria (source document's four, plus one new):**

- Metadata aligned with PR1 standards.
- No `SKILL.md` over 500 lines.
- Side-effect skills have explicit invocation controls.
- Repo hygiene and baseline validator pass.
- **New:** CIDF doctrine consolidated to one canonical body; the other two locations reduced to thin pointers.

### Phase 3 — Review Loop

Publish this document to Margin for phone review. Fold comments back into this repo file before final approval. Re-publish to the same Margin document — do not create a new one.

## Test Plan

| Codepath or artifact | Required coverage | Phase |
|---|---|---|
| PR3 file inventory | matches live tree, not prior planning docs | Phase 0 |
| GLM52 credential sweep | zero runtime values in tracked files | Phase 1 |
| `code-review`, `git-history-surgery` dispatch grep | zero MCP/OpenClaw/Hermes entrypoint hits | Phase 2 |
| CIDF consolidation | single canonical body, two thin pointers, zero content loss | Phase 2 |
| Baseline validator | no new unexpected errors vs `/tmp/orama-skill-baseline.json` | Phase 2 |

## Failure Modes Registry

| Failure mode | Severity | Mitigation |
|---|---|---|
| PR3 opens before credential decision is recorded | High | Phase 1 is a hard gate, not parallel |
| CIDF standardized in three places independently | High | Explicit consolidation acceptance criterion |
| `afrp`/`cidf` path names copied verbatim from source doc into a real branch | Medium | Corrected inventory in this document is the only one to use |
| `gstack/SKILL.md` re-crosses 500 lines on next edit | Medium | Flag for extraction before next touch, not after |
| "New skill" strict-mode boundary re-litigated per PR | Low | Mechanical definition via baseline snapshot diff |

## Decision Audit Trail

| # | Phase | Decision | Classification | Rationale | Rejected |
|---|---|---|---|---|---|
| 1 | CEO | Approve overall verdict, correct two factual claims | Auto-decided | Source document's sequencing logic is sound; specific claims were not | Wholesale rejection of the source plan |
| 2 | Eng | Downgrade "no workflow runs" from Critical to Minor | Auto-decided | Directly contradicted by live Checks API query (14 runs found) | Leaving the claim as Critical |
| 3 | Eng | Correct PR3 inventory from `cidf/`+`afrp/` to `orama-cidf/`+`orama-afrp/` | Auto-decided | Verified directly against the live directory tree | Opening PR3 with non-existent paths |
| 4 | Eng | Add CIDF consolidation as a PR3 acceptance criterion | Auto-decided | Three-location duplication is a real, checkable defect | Treating standardization as metadata-only |
| 5 | CEO | Make credential-rotation decision a hard gate on PR3, not parallel | Auto-decided | Matches this repo's own established security-first sequencing precedent | Parallel-track security decision |

## User Challenges

None. This review's corrections are evidence-based, not judgment calls requiring user input.

## Taste Decisions

None requiring user input now. Defaults are conservative: verify paths against the live tree, gate on the security decision, consolidate rather than re-duplicate CIDF.

## Implementation Tasks Aggregated Across Phases

- [ ] Phase 0: Run source document's Action 1 commands; additionally confirm corrected PR3 inventory against live tree.
- [ ] Phase 1: Run GLM52 credential sweep; record operator rotate/no-rotate decision in this file.
- [ ] Phase 2: Open PR3 using the corrected file inventory above, including CIDF consolidation as an explicit deliverable.
- [ ] Phase 3: Publish this document to Margin; fold comments back before final approval.

## Final Recommendation

Approve the source document's sequencing and intent. Do not execute its PR3 file inventory as written — two of four proposed paths do not exist in the live tree. Use the corrected inventory in this document instead. Treat GLM52 credential rotation as a hard gate, not a parallel action, before PR3 opens.
