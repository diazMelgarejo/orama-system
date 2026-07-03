# Modular Skill Authoring Reference

Use this file after `skillify/SKILL.md` activates. The always-loaded skill file stays short; this reference carries the working procedure.

## Purpose

Create skills that are easy to trigger, easy to audit, and hard to misuse.

## Intake Questions

Ask for:

1. Skill name: lowercase kebab-case, 1-64 chars, matching directory name.
2. Purpose: one third-person sentence with trigger contexts.
3. Target harness: orama-system, gstack, raw Claude Code, Codex wrapper, ECC, or all applicable.
4. Trigger phrases: what the user would actually type.
5. Boundaries: always do, ask first, never do.
6. Modularity: tiny skill or production folder.

## Size Rules

- New generated `SKILL.md`: target <= 200 lines.
- Existing or exceptional `SKILL.md`: hard ceiling <= 500 lines.
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

## Validation

After writing, validate:

```python
import pathlib
import re
import yaml

path = pathlib.Path("<target_dir>/SKILL.md")
content = path.read_text(encoding="utf-8")
assert content.startswith("---")
match = re.search(r"\n---\s*\n", content[3:])
assert match, "missing closing frontmatter fence"
frontmatter = yaml.safe_load(content[3:match.start() + 3])
assert "name" in frontmatter and "description" in frontmatter
assert re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", frontmatter["name"])
assert len(frontmatter["description"]) <= 1024
line_count = len(content.splitlines())
assert line_count <= 500
if line_count > 200:
    print(f"WARN: generated SKILL.md is {line_count} lines; move more into references")
for fence in re.findall(r"^```(.*)$", content, flags=re.MULTILINE):
    assert fence.strip(), "all fenced code blocks need language specifiers"
```

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
  frontmatter: PASS/FAIL
  line count: <n> lines
  modularity: PASS/FAIL
  6Cs: PASS/PASS_WITH_NOTES/FAIL
```
