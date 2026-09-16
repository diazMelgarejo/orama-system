# Open Standard Skill Format — Part 4: Conformance and Validation

**Suite:** Open Standard Skill Format (OSSF)  
**Part:** 4 of 4 (normative)  
**Status:** 1.0.0-draft  
**Date:** 2026-09-16  

**Navigation:** [← Part 3](2026-09-16-ossf-part3-composite-consumer-profile.md) ·
[Part 0](2026-09-16-ossf-part0-introduction.md) ·
[Publication plan (informative)](2026-09-16-atomic-skill-card-format-extension-publication-plan.md)

---

## 4.1 Conformance targets

| Target | Responsibility |
| -------- | ---------------- |
| **Producer** | Authors skill cards that validate before commit/publish. |
| **Consumer** | Harness/router loads cards and dispatches by profile. |
| **Validator** | Tooling that enforces Parts 1–3 without forking rule sets. |

## 4.2 Single-validator rule

Implementations MUST provide **one** validator pipeline whose first pass is
always Part 1 (core). Profile-specific checks MUST extend that pipeline.

Implementations MUST NOT ship parallel SKILL.md validators with diverging
rules (namespace-collision script lesson applies).

**Implementation alias today:** `check_ossf1_skill_md.py` — validates Part 1
subset for staged paths; MUST be extended for profiles per this part.

**VARIABLE — pilot-gated, not locked before G2 (2026-09-16 dual review,
publication plan §14.2/§14.3, both Claude and Codex independently, Codex
Critical #1):** the "single validator pipeline" requirement above is not
currently satisfied by the named alias. `check_ossf1_skill_md.py` is
hardcoded to one repository (`bin/orama-system/`), reads only that repo's
`git diff --cached` staged index, and has no path- or repository-resolution
model for cards living in a different repository (e.g. a Kungfu kernel
repo). Extending it "in place" to cover atoms/composites elsewhere means
building real multi-repo architecture — a reusable core validation library,
explicit input modes (working tree / staged index / packaged artifact),
repository-root context, and per-repo hook/CI adapters — not a small patch
to the existing script. Until that architecture exists and is pilot-tested,
"one validator" is a design intent this part states, not a working
implementation this part can point to.

## 4.3 Validator algorithm (normative intent)

```text
validate(skill_path):
  1. Parse UTF-8 without BOM; fail if BOM present
  2. Run Part 1 (core) checks — MUST pass for all profiles
  3. Read format_profile (default: core)
  4. If composable-atom → run Part 2 checks
  5. If composite-consumer → run Part 3 checks; MUST NOT require Part 2 fields
  6. If unknown profile → fail closed
```

## 4.4 Interoperability matrix

| Card declares | Part 2 fields present | Validator result |
| --------------- | ---------------------- | ------------------ |
| `core` | absent | PASS (Part 1 only) |
| `core` | present | SHOULD warn; MAY fail in strict mode |
| `composable-atom` | required set complete | PASS |
| `composable-atom` | incomplete | FAIL |
| `composite-consumer` | absent | PASS (Part 1 + 3) |
| `composite-consumer` | present as atom fields | PASS if not required; router MUST NOT treat as atom |

## 4.5 Capability discovery

Manifest rows SHOULD record:

- `disposition: atom | composite | adapter | ...`
- `format_profile` expectation
- `source_revision` pin

Routers MUST fail closed when manifest says `atom` but card is not
`composable-atom` conforming.

## 4.6 Publication stages (informative)

See [`2026-09-16-atomic-skill-card-format-extension-publication-plan.md`](2026-09-16-atomic-skill-card-format-extension-publication-plan.md)
§7 for G0–G4 ladder (references draft → alexandria ratification).

## 4.7 Pilot exit criteria (2026-09-16, publication plan §14.4)

G2 ("Candidate draft") additionally requires, beyond §7's original exit
criteria: the pilot atom/composite (publication plan §14.3) complete, its
predeclared v1-comparison metric reported against its own threshold, and
every VARIABLE row in publication plan §14.2 — including this part's own
§4.2/§4.3 single-validator architecture and Part 2 §2.5's typed-`references`
parsing — either resolved with pilot evidence or explicitly re-classified INVARIANT
with a stated reason. This is additive to §4.2's single-validator rule, not
a relaxation of it: the rule stands as the target; this section defines what
evidence is required before claiming it is met.

## 4.8 Suite index

| Part | Document |
| ------ | ---------- |
| 0 | [`2026-09-16-ossf-part0-introduction.md`](2026-09-16-ossf-part0-introduction.md) |
| 1 | [`2026-09-16-ossf-part1-core-open-standard-skill-format.md`](2026-09-16-ossf-part1-core-open-standard-skill-format.md) |
| 2 | [`2026-09-16-ossf-part2-atomic-skill-card-format-extension.md`](2026-09-16-ossf-part2-atomic-skill-card-format-extension.md) |
| 3 | [`2026-09-16-ossf-part3-composite-consumer-profile.md`](2026-09-16-ossf-part3-composite-consumer-profile.md) |
| 4 | This document |
