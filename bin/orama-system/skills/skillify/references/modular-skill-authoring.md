# Modular Skill Authoring Reference

Use this file after `skillify/SKILL.md` activates. The always-loaded skill file stays short; this reference carries the working procedure.

## Purpose

Create skills that are easy to trigger, easy to audit, and hard to misuse.

## Claude Code Skill Standards To Preserve

Source: `https://code.claude.com/docs/en/skills`

- Keep `SKILL.md` as the discovery and orchestration card.
- Put detailed rules, examples, templates, and checklists in one-level modular files.
- Split trigger text between `description` and `when_to_use`; keep their combined listing text <= 1,536 characters.
- Use `disable-model-invocation: true` for side-effect skills that must be invoked explicitly.
- Use `user-invocable: false` for background doctrine skills that should not appear as user commands.
- Use `context: fork` plus `agent:` for isolated review, research, QA, or harness execution.
- Use `argument-hint`, `arguments`, `$ARGUMENTS`, `$0`, and named arguments for reusable invocations.
- Prefer `${CLAUDE_SKILL_DIR}` for bundled scripts and `${CLAUDE_PROJECT_DIR}` for project-local scripts.
- Treat dynamic context injection as pre-execution shell: scope tools narrowly and avoid it in auto-triggered side-effect skills.
- Treat skills as executable supply-chain material: audit scripts, tool use, network use, hooks, and security-relevant scope.
- Before merging skill doc changes, read [`skill-security-wording-reference-card.md`](skill-security-wording-reference-card.md) — production skills use safe wording only; literal bad→good pairs belong in [`../examples/bad/security-wording-anti-patterns.md`](../examples/bad/security-wording-anti-patterns.md) with `aguara-ignore-next-line` quarantine (never copy bad lines into `SKILL.md`).

## Intake Questions

Ask for:

1. Skill name: lowercase kebab-case, 1-64 chars, matching directory name.
2. Purpose: one third-person sentence with trigger contexts.
3. Target harness: orama-system, gstack, raw Claude Code, Codex wrapper, ECC, or all applicable.
4. Trigger phrases: what the user would actually type.
5. Boundaries: always do, ask first, never do.
6. Modularity: tiny skill or production folder.
7. Invocation mode: user command, model-invoked background skill, forked subagent, or explicit side-effect workflow.

## Size Rules

- New generated `SKILL.md`: target <= 200 lines.
- Existing or exceptional `SKILL.md`: hard ceiling <= 500 lines.
- `description` + `when_to_use`: combined Claude listing cap <= 1,536 characters.
- If a generated skill wants to exceed 200 lines, move material to `instructions/`, `examples/`, `templates/`, `references/`, or `eval/`.
- If it still exceeds 500 lines, stop and report `STATUS: BLOCKED - SKILL.md too large`.

## Content Routing

| Content | Destination |
|---|---|
| Discovery metadata and 5-10 step workflow | `SKILL.md` |
| Long rules and procedures | `instructions/*.md` |
| Golden paths and anti-patterns | `examples/good/*.md`, `examples/bad/*.md` |
| Architecture notes or external docs | `references/*.md` |
| Deterministic checks and generators | `scripts/*` |
| Reusable output formats | `templates/*.md` |
| Review checklist and personas | `eval/checklist.md` |

## Frontmatter Routing

Use these fields where they fit the skill's risk and invocation style:

```yaml
---
name: <skill-name>
description: >-
  <short core capability and primary use case.>
when_to_use: >-
  Activates for: <trigger phrase>, <task shape>, <file or workflow context>.
argument-hint: "[target]"
arguments: [target]
effort: low|medium|high
context: fork
agent: Explore|Plan|Execute
disable-model-invocation: true
user-invocable: false
allowed-tools: Read Grep Bash(${CLAUDE_PROJECT_DIR}/scripts/review/check_orama_skills.py *)
disallowed-tools: AskUserQuestion
paths:
  - "bin/orama-system/skills/**"
---
```

Rules:

- Do not use all fields by default.
- Add `disable-model-invocation: true` when the skill installs, deploys, mutates git history, changes MCP config, or dispatches harnesses.
- Add `user-invocable: false` for pure background doctrine such as AFRP/CIDF-style protocols.
- Add `context: fork` only when `SKILL.md` contains a task a subagent can execute.
- Add `hooks:` only when an audit or policy action must be deterministic.

## Clobber Guard

Run before writing:

```bash
TARGET_DIR="bin/orama-system/skills/<name>"
if [ -d "$TARGET_DIR" ]; then
  echo "SKILL_EXISTS: $TARGET_DIR already exists"
  find "$TARGET_DIR" -maxdepth 2 -type f | sort
else
  echo "SKILL_EXISTS: false"
fi
```

If the directory exists, ask whether to overwrite, merge missing files only, or cancel.

### External Namespace Collision Check (mandatory before ANY write outside this repo)

The in-repo clobber guard above only checks THIS repo's own manifest. It
cannot see a same-named skill owned by an unrelated suite that shares a
write target — the failure mode that actually happened: gstack ships its
own bundled `skillify` skill directly at `~/.claude/skills/skillify/`, and
a dogfood pass added `~/.claude/skills` as a write target for orama's
*different* `skillify` skill, silently overwriting gstack's file (2026-07-22,
recovered from gstack's own source copy at `~/.claude/skills/gstack/<name>/`
— see `references/dogfood-upgrade-log.md` for the full incident record).

Before writing to ANY shared global namespace (`~/.claude/skills/`,
`~/.codex/skills/`, `~/.agents/skills/`, or any future one) — and as part of
**Intake Question 1, when a NEW skill's name is first chosen**, not only at
publish time — run the single shared collision check, never a hand-rolled
inline one:

```bash
bash "$(git rev-parse --show-toplevel)/scripts/check-skill-namespace-collision.sh" <name>
```

Exit 0 + `clear: <name>` means safe. Exit 1 + `COLLISION: ...` means pick a
disambiguated name instead (e.g. `oramasys-<name>`, matching the
`oramasys-method` / `oramasys-skillify` precedent) before proceeding any
further — do not continue with the colliding name and "fix it later."

This is the ONE place the check lives — `scripts/install-skills.sh`'s
`sync_one()` calls the same script before every global-publish sync, so the
naming-time check (here) and the publish-time check (there) can never drift
apart the way a doc-embedded snippet and a script's own inline logic did on
2026-07-22 (full incident: `references/dogfood-upgrade-log.md`). gstack is
the only known external suite as of this writing (`EXTERNAL_SUITE_DIRS` in
the script, ~30 skills at `~/.claude/skills/gstack/*/SKILL.md`); if another
suite is later found to populate a shared namespace, extend that array in
the script — never add a second implementation of this check anywhere.

## Validation

After writing, validate the edited skill directly and then run the repo skill checker.

Direct file validation:

```python
import pathlib
import re

path = pathlib.Path("<target_dir>/SKILL.md")
content = path.read_text(encoding="utf-8")
assert content.startswith("---")
match = re.search(r"\n---\s*\n", content[3:])
assert match, "missing closing frontmatter fence"
line_count = len(content.splitlines())
assert line_count <= 500
if line_count > 200:
    print(f"WARN: generated SKILL.md is {line_count} lines; move more into references")

fence_pattern = re.compile(r"^```(?P<info>[^`]*)$", flags=re.MULTILINE)
in_fence = False
for fence in fence_pattern.finditer(content):
    info = fence.group("info").strip()
    if not in_fence:
        assert info, f"opening code fence at line {content[:fence.start()].count(chr(10)) + 1} needs a language specifier"
        in_fence = True
    else:
        in_fence = False
```

Repo-level validation:

```bash
python3 scripts/review/check_orama_skills.py --mode baseline
```

Agent-security wording (aguara — run before opening a skill doc PR):

```bash
aguara scan bin/orama-system/skills \
  --ci \
  --baseline config/agent-security/aguara-skills.baseline.json \
  --disable-rule TOXIC_CROSS_002
```

See [`skill-security-wording-reference-card.md`](skill-security-wording-reference-card.md).

Use strict mode only after the current legacy skill corpus has been upgraded or warnings have been allowlisted:

```bash
python3 scripts/review/check_orama_skills.py --mode strict
```

Baseline mode reports findings without blocking. Strict mode exits non-zero on errors or unallowlisted warnings.

## Registration

For orama-system sub-skills only:

1. Read `bin/orama-system/SKILL.md`.
2. Locate the `sub_skills:` block.
3. Check whether the skill is already registered.
4. Ask before editing.
5. Append the smallest entry that matches the existing path convention.

## CLAUDE.md Pointer

Only touch `CLAUDE.md` after confirmation. Keep the insertion to one line and follow CIDF placement rules.

## 6Cs Review

Before reporting done, score:

| C | Pass condition |
|---|---|
| Clarity | No ambiguous instructions |
| Completeness | Edge cases and boundaries are covered |
| Conciseness | No repeated low-value text |
| Consistency | Same term for same concept |
| Correctness | Steps are executable and verified |
| Context | Stands alone without unexplained jargon |

## Distillation Readiness

A skill is smaller-model ready when:

- It uses imperative runbook voice.
- It defines every jargon term once.
- It has a clear done condition.
- Unsafe or costly actions are gated with invocation controls.
- Commands are verified, copy-pasteable, and dated when volatile.
- Dynamic context injection is scoped, justified, and portable.
- Unproven claims are labeled `open` or `candidate`.

## Report Format

```text
STATUS: DONE
Created or updated:
  <target_dir>/SKILL.md
  <modular files>
Registered:
  bin/orama-system/SKILL.md <added/skipped/not applicable>
  CLAUDE.md <added/skipped/not applicable>
Validation:
  direct file: PASS/FAIL
  check_orama_skills baseline: PASS/WARN/FAIL
  line count: <n> lines
  frontmatter listing length: <n>/1536
  modularity: PASS/FAIL
  6Cs: PASS/PASS_WITH_NOTES/FAIL
```
