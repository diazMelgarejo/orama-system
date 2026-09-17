# Open Standard Skill Format — Part 0: Introduction

**Suite:** Open Standard Skill Format (OSSF)  
**Status:** 1.0.0-draft — mock publication target (`references/` only; G0 complete)  
**Version:** 1.0.0-draft  
**Date:** 2026-09-16  

---

## 0.1 Scope

This multi-part draft defines a **vendor-neutral**, **implementation-neutral**
standard for agent skill cards (`SKILL.md` and packaged equivalents). It
specifies:

- required structure for every skill card (**OSSF core**),
- an optional extension profile for composable atomic subskills,
- rules for composite consumer cards that orchestrate atoms without duplicating
  their semantics,
- conformance classes for producers, consumers, and validators.

This standard deliberately excludes implementation-specific names, repositories,
or harness brands from normative text. Implementations (validators, manifests,
routers) MAY map to this standard without being named here.

**Scope of the neutrality claim (2026-09-16 dual review, publication plan
§14):** "implementation-neutral" applies to naming and normative
*requirements* — it does not yet mean the suite is binding-neutral. Part 1
§1.4.1/§1.3.1 mandates a concrete binding (a `SKILL.md` file, specific
Markdown section hierarchy, directory-name matching). That binding is a
deliberate reference implementation choice for this publication, not proof
that an alternative binding (a different filename, a different structural
container) would be equally conforming today. Treat "implementation-neutral"
as "names no specific harness/vendor," not "binding-agnostic," until a
second concrete binding is demonstrated.

## 0.2 Suite map (normative parts)

| Part | Title | Normative? | File |
| ------ | ------- | ------------ | ------ |
| **0** | Introduction | Informative + registry | [`2026-09-16-ossf-part0-introduction.md`](2026-09-16-ossf-part0-introduction.md) |
| **1** | Core Open Standard Skill Format | **Normative** | [`2026-09-16-ossf-part1-core-open-standard-skill-format.md`](2026-09-16-ossf-part1-core-open-standard-skill-format.md) |
| **2** | Open Standard Skill Format (Atomic Skill Card Format Extension) | **Normative (profile)** | [`2026-09-16-ossf-part2-atomic-skill-card-format-extension.md`](2026-09-16-ossf-part2-atomic-skill-card-format-extension.md) |
| **3** | Composite consumer profile | **Normative** | [`2026-09-16-ossf-part3-composite-consumer-profile.md`](2026-09-16-ossf-part3-composite-consumer-profile.md) |
| **4** | Conformance and validation | **Normative** | [`2026-09-16-ossf-part4-conformance-and-validation.md`](2026-09-16-ossf-part4-conformance-and-validation.md) |

**Informative companions (not normative):**

| Document | Role |
| ---------- | ------ |
| [`2026-09-12-v2-skill-construction-guide.md`](2026-09-12-v2-skill-construction-guide.md) | Onboarding hub — altitude routing, folder shape, methodology |
| [`2026-09-12-ossf1-to-atomic-card-reconciliation-plan.md`](2026-09-12-ossf1-to-atomic-card-reconciliation-plan.md) | Convergence record (2026-09-16 applied) |
| [`2026-09-16-atomic-skill-card-format-extension-publication-plan.md`](2026-09-16-atomic-skill-card-format-extension-publication-plan.md) | Publication ladder and open-standards research |
| [`2026-09-14-kungfu-v2-plan-reviews-ceo-eng-dx.md`](2026-09-14-kungfu-v2-plan-reviews-ceo-eng-dx.md) Part 4 | Atom frontmatter reconciliation (informative input) |

## 0.3 Terminology

| Term | Definition |
| ------ | ------------ |
| **OSSF** | Open Standard Skill Format — the suite name for this draft publication. |
| **OSSF (core)** | Part 1 — required rules for every skill card. |
| **OSSF (Atomic Skill Card Format Extension)** | Part 2 — optional profile for composable atoms; abbreviated **OSSF-ASCFE** in tables only. |
| **Skill card** | A `SKILL.md` file or packaged skill artifact with YAML frontmatter and markdown body. |
| **Composable atom** | A skill card with one trigger boundary and one outcome, composed by higher-level workflows. |
| **Composite consumer** | A thin orchestrator card that orders atom references; does not require Part 2 fields. |
| **Profile** | A named conformance subset declared via `format_profile` in frontmatter. |

## 0.4 Requirement language (BCP 14)

Normative parts use RFC 2119 / RFC 8174 keywords. The key words "MUST",
"MUST NOT", "SHOULD", "SHOULD NOT", "MAY", and "OPTIONAL" in normative parts
are to be interpreted as described in those documents.

## 0.5 Lineage (informative — retires nothing)

```text
USF-1 fusion inventory (2026-08-07, skill-format-fusion spec)
  → OSSF draft v1 implementation ("OSSF-1" working name, 2026-08-08 hook)
    → doc 44 folder/size/dry-run baseline
      → OSSF (core) Part 1 [this publication]
        → OSSF (Atomic Skill Card Format Extension) Part 2 [optional profile]
          → Composite consumer Part 3
```

Earlier working names **"Oramasys Standard Skill Format"** and **"Oramasys
Atomic Skill Card Format"** are superseded by **Open Standard Skill Format**
for normative publication. Historical commits and hook filenames MAY retain
`ossf1` labels as implementation aliases until validators are renamed in a
separate change.

## 0.6 Conformance profiles (overview)

| `format_profile` | Parts required | Typical use |
| ------------------ | ---------------- | ------------- |
| *(absent)* or `core` | Part 1 only | Generic skills, adapters, orbit packages |
| `composable-atom` | Part 1 + Part 2 | Kungfu atoms, composable subskills |
| `composite-consumer` | Part 1 + Part 3 | Kungfu composites, thin orchestrators |

See Part 4 for producer/consumer/validator classes.

## 0.7 Publication target (mock)

This suite is a **draft specification** staged in the OpenClaw references
working tree for manual review. Target ratification path: `oramasys/alexandria`
(canonical documentation authority) after G1–G3 gates in the publication plan.
Until ratification, informative guides MUST cite these parts by filename and
version `1.0.0-draft`.

**Mirror status (2026-09-16, publication plan §14):** a sanitized copy of
this suite is also staged, informative-only, under `orama-system`'s
`docs/v2/references/` for repo-local visibility. That mirror is not the
canonical source — this working tree is — and carries the same
`1.0.0-draft` / non-ratified status. Do not edit the mirror independently;
changes flow from this canonical location outward.
