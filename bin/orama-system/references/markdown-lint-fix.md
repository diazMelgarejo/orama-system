# Markdown lint repair: mechanical fixes first, judgement second

Lint failures on documents are mostly mechanical. Fix those with a tool, so the author's
attention goes to the few that need words. The tool is
[`scripts/review/md_lint_fix.py`](../../../scripts/review/md_lint_fix.py).

## What it fixes, and what it refuses

| Rule | Repair | Safe because |
| --- | --- | --- |
| MD022 | Blank line around headings | Adds whitespace only |
| MD032, MD058 | Blank line around lists and tables | Adds whitespace only |
| MD013 | Wrap prose and list items to the width (default 100) | Same words, new line breaks |
| MD060 (compact) | Spaced table delimiter row | Cosmetic |

It never edits fenced code, front matter, HTML comments, block quotes, indented code,
headings, table rows or hard-break lines. A line it cannot wrap safely (a long URL, or a
wrap that would start a line with a list or heading marker) is reported as
`cannot wrap safely` and left alone. Rewording, deduplicating or dropping content is an
author decision and goes through the CIDF rules, never through a formatter.

## Procedure

```bash
python3 scripts/review/md_lint_fix.py --check docs/path/to/file.md   # exit 1: would change
python3 scripts/review/md_lint_fix.py --write docs/path/to/file.md   # idempotent rewrite
markdownlint-cli2 docs/path/to/file.md                               # the linter is the judge
git diff -w --stat                                                   # whitespace-only? say so
```

1. Run `--write` on the files the failing job names, then run the real linter on them.
2. Whatever the linter still reports is a content problem: fix it by hand, additively
   (see [`integrative-editing-examples.md`](../cidf/references/integrative-editing-examples.md)).
3. State in the commit message that the repair is whitespace and line-wrap only.

## Where it sits

- **Verification, not insertion.** CIDF decides where content goes; this tool runs at the
  readback step, after content is in place, as a mechanical gate before commit.
- **Same width as CI.** The default 100 matches `.markdownlint-cli2.jsonc` (tables, code
  and headings are exempt there). Pass `--width` only where a repo's config differs.
- **Local linter drift.** CI pins `markdownlint-cli2-action`; a newer local
  `markdownlint-cli2` can report extra rules (for example MD060). Judge by the CI pin.
- **Ignored files** (for example `**/SKILL.md`, `**/LESSONS.md`) are exempt from lint;
  do not run the tool on them.

## Incident this came from

Orama PR #412 (2026-10-17): four long-form plan files failed with 72 errors, almost all
blank-line and line-length findings. A one-off script cleared them with the text
unchanged, which is why it is now a tested tool
([`tests/test_md_lint_fix.py`](../../../tests/test_md_lint_fix.py)) rather than a snippet.
