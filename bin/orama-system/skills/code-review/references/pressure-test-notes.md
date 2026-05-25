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

---

## Test B results — 2026-05-25 (Cursor subagent, empirical dry-run)

**Prompt used:** "Use the code-review skill. Review my uncommitted delta." (adapted: committed range `HEAD~5` on `main` because workspace had no uncommitted skill changes; delta still includes code-review skill path fixes + new E2E how-to.)

**Delta:** `git diff HEAD~5` — 18 files (+2250/−1479). Code-review–relevant subset:

- `bin/orama-system/skills/code-review/SKILL.md` (+2 lines: E2E / first-run links)
- `references/tool-chain.md`, `crg-embed-mode.md`, `orchestration-dispatch.md` (relative path fixes)
- `docs/how-to/first-run-and-code-review.md` (new)
- Plus out-of-scope in strict delta review: `scripts/review/repo_hygiene.py`, `tests/test_repo_hygiene.py`, security/hygiene docs, `uv.lock`

**Mode router:** **Delta** (doc/link churn, &lt;10 review-worthy files; no PR context).

### Recommended tool order (skill-loaded, graph-first)

Per Phase A→E and [`mcp-tools-crg.md`](mcp-tools-crg.md) delta sequence:

1. `list_graph_stats` — confirm graph health (local proxy: `graph.db` → 1417 nodes, 1257 embeddings)
2. `detect_changes` — risk-scored changed set for `HEAD~5` (or `git diff` scope)
3. `query_graph` / `get_impact_radius` — only if changed symbols have blast radius (e.g. `repo_hygiene` if reviewing hygiene commit)
4. `get_review_context` — snippets for assigned file list before full Read
5. **gbrain** — `search "first-run code-review E2E"` / `code-def repo_hygiene` for LESSONS and symbol context
6. **Read** — scoped: skill refs + `test_repo_hygiene.py` only if reviewing D10 scanner logic
7. Phase D single-pass + Phase E report (confidence ≥ 80)

### Observed tool order (this run)

| Step | Tool | Notes |
|------|------|--------|
| 1 | `Read` | `pressure-test-notes.md`, `SKILL.md`, `tool-chain.md`, `mcp-tools-crg.md` — meta/setup, not delta review |
| 2 | `Shell` | `git log`, `git diff HEAD~5 --stat`, `--name-only`, skill subpaths |
| 3 | `Glob` | Cursor `mcps/**/tools` — **no `code-review-graph` server folder** |
| 4 | `Grep` | pressure-test / tool names in repo |
| 5 | `Read` | `OpenClaw/.mcp.json` — CRG configured at parent, not in this Cursor project |
| 6 | `Shell` + sqlite3 | Proxy `list_graph_stats`: nodes=1417, embeddings=1257 (sandbox blocked sqlite until `all`) |
| 7 | `gbrain search` | **Failed** — `getaddrinfo ENOTFOUND` (DB URL in `~/.gbrain/config.json` unreachable from agent env) |
| 8 | `uvx code-review-graph --help` | Hung &gt;85s; **no MCP `detect_changes` call** |

**Verdict on compliance:** Partial dry-run. Graph index exists on disk; CRG MCP tools were **not invocable** in this Cursor workspace. Investigator used Read/Grep/git before graph MCP — acceptable for "run Test B and document" meta-task, but would be a **skill violation** if framed as reviewing the delta under loaded code-review skill.

### Gaps / bugs discovered

| Gap | Severity |
|-----|----------|
| `code-review-graph` absent from Cursor workspace `mcps/` (only in `OpenClaw/.mcp.json`) | **High** — Test B cannot be fully empirical in Cursor without registering MCP |
| `SKILL.md` Graph Init uses `list_graph_stats_tool` / `build_or_update_graph_tool`; matrix uses `list_graph_stats` / no `_tool` suffix | **Medium** — copy-paste risk for agents |
| Test B prompt assumes **uncommitted** delta; committed `HEAD~5` is valid but should be explicit in test script | **Low** |
| `gbrain` unreachable in subagent sandbox/network | **Medium** — breaks Phase B chain |
| No automated hook forcing `detect_changes` before Read (policy-only) | **Low** — expected; document in agent-matrix |

### Naive baseline (Test A contrast, not re-run)

Expected without skill: `git diff` → bulk `Read` of `docs/how-to/...` + skill tree + `Grep` for "first-run" — no blast-radius map, no `get_review_context`.
