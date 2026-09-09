# Instruction Debt Remediation Plan

> **Status:** approved 2026-09-09, pending execution
> **Derived from:** [`instruction-debt-audit-2026-09-09.md`](instruction-debt-audit-2026-09-09.md)
> **Companion plans:**
> [`oramasys-migration-execution-plan.md`](oramasys-migration-execution-plan.md) ·
> [`portable-memory-sanitization-runbook.md`](portable-memory-sanitization-runbook.md)
> **Standards applied:** [doc 46 — repository standard](../46-repository-standard.md) ·
> [doc 47 — portable-memory invariant](../47-portable-memory-local-topology-invariant.md)

---

## Scope boundary

This plan covers **instruction-surface repairs only** — skill descriptions, hooks,
permissions, and completion rules. It does not move content between repositories; that is
the migration plan's job.

Findings F1 and F8 are deliberately **not** remediated here:

- **F1** (portable-memory leaks) is migration-gating and needs its own reviewed pass. It
  is [`portable-memory-sanitization-runbook.md`](portable-memory-sanitization-runbook.md).
- **F8** (root-level `scripts/`/`tests/` versus doc 46) is recorded as a **documented v1
  exception**, not fixed. v1 is working as intended and must not change. Doc 46 explicitly
  permits exceptions when documented and linked back — this plan is that documentation.

---

## Smallest useful batch — do these four first

Ordered by value per unit of risk. Roughly one working session.

| # | Finding | Change | Why first |
| --- | --- | --- | --- |
| R1 | F4 | Narrow design-skill description; identity to registry | Only change closing a live confidentiality exposure |
| R2 | F2 | Scope pytest hook to `.py` edits | One line; removes the largest recurring waste |
| R3 | F6 | Port read-only allowlist to orama-system | Adds no authority; removes approval stops |
| R4 | F5 | Delete the catch-all trigger clause | One sentence; fixes the worst over-activation |

Everything below R4 is follow-up work, valuable but not urgent.

---

## R1 — Narrow the design-skill description, move identity to the registry

**Finding:** F4 · **Disposition:** narrow trigger + clarify boundary
**File:** operator's synced skill bucket, `clarence-design-preferences/SKILL.md`

### R1a — Description

The current `description` is 950 characters and loads into every session on the account.
It contains a confidential product name. Replace with:

```yaml
description: >-
  Personal design preferences, project registry, and design-system conventions
  for the operator's UI/UX work. Use when generating, reviewing, or critiquing a
  UI/UX design, wireframe, prototype, dashboard, or design-system component, or
  when asked to match, check, or align work to the operator's style. Load before
  any Figma or Adobe tool call.
```

326 characters. Measured saving: **≈624 characters ≈ 156 tokens per session.**

**Preserves:** every real activation path — design generation, design review, style
matching, and the load-before-vendor-tool-call rule. What it drops is the enumeration of
project codenames, which was doing the confidentiality damage and little routing work: a
design request is recognisable without them.

### R1b — Identity table, lines 40-50

Replace concrete rows with local-only registry keys resolved at load time, per doc 47's
registry contract:

| Row | Current | Becomes |
| --- | --- | --- |
| Email | full literal | `owner_gmail` |
| Social profile | full URL | `owner_profile_url` |
| Name | full literal | `owner_name` |

Non-sensitive rows (title, tagline, years of experience, project count, industries) stay
tracked as-is — they are public portfolio facts and carry no invariant risk.

### R1c — Line 174, the confidentiality rule

The rule currently spells both the protected product name and the client organisation.
Replace with registry keys:

```markdown
- **Confidential:** never use `product_codename_p1` or `client_alias_p1` in any
  public-facing output. The tracked public label is "B2B SaaS BPO Platform".
```

**Preserves:** the constraint itself, and makes it *more* enforceable — a guard can now
assert the registry values never appear in output, which is impossible while the file
itself contains them.

**Acceptance:** the portable-brain guard reports zero hits on the skill bucket; the skill
still activates on a plain "review this dashboard design" request.

---

## R2 — Scope the pytest hook to Python edits

**Finding:** F2 · **Disposition:** narrow trigger
**File:** `Perpetua-Tools/.claude/settings.json:77`

Current — runs the whole suite on any file type:

```json
"command": "[[ -f pyproject.toml ]] && python -m pytest tests/ -x -q --tb=short 2>&1 | tail -12 || true"
```

Replacement:

```json
"command": "payload=$(cat); file=$(printf '%s' \"$payload\" | python3 -c \"import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))\" 2>/dev/null); case \"$file\" in *.py) [[ -f pyproject.toml ]] && python -m pytest tests/ -x -q --tb=short 2>&1 | tail -30 ;; *) true ;; esac"
```

Three changes: reads the path from stdin JSON rather than assuming a suite run is always
wanted; gates on `.py`; raises `tail` from 12 to 30 so a caught failure is actionable.

**Preserves:** fast feedback on Python edits — the reason the hook exists.

**Stronger alternative, if the operator prefers:** move the suite to a `Stop` hook so one
run covers an entire edit burst instead of firing per-edit. That is a larger behavioural
change and is offered, not assumed.

**Acceptance:** editing a `.md` file triggers no suite run; editing a `.py` file does.

---

## R3 — Repair the ruff hook and align permission allowlists

**Findings:** F3, F6 · **Disposition:** repair + clarify boundary

### R3a — Ruff hook (both repos)

**Files:** `orama-system/.claude/settings.json:42`,
`Perpetua-Tools/.claude/settings.json:68`

Read stdin first, keep the environment variable as fallback — mirroring the pattern
already proven in `Perpetua-Tools/.agent/harness/hooks/claude_code_post_tool.py:658-681`:

```json
"command": "payload=$(cat); file=$(printf '%s' \"$payload\" | python3 -c \"import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))\" 2>/dev/null); [ -z \"$file\" ] && file=$(python3 -c \"import os,json;print(json.loads(os.environ.get('CLAUDE_TOOL_INPUT','{}')).get('file_path',''))\" 2>/dev/null); [[ \"$file\" == *.py ]] && ruff check \"$file\" 2>&1 | head -10 || true"
```

**Preserves:** per-file ruff feedback on Python edits, and backward compatibility with
older harnesses through the retained fallback.

**Do not skip the confirming task.** F3's runtime claim is a hypothesis. Before and after
the change, edit a `.py` file containing a deliberate lint error and record whether ruff
output appears. If it already appears, this repair is unnecessary and should be dropped.

### R3b — orama-system permission allowlist

**File:** `orama-system/.claude/settings.json`, `permissions.allow`

Add the read-only entries already proven in Perpetua-Tools:

```json
"Bash(git status *)",
"Bash(git log *)",
"Bash(git diff *)",
"Bash(git show *)",
"Bash(git branch *)",
"Bash(git rev-parse *)",
"Bash(grep *)",
"Bash(rg *)",
"Bash(find *)",
"Bash(jq *)",
"Bash(sort *)",
"Bash(uniq *)"
```

**Preserves the write boundary exactly.** This adds **no** mutating verb: no `git push`,
no `git commit`, no `rm`, no `gh pr merge`, no deploy command. It removes approval stops on
reads only. The existing five entries stay.

**Explicitly not proposed:** broadening `Bash(git *)` or any wildcard that would sweep in
mutating subcommands. The value here comes from being narrow.

**Acceptance:** a `git status` in an orama-system session raises no approval prompt; a
`git push` still does.

---

## R4 — Fix the over-broad trigger and the visual-verification collision

**Finding:** F5, S3 · **Disposition:** narrow trigger + clarify boundary
**File:** `orama-system/bin/orama-system/skills/oramasys-method/SKILL.md` (canonical)

### R4a — Delete the catch-all clause

Remove from the description:

> If a request is non-trivial, multi-step, or design-heavy, prefer this skill.

The packaged 1.3.0 description is already the model: explicit trigger words, no catch-all.
Adopt it as canonical.

**Preserves:** every genuine trigger — the "ultrathink"/"oramasys" aliases, architecture
and re-architecture work, complex refactors, system overhauls, and the PR-merge and
conflict-resolution triggers. What it drops is the clause that made the skill argue for
its own activation on trivial work.

### R4b — Scope the visual-verification rule

The rule currently reads as an absolute and collides with design review (scenario S3).
Replace with:

```markdown
- Never trust visual confirmation as verification **of code correctness** — run the tests.
  Visual review remains the correct check for design fidelity and UI appearance.
```

**Preserves:** the real constraint — that a screenshot is not proof the code works — while
removing the contradiction that fires whenever a design task and a methodology task
overlap.

---

## R5 — Generate skill wrappers instead of hand-copying them

**Finding:** F5 · **Disposition:** split (mechanise the duplication)

29 of 36 wrapper descriptions have drifted from canonical. Hand-fixing them fixes today
and not tomorrow.

**New file:** `orama-system/src/tools/sync_skill_wrappers.py`

Note the path: `src/`, per doc 46, **not** root `scripts/`. New tooling conforms to the
standard even though the surrounding legacy tree does not — this is how F8's exception
stays bounded rather than compounding.

Behaviour:

1. For each canonical skill in `bin/orama-system/skills/<name>/SKILL.md`, read the
   frontmatter.
2. Regenerate the matching wrapper's frontmatter verbatim, preserving the wrapper body
   (the thin-wrapper pointer text) untouched.
3. `--check` mode exits non-zero on any drift, for CI.

Wire `--check` into the existing lint job. Once green, wrapper drift becomes impossible
rather than merely fixed.

**Preserves:** the thin-wrapper architecture completely. This mechanises the sync; it does
not change the pattern.

**Sequencing note:** this must land **before** Wave 4 of the migration. Migrating 29
drifted descriptions would carry the drift across the org boundary permanently.

---

## R6 — Gate the lessons write-back warning behind a size threshold

**Finding:** F7 · **Disposition:** narrow trigger
**File:** `orama-system/.claude/settings.json:52`

```bash
changed=$(git diff --name-only HEAD 2>/dev/null | grep -vc '^\.claude/lessons/' || echo 0)
[ "$changed" -ge 3 ] && {
  git diff --name-only HEAD -- .claude/lessons/ 2>/dev/null | grep -q . \
    || echo 'NOTE: 3+ files changed and .claude/lessons/ was not updated — consider a write-back.'
}
true
```

**Preserves:** the write-back discipline on substantial sessions, which is where the
practice earns its keep. A question-answering session or a one-line fix no longer gets
told it violated a requirement.

**Threshold rationale:** three changed files is a judgement call, not a measurement. If it
proves wrong in practice, it is one number to tune — which is the point of putting it in a
variable rather than leaving the rule unconditional.

---

## R7 — Add explicit completion rules to the always-loaded layer

**Finding:** F9 · **Disposition:** keep and extend
**Files:** `orama-system/CLAUDE.md`, `Perpetua-Tools/CLAUDE.md`

The completion rules currently live only inside `oramasys-method`, which means they arrive
either with a full five-stage methodology attached or not at all. Promote the minimum to
the always-loaded layer:

```markdown
## Done means

- Docs- or comment-only change: no test run required.
- Code change: run the tests covering the touched module, not the full suite.
- A test already failing on the base commit does not block your change — say so, and
  continue.
- Blocked means: a missing credential, an ambiguous requirement, or a destructive action
  needing approval. Everything else: proceed and report.
```

Six lines. **Preserves:** the TDD gate for real code changes, which `oramasys-method`
continues to own in full. What it adds is a floor that applies without activating the
methodology — and it removes the implicit "always run everything" that F2's hook currently
teaches by example.

---

## Execution order and verification

```text
R1 ──> R2 ──> R3 ──> R4        (the approved first batch, one session)
                      │
                      └──> R5 ──> R6 ──> R7   (follow-up, before migration Wave 4)
```

R5 is the only item with a hard downstream dependency: it must precede migration Wave 4.

### Verification table

| Check | Before | Target |
| --- | --- | --- |
| Non-benign literals in `.agent/` scan | 21 | **0** (runbook, not this plan) |
| Wrapper/canonical description drift | 29 of 36 | **0** |
| Suite runs per 10-file docs edit | 10 | **0** |
| Approval prompts for `git status` in orama-system | every time | **0** |
| Ruff output on a deliberately bad `.py` edit | none (dead) | **lint appears** |
| Design-skill description length | 950 chars | **326 chars** |

### Comparison task for the uncertain items

R3a and R4 rest partly on hypothesis. Before committing to them, run one typo fix and one
small refactor in each repo, before and after the change. Count approval prompts, suite
runs, and which skills activated. That distinguishes a real improvement from a plausible
one — and R3a in particular should be dropped if ruff turns out to fire already.

**Do not assume an instruction is obsolete because the model is newer.** Every disposition
above rests on measured drift, a documented internal contradiction, or a stated standard in
docs 46 or 47 — not on the age of the rule.
