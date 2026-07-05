# Retiring Fellow Skill Library Runbook

Adapted from `tomicz/fable-5-train-opus-skills-after-it-retires` for orama-system.

## Goal

Build or upgrade a complete skill library under:

```text
bin/orama-system/skills/<skill-name>/
```

Do not write canonical orama skills to `.claude/skills/`.

The purpose is continuity: junior/mid-level engineers and smaller AI models must be able to debug, extend, validate, and advance this repo using verified skill runbooks.

## Hard Boundaries

- Write only under `bin/orama-system/skills/` unless the user explicitly approves registry or pointer updates.
- Prefer upgrading existing skills over creating duplicates.
- Do not mutate `.claude/skills/`; that path may be a consumer or wrapper location, not the canonical orama source.
- Ground every command, flag, path, and claim in the repo before writing it.
- Date-stamp volatile facts.
- End each skill or reference with provenance and re-verification commands for facts that may drift.
- Do not use private/user-specific paths as load-bearing sources.
- Keep new `SKILL.md` files <= 200 lines; hard ceiling <= 500 lines.
- Append an audit note for every skill upgraded or intentionally deferred.

## Source Fallback Rule

If an upstream source repo, README, branch, or artifact is unreachable:

1. Retry once with the canonical GitHub URL or raw URL.
2. If still unreachable, continue only from repo-verified local/cached material.
3. Mark the source `UNVERIFIED - retry required` in the output report.
4. Do not invent missing commands, flags, or claims.
5. Do not block safe local upgrades that are independent of the missing source.

## Phase 1 - Discover Before Writing

Investigate like an incoming principal engineer before authoring any skill.

Read or inspect:

- `README.md`, `pyproject.toml`, `package.json`, manifests, and install docs.
- `bin/orama-system/SKILL.md` and registered sub-skills.
- `bin/orama-system/references/skill-architecture-guide.md`.
- `docs/v2/README.md`, `docs/LESSONS.md`, `docs/wiki/README.md`, and active plans.
- `docs/v2/references/HUMAN-IN-LOOP-ACCOUNTABILITY.md` for HITL gates.
- `docs/v2/32-agentic-security-controls.md` for mediator/context-firewall controls.
- `docs/v2/39-maestro-owasp-genai-reference.md` for MAESTRO/OWASP mapping.
- CI workflows and repo hygiene scripts.
- Existing tests and how they are actually run.
- Git history, reverted work, stalled branches, TODO/FIXME hotspots, and `.agent` memory when available.

Ask at most five questions only for facts the repo cannot reveal:

1. What is the hardest live problem now?
2. What unwritten discipline rule exists?
3. Who is the audience and what do they not know?
4. Which past failure cost the most time?
5. What does `beyond state of the art` mean for this repo?

## Phase 2 - Reuse Or Upgrade Existing Skills First

Existing registered skills already cover major parts of the taxonomy. Use this matrix before creating anything new.

| Source README need | Existing orama skill to reuse or upgrade |
|---|---|
| Change control and doctrine | `skills/code-review`, `cidf`, parent `orama-system` |
| Debugging playbook | `skills/code-review`, `skills/shell-hygiene` |
| Failure archaeology | `skills/git-history-surgery` |
| Architecture contract | parent `orama-system`, `docs/v2/*`, `afrp`, `cidf` |
| Domain reference | create only if no existing reference owns the domain |
| Config and flags | `skills/first-run-setup`, `skills/mcp-install`, `skills/openclaw-skills` |
| Build and environment | `skills/first-run-setup`, `skills/hermes-harness` |
| Run and operate | `skills/openclaw-skills`, `skills/mcp-orchestration` |
| Diagnostics and tooling | `skills/shell-hygiene`, `skills/code-review`, `gstack` |
| Validation and QA | `skills/code-review`, `gstack` QA/review routes |
| Docs and writing | `skills/skillify`, `../../references/skill-architecture-guide.md` |
| External positioning | add a reference or docs/v2 plan only if verified from public sources |
| Hardest-problem campaign | create a narrow campaign skill only after Phase 1 questions |
| Proof and analysis toolkit | create only if repo history has reusable proof patterns |
| Research frontier | create only with falsifiable milestones and no hype |
| Research methodology | create as a compact methodology skill or reference when not covered by existing docs |

If an existing skill is thin, upgrade it in place with a modular reference file. Do not create a sibling with overlapping ownership.

## High-Risk Upgrade Precondition

Before upgrading `mcp-orchestration` or `hermes-harness`, stop and verify:

- [ ] Gate 3 / HITL human-approval node is present, non-bypassable, and anchored to `docs/v2/references/HUMAN-IN-LOOP-ACCOUNTABILITY.md`.
- [ ] Audit append target is configured, preferably `audit_log.jsonl` or the repo's current append-only audit target.
- [ ] MCP context-firewall / mediator rules from `docs/v2/32-agentic-security-controls.md` are incorporated.
- [ ] MAESTRO/OWASP mapping from `docs/v2/39-maestro-owasp-genai-reference.md` is cited where the skill changes execution risk.
- [ ] Operator acknowledges the risk class before edits proceed.

If any item fails, report:

```text
STATUS: BLOCKED - high-risk upgrade precondition failed
Skill: <mcp-orchestration|hermes-harness>
Missing: <checklist item>
Next safe action: <verification or doc/code prerequisite>
```

Do not proceed on configuration alone. This is a MAESTRO Class 2 style gate for this authoring workflow: operator acknowledgment is required before upgrading high-risk execution skills.

## Recommended Upgrade Order

Run low-risk upgrades first, then medium, then high-risk.

| Order | Skills | Rule |
|---|---|---|
| 1 | `shell-hygiene`, `first-run-setup`, `gstack` | Lowest risk; verify path conventions and compatibility only |
| 2 | `code-review`, `git-history-surgery`, `cidf`, `afrp` | Medium risk; preserve doctrine and avoid duplicate ownership |
| 3 | `mcp-install`, `openclaw-skills` | Elevated risk; verify least-privilege and secrets handling |
| 4 | `hermes-harness`, `mcp-orchestration` | Highest risk; require high-risk precondition checklist first |

## Phase 3 - Author Missing Skills

If Phase 2 shows a real gap, create one skill per gap.

Possible candidates must still pass reuse-before-create:

| Candidate | Create only if |
|---|---|
| `human-gate-verifier` | Existing HITL/accountability docs cannot be routed through a current skill |
| `workflow-qualifier` | No existing review skill owns green/red workflow gating |
| `compliance-checker` | Compliance gates cannot fit into existing security/review skills |
| `hallucination-guard` | Grounding checks cannot be added cleanly to `code-review` or `cidf` |
| `prompt-engineer` | Existing skillify/docs-writing routes cannot own prompt design |

Required shape:

```text
bin/orama-system/skills/<name>/
├── SKILL.md
├── instructions/
├── examples/good/
├── examples/bad/
├── references/
├── scripts/
├── templates/
└── eval/
```

Trim unused folders. Do not create empty decorative structure.

Every new skill must include:

- trigger-rich YAML `description`,
- when to use and when not to use,
- sibling skill routing,
- copy-pasteable commands only after verification,
- acceptance checks,
- provenance and maintenance notes.

## Audit Trail Requirement

For every upgrade or deliberate deferral, append a compact audit note to the touched skill reference or final output report:

```text
AUDIT: <date> <skill> <upgrade|defer|create> <reason> <verification source>
```

If the action changes execution risk, include the human approval or blocker reference.

## Phase 4 - Review And Fix

After all planned skills or upgrades exist, run three reviews:

| Review | Checks |
|---|---|
| Factual | Paths, commands, flags, CI, tests, and citations are verified against repo state |
| Doctrine | No contradiction with parent `orama-system`, CIDF, AFRP, security, dry-run, or change-control rules |
| Usability | Trigger quality of descriptions, duplication, self-containedness, scannability, and sibling routing |

Then apply blocking and important fixes.

## Output Report

Return:

```text
STATUS: DONE / BLOCKED

Inventory:
  <skill> - <one-line purpose>

Reused/upgraded:
  <existing skill> - <what changed>

Created:
  <new skill> - <why existing skills did not cover it>

Deferred:
  <skill> - <blocker and next safe action>

Verified:
  <commands/files checked>

Uncertain:
  <facts requiring user answer or future verification>
```

## Provenance And Maintenance

Source adapted on 2026-07-06 from:

```text
https://github.com/tomicz/fable-5-train-opus-skills-after-it-retires/blob/main/README.md
```

Re-verify source and target path before rerunning:

```bash
git fetch origin --prune
git status --short --branch
find bin/orama-system/skills -maxdepth 2 -name SKILL.md | sort
sed -n '1,120p' bin/orama-system/SKILL.md
sed -n '1,140p' docs/v2/references/HUMAN-IN-LOOP-ACCOUNTABILITY.md
sed -n '1,120p' docs/v2/32-agentic-security-controls.md
```
