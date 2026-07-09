# Gstack AutoPlan Review — PR1/PR2 Post-Merge Audit and PR3 Scope

Date: 2026-07-09 (revised)
Status: phone-review draft
Source artifact reviewed: `2026-07-09-orama-pr1-pr2-postmerge-code-review-autoplan.md` (uploaded)
AutoPlan source: `garrytan/gstack/autoplan/SKILL.md` on `main`
Margin source: `https://margin.fieldspan.ai/skill.md`
**Mother plan (link in all derivatives of this document):** [`docs/plans/2026-07-06-orama-skill-upgrade-roadmap.md`](2026-07-06-orama-skill-upgrade-roadmap.md)
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

### 2. CORRECTED (2026-07-09): `bin/orama-system/afrp` and `bin/orama-system/cidf` are the canonical targets — my earlier framing was backwards

**Prior version of this document incorrectly stated** that `bin/orama-system/skills/cidf/**` and `bin/orama-system/skills/afrp/**` don't exist and redirected to `orama-cidf/SKILL.md` / `orama-afrp/SKILL.md` as "the real paths." This was wrong. Re-verified directly:

| Path | Status | Role |
|---|---|---|
| `bin/orama-system/afrp/` | **Exists** (SKILL.md 163L, README.md, DESIGN.md, FRAMEWORK.md, failure-modes.md, `__init__.py`) | **Canonical target** — user-confirmed |
| `bin/orama-system/cidf/` | **Exists** (SKILL.md 238L, README.md, `__init__.py`, `core/`, `linter/`, `tests/`) | **Canonical target** — user-confirmed |
| `bin/orama-system/skills/orama-afrp/SKILL.md` | Exists (45L) | **Already a correct thin wrapper** — points at `bin/orama-system/afrp/` at runtime. No action needed. |
| `bin/orama-system/skills/orama-cidf/SKILL.md` | Exists (45L) | **Already a correct thin wrapper** — points at `bin/orama-system/cidf/` at runtime. No action needed. |
| `bin/orama-system/references/content-insertion-framework.md` | Exists (316L) | **Genuine duplicate** — a full independent CIDF v1.2 spec, not a pointer. Substantively overlaps `cidf/SKILL.md` (238L, also v1.2). Needs harmonizing into canonical, not deletion. |
| `bin/orama-system/skills/oramasys-method/references/cidf-and-mcp.md` | Exists (36L) | **Partial duplicate** — restates the CIDF rank table (5 lines) but also holds genuinely unique MCP-routing and legacy-compatibility content (not in canonical `cidf/SKILL.md`). Keep the unique content; replace the restated rank table with a link to canonical. |

The mother plan (`2026-07-06-orama-skill-upgrade-roadmap.md`, PR3 section) confirms this reading directly: it names `cidf` and `afrp` as literal PR3 target skills with planned metadata moves (`user-invocable: false`, `when_to_use`, `effort`) — i.e. edits to the **canonical directories**, not to the thin wrappers or the scattered references.

**Corrected rule, per explicit instruction:** duplicates and adjacent skills are never deleted. They are merged and harmonized back into the existing canonical source, and become (or remain) thin wrappers pointing at canon. `orama-afrp/` and `orama-cidf/` already satisfy this. `content-insertion-framework.md` and `cidf-and-mcp.md` do not yet, and are PR3's real remaining CIDF work.

### 3. `gstack/SKILL.md` is 497 lines — a near-miss, not a clean pass

The source document marks the 500-line ceiling as "Met" for PR2. True at present (497 lines), but with only 3 lines of headroom. Any future gstack edit risks tripping the ceiling immediately. Recommend flagging this file for extraction-to-reference before it is touched again, rather than treating "under 500" as a stable resting state.

## Ruthless Criticism

### 1. The PR3 acceptance criteria are self-referential

"Metadata aligned with PR1 standards" and "repo hygiene and baseline validator pass" are necessary but not sufficient. Neither criterion checks whether the genuine CIDF duplicate (`content-insertion-framework.md`, 316 lines, a full independent v1.2 spec) actually gets harmonized into `bin/orama-system/cidf/SKILL.md`, or just gets metadata-polished in place while the duplication persists.

**Required refinement:** add an explicit PR3 acceptance criterion: *"`content-insertion-framework.md` is either reduced to a thin pointer at `bin/orama-system/cidf/SKILL.md`, or its unique content (if any, beyond what canonical already covers) is merged into canonical first. `cidf-and-mcp.md` keeps its unique MCP-routing/legacy-compat content and drops its restated CIDF rank table in favor of a link to canonical. `orama-afrp/` and `orama-cidf/` are already correct thin wrappers — verify, do not re-edit."*

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

**Mother plan:** [`docs/plans/2026-07-06-orama-skill-upgrade-roadmap.md`](2026-07-06-orama-skill-upgrade-roadmap.md) — link this in the PR body and in any further derivative planning doc.

**Corrected file inventory** (edit the canonical directories; leave the already-correct thin wrappers alone; harmonize the one genuine duplicate):

- `bin/orama-system/skills/code-review/SKILL.md` — metadata standardization
- `bin/orama-system/skills/git-history-surgery/SKILL.md` — metadata standardization
- `bin/orama-system/afrp/SKILL.md` — metadata standardization (`user-invocable: false`, `when_to_use`, `effort: low`, per mother plan)
- `bin/orama-system/cidf/SKILL.md` — metadata standardization (`user-invocable: false`, `when_to_use`, `effort: low/medium`, per mother plan)
- `bin/orama-system/references/content-insertion-framework.md` — harmonize into `cidf/SKILL.md` (merge, don't delete; verify no unique content is lost, then reduce to a thin pointer)
- `bin/orama-system/skills/oramasys-method/references/cidf-and-mcp.md` — drop the restated CIDF rank table in favor of a link to canonical `cidf/SKILL.md`; keep the unique MCP-routing/legacy-compat content unchanged

**Explicitly out of scope (already correct, do not touch):**

- `bin/orama-system/skills/orama-afrp/SKILL.md` — verified as a correct thin wrapper
- `bin/orama-system/skills/orama-cidf/SKILL.md` — verified as a correct thin wrapper

**Non-goals (unchanged from source document, still correct):**

- No `mcp-orchestration` or `hermes-harness` changes.
- No runtime dispatch changes (now verified via Phase 0 grep, not assumed).
- No strict-mode global enablement.
- **No deletions.** Every duplicate or adjacent skill in scope is merged/harmonized back to its canonical source and left as (or converted into) a thin wrapper — never removed outright.

**Acceptance criteria (source document's four, plus one new):**

- Metadata aligned with PR1 standards.
- No `SKILL.md` over 500 lines.
- Side-effect skills have explicit invocation controls.
- Repo hygiene and baseline validator pass.
- **New:** `content-insertion-framework.md` harmonized into canonical `cidf/SKILL.md` (merged, not deleted; reduced to a thin pointer) and `cidf-and-mcp.md`'s restated rank table replaced with a canonical link.

### Phase 3 — Review Loop

Publish this document to Margin for phone review. Fold comments back into this repo file before final approval. Re-publish to the same Margin document — do not create a new one.

## Test Plan

| Codepath or artifact | Required coverage | Phase |
|---|---|---|
| PR3 file inventory | matches live tree, not prior planning docs | Phase 0 |
| GLM52 credential sweep | zero runtime values in tracked files | Phase 1 |
| `code-review`, `git-history-surgery` dispatch grep | zero MCP/OpenClaw/Hermes entrypoint hits | Phase 2 |
| `orama-afrp/`, `orama-cidf/` thin wrappers | confirmed still-correct pointers, untouched | Phase 2 |
| CIDF harmonization | `content-insertion-framework.md` merged into canonical, zero content loss, reduced to pointer | Phase 2 |
| Baseline validator | no new unexpected errors vs `/tmp/orama-skill-baseline.json` | Phase 2 |

## Failure Modes Registry

| Failure mode | Severity | Mitigation |
|---|---|---|
| PR3 opens before credential decision is recorded | High | Phase 1 is a hard gate, not parallel |
| `content-insertion-framework.md` deleted instead of merged | High | Explicit no-deletion non-goal + merge-first acceptance criterion |
| Already-correct `orama-afrp/`/`orama-cidf/` thin wrappers re-edited unnecessarily | Medium | Explicitly listed as out-of-scope, do-not-touch |
| `gstack/SKILL.md` re-crosses 500 lines on next edit | Medium | Flag for extraction before next touch, not after |
| Derivative planning docs omit the mother-plan link | Medium | Required in this document's header; carry forward to every PR3 derivative |
| "New skill" strict-mode boundary re-litigated per PR | Low | Mechanical definition via baseline snapshot diff |

## Decision Audit Trail

| # | Phase | Decision | Classification | Rationale | Rejected |
|---|---|---|---|---|---|
| 1 | CEO | Approve overall verdict, correct two factual claims | Auto-decided | Source document's sequencing logic is sound; specific claims were not | Wholesale rejection of the source plan |
| 2 | Eng | Downgrade "no workflow runs" from Critical to Minor | Auto-decided | Directly contradicted by live Checks API query (14 runs found) | Leaving the claim as Critical |
| 3 | Eng | Corrected: `bin/orama-system/{afrp,cidf}/` ARE canonical and exist; `orama-afrp/`/`orama-cidf/` are already-correct thin wrappers | Auto-decided | Verified directly against live tree + mother plan's PR3 section, which names `cidf`/`afrp` as literal targets | My own earlier (2026-07-09, same-day) redirection to `orama-cidf`/`orama-afrp` as "the real paths" — that was backwards |
| 4 | Eng | Add CIDF harmonization (merge `content-insertion-framework.md` into canonical, not delete) as a PR3 acceptance criterion | Auto-decided | 316-line genuine duplicate spec confirmed by direct read; user's explicit no-deletion instruction applies | Deleting the duplicate outright, or leaving it unharmonized |
| 5 | CEO | Make credential-rotation decision a hard gate on PR3, not parallel | Auto-decided | Matches this repo's own established security-first sequencing precedent | Parallel-track security decision |
| 6 | CEO | Require the mother-plan link in this document and all its derivatives | Auto-decided | Explicit user instruction; also prevents the path-confusion in row 3 from recurring in future derivative docs that don't trace back to source intent | Omitting the link as implied/optional |

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

Approve the source document's sequencing and intent. The corrected PR3 file inventory in this document (revised 2026-07-09) edits the canonical `bin/orama-system/afrp/` and `bin/orama-system/cidf/` directories directly, leaves the already-correct `orama-afrp/`/`orama-cidf/` thin wrappers untouched, and harmonizes (merges, never deletes) the one genuine remaining duplicate — `content-insertion-framework.md` — into canonical `cidf/SKILL.md`. Treat GLM52 credential rotation as a hard gate, not a parallel action, before PR3 opens. Every derivative of this document must carry forward the link to the mother plan.
