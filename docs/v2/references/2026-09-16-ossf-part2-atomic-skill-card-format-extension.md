# Open Standard Skill Format (Atomic Skill Card Format Extension)

**Suite:** Open Standard Skill Format (OSSF)  
**Part:** 2 of 4 — **Composable-Atom Extension profile** (normative)  
**Status:** 1.0.0-draft  
**Date:** 2026-09-16  

**Navigation:** [← Part 1 Core](2026-09-16-ossf-part1-core-open-standard-skill-format.md) ·
[Part 0](2026-09-16-ossf-part0-introduction.md) ·
[Part 3 Composite →](2026-09-16-ossf-part3-composite-consumer-profile.md) ·
[Kungfu reviews Part 4 (informative)](2026-09-14-kungfu-v2-plan-reviews-ceo-eng-dx.md)

---

## 2.1 Scope

This part defines the **Atomic Skill Card Format Extension** — an optional
profile of the Open Standard Skill Format for **composable atoms and
subskills** only.

A card activates this extension by declaring:

```yaml
format_profile: composable-atom
```

**Composite consumer cards MUST NOT use this profile.** They MUST use
`format_profile: composite-consumer` per
[Part 3](2026-09-16-ossf-part3-composite-consumer-profile.md).

## 2.2 Conformance

A card is **OSSF Atomic Skill Card Extension conforming** when:

1. It satisfies every MUST in [Part 1](2026-09-16-ossf-part1-core-open-standard-skill-format.md), and
2. It satisfies every MUST in this part, and
3. `format_profile` is exactly `composable-atom`.

Validators MUST reject cards that declare `format_profile: composable-atom`
but fail Part 2.

The Part 2 required-field set (`outcome`, `approval_limit`, typed
`references`) is a **composable-atom conformance** check only. Validators MUST
NOT reject `format_profile: core` or `format_profile: composite-consumer`
cards solely because those documentation-only fields appear. Composite
consumers are governed by [Part 3](2026-09-16-ossf-part3-composite-consumer-profile.md)
(documentation-only Part 2 fields are allowed; routers MUST NOT treat the
card as an atom). `core` cards follow Part 1 plus the Part 4 matrix
(SHOULD warn; MAY fail only in an explicitly documented strict mode).

An implementation-defined migration shim that rewrites a card into
`composable-atom` MAY exist (SHOULD NOT be used in new authoring).

## 2.3 Design invariants (composable atoms)

| Invariant | Rule |
| ----------- | ------ |
| One trigger boundary | Atom MUST be activatable as a single discrete capability. |
| One outcome | Atom MUST declare exactly one observable success condition. |
| Explicit approval limits | Atom MUST declare machine-readable approval ceiling. |
| Typed references | Atom MUST link supporting material via typed reference entries. |
| No policy duplication | Security, endpoint, hardware, memory policy MUST link to owner specs, not copy prose. |
| Fail closed | Missing atom, dead reference, or stale manifest row MUST hard-error at dispatch — never silent fallback to a monolithic v1 card. |

**VARIABLE — pilot-gated, not locked before G2 (2026-09-16 dual review,
publication plan §14.2/§14.3):** these six rows are stated as prose MUSTs
with no formal registry or deterministic test per rule ("one trigger
boundary," "no policy duplication," and the atom-domain "fixed directory
set" in §2.4 are not yet machine-checkable). The pilot atom/composite
(publication plan §14.3) is expected to surface what a real test for each
row looks like; do not treat these as enforced today.

## 2.4 Frontmatter — extension fields

When `format_profile: composable-atom`, the following keys are **required**
in addition to Part 1.

| Key | Requirement |
| ----- | ------------- |
| `name` | MUST follow `<domain>/<verb-phrase>` — domain from a fixed directory set; verb imperative; no owner brand names in the atom ID. |
| `outcome` | MUST be present. States what MUST be true before success is declared (outcome-over-activity). |
| `approval_limit` | MUST be one of: `never`, `ask-first`, `auto`. |
| `references` | MUST be a YAML list of typed objects (see §2.5). At least one entry. |

### 2.4.1 Recommended keys for Kungfu implementations

`compatibility` SHOULD include `kungfu-atom` when hosted in a Kungfu kernel repo.

## 2.5 Typed `references` list

Each entry MUST be a mapping with a `type` field.

| `type` | Required fields | Semantics |
| -------- | ----------------- | ----------- |
| `owner` | `repo`, `ref` | Boundary link to policy owner (security, endpoint, hardware, memory, docs). |
| `reference` | `path` | Relative path to supporting markdown under the skill folder. |
| `pr` | `repo`, `id` | Evidence anchor for a merged or in-flight change. |

Conforming validators SHOULD verify that `reference` paths exist at validation
time and that `owner` refs resolve to known owner registry entries when a
registry is available.

**VARIABLE — pilot-gated, not locked before G2 (publication plan §14.2):**
the reference implementation alias (`check_ossf1_skill_md.py`, per Part 4
§4.2) uses a hand-rolled regex frontmatter parser that stores each
frontmatter value as a string, not a parsed structure. It cannot today parse
or validate this typed mapping list (`type` discriminator, per-type required
fields). Its list-detection heuristic (`has_list_key`) only treats a value as
a list when a line begins with `- ` (block-style). **§2.9 below is
block-style** (`references:` entries each start with `- {type: ...}`): the
inner `{...}` is a flow-style *mapping*, not a flow-style *sequence*.
`has_list_key` therefore accepts §2.9 `references` and rejects a true
flow-style sequence such as `triggers: [pre-merge integrity]` (Part 3 §3.5)
or `triggers: [cherry reanchor, rewritten history, headRefOid]`
(publication plan §11.1). A real YAML parser and versioned schema for
typed `references` are pilot deliverables, not assumed-already-true today.

## 2.6 Body — extension expectations

Part 1 body rules apply unchanged. Additionally:

- Workflow steps SHOULD be 5–10 ordered actions maximum on the card; detail
  belongs in `references/`.
- Atom cards MUST NOT embed composite-edge graphs (those belong on composite
  consumers, Part 3).

## 2.7 Packaged export (informative)

When exporting to packaged `.skill` artifacts for external harnesses, an
implementation MAY move extension fields under a `metadata:` key and trim
`description` for listing caps. The **canonical repository card** MUST retain
full Part 1 + Part 2 frontmatter. Packaged form MUST NOT be edited in place as
canonical truth.

## 2.8 Interoperability with composite consumers

- Composite consumers MUST reference atoms by `name` (atom ID).
- Composite consumers MUST NOT require atoms to expose fields beyond this part.
- If a composite lists an atom ID, that atom MUST be extension-conforming at
  the pinned `source_revision` in the manifest.

## 2.9 Normative example

```yaml
---
name: git/verify-remote-head
format_profile: composable-atom
description: >-
  Verifies local tree against the remote head OID for a named branch.
  Activates when reanchor or merge safety requires tree evidence.
version: 1.0.0
license: Apache 2.0
compatibility: kungfu-atom, claude-code
triggers:
  - verify remote head
  - headRefOid check
  - reanchor safety
allowed-tools: bash, file-operations
outcome: >-
  Validator reports match or explicit documented supersession between local
  tip and remote head OID; no message-match-only conclusion.
approval_limit: never
references:
  - {type: reference, path: references/headrefoid-diff-protocol.md}
  - {type: pr, repo: example/orama-system, id: 283}
---

## Purpose

Provide tree-evidence gate before declaring reanchor safe.

## When to Use

- After history rewrite or cherry-pick reanchor on a skill or docs branch.

## Boundaries

### Always Do

- Diff local tip against remote head OID, not commit message text alone.

### Ask First

- Force-pushing after a failed head match.

### Never Do

- Treat `cherry -v` message match as proof of content preservation.
```

## 2.10 Informative inputs

- [`2026-09-14-kungfu-v2-plan-reviews-ceo-eng-dx.md`](2026-09-14-kungfu-v2-plan-reviews-ceo-eng-dx.md)
  Part 4 — field reconciliation table
- [`2026-09-14-kungfu-v2-composable-skills-mvp-plan.md`](2026-09-14-kungfu-v2-composable-skills-mvp-plan.md)
  — atom/composite invariants, typed edges
- [`2026-09-12-v2-skill-construction-guide.md`](2026-09-12-v2-skill-construction-guide.md)
  §9 — manifest and Wave gates
