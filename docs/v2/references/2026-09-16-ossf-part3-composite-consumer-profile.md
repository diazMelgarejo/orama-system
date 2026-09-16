# Open Standard Skill Format — Part 3: Composite Consumer Profile

**Suite:** Open Standard Skill Format (OSSF)  
**Part:** 3 of 4 (normative)  
**Status:** 1.0.0-draft  
**Date:** 2026-09-16  

**Navigation:** [← Part 2 Extension](2026-09-16-ossf-part2-atomic-skill-card-format-extension.md) ·
[Part 1 Core](2026-09-16-ossf-part1-core-open-standard-skill-format.md) ·
[Part 4 Conformance →](2026-09-16-ossf-part4-conformance-and-validation.md)

---

## 3.1 Scope

This part defines the **composite consumer profile** — thin orchestrator skill
cards that order composable atoms without duplicating atom semantics.

Composite consumers MUST declare:

```yaml
format_profile: composite-consumer
```

They MUST satisfy [Part 1](2026-09-16-ossf-part1-core-open-standard-skill-format.md)
only. They MUST NOT be required to satisfy
[Part 2](2026-09-16-ossf-part2-atomic-skill-card-format-extension.md).

## 3.2 Conformance

A composite consumer card is conforming when:

1. Part 1 MUST rules pass.
2. `format_profile` is exactly `composite-consumer`.
3. Part 2 fields (`outcome`, `approval_limit`, typed `references` as atom
   requirements) are **absent** OR, if present for documentation only, are
   not used as dispatch requirements by conforming routers.
4. A `## Composition` section lists ordered atom references by ID.
5. Typed composite edges are defined in a companion artifact (YAML/JSON
   manifest) — not by duplicating atom Boundaries in prose.

## 3.3 Required body section: Composition

```markdown
## Composition

1. `<domain>/<verb-phrase>`
2. `<domain>/<verb-phrase>`
```

Rules:

- Entries MUST be atom IDs conforming to Part 2 naming when those atoms use
  the extension profile.
- Composite MUST NOT paste atom `## Boundaries` or owner policy into this card.
- Composite MAY include one-line role per atom (routing hint only).

## 3.4 Typed edges (companion artifact)

Composite graphs MUST declare edges separately, e.g. in
`composites/<name>.yaml` or manifest rows. Allowed edge kinds (informative
source: Kungfu MVP plan):

| Edge | Meaning |
| ------ | --------- |
| `requires-success` | Downstream atom runs only if upstream succeeded |
| `must-precede` | Ordering constraint |
| `conditional-on` | Conditional branch |
| `approval-before` | Human approval gate |
| `on-failure` | Failure handling route |

Validators for composite consumers MUST lint graph files; Part 1 card lint
alone is insufficient.

**VARIABLE — pilot-gated, not locked before G2 (2026-09-16 dual review,
publication plan §14.2/§14.3):** this companion artifact has no schema,
canonical file location, atom-resolution algorithm, `source_revision`
binding rule, or graph-conflict/cycle semantics defined anywhere in this
suite as of this draft. A validator cannot reliably lint an artifact the
standard has not yet specified. The pilot composite (publication plan §14.3)
is expected to produce a real, versioned schema for this artifact before G2;
until then, treat "declare edges in a companion artifact" as directional
intent, not an implementable requirement.

## 3.5 Example

See publication plan §11.2 or construction guide (informative) for a full
`composite-consumer` YAML example. Minimal fragment:

```yaml
---
name: review/pre-merge-integrity
format_profile: composite-consumer
description: >-
  Orchestrates pre-merge integrity atoms. Activates before merging skill
  format changes across repositories.
version: 1.0.0
compatibility: kungfu-composite
triggers: [pre-merge integrity]
allowed-tools: bash, file-operations
---

## Purpose

Order atoms; do not restate their policy.

## Composition

1. `git/verify-remote-head`
2. `security/three-gate-content-integrity`

## Boundaries

### Always Do

- Fail closed if any atom returns hard error.

### Ask First

- Skipping an atom in the chain.

### Never Do

- Duplicate atom Boundaries or owner policy prose.
```

## 3.6 Cross-references

- [Part 2](2026-09-16-ossf-part2-atomic-skill-card-format-extension.md) — atom requirements
- [Part 4](2026-09-16-ossf-part4-conformance-and-validation.md) — validator classes
- [`2026-09-14-kungfu-v2-composable-skills-mvp-plan.md`](2026-09-14-kungfu-v2-composable-skills-mvp-plan.md)
