# Review output format

> Used by [`agents/code-reviewer.md`](../agents/code-reviewer.md) and Phase E of [`SKILL.md`](../SKILL.md).

## Confidence rubric (0–100)

Give this scale to confidence-filter passes (adapted from Claude official code-review plugin):

| Score | Meaning |
|-------|---------|
| **0** | Not confident. False positive or pre-existing; fails light scrutiny. |
| **25** | Somewhat confident. Might be real; not verified. Stylistic issues not explicit in CLAUDE.md/AGENTS.md. |
| **50** | Moderately confident. Real but nitpick or rare in practice; low relative importance. |
| **75** | Highly confident. Verified likely real; current approach insufficient; important for behavior or explicit in project rules. |
| **100** | Certain. Will happen in practice; evidence confirms. |

**Report threshold:** include only issues with **confidence ≥ 80**.

Severity mapping:

- **Critical:** 90–100
- **Important:** 80–89

## Report template (markdown)

```markdown
## Code review

**Scope:** <diff summary or file list>
**Mode:** Delta | PR
**Verdict:** Ready to merge? Yes | No | With fixes

### Strengths

- <optional, 1–3 bullets>

### Critical (90–100)

1. **<title>** — `path/to/file.ext:LINE`
   - **Confidence:** <80–100>
   - **Reason:** <bug or rule violation>
   - **Fix:** <concrete suggestion>

### Important (80–89)

1. ...

### Filtered (not reported)

- <optional: count of issues dropped below 80, no detail unless user asks>

### Graph / gbrain used

- CRG: <tools called>
- gbrain: <symbols or searches>
- Files read: <list, should match blast radius>
```

## PR comment format (when using `gh`)

When posting on GitHub, link with **full commit SHA** (not a shell substitution in the comment body):

```text
https://github.com/<owner>/<repo>/blob/<FULL_SHA>/path/file.py#L10-L15
```

Include at least one line of context before/after the cited range.

## Optional gstack / ship tags

For compatibility with `/review` or ship workflows:

```text
[P1] (confidence: 95/100) <description> — file:line
[P2] (confidence: 85/100) <description> — file:line
```

Map: P1 ≈ Critical (90+), P2 ≈ Important (80–89).

## Review rules (coding profile)

From [`profiles/CLAUDE.coding.md`](../profiles/CLAUDE.coding.md):

- State the bug. Show the fix. Stop.
- No suggestions beyond review scope.
- No compliments before or after the review.
- No speculative bugs without reading the relevant code (graph + gbrain first).

## Anti-patterns in reports

- Listing nitpicks as Critical
- Issues without `file:line`
- Whole-repo Read without CRG blast radius
- Reporting linter/type errors CI will catch
- Workflow summary in place of actionable findings
