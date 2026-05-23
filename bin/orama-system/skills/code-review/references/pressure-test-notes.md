# Pressure test notes (expected behavior)

> Optional RED test from writing-skills methodology. **Not run automatically** in this fortify pass.

## Hypothesis

Agents without the code-review skill loaded will **Read/Grep first** on multi-file tasks. With the skill loaded, they should call **`detect_changes`** (or graph equivalent) before bulk `Read`.

## Test A — without skill

**Prompt:** "Review my uncommitted changes in this repo for bugs before I commit."

**Expected failure modes:**

- Opens many files via `Read` without blast-radius map
- `Grep` for symbols instead of `gbrain code-def`
- No `get_review_context` before full file reads
- Nitpick flood without confidence filter

## Test B — with skill

**Prompt:** "Use the code-review skill. Review my uncommitted delta."

**Expected behavior:**

1. `list_graph_stats` or `detect_changes`
2. `get_impact_radius` / `query_graph` as needed
3. `get_review_context` then scoped `Read`
4. gbrain for symbols and LESSONS
5. Single-pass report; confidence ≥ 80 only
6. Verdict: Yes | No | With fixes

## Test C — PR mode

**Prompt:** "Review PR #N with multi-lens fan-out."

**Expected:**

- Mode router chooses **PR** not Delta
- Assigned file list from CRG, not whole repo
- Orchestration probe → OmniRoute | ai-cli | Task | sequential
- Merge + confidence filter per `review-lenses-pr.md`

## Rationalizations to watch

| Rationalization | Correct response |
|-----------------|------------------|
| "I already know this repo" | Still run `detect_changes` |
| "Diff is small" | Delta mode OK; still graph-first if multi-file |
| "Grep is faster" | Grep only for exact strings after graph |
| "I'll read SKILL.md in gstack for review steps" | Use `agents/code-reviewer.md` only |

## Recording results

If tests are run, append dated bullets to `orama-system/docs/LESSONS.md` only when the user requests — do not auto-commit.
