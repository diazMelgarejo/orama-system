# The v2 Skill Construction Guide — Harmonized Canonical Instruction Set

**Status:** synthesis guide, additive and convergent — merges, harmonizes,
and cross-references; replaces nothing. Every source remains authoritative
for its own layer.
**Date:** 2026-09-12
**Compiled from (all verified at `diazMelgarejo/orama-system` main `bb7069c7`):**

- [`docs/v2/44-docs-v2-skills.md`](https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/44-docs-v2-skills.md)
  — the v2 Skills Format Standard (normative shape, size policy, dry-run
  rule, acceptance criteria)
- [`docs/v2/46-repository-standard.md`](https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/46-repository-standard.md)
  — cross-cutting repository standard (additive to every docs/v2 plan)
- [`docs/v2/02-modules/lessons-and-skill-authoring.md`](https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/02-modules/lessons-and-skill-authoring.md)
  — authoring toolchain module
- `bin/orama-system/skills/skillify/references/modular-skill-authoring.md`
  — Claude Code skill standards, intake questions, frontmatter routing,
  clobber/collision guards
- `bin/orama-system/skills/skillify/references/skill-folder-template.md`
  — folder + SKILL.md skeleton source
- `docs/v2/references/ORAMASYS-MASTERY-v3.md` — methodology authority
  (outcome-over-activity, verification-before-done/LINT-002, 3-Layer
  Framework)
- Kungfu v2 plan + v1 skill inventory
  (`2026-09-14-kungfu-v2-composable-skills-mvp-plan.md`,
  `2026-09-14-kungfu-v1-skill-inventory.md`) — atom/composite/manifest
  layer and the five-owner routing table
- **OSSF draft suite** (`2026-09-16-ossf-part0-introduction.md` → Parts
  1–4) — normative target for **Open Standard Skill Format (core)** +
  **Atomic Skill Card Format Extension**
- **OSSF-1 saga** (PT
  `.agent/memory/semantic/OSSF1_SKILL_FORMAT_STANDARDIZATION_SAGA_2026-08-07.md`)
  — fusion inventory, pilot wave, pre-commit enforcement; reconciled here
  2026-09-16 via `2026-09-12-ossf1-to-atomic-card-reconciliation-plan.md`
- PT `lesson_adda4d2b02c3`, `lesson_74da980b662b`, `lesson_1e176602744c`,
  `lesson_2bb73f680949` — merge/reanchor, scope, progressive disclosure,
  BOM traps
- PT PR #391 + orama-system PR #357 — remote content-integrity gates
  (three-gate check, append-only dossier)
- oramasys PR #12 — routed-model parity invariant (dispatch executes
  exactly what routing selected)

**Format lineage (additive — retires nothing):**

`USF-1 fusion inventory` (2026-08-07, OpenClaw `v1/2026-08-07-skill-format-fusion.md`)
→ **OSSF implementation draft v1** (2026-08-08 working name "OSSF-1"; hook
`check_ossf1_skill_md.py` on staged canonical paths)
→ **doc 44** planning baseline (folder shape, ≤200 preferred / ≤500 hard, dry-run,
acceptance criteria)
→ **Open Standard Skill Format (core)** — [`2026-09-16-ossf-part1-core-open-standard-skill-format.md`](2026-09-16-ossf-part1-core-open-standard-skill-format.md)
→ **OSSF (Atomic Skill Card Format Extension)** — optional profile for composable
atoms only — [`2026-09-16-ossf-part2-atomic-skill-card-format-extension.md`](2026-09-16-ossf-part2-atomic-skill-card-format-extension.md)
→ **Composite consumer profile** — core only, no extension fields —
[`2026-09-16-ossf-part3-composite-consumer-profile.md`](2026-09-16-ossf-part3-composite-consumer-profile.md)

Subset chain: **OSSF (core) ⊂ doc 44 card shape**; extension profile adds atom
fields only when `format_profile: composable-atom`. Suite index:
[`2026-09-16-ossf-part0-introduction.md`](2026-09-16-ossf-part0-introduction.md).

**Purpose:** a future agent follows this document literally to construct a
new v2 skill — at any of the three altitudes (single card, Kungfu atom,
orbit-satellite package) — without re-deriving rules scattered across ten
documents. This guide is itself a pointer-network node: where a source is
stricter, the source governs.

---

## 0. Decide the altitude first (three legal homes for a new skill)

Before writing anything, classify the new skill:

| Altitude | When | Home |
| --- | --- | --- |
| **A. Skill-local card** | Generic method/behavior with no policy authority and only skill-local scripts (responsibility test passes) | `oramasys/kungfu` (`skills/<domain>/<verb>`) or a v1 repo per the routing table |
| **B. Kungfu atom + composite** | The skill is one trigger boundary / one outcome in the Kungfu kernel; composites order atoms | `oramasys/kungfu` `skills/` + `composites/` |
| **C. Orbit-satellite package** | It makes policy decisions, holds credentials, dials endpoints, owns hardware/model selection, or persists memory | A specialist v2 repo: telos (endpoint/transport), phylax (security/admission), agate (hardware/model selection), anamnesis (memory/lessons), alexandria (canonical docs/specs) |

**Routing precedence (applies in this order):**

1. **Domain-owner routing first** — if the content makes policy decisions
   (security/admission → phylax; endpoint/transport/auth → telos;
   hardware/model selection → agate; memory/lesson persistence → anamnesis),
   it routes to that owner **regardless of size**. LOC is a weak secondary
   signal, never the ownership test.
2. **Kungfu altitude second** — only content confirmed generic routes to
   altitude A/B. Cross-boundary cards must be **split**: generic method →
   Kungfu atom; owner-specific policy → boundary link to the owner.
3. **Execution scripts:** skill-local scripts land in the skill's
   `scripts/` folder (doc 44 shape) when the responsibility test passes;
   anything growing into a subsystem (multi-file, own tests, runtime
   authority) splits to the owning specialist repo. Mirrors the docs/v2
   microkernel + orbit-plugin model (README D4/D22): perpetua primitives are
   the core; skills and their small helpers are composable legos orbiting it.

## 1. Name it (collision-checked, kebab-case)

1. lowercase kebab-case, 1-64 chars, matching the directory name.
2. Run the ONE shared namespace collision check before ANY write — including
   at naming time, not just publish time:

   ```bash
   bash "$(git rev-parse --show-toplevel)/scripts/check-skill-namespace-collision.sh" <name>
   ```

   Exit 0 + `clear: <name>` → safe. Exit 1 + `COLLISION: ...` → pick a
   disambiguated name (precedent: `oramasys-<name>`, e.g. `oramasys-method`,
   `oramasys-skillify`). Never continue with a colliding name.
3. Kungfu atom naming rule: `<domain>/<verb-phrase>` — domain from the fixed
   directory set (intent, method, edit, shell, git, review, coordination),
   verb in imperative, no owner names in atom IDs.
4. Run the in-repo clobber guard before writing:

   ```bash
   TARGET_DIR="bin/orama-system/skills/<name>"   # or kungfu skills/<domain>/<verb>
   [ -d "$TARGET_DIR" ] && find "$TARGET_DIR" -maxdepth 2 -type f | sort
   ```

## 2. Intake (answer before writing)

1. Skill name (step 1). 2. Purpose: one third-person sentence with trigger
contexts. 3. Target harness: orama-system, gstack, raw Claude Code, Codex
wrapper, ECC, Kungfu-atom, or all applicable. 4. Trigger phrases the user
would actually type. 5. Boundaries: always do / ask first / never do. 6.
Modularity: tiny skill or production folder. 7. Invocation mode: user
command, model-invoked background skill, forked subagent, or explicit
side-effect workflow. 8. **Outcome statement** (mastery standard: "what
must be true before success is declared?" — not the activity).

## 3. Build the folder (doc 44 normative shape)

```text
<skill-name>/
├── SKILL.md              # activation, routing, boundary card — never an encyclopedia
├── instructions/         # long rules and procedures
├── examples/good/        # golden paths
├── examples/bad/         # anti-patterns (with aguara-ignore-next-line quarantine)
├── references/           # architecture notes, external docs, linked specs
├── scripts/              # deterministic checks and generators (skill-local only)
├── templates/            # reusable output formats
└── eval/                 # eval/{skill-prefix}-checklist.md (6Cs + reviewer personas)
```

Trim unused folders for tiny skills; never create empty decorative folders.
**Kungfu atoms** additionally follow the atom naming/trigger rules and live
under `skills/<domain>/<verb>/` with a selection-frontmatter card and
optional `references/` — composites order atoms but never duplicate prose.

## 4. Write SKILL.md (the card)

### 4.0 Open Standard Skill Format (normative draft — this guide is informative)

**Normative target:**
[`2026-09-16-ossf-part1-core-open-standard-skill-format.md`](2026-09-16-ossf-part1-core-open-standard-skill-format.md)
(**OSSF core**). This section summarizes for onboarding; where they differ,
Part 1 wins.

Every skill card at every altitude (A/B/C) MUST satisfy **OSSF (core)**:

| Requirement | Rule |
| --- | --- |
| Frontmatter | `name`, `description` (≥20 chars), `version`, `allowed-tools` |
| Activation | `triggers` list **or** `Activates when` / `Activates for` in `description` |
| Compatibility | `compatibility` **or** `agent_compatibility` (overlay/install mirrors) |
| Profile | `format_profile` MAY be omitted (defaults to `core`) |
| Body | `## Purpose` **or** `## When to Use`, then mandatory `## Boundaries` |
| Boundaries | `### Always Do`, `### Ask First`, `### Never Do` (never weaken to save lines) |
| Size | ≤200 lines preferred; **500 hard ceiling** — move bulk to `references/` |
| Encoding | UTF-8 without BOM |

**Composable atoms only** (`format_profile: composable-atom`) MUST also satisfy
[`2026-09-16-ossf-part2-atomic-skill-card-format-extension.md`](2026-09-16-ossf-part2-atomic-skill-card-format-extension.md):
`outcome`, `approval_limit`, typed `references[]`, `<domain>/<verb-phrase>` name.

**Composite consumers** (`format_profile: composite-consumer`) satisfy core +
[`2026-09-16-ossf-part3-composite-consumer-profile.md`](2026-09-16-ossf-part3-composite-consumer-profile.md)
only — **no Part 2 fields required**.

Kungfu atom field reconciliation (informative): Kungfu reviews Part 4 in
[`2026-09-14-kungfu-v2-plan-reviews-ceo-eng-dx.md`](2026-09-14-kungfu-v2-plan-reviews-ceo-eng-dx.md).

- Target ≤ 200 lines (hard ceiling 500 for existing/exceptional — exceeding
  it is `STATUS: BLOCKED - SKILL.md too large`; move material to the
  sub-folders instead).
- Frontmatter fields, added only as the risk/invocation style requires —
  never all fields by default:

```yaml
---
name: <skill-name>
description: >-
  <third-person purpose>. Use when the user asks for <trigger contexts>.
when_to_use: >-
  Activates for: <trigger phrase>, <task shape>, <file or workflow context>.
version: 1.0.0
license: Apache 2.0
compatibility: claude-code
triggers: ["<trigger>"]
allowed-tools: bash, file-operations
# add only as needed:
argument-hint: "[target]"
arguments: [target]
effort: low|medium|high
context: fork
agent: Explore|Plan|Execute
disable-model-invocation: true   # REQUIRED for install/deploy/git-history/MCP-config/dispatch side-effect skills
user-invocable: false            # for background doctrine (AFRP/CIDF-style protocols)
disallowed-tools: AskUserQuestion
paths: ["bin/orama-system/skills/**"]
---
```

- `description` + `when_to_use` combined ≤ 1,536 characters (Claude listing
  cap); `description` alone must be ≥20 characters (OSSF-1 floor).
- Card body (required section order): `## Purpose` or `## When to Use` →
  activation/load-order/workflow (5–10 steps) → `## Boundaries` with the three
  OSSF-1 subsections → pointers to `references/` / owner boundaries. All
  markdown fences carry language specifiers.
- Prefer `${CLAUDE_SKILL_DIR}` for bundled scripts, `${CLAUDE_PROJECT_DIR}`
  for project-local scripts.
- Treat skills as executable supply-chain material: audit scripts, tool use,
  network use, hooks, and security scope. Use safe wording only — literal
  bad→good pairs belong in `examples/bad/security-wording-anti-patterns.md`
  with `aguara-ignore-next-line` quarantine.

## 5. Content routing table (where every kind of content goes)

| Content | Destination |
| --- | --- |
| Discovery metadata, 5-10 step workflow, hard prohibitions | `SKILL.md` |
| Long rules, detailed procedures | `instructions/*.md` |
| Golden paths and anti-patterns | `examples/good/*.md`, `examples/bad/*.md` |
| Architecture notes, external doc links, linked owner specs | `references/*.md` |
| Deterministic checks and generators (skill-local) | `scripts/*` |
| Reusable output formats | `templates/*.md` |
| Review checklist + personas | `eval/{skill-prefix}-checklist.md` |
| Security/endpoint/hardware/memory policy | **NOT here** — boundary link to phylax/telos/agate/anamnesis |
| Canonical spec/ADR authority | **NOT here** — link to alexandria |

## 6. Mandatory behaviors (doc 44 + mastery, all additive)

- **Dry-run rule:** any long-running or autonomous skill must support
  dry-run first. Dry-run must NOT call paid/external LLMs, install plugins,
  touch GPUs, mutate repos beyond a plan/report file, run autonomous loops,
  or edit AlphaClaw directly. Dry-run SHOULD list affected files, show
  intended commands, show expected outputs, classify risks, stop for review.
- **Verification before done (LINT-002 hard block):** verify
  programmatically — never trust visual confirmation.
- **Outcome-first goal statement:** declare what must be true before
  success, not the activity.
- **Remote content-integrity gates** (three-gate check from orama-system
  PR #357, dossier from PT PR #391): local pre-commit gate → remote branch
  post-write gate (re-read remote, fetch markers) → exact-head pre-merge
  gate + post-merge destination re-read. Evidence: UTF-8 blob SHA of every
  changed file + remote head SHAs before/after merge.
- **Routed-model parity:** dispatch must execute exactly the model routing
  selected and reported (agate authority; oramasys PR #12 invariant).
- **Cross-skill dependencies are referenced, never copied.**

## 7. Security & boundary checklist (Kungfu routing + ADR 62)

- Security/admission/secret lifecycle → **phylax** (link, never copy).
- Endpoint identity/transport/redirect/auth → **telos** (link, never copy).
- Hardware/backend/model selection/tier progression → **agate** (link;
  agate decides policy → oramasys composes → core executes).
- Memory/lesson persistence → **anamnesis** with a Phylax pre-write/redaction
  boundary link.
- Canonical spec/ADR authority → **alexandria** (link; this guide itself
  reconciles there after human review).
- Forbidden in any skill file: API keys, personal paths, doxxing material,
  SecOps-sensitive material, raw workstation paths, LAN IPs, hidden side
  effects (doc 46; use abstract wording or synthetic registry fixtures per
  doc 47).

## 8. Eval + acceptance (doc 44 acceptance criteria)

- Every non-trivial skill gets `eval/{skill-prefix}-checklist.md` (6Cs +
  reviewer personas; skill-prefixed to avoid SkillNameCollision).
- Acceptance checklist: concise + triggerable card; long examples outside
  SKILL.md; eval checklist present; cross-skill deps referenced not copied;
  dry-run present for long-running/autonomous skills; AlphaClaw controlled
  through Perpetua, not edited from v2 skill planning; all fences
  language-tagged; no raw paths/secrets/side effects.

## 9. Kungfu-specific extras (atoms, composites, manifest)

**Single-validator rule (OSSF continuity):** Wave-1 boundary lint and format
contract tests must **extend** `orama-system/scripts/hooks/check_ossf1_skill_md.py`
(Part 1 / core subset today) per
[`2026-09-16-ossf-part4-conformance-and-validation.md`](2026-09-16-ossf-part4-conformance-and-validation.md).
Never run a second parallel SKILL.md validator — same lesson as the namespace-
collision script duplication incident.

- Manifest row contract (`sources/v1-skill-manifest.jsonl`): source_repo,
  source_path, source_revision (immutable commit), logical_capability,
  disposition (atom | composite-input | adapter | provenance-only |
  external-owner), target, owner (kungfu | phylax | telos | agate |
  anamnesis | undecided-integration), verification (typed test ref), plus
  the review-mandated additions: manifest_version, status
  (active | stale | superseded), and typed verification references.

  **Normalization amendment (2026-09-15):** this summary does not authorize a
  second manifest schema. The v1 inventory is the canonical row shape:
  `root_disposition` describes the source-level migration choice, while one or
  more non-overlapping `ownership_slices` carry target and owner decisions.
  Each candidate also records target altitude, the eight-question intake,
  effect/dry-run classification, namespace-check status, and evaluation
  obligation. `candidate` and `blocked` are valid pre-implementation states;
  a pending namespace check blocks an implementation PR once a target
  repository exists. The owner set also includes Alexandria for canonical
  authority and Perpetua Core for execution-mechanics boundaries. See the
  inventory's Manifest Row Contract for the complete typed example.
- Wave gates: Wave 0 (manifest + ownership boundaries + baseline corpus +
  A/B harness) → Wave 1 (portable kernel: 13 atoms, contract tests,
  boundary lint **including OSSF-1 subset**, negative fixtures) → Wave 2
  (thin v1 adapters) → Wave 3
  (remaining inventory). Product-level gate invariants O1-O3 (completion
  parity, token parity ≤1.0x, correct-selection rate) measured before
  implementation merges — v1 cards stay the working default until all green.
- Review-binding decisions: fail-closed semantics (missing atom/dead
  link/stale row = hard error, never v1 fallback); typed composite edges
  (requires-success, must-precede, conditional-on, approval-before,
  on-failure); negative fixtures; manifest freshness CI; sanctioned
  flattened-bundle export generated in CI only with a provenance header;
  script classification runs the domain-owner test FIRST, LOC secondary.
- Naming rule for atoms: `<domain>/<verb-phrase>` — domain from the fixed
  directory set, verb imperative, no owner names in atom IDs.

## 10. Source precedence (when sources disagree)

`docs/v2/44-docs-v2-skills.md` governs format/shape; doc 46 governs repo
layout (additive, stricter-rule-wins); the skillify authoring references
govern Claude Code frontmatter mechanics; ORAMASYS-MASTERY-v3 governs
methodology; the Kungfu plan governs atom/composite/manifest specifics; the
five-owner routing table (v1 skill inventory) governs ownership. Where this
guide summarizes and a source is stricter, the source wins — file an
amendment here rather than diverging silently. This guide reconciles into
`oramasys/alexandria` after human review (canonical documentation
authority), consistent with the pointer-network single-source-of-truth
model.
