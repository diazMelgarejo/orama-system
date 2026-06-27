# Platform line endings — each turf, its own EOL

> **Policy:** Do not play tug-of-war on Windows-owned files from macOS/Linux agents.
> Each platform keeps the line endings its runtime expects.

## Turf map

| Turf | Paths (examples) | Working-tree EOL | Agent on Mac/Linux |
|------|------------------|------------------|---------------------|
| **Windows-serving** | `platform/windows/**`, `*.cmd`, `*.bat`, `*.ps1` | **CRLF** (`\r\n`) | Do **not** convert to LF. Do **not** "hygiene-fix" `\r`. |
| **Mac/Linux-owned** | `*.sh`, `*.py`, most `docs/`, `src/` | **LF** (`\n`) | Keep LF. Repo hygiene enforces this. |

## Git attributes (orama-system)

```gitattributes
*.cmd  text  eol=crlf
*.bat  text  eol=crlf
*.ps1  text  eol=crlf
```

With `eol=crlf`, Git stores a normalized text blob and checks out **CRLF** in the
working tree. A Mac editor may show the file as "modified" when the **index blob**
was committed before attributes landed (CRLF stored literally in the object).

**Correct fix (not a content war):**

```bash
# Worktree already has CRLF; re-normalize the git object once:
git add platform/windows/gstack-brain-sync.cmd
# Verify: git diff --cached should show LF-in-blob normalization only
git ls-files --eol platform/windows/gstack-brain-sync.cmd
# expect: i/lf w/crlf attr/text eol=crlf  (after add, before commit)
```

**Wrong fixes:**

- Stripping `\r` from `.cmd` files "because Mac hygiene wants LF"
- Committing LF-only `.cmd` content (breaks `cmd.exe` tokenization)
- Repeated `git restore` / re-edit cycles between agents on different OSes

## False dirty on Mac

Symptom: `git status` shows `platform/windows/*.cmd` modified; `cmp` or
`git diff --ignore-cr-at-eol` shows no semantic change.

Cause: blob in history predates `.gitattributes`, or index stat drift.

Action: `git add <file>` once to normalize the object; commit with message noting
EOL normalization. Do not hand-edit line endings.

## Verification

```bash
# Working tree must be CRLF for .cmd
xxd platform/windows/gstack-brain-sync.cmd | head -2   # 0d 0a after lines

# After normalize commit, object is LF, worktree CRLF
git ls-files --eol platform/windows/gstack-brain-sync.cmd
```

## Cross-references

- [`docs/wiki/08-git-hygiene-and-branching.md`](../../../../docs/wiki/08-git-hygiene-and-branching.md) § Windows batch file line endings
- [`hermes-harness/SKILL.md`](../../hermes-harness/SKILL.md) § Line Endings (CRLF)
- [`.gitattributes`](../../../../.gitattributes)
