# Lessons and Memory Capture Timeline — 2026-08-25

> **Quadrant:** Reference (historical synthesis and operating boundaries).
> **Status:** Current through 2026-08-25. This records the decision trail from
> the recent cross-repository remediation session; it does not create runtime
> persistence or supersede the canonical policy documents it links.

## Purpose and reading order

This document preserves why lesson capture changed, how the accidental-deletion
incident changed publication safeguards, and where v1 ends and the deferred
Anamnesis v2 design begins. Read the sources in this order:

1. [PT `.agent` rules](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/.agent/AGENTS.md)
   — canonical v1 development-memory workflow and path-hygiene rules.
2. [v1/v2 controller contract](../v2/56-anamnesis-runtime-memory-migration.md)
   — current behavior, deferred runtime boundary, promotion policy, and acceptance checks.
3. [portable-memory invariant](../v2/47-portable-memory-local-topology-invariant.md)
   — what may be tracked and what must remain local-only.
4. [whole-file deletion preflight](../../bin/orama-system/skills/git-history-surgery/references/file-deletion-preflight-reference-card.md)
   — required proof before every commit, push, or Git-data API publication.

## Authority map

| Concern | v1 authority | v2 direction | Non-negotiable boundary |
| --- | --- | --- | --- |
| Development/system lessons | PT tracked `.agent/` Agentic-Stack | Continues as repository-development memory | Orama must not silently create a competing canonical log |
| Capture frontend | `bin/orama-system/scripts/capture_lesson.py` | Same user-facing workflow/controller | Backends are explicit and fail closed when unavailable |
| User/runtime evidence | Not implemented in v1 | Tentative `oramasys/anamnesis` | Private by default; never substituted by a tracked fallback |
| Cross-project memory | PT bundle, internally scoped by lesson context | One user-level runtime bundle with project namespaces/tags | Project-specific evidence is not automatically general policy |
| Promotion | PT `learn.py`, `auto_dream`, human-reviewed tracked changes | Weekly crystallization joins development lessons and private runtime evidence | Sanitize before commit and again immediately before a human-approved push |
| Publication | Git/PR workflow | Same | `allow_automatic_push=false` by default; no automatic push without HITL |

The current system is therefore intentionally asymmetric: development lessons are
durable and tracked in PT; future runtime evidence is private and local until a
sanitized technical pattern qualifies for promotion.

## Timeline

| Date / phase | Event | Lesson or decision | Durable evidence |
| --- | --- | --- | --- |
| 2026-03-22 | Orama's original `capture_lesson.py` entered the repository as a standalone Markdown lesson system. | Direct append was the original compatibility behavior, not the future memory authority. | [`capture_lesson.py`](../../bin/orama-system/scripts/capture_lesson.py) history |
| 2026-06-18 | PT's Agentic-Stack `.agent` portable brain was installed locally. | The durable, harness-neutral memory path began in PT, before the current controller work. | [PT `.agent` rules](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/.agent/AGENTS.md) |
| 2026-06-19 | PT commit [`82bcbfae`](https://github.com/diazMelgarejo/Perpetua-Tools/commit/82bcbfae) first tracked the complete `.agent` system. | Episodic evidence, semantic lessons, candidates, graduation, recall, review queue, and harness-neutral tooling entered one portable brain. | [PT commit `82bcbfae`](https://github.com/diazMelgarejo/Perpetua-Tools/commit/82bcbfae) |
| 2026-06-26 | PT formalized Agentic-Stack under `vendor/agentic-stack`; lesson `lesson_821b2a648956` recorded PT as canonical and Orama as consumer. | PT owns customized development memory; Orama consumes it rather than cloning it. | [agentic-stack memory blend](../v2/41-agentic-stack-gstack-gbrain-memory-blend.md) |
| 2026-06-26 | Orama commit [`97061371`](https://github.com/diazMelgarejo/orama-system/commit/97061371) added v2 plan 41. | The plan already said PT owns the customized `.agent`, every harness reads the same memory, Orama must not duplicate it, sibling discovery supplies it, and `learn.py` / `recall.py` / `auto_dream.py` are canonical. | [plan 41](../v2/41-agentic-stack-gstack-gbrain-memory-blend.md) |
| 2026-07-18 | Portable-memory policy was locked. | Tracked policy may name categories but must not contain concrete local identity, device, path, or topology material. | [D25 invariant](../v2/47-portable-memory-local-topology-invariant.md) |
| 2026-08-20 to 2026-08-24 | SSRF, endpoint-policy, Calico, and observability remediation was reviewed across Orama and PT. | Security controls need defense in depth, exact endpoint policy, CA-bundle preservation, and one failure-to-one telemetry-event behavior. | [SSRF plan](../v2/plans/2026-08-20-ssrf-defense-in-depth.md), [observability contract](../v2/55-oramasys-agent-observability-contract-adr.md) |
| 2026-08-24 | A published commit unexpectedly showed 1,881 changed files and 270,621 deletions, including tracked `.agent` material. | A whole-file disappearance is a publication-integrity event, not ordinary diff noise. Git state and tree scope must be proved before a ref moves. | [incident commit](https://github.com/diazMelgarejo/orama-system/commit/95db1dd017a7b982778f62b53ee1a66b3599a436), [deletion preflight](../../bin/orama-system/skills/git-history-surgery/references/file-deletion-preflight-reference-card.md) |
| 2026-08-24 | Deletion safeguards were added to Orama. | Check staged scope and outgoing range; require a deliberate justification for any tracked-file removal; for Git-data API publication, require remote constructed tree SHA = local `HEAD^{tree}`. | [guard commit](https://github.com/diazMelgarejo/orama-system/commit/0cdd36ac49bd80b1f4b8d02e2a597673d7a25bac) |
| 2026-08-25 | The memory migration questions were resolved. | PT `.agent` stays canonical in v1; Anamnesis is a tentative future runtime backend, not a dependency to invent early. | [D26 controller contract](../v2/56-anamnesis-runtime-memory-migration.md) |
| 2026-08-25 | `capture_lesson.py` was converted from implicit direct append to a controller. | Development delegates to PT; legacy Markdown is an explicit compatibility escape hatch; runtime mode fails closed until Anamnesis is provisioned. | [controller commit](https://github.com/diazMelgarejo/orama-system/commit/2b1f5ed9cb243ef4f952673cfec204d4017f73a2) |
| 2026-08-25 | PT memory was updated with the integrity and ownership lessons. | Capture the cause, evidence, prevention rule, and verification trigger through the existing `learn.py` pipeline—not by hand-editing rendered lessons. | [PT lesson workflow](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/.agent/AGENTS.md) |

## The deletion incident: causal chain and permanent repair

The visible symptom was an implausibly large deletion-only change under a narrow
security commit. The dangerous failure mode was not merely a bad local diff: a
Git-data/tree API publication can create a valid commit that omits paths, then
move a public branch ref without Git reporting a semantic error.

The permanent repair is a two-boundary proof bundle:

```bash
git status --short
git diff --cached --name-status
bash scripts/git/check_file_deletion_guard.sh --staged
git diff --name-status <remote-base>..HEAD
bash scripts/git/check_file_deletion_guard.sh --range <remote-base>..HEAD
```

For a Git-data API publication, create blobs and a tree from the intended local
commit, compare the resulting remote tree SHA to local `HEAD^{tree}`, and only
then create the remote commit and update the branch ref. The controller work in
this session used that proof: remote and local trees both resolved to
`70cc4f650e62922619c1194ca1e21c7d2e10496a` before PR #328 moved.

This is deliberately stricter than a visual PR scan. It protects against a
wrong worktree, a partial tree payload, `git add -u`, and reverse-diff-style
mistakes. See the [canonical guard skill](../../bin/orama-system/skills/git-file-deletion-guard/SKILL.md)
and its [parent git-history doctrine](../../bin/orama-system/skills/git-history-surgery/SKILL.md).

## Memory-capture evolution

### Before this session

`capture_lesson.py` directly appended a Markdown entry to `tasks/lessons.md`.
That was convenient for standalone installs but contradicted the later PT
Agentic-Stack authority: two stores could diverge, and selecting a backend could
create a new log before any lesson had been captured.

### Current v1 controller

The controller preserves the CLI workflow while changing backend ownership:

| Invocation | Behavior |
| --- | --- |
| `--mode development --backend auto` | Requires `PERPETUA_TOOLS_ROOT` / `--pt-root`; delegates to PT `.agent/tools/learn.py` |
| `--quick` | Collects one prevention rule and produces a complete structured payload |
| `--review` / `--stats` with PT | Reads PT's rendered semantic lesson view; does not mutate memory |
| `--backend legacy` | Explicit compatibility path for an already-initialized Markdown log; it never creates a new v1 log |
| `--mode runtime --backend auto` | Fails closed with `ORAMASYS_LESSON_E_ANAMNESIS_UNAVAILABLE` until v2 provisioning exists |

The implementation and regression coverage live in
[`capture_lesson.py`](../../bin/orama-system/scripts/capture_lesson.py),
[`lesson_controller.py`](../../bin/orama-system/scripts/lesson_controller.py), and
[`test_capture_lesson_controller.py`](../../tests/test_capture_lesson_controller.py).

### Frontend completion contract

“Fix all frontend issues” means preserve the familiar `capture_lesson.py`
workflow while correcting accidental behavior and making backend ownership
explicit. The completed v1 controller establishes these compatibility and
security requirements; the remaining runtime-specific checks are acceptance
requirements for Anamnesis:

| Requirement | v1 status | v2 runtime completion requirement |
| --- | --- | --- |
| Interactive prompts, `--pattern`, `--quick`, `--review`, `--stats`, and `--dir` | Preserved | Preserve unchanged |
| `--quick` minimal capture | Implemented | Preserve unchanged |
| Backend selection by context/configuration | Implemented for PT, legacy, and deferred Anamnesis | Add provisioned runtime resolver and explicit enable/disable configuration |
| Direct `tasks/lessons.md` default persistence | Removed | Legacy-only explicit compatibility path |
| Review/stat tier identity | PT view is labeled; legacy stays explicit | Identify authorized runtime tier without disclosing private evidence |
| UTF-8, atomic persistence, invalid-config and unavailable-store behavior | Explicit UTF-8; legacy atomic write; stable error symbols and fail-closed backend selection | Apply to every runtime provider and authorization boundary |
| Non-interactive/machine-readable capture | Deferred | Required for runtime-service capture and automation |
| Sanitation and privacy | PT path hygiene governs tracked development memory | Sanitize at runtime persistence and promotion; prohibit unauthorized runtime review/stat disclosure |
| Terminology and exit compatibility | Stale `ultrathink` frontend branding removed; error exit is stable | Maintain documented machine-readable symbols and CLI compatibility |
| Regression coverage | Controller backend and quick-capture tests added | Cover every CLI mode, resolver path, sanitation boundary, authorization rule, and HITL rule |

### Deferred v2 Anamnesis contract

Anamnesis is a future repository and runtime backend, not a retrofitted v1
dependency. When it exists, runtime memory will default to a repo-local,
gitignored private store and support intentional disablement or configured
external/provider storage. It will preserve raw local evidence, namespace
project-specific observations, and promote only sanitized, technical,
non-personal patterns.

The weekly promotion process combines runtime evidence with PT development
lessons, applies the Orama crystallization formula and PT `auto_dream`, and
creates a candidate on a dedicated PT memory branch/worktree by default. An
agent may graduate and commit a qualifying pattern, but it must not push it
without human approval unless a deliberate override changes that policy.

## Refined architecture and transition

This is an architectural continuation of the June lineage, not a new memory
direction.

### V1 — development only

**PT `.agent`** is the sole canonical development/system memory: tracked and
preserved in PT, with `learn.py`, `recall.py`, AutoDream, and graduation. The
default crystallization cadence is weekly; qualifying development candidates are
committed locally on a dedicated PT memory branch/worktree. A deliberate
local-only Git-repository override is supported, but push remains human-gated.

**Orama v1 `capture_lesson.py`** is the stable frontend/controller, not a
runtime persistence system. It delegates development capture to PT. Existing
direct-Markdown documentation remains historically useful but is partially
superseded rather than erased.

### V2 — Anamnesis

`oramasys/anamnesis` will be forked from the proven PT Agentic-Stack backend
and become the independently versioned shared memory service. PT and all
`oramasys/*` repositories will consume it while PT preserves its v1 history.

Anamnesis will hold one user-level OramaSys memory bundle. Provisioning is
explicit and capture can be enabled or disabled. The default store is
repo-local and gitignored; deliberate alternatives include an off-repo
filesystem location, environment/configured path, local Git repository,
database, or future provider. Weekly crystallization, schedules, and evidence
thresholds are configurable, with weekly as the default.

In this mode the same stable controller becomes the runtime lesson-capture
workflow: development context routes to tracked PT `.agent`; runtime context
routes to private Anamnesis evidence. There is no user-facing deprecation,
because the frontend workflow remains supported while its backend matures.

### Weekly promotion and contribution

Weekly promotion scans both development lessons and private runtime evidence.
It combines PT AutoDream with Orama crystallization scoring, preserves all raw
runtime memory locally, extracts recurring global technical non-personal
patterns, and retains project-specific patterns under namespace tags.

The pipeline sanitizes before candidate persistence; automatically stages,
graduates, and commits qualifying candidates locally; and prepares an
auto-fork contribution branch for the upstream canonical corpus.
`allow_automatic_push` defaults to `false`. After HITL approval, it sanitizes
and verifies again immediately before push. Only an explicit
`allow_automatic_push=true` override permits an automatic push.

## Partial supersession register

The following sources are partially superseded only for their old persistence
claims; their historical rationale and trace-tree work remain available:

- [`docs/v2/02-modules/lessons-and-skill-authoring.md`](../v2/02-modules/lessons-and-skill-authoring.md)
- [`docs/v2/35-langfuse-trace-tree-pattern.md`](../v2/35-langfuse-trace-tree-pattern.md)
- [`docs/v2/41-agentic-stack-gstack-gbrain-memory-blend.md`](../v2/41-agentic-stack-gstack-gbrain-memory-blend.md)
- [`docs/v2/20-rag-and-memory-design.md`](../v2/20-rag-and-memory-design.md)
- [`scripts/README.md`](../../bin/orama-system/scripts/README.md) and other
  references that describe `capture_lesson.py` as directly appending Markdown
- [`distill_session.py`](../../bin/orama-system/scripts/distill_session.py) and
  its integration documentation
- [`self-improve`](../../bin/orama-system/skills/self-improve/SKILL.md) and
  [Stage 5 crystallization](../../bin/orama-system/references/oramasys-5-stages.md)
  references

Plan 35's “never runtime state” and “never a PT change” statements are
specifically superseded. Its trace-tree concept remains useful as runtime
evidence to be consumed by the Agentic-Stack/Anamnesis backend, not as a
separate permanent store.

## Cross-repository outcomes and remaining boundary

| Repository | Completed in this session | Publication state |
| --- | --- | --- |
| `orama-system` | Deletion guard doctrine; v1 capture controller; compatibility tests; D26 migration contract; active docs and templates reconciled. | Published to [PR #328](https://github.com/diazMelgarejo/orama-system/pull/328) after tree-SHA verification. |
| `Perpetua-Tools` | Recorded the publication-integrity lesson and v1/v2 ownership lesson through `.agent/tools/learn.py`. | Local commits were created on the existing branch. Publication remained intentionally blocked when an exact remote tree could not be reconstructed from the available transport; no PT ref was moved. |

That final boundary is itself a success condition: when a transport cannot prove
that a large JSONL memory blob survived intact, it must not publish. The correct
next action is an authenticated, normal Git push from a PT checkout after the
same outgoing-range inspection—not a degraded API workaround.

## Related documents

- [D26 — Anamnesis runtime-memory migration](../v2/56-anamnesis-runtime-memory-migration.md)
- [D25 — Portable-memory local-topology invariant](../v2/47-portable-memory-local-topology-invariant.md)
- [Agentic-Stack, Gstack, Gbrain, RAG, and memory blend](../v2/41-agentic-stack-gstack-gbrain-memory-blend.md)
- [Lessons and SKILL authoring module](../v2/02-modules/lessons-and-skill-authoring.md)
- [Langfuse trace-tree pattern](../v2/35-langfuse-trace-tree-pattern.md)
- [Observability contract ADR](../v2/55-oramasys-agent-observability-contract-adr.md)
- [Git hygiene and branching](../wiki/08-git-hygiene-and-branching.md)
- [PT `.agent` workflow](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/.agent/AGENTS.md)
