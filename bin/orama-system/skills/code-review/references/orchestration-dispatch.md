# Orchestration dispatch (PR multi-lens)

> Fan-out **only** for PR / full-branch review. Delta mode stays **single-pass** (see [`SKILL.md`](../SKILL.md)).
> Lens prompts: [`review-lenses-pr.md`](review-lenses-pr.md)
> Mother skill OmniRoute probe: `bin/orama-system/SKILL.md`

## Probe order (fail open)

Do **not** warn the user if backends are missing. Degrade silently.

| Priority | Backend | When |
|----------|---------|------|
| 1 | **OmniRoute** | Mother skill reports `OMNIROUTE: running` or `started` — fan lenses via OmniRoute MCP |
| 2 | **ai-cli-mcp** | `run` per lens + `wait` / `get_result` |
| 3 | **Cursor Task** | Up to 5 parallel `Task` calls with [`agents/code-reviewer.md`](../agents/code-reviewer.md) + lens prompt |
| 4 | **Sequential** | Same lenses in one agent session |

Lead agent always: CRG + gbrain + assigned file list **before** fan-out.

## OmniRoute (priority 1)

When OmniRoute MCP is active (port 20128 per mcp-orchestration):

- Dispatch one task per lens with shared file list + lens block from `review-lenses-pr.md`
- Prefer free/fast models for shallow scans; stronger model for guidelines lens
- Collect structured JSON issues; merge locally

Verify (optional):

```bash
curl -s http://127.0.0.1:20128/api/mcp/stream -H "Authorization: Bearer $OMNIROUTE_KEY" | head -c 80
```

## ai-cli-mcp (priority 2)

Pattern (from mcp-orchestration §5):

```text
For each lens 1–5:
  run model=<pick> workFolder=<ABS_REPO_PATH> prompt="<lens prompt + shared worker block>"
Then wait for all PIDs → get_result → merge
```

**Model routing hints** (use what is installed; never block review):

| Lens | Suggested backend |
|------|-------------------|
| 1 Guidelines | `sonnet` / Claude |
| 2 Shallow bugs | `gpt-*-codex` / Codex |
| 3 Git history | Codex |
| 4 Prior PRs | Codex |
| 5 In-file guidance | Sonnet |
| Optional 6 Doc drift | `gemini-*` via gemini-mcp-tool (read-only) |

Rules:

- `workFolder` must be **absolute** path to repo root
- Workers: findings only — **no commit, push, or file writes**
- Kill stuck PIDs with `kill_process`

## Cursor Task (priority 3)

```text
Task subagent_type=code-reviewer (or generalPurpose)
prompt: <contents of agents/code-reviewer.md> + lens N block + assigned files
```

Launch up to **5** parallel tasks (one per lens). Lead merges outputs.

## Sequential (priority 4)

Run lenses 1→5 in one session with the code-reviewer persona. Slower but complete.

## Lead merge checklist

1. Union issues from all workers
2. Dedupe by file, line, and issue text
3. Apply confidence filter (≥ 80) — [`output-format.md`](output-format.md)
4. Write verdict: Yes | No | With fixes

## Anti-patterns

| Anti-pattern | Why |
|--------------|-----|
| Parallel-fire gbrain + Grep + Read on whole repo | Token leak; violates chain |
| Workers without `workFolder` | Wrong cwd / missed files |
| Letting workers commit | Safety / review integrity |
| PR fan-out for 1–2 file delta | Overkill — use Delta mode |
| Executing gstack SKILL.md in worker prompts | Wrong host / scope creep |
| Blocking review when OmniRoute/ai-cli down | Must degrade to Task or sequential |

## Cross-links

- [`~/.claude/skills/mcp-orchestration/SKILL.md`](~/.claude/skills/mcp-orchestration/SKILL.md) — install, OmniRoute, ai-cli patterns

### Open TODOs

- [ ] **PR fan-out recipe** — §5 in `mcp-orchestration` SKILL (global) vs in-repo [`review-lenses-pr.md`](review-lenses-pr.md); fortify: verify example prompts match current lens blocks (see [`pressure-test-notes.md`](pressure-test-notes.md) § Fortify pass)
- [`bin/orama-system/mcp-install/SKILL.md`](../../../mcp-install/SKILL.md) — stack install
- [`agent-matrix.md`](agent-matrix.md) — per-host tool invocation
