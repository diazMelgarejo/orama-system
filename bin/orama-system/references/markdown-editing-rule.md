<!-- lint-ignore LINT-013 -->
# Markdown Editing Rule

> The six-step discipline for any `*.md` write or edit in this stack: memory first, relative
> links, redirect trails, size warnings, diff inspection and mechanical lint repair. Moved
> verbatim out of `SKILL.md`; the heading stays there as a pointer.

## Markdown Editing Rule

For any `*.md` write or edit:

1. Read PT `.agent` development memory and `docs/wiki/README.md` first if the change touches repo guidance or a moved doc.
2. Keep all links relative and GitHub-renderable; do not use absolute filesystem paths or sibling checkout paths.
3. If a markdown file moves or is renamed, preserve a repo-wide redirect trail by updating the canonical index or adding a `Previous path` / `Canonical path` note where appropriate.
4. Warn and ask the user before adding a new markdown file over 200 lines or growing an existing markdown file over 500 lines. Suggest moving details to `references/`, `docs/wiki/`, or a sub-skill.
5. Before committing `*.md`, inspect the diff for broken anchors, stale paths, and missing redirect notes.
6. Repair mechanical lint findings (blank lines, line length) with `scripts/review/md_lint_fix.py` before hand edits; see the [markdown lint repair card](markdown-lint-fix.md).
