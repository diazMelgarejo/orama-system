# Instruction Debt Audit — Agent Setup, 2026-09-09

> **Status:** completed audit, findings pending remediation approval
> **Scope:** always-loaded instructions, skill discovery metadata, hooks, permissions,
> completion rules across `diazMelgarejo/orama-system`, `diazMelgarejo/Perpetua-Tools`,
> and the operator's synced skill bucket.
> **Derived plans:**
> [`instruction-debt-remediation-plan.md`](instruction-debt-remediation-plan.md) ·
> [`oramasys-migration-execution-plan.md`](oramasys-migration-execution-plan.md) ·
> [`portable-memory-sanitization-runbook.md`](portable-memory-sanitization-runbook.md)
> **Standards applied:** [doc 46 — repository standard](../46-repository-standard.md) ·
> [doc 47 — portable-memory invariant](../47-portable-memory-local-topology-invariant.md)

---

## Redaction notice

Every sensitive fragment in this document is named by **category only**, per doc 47's
documentation rule: *"Docs must not include the concrete string form of the prohibited
fragment just to explain what is prohibited."*

No email, workstation path, client name, product codename, or dotted-quad address literal
is reproduced anywhere in this audit or its derived plans. Network findings use CIDR-block
notation, which is both accurate and `LINT-013`-clean.

## Method

Read-only inspection. No file, setting, or repository was modified during the audit.
Both legacy repos and all six `oramasys/*` targets were cloned for inspection.
Measurements are programmatic where stated; predictions are labelled as hypotheses.

---

## Findings, highest impact first

### F1 — Portable memory carries live leaks and is on the migration path

**Severity: critical · Confirmed (measured)**

Category scan of `Perpetua-Tools/.agent/` (825 files):

| Category | Files | Lines |
| --- | --- | --- |
| Non-benign full email literals | 7 | 10 |
| RFC1918 `192.168/16` block literals | — | 15 |
| Link-local `169.254/16` block literals | — | 6 |
| API-key-shaped literals | 1 | 2 |
| Personal home-directory paths | 0 | 0 |

Benign synthetic hits (`anthropic.com` ×8, `example.com` ×3) were correctly excluded from
the non-benign counts.

Affected paths — **both source rows and derived views**:

```text
.agent/memory/episodic/AGENT_LEARNINGS.jsonl       <- source row
.agent/memory/semantic/lessons.jsonl               <- source row
.agent/memory/candidates/graduated/<id>.json       <- source row
.agent/memory/semantic/LESSONS.md                  <- derived view
.agent/memory/semantic/DECISIONS.md                <- derived view
```

This is the exact failure doc 47 exists to prevent, and it is the
*supersession-is-not-sanitization* case verbatim. Doc 47's acceptance criterion reads:

> A whole `.agent/` or equivalent portable-memory scan reports zero hits.

Doc 47 binds *"every future `oramasys/*`, `perpetua-core/*`, and sibling agentic repo that
carries portable memory."* The moment this tree lands in a successor repo, that repo is
born in violation of its own governing invariant.

**Disposition:** gate, do not copy. Sanitize source rows, regenerate derived views,
re-scan to zero, then migrate. Full procedure in
[`portable-memory-sanitization-runbook.md`](portable-memory-sanitization-runbook.md).

**Preserves:** the memory itself. Per the operator's standing rule — *do not amputate
memory to fix a leak.* Nothing here proposes dropping `.agent/`; it proposes cleaning the
source before it crosses the org boundary.

---

### F2 — Full test suite runs on every file edit

**Severity: high · Confirmed**

`Perpetua-Tools/.claude/settings.json:77`, `PostToolUse` matcher `Edit|Write`:

```json
"command": "[[ -f pyproject.toml ]] && python -m pytest tests/ -x -q --tb=short 2>&1 | tail -12 || true"
```

The matcher covers **every file type**. Editing a Markdown, YAML, or JSON file runs the
entire 143-file pytest suite. A ten-file documentation pass triggers ten full suite runs,
none of them requested.

Two compounding defects:

- `|| true` discards the exit code, so a genuine failure is advisory noise, not a gate.
- `tail -12` truncates output, so when it does catch a real break the failing test is
  often not visible without re-running.

**Disposition:** narrow trigger, scale verification to the change. See remediation plan
R2.

---

### F3 — The lint safeguard is silently dead in both repos

**Severity: high · Confirmed by internal evidence · Runtime behaviour is a hypothesis**

`orama-system/.claude/settings.json:42` and `Perpetua-Tools/.claude/settings.json:68` are
byte-identical:

```bash
file=$(python3 -c "... os.environ.get('CLAUDE_TOOL_INPUT','{}') ...")
[[ "$file" == *.py ]] && ruff check "$file" 2>&1 | head -10 || true
```

The hook reads the target path from the `CLAUDE_TOOL_INPUT` environment variable. Current
Claude Code delivers hook payloads as **JSON on stdin**. When the variable is unset the
expression yields an empty string, the `[[ ]]` test fails, and `|| true` swallows the
result — the hook exits 0 having linted nothing, on every invocation, invisibly.

The evidence that this is staleness rather than intent is in the operator's own tree:
`Perpetua-Tools/.agent/harness/hooks/claude_code_post_tool.py:658-681` reads **stdin
first** and documents the environment variable as the fallback for *"older Claude Code
versions, or empty stdin."* The sibling inline hooks never received that upgrade.

**Disposition:** repair, do not remove — the intent is sound. See R3.

**Confirming task:** edit one `.py` file with a deliberate lint error and observe whether
ruff output appears. Two minutes, and it settles whether this is dead or live in the
operator's harness version.

---

### F4 — Always-loaded skill metadata carries identity and a confidential client name

**Severity: high (confidentiality, not context budget) · Confirmed**

Operator's synced skill bucket, `clarence-design-preferences/SKILL.md`:

- Line 42 — full personal email literal
- Line 43 — personal social profile URL
- Line 174 — a confidentiality rule that spells the protected product name and the client
  organisation name it exists to protect

Two distinct problems:

**(a) The self-defeating negative rule.** Line 174 forbids a name by spelling it. This is
precisely the anti-pattern doc 47 codifies and that the operator's own standing invariant
names: *a negative rule that quotes the secret it forbids is self-defeating.*

**(b) The protected name is also in the skill's `description`.** That description is 950
characters and loads into the **system prompt of every session on the account**, whether
or not any design work occurs. The identity table at lines 40-50 is `SKILL.md` body and
therefore loads only on activation; the description has no such protection.

**Disposition:** narrow the description, move concrete identity to the local-only registry.
See R1 — this is the only finding that closes a live confidentiality exposure, and it is
first in the remediation batch.

---

### F5 — Over-broad skill trigger, and 29 skills advertising stale descriptions

**Severity: medium-high · Confirmed (measured)**

`orama-system/.claude/skills/oramasys-method/SKILL.md` — the thin wrapper, version 1.2.0,
which is the copy the harness reads for discovery:

> "**ALWAYS** use this skill when the user says … **If a request is non-trivial,
> multi-step, or design-heavy, prefer this skill.**"

The final clause has no boundary. Nearly every engineering request is non-trivial or
multi-step, so the rule as written argues for loading a mandatory five-stage methodology —
AFRP gate, CIDF, five stages, six directives — onto a two-line bug fix.

The packaged 1.3.0 copy in the operator's synced bucket already fixed this: 258
characters, an explicit trigger-word list, no catch-all clause. The wrapper is 1,231
characters — **973 characters longer, and it is the stale one.**

This is not isolated. Measured across all comparable pairs in
`orama-system/.claude/skills/` versus `bin/orama-system/skills/`:

| Comparison | Count |
| --- | --- |
| Wrapper description identical to canonical | 7 |
| Wrapper description drifted from canonical | **29** |

Because the wrapper is what the harness loads for discovery, **29 skills currently
advertise themselves with text their canonical body no longer says.** Five drifted
*shorter*, which is the worse direction — those skills are now under-described and will
fail to activate when they should:

| Skill | Wrapper | Canonical | Delta |
| --- | --- | --- | --- |
| `oramasys-method` | 1231 | 258 | **+973** |
| `perpetua-hardware` | 81 | 419 | −338 |
| `cline-openclaw-agent` | 229 | 540 | −311 |
| `cursor-pr-body` | 109 | 399 | −290 |
| `git-pending-push-guard` | 80 | 370 | −290 |
| `periscope-ecc` | 94 | 382 | −288 |

**The thin-wrapper pattern itself is correct and must be preserved.** It is what
`skillify` prescribes — *"create thin wrappers only; never copy canonical skill bodies
into local wrapper dirs"* — and it is the right way to serve two skill roots. The defect
is that the description is duplicated by hand and drifts. See R4 and R5.

---

### F6 — Permission allowlists are inconsistent between two repos with one operator

**Severity: medium · Confirmed**

| Capability | `orama-system` | `Perpetua-Tools` |
| --- | --- | --- |
| Allowlist entries | **5** | **31** |
| `git status` / `log` / `diff` pre-approved | no | yes |
| `grep` / `rg` / `find` / `jq` pre-approved | no | yes |
| MCP read tools pre-approved | no | yes (5) |

`orama-system/.claude/settings.json` allows only `command -v`, `claude mcp list`,
`gstack-config get`, `openclaw mcp list`, and `openclaw mcp show`. None of the routine
read-only operations. Every `git status` in an orama-system session is an approval stop.

The Perpetua-Tools list is well-built: read-only verbs only, no `git push`, no
`git commit`, no `rm`, no `gh pr merge`. **That is the correct boundary and should become
the shared baseline.** See R3.

**Also noted:** the audit's own session workspace had no project `.claude/settings.json`
at all, inheriting only `{"permissions":{"allow":["Skill"]}}`. Every read in that session
was an unallowlisted call.

---

### F7 — Stop hook demands a lessons write-back on every session at any size

**Severity: medium · Confirmed**

`orama-system/.claude/settings.json:52`:

```bash
git diff --name-only HEAD -- .claude/lessons/ 2>/dev/null | grep -q . \
  || echo 'LESSONS.md not updated this session — CLAUDE.md requires a write-back before ending.'
```

**Accuracy note:** this does **not** block. `echo` exits 0, so the hook always succeeds.
It is advisory noise, not a trap.

The defect is that it is unconditional. A session that answered a single question, or
fixed one typo, is told it violated a `CLAUDE.md` requirement. Warnings that fire when
nothing is wrong stop being read — including on the sessions where a lessons write-back
genuinely mattered. See R6.

---

### F8 — Both legacy repos violate their own repository standard

**Severity: medium (migration-blocking, not runtime) · Confirmed**

Doc 46 states: *"Everything executable belongs under `/src`. No root-level: `scripts`,
`tests`, `tools`, `examples`."* Status: active, cross-cutting, applies to every
`docs/v2/*` plan.

| Repo | root `scripts/` | root `tests/` | root `examples/` |
| --- | --- | --- | --- |
| `orama-system` | 189 files | 124 files | 9 files |
| `Perpetua-Tools` | 112 files | 143 files | — |

Every `oramasys/*` target **already conforms**: `src/<pkg>/` plus `src/tests/`, with a
`pyproject.toml` using hatchling src-layout.

This is the single most important structural fact for the migration: a lift-and-shift of
either legacy tree would import the violation into clean-room repos that are currently
compliant. F2's pytest hook is also coupled to the non-conformant root `tests/` path and
would break against a conforming target.

**Disposition:** keep the standard; treat it as the migration's acceptance criterion, not
as a defect to fix in v1. v1 is working as intended and must not change — doc 46
explicitly permits documented exceptions. Record the exception in v1, enforce the standard
in v2.

---

### F9 — Completion rules are missing from the always-loaded layer

**Severity: medium · Confirmed by absence**

Across every scenario traced in the next section, the always-loaded layer never answers:

- Does a **pre-existing** failing test block the current change?
- What verification does a documentation-only change require?
- When is a task done, versus blocked and waiting on the operator?

`oramasys-method` answers these well — but only once activated, and its own trigger is
the over-broad one from F5. The rules therefore arrive either with a heavyweight
methodology attached or not at all. See R7.

---

## What is already well scoped — do not touch

Genuine engineering, recorded here so no future cleanup pass removes it:

- **The thin-wrapper skill pattern.** Correct, deliberate, matches `skillify` doctrine.
  Only the description sync is broken (F5), not the design.
- **Docs 46 and 47 as a pair.** 46 governs *where things live*, 47 governs *what they may
  contain*, and both declare themselves additive rather than overriding. Well-constructed
  policy layering.
- **The `oramasys-method` skill body.** 200 lines, real progressive disclosure into eight
  `references/` files, explicit Always / Ask-First / Never boundaries, an `eval/` folder.
  A well-built skill; only its wrapper description is over-broad.
- **`Perpetua-Tools/.claude/settings.json` allowlist.** Read-only verbs only. Correct.
- **`.agent/harness/hooks/claude_code_post_tool.py`.** Reads stdin with an environment
  fallback — the robust pattern its sibling inline hooks lack.
- **Target-repo boundary docs.** `telos` and `phylax` both ship `docs/BOUNDARIES.md`
  stating what they explicitly do not own. Unusually disciplined.
- **`CLAUDE.md` and `AGENTS.md` are not duplicates.** Measured: 2 shared non-blank lines
  in orama-system, 3 in Perpetua-Tools. Genuinely distinct documents. No action.
- **All four platform hooks in the operator's harness home.** Vendor-managed, not
  operator-authored. Two are inert in the audited session — their environment gates were
  unset. Zero cost, nothing to do.

---

## Inventory and coverage

### Fully inspected

| Layer | Artifact | Result |
| --- | --- | --- |
| Session preferences | operator preferences block | Audited; see note below |
| Platform hooks | 4 scripts in harness home | Read; 2 inert (env gates unset) |
| Launcher config | `launcher-settings.json` | Read: 2 hooks, 1 permission entry |
| Skill metadata | 16 synced skills, `manifest.json` | Measured: 8,389 desc chars ≈ 2,100 tokens |
| Custom skills | `oramasys-method`, `skillify`, design-preferences | Full `SKILL.md` read |
| Legacy repo config | both `.claude/settings.json` | Full read plus hook analysis |
| Legacy instructions | `CLAUDE.md`, `AGENTS.md`, `SKILL.md` ×2 | Sizes and overlap measured |
| Skill drift | 36 wrapper/canonical pairs | Programmatic diff; 29 drifted |
| Memory hygiene | `Perpetua-Tools/.agent/` (825 files) | Category scan, 4 categories |
| Migration standards | docs 18, 41, 46, 47 | Read in full |
| Target repos | all 6 `oramasys/*` | Cloned; file lists and READMEs read |

### Inspected by metadata only

62 canonical skill bodies in `bin/orama-system/skills/` and 39 in
`Perpetua-Tools/.claude/skills/`, plus the `docs/v2/` tree beyond docs 18, 41, 46, and 47.
Their **descriptions** — the always-loaded layer — were audited programmatically across
all 36 comparable pairs, but the bodies were not read individually. A per-skill body audit
of 100-plus skills is a separate engagement, scoped as Wave 4 of the migration plan.

### Access gaps

| Item | Why |
| --- | --- |
| Push access to any `oramasys/*` repo | Cross-tier attach refused by the session harness |
| Push access to `diazMelgarejo/*` | Same cross-tier restriction |
| The local-only registry | Outside git by design. Correct. |
| Whether hooks fire in the live harness | Not executable from the audit session; F3 labelled accordingly |

### Note on the operator preferences block

The preferences block states the portable-memory invariant correctly, and its own trailing
lines then carry a workstation path literal and a personal-directory path. By the block's
own rule those belong in the local-only registry, referenced by key. This is the one place
where the invariant is stated and violated in the same document — worth fixing first,
because it is the source everything else derives from. Those literals are not reproduced
anywhere in this audit.

### Measured context figures

Only two figures here are measured, both from the synced skill `manifest.json`: total
skill-description load is **8,389 characters ≈ 2,100 tokens**, and the F4 description
rewrite saves **≈624 characters ≈ 156 tokens** per session. Everything else in this audit
is a correctness or friction finding rather than a context-budget one. No token savings
are estimated that were not measured.

---

## Scenario walkthroughs

Paper traces against the instruction set as it stands. Nothing was executed. All predicted
behaviour is **hypothesis**.

### S1 — Typo fix in a Markdown file (Perpetua-Tools)

```text
request -> CLAUDE.md (343 ln) + AGENTS.md (139 ln) + SKILL.md (483 ln) always loaded
        -> Edit
        -> PostToolUse fires 3 hooks:
             ruff hook     -> silently no-ops (F3)
             pytest hook   -> RUNS 143-FILE SUITE on a .md typo (F2)
             harness hook  -> runs correctly
        -> Stop -> git-check demands commit and push
```

**Predicted friction:** a full test suite for a typo. If any test is already red, F2's
`|| true` prints a truncated failure the agent did not cause — a strong pull toward
investigating an unrelated failure mid-typo-fix. The worst offender in the audit.

### S2 — Database migration

```text
request -> oramasys-method wrapper: "non-trivial/multi-step -> prefer this skill" (F5)
        -> loads AFRP gate + 5 stages + 6 directives + references/
        -> Ask-First boundary correctly catches "any destructive action"
        -> PostToolUse pytest on every migration-file write (F2)
```

**Predicted:** the safeguard works. `oramasys-method`'s *Ask First: any destructive
action* is exactly right for a migration and must be preserved. The friction is that the
same heavyweight load also attaches to trivial tasks, which is what R4 narrows.

### S3 — UI change requiring visual inspection

```text
request -> design-preferences skill activates (correct)
        -> "always call the vendor init tool first" + Figma routing
        -> oramasys-method: "Never trust visual confirmation as verification"
```

**Predicted conflict:** the design skill's entire purpose is visual review; the method
skill forbids visual confirmation as *verification*. Both are correct in their own domain
and neither says so. A UI task loading both gets a contradiction with no precedence rule.
Fix in R4b.

### S4 — A local test fails

```text
failing test -> F2's pytest hook already ran it, output truncated to 12 lines
             -> `|| true` means non-blocking -> agent may proceed past a real break
             -> oramasys-method "Verify before done" + TDD gate -> correctly pulls back
             -> Stop hook demands commit and push
```

**Predicted:** two rules in tension. The hook treats failures as advisory; the method
skill treats verification as mandatory. The method skill is right. The hook should either
gate properly or stop presenting itself as a check. Nothing in the always-loaded layer
says whether a pre-existing red test blocks the current change — the F9 gap.

### S5 — Deployment requiring approval

```text
request -> no allowlist entry matches deploy verbs (correct)
        -> oramasys-method "Ask First: any destructive action" (correct)
        -> Stop hook demands commit and push
        -> PR template and draft-PR rule apply
```

**Predicted:** this one behaves. The approval boundary holds in both repos. No change
proposed; recorded to confirm the gate is real.

---

## Cross-references

- Exact edits, batched by risk:
  [`instruction-debt-remediation-plan.md`](instruction-debt-remediation-plan.md)
- Migration waves and sequencing:
  [`oramasys-migration-execution-plan.md`](oramasys-migration-execution-plan.md)
- F1 procedure: [`portable-memory-sanitization-runbook.md`](portable-memory-sanitization-runbook.md)
