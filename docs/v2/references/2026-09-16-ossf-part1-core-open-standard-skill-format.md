# Open Standard Skill Format — Part 1: Core Open Standard Skill Format

**Suite:** Open Standard Skill Format (OSSF)  
**Part:** 1 of 4 (normative)  
**Status:** 1.0.0-draft  
**Date:** 2026-09-16  

**Navigation:** [← Part 0](2026-09-16-ossf-part0-introduction.md) ·
[Part 2 Extension →](2026-09-16-ossf-part2-atomic-skill-card-format-extension.md) ·
[Construction guide (informative)](2026-09-12-v2-skill-construction-guide.md)

---

## 1.1 Scope

Part 1 defines the **core** Open Standard Skill Format — requirements that apply
to **every** skill card regardless of harness, repository, or composition role.

Part 2 (Atomic Skill Card Format Extension) and Part 3 (composite consumer)
add profile-specific rules on top of this core. Nothing in Part 1 is relaxed
by optional profiles.

## 1.2 Conformance

A skill card is **OSSF (core) conforming** when it satisfies every MUST in
this part. Validators MUST implement Part 1 checks before any profile-specific
checks (Part 4).

## 1.3 Document representation

### 1.3.1 File form

- Primary form: `SKILL.md` at the root of a skill directory.
- Encoding: UTF-8 **without** byte-order mark (BOM). A leading U+FEFF before
  the opening `---` makes frontmatter detection fail and the card MUST be
  rejected by conforming validators.
- Line endings: LF preferred; CRLF MUST NOT change semantic content.

### 1.3.2 Size

- **SHOULD** be ≤200 lines total (frontmatter + body).
- **MUST NOT** exceed 500 lines total. Excess material MUST move to
  `references/`, `instructions/`, or sibling folders per the informative
  construction guide folder shape.

## 1.4 Frontmatter (discovery layer)

Every conforming card MUST begin with YAML frontmatter delimited by `---`.

### 1.4.1 Required keys

| Key | Requirement |
| ----- | ------------- |
| `name` | MUST be present. 1–64 chars, lowercase kebab-case (or profile-specific atom ID in Part 2). MUST match directory name where the construction guide applies. |
| `description` | MUST be present. ≥20 characters. Third-person purpose text with activation context. |
| `version` | MUST be present. Semantic version string. |
| `allowed-tools` | MUST be present. Space-delimited tool capability list (e.g. `bash, file-operations`). |

### 1.4.2 Activation

The card MUST declare how harnesses discover it:

- `triggers:` list with at least one entry, **OR**
- `Activates when` / `Activates for` phrasing embedded in `description`.

### 1.4.3 Compatibility

The card MUST declare environment compatibility using **one** of:

- `compatibility:` — harness/platform list, **OR**
- `agent_compatibility:` — overlay/install mirror list (array form).

### 1.4.4 Profile declaration

`format_profile` MAY be omitted (defaults to `core`). Allowed values: `core`,
`composable-atom`, `composite-consumer`. Values outside this set MUST cause
validators to fail closed.

When omitted, conforming consumers MUST treat the card as `format_profile: core`.

**`format_profile` is the sole canonical field name (2026-09-16 dual review,
publication plan §14.2, INVARIANT).** Earlier working notes floated a
`card_kind` alias; no such alias exists in this normative text. A card MUST
NOT declare `card_kind` as a substitute — implementations that encounter it
SHOULD treat it as an unrecognized optional key (§1.4.6), never as a
profile declaration.

### 1.4.5 Listing cap

Where a harness combines `description` with `when_to_use`, the combined
character count SHOULD NOT exceed 1,536 characters (common listing cap).
`description` alone MUST still satisfy the ≥20 character floor.

### 1.4.6 Optional keys

Implementations MAY support additional frontmatter keys (argument hints,
invocation mode, path scopes) provided Part 1 requirements remain satisfied.
Optional keys MUST NOT contradict Part 1 MUST rules.

## 1.5 Body (execution layer)

### 1.5.1 Required sections

Body MUST include, in order:

1. **`## Purpose`** OR **`## When to Use`** (at least one).
2. Workflow or activation content (steps, load order, prohibitions) as needed.
3. **`## Boundaries`** with exactly these subsections:
   - `### Always Do`
   - `### Ask First`
   - `### Never Do`

Boundaries MUST NOT be removed or weakened to satisfy line limits; bulk MUST
move to `references/` instead.

### 1.5.2 Progressive disclosure

Long procedures, examples, and doctrine MUST NOT inflate the skill card.
They MUST live under `references/`, `instructions/`, `examples/`, or `eval/`
and be linked from the card.

### 1.5.3 Code fences

Markdown code fences MUST specify a language identifier where a language applies.

## 1.6 Security and portability

Skill cards are supply-chain material. Cards MUST NOT contain:

- API keys, tokens, or credentials
- Raw workstation paths or LAN-specific endpoints
- Personal or doxxing material

Use abstract placeholders and owner-boundary links for policy (informative
construction guide §7).

## 1.7 Relationship to other parts

| Profile | Part 1 | Also requires |
| --------- | -------- | --------------- |
| `core` (default) | MUST | — |
| `composable-atom` | MUST | [Part 2](2026-09-16-ossf-part2-atomic-skill-card-format-extension.md) |
| `composite-consumer` | MUST | [Part 3](2026-09-16-ossf-part3-composite-consumer-profile.md) |

Part 2 fields (`outcome`, `approval_limit`, typed `references`) MUST NOT be
required for `format_profile: core` or `composite-consumer`.

## 1.8 Minimal conforming example

```yaml
---
name: example-greeting
description: >-
  Greets the user with context-aware tone. Activates when the user asks for
  a formal or informal greeting template.
version: 1.0.0
compatibility: claude-code, cursor
triggers:
  - greeting template
  - formal greeting
allowed-tools: bash, file-operations
format_profile: core
---

## Purpose

Produce a greeting appropriate to audience level.

## When to Use

- User requests greeting wording without broader writing task.

## Boundaries

### Always Do

- Match tone to stated audience (formal vs casual).

### Ask First

- Publishing greeting text externally on user's behalf.

### Never Do

- Impersonate a real person without explicit instruction.
```

## 1.9 Informative references

- [`2026-09-12-v2-skill-construction-guide.md`](2026-09-12-v2-skill-construction-guide.md)
  §3–§5 — folder shape and content routing
- [`2026-09-12-ossf1-to-atomic-card-reconciliation-plan.md`](2026-09-12-ossf1-to-atomic-card-reconciliation-plan.md)
  — convergence from OSSF-1 implementation draft
- Implementation alias: `check_ossf1_skill_md.py` (validates Part 1 subset today)
