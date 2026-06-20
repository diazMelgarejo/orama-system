---
name: cidf
description: Content Insertion Decision Framework v1.2 — sub-skill. Provides the executable decide(), lint_strict(), and execute_with_fallback() API for content insertion decisions. Activates whenever content must be inserted, written, pasted, uploaded, or scripted.
version: 1.2.0
license: Apache 2.0
compatibility: claude-code, cowork, open, codex, clawdbot
allowed-tools: bash, file-operations
---

# CIDF Sub-Skill — Content Insertion Decision Framework v1.2

**Sub-skill of `bin/orama-system/SKILL.md`. Load on demand for any content insertion task.**

---

## The One Rule
>
> Use the simplest tool that works. Complexity is a cost, not a feature.

---

## Quick API

```python
from cidf.core.content_insertion_framework import Task, Env, decide
from cidf.linter.policy_linter import lint_strict

decision = decide(task, env)      # always starts at rank 1
lint_strict(decision, task, env)  # raises LintError on LINT-001–005
```

---

## Method Priority (always top-to-bottom, stop at first eligible)

| Rank | Method | Eligible When | Complexity |
| ------ | -------- | --------------- | ----------- |
| 1 | `direct_form_input` | `field_accessible == True`, content < 10k | ★☆☆☆☆ |
| 2 | `direct_typing` | `editor_visible == True`, content < 5k | ★★☆☆☆ |
| 3 | `clipboard_paste` | `paste_supported == True` | ★★☆☆☆ |
| 4 | `file_upload` | `upload_available == True` | ★★★☆☆ |
| 5 | `scripting` | **Automation gate open only** | ★★★★★ |

---

## Automation Gate

```text
OPEN (any one true):   frequency ≥ 5 · conditional_logic · transformation · external_integration
CLOSED (any one true): one_time + static · simpler_method_available · setup_time > run_time
```

When gate is CLOSED and ranks 1–4 all fail → notify user. Do NOT script.

---

## Verification (mandatory)

```text
execute → visual_ok? ──no──→ refresh() → verify_programmatically(signature)
                                              ↓
                                    found? → ✅ complete
                                    missing → log + try next rank
```

**Never trust visual confirmation alone.**

## Markdown Write Rule

When the content is markdown:

- Read the repo markdown index and lessons log before editing repo guidance.
- Keep links relative and GitHub-renderable.
- **Paths: relative in-repo links + GitHub URLs only — NEVER absolute workstation paths.** A literal `/Users/<name>/…` or the `…/claude/OpenClaw` tree doxes the owner and fails CI (`scripts/review/repo_hygiene.py`). For cross-repo references use a relative path (`../<repo>/…`) or a `https://github.com/diazMelgarejo/<repo>/blob/<branch>/…` URL; for runtime paths use `$OPENCLAW_ROOT`/`$REPO_ROOT`/`~`. Same rule as the git-hygiene "no workstation paths" check.
- If a markdown file moves or gets renamed, preserve the redirect trail with a canonical-path note or an updated index link before commit.
- Warn and ask the user before adding a new markdown file over 200 lines or growing an existing markdown file over 500 lines; suggest moving detail to `references/`, `docs/wiki/`, or a sub-skill.
- Format all markdown tables with spaces inside the pipe characters to comply with MD060 table-column-style (compact). Delimiter rows must use `| ----- | --------- |` instead of `|-------|-----------|` to avoid lint warnings. Remove one ("-") and add one space (" ") on each side of the pipe.
- Review the diff for stale anchors and broken relative links before the final write.

---

## Lint Rules (pre-execution guard)

| Rule | What it catches |
| ------ | ---------------- |
| LINT-001 | Scripting chosen while simpler rank eligible |
| LINT-002 | `verification_required == False` — hard block |
| LINT-003 | Complexity bias (chosen rank > min eligible) |
| LINT-004 | Scripting for one-time static task |
| LINT-005 | No fallback chain defined (warning) |
| LINT-006 | Absolute workstation path in tracked content (`/Users/<name>/…` or `…/claude/OpenClaw`) — use relative/GitHub link or `$REPO_ROOT` |
| LINT-007 | **UTF-8 mojibake** — a multibyte lead char (U+00C2–U+00EF) followed by a continuation byte (U+0080–U+00BF) or a cp1252 high-punctuation codepoint. Caused by UTF-8 bytes read as Windows-1252/Latin-1 then re-saved (e.g. an em-dash U+2014 becoming `a-circumflex+euro+quote`); most often a tool reading/writing without explicit `encoding="utf-8"` on a cp1252-default platform (Windows). **Fix:** repair the bytes (per-char cp1252→latin-1 re-encode → decode UTF-8); always pass `encoding="utf-8"` to `open()`. **When documenting mojibake, describe it by codepoint — never paste a literal example, or you trip this rule.** |

> LINT-006 and LINT-007 are enforced by `scripts/review/repo_hygiene.py`
> (`scan_personal_paths` / `scan_openclaw_workstation_layout`, `scan_mojibake`),
> which the **pre-commit hook and CI both run** — single source of truth, zero
> fragmentation. Root cause + repair recipe: `docs/LESSONS.md` 2026-06-10.

### IMPERATIVE — fresh Claude install: install the write-time path guard

`repo_hygiene.py` catches LINT-006 at **commit/CI** (late). Relying on memory still
let a workstation path re-leak into a tracked skill (2026-06-12). The durable fix is
a **write-time** guard the harness runs on every edit. **On a fresh Claude install,
verify it exists — if absent, create and register it:**

1. Create `~/.claude/hooks/no-workstation-paths.py` — a **PreToolUse** guard that, for
   `Write`/`Edit` whose `tool_input.file_path` is inside a git work tree and is **not**
   gitignored, scans the incoming `content`/`new_string` and **exits 2 (blocks)** if it
   injects: an absolute Unix home prefix where the home segment starts with a real
   letter, the synced-Documents OpenClaw working tree, or a `code/OpenClaw` path under a
   home prefix. It must **allow** doc placeholders (segment not starting with a letter),
   scratch/`/tmp`, and gitignored files (`.env`, `pyvenv.cfg`). Build the match patterns
   in code — same "describe, don't paste a real literal" rule as LINT-007 mojibake.
2. Register it in `~/.claude/settings.json` under `hooks.PreToolUse`, matcher `Write|Edit`
   → `python3 "$HOME/.claude/hooks/no-workstation-paths.py"` (merge, don't overwrite
   existing hooks; validate the JSON round-trips).
3. Block message must redirect the writer to **repo-relative** paths
   (`"$(git rev-parse --show-toplevel)/…"` or sibling `"../../<repo>/…"`).
   `repo_hygiene.py` stays the commit/CI backstop.

Global on purpose (`~/.claude/`, not the repo) so it protects every repo on the
machine; the repo's `repo_hygiene.py` is the portable committed backstop.

---

## Package Contents

```text
bin/orama-system/cidf/
├── SKILL.md                          ← this file (sub-skill)
├── FRAMEWORK.md                      ← canonical v1.2 spec
├── core/
│   ├── content_insertion_framework.py  ← decide(), verify(), execute_with_fallback()
│   ├── content_insertion_policy.json   ← machine policy + 6 test vectors
│   └── contentInsertionFramework.ts    ← TypeScript port
├── linter/
│   ├── policy_linter.py                ← LINT-001–005 guard
│   └── policyLinter.ts
└── tests/
    ├── test_conformance.py             ← 30 pytest tests (all must pass)
    └── conformance.test.ts
```

---

## Version Alignment (all must match)

| File | Must say |
| ------ | --------- |
| This SKILL.md `version:` | `1.2.0` |
| `cidf/FRAMEWORK.md` header | `Version: 1.2` |
| `cidf/core/content_insertion_policy.json` → `framework_version` | `"1.2"` |
| `cidf/tests/test_conformance.py` assertion | `== "1.2"` |

**Never update the policy without bumping all four in the same commit.**

---

## Run Conformance Tests

```bash
pytest bin/orama-system/cidf/tests/test_conformance.py -v   # must be 30 passed, 0 failed
```
