# Partner Prompt Contract

Bounded coding-partner dispatch protocol for Hermes, Codex, Gemini, and AGY.
All coding partner invocations must conform to this contract.

## Mandatory Prompt Elements

Every partner task prompt must include all five elements:

```
1. GOAL       — one sentence: what outcome is expected
2. CONSTRAINTS — forbid commits / deletes / deploys / secrets
3. SCOPE      — cite the canonical skills or files to inspect
4. OUTPUT     — request JSON with: assumptions, findings, proposed_edits, tests, risks
5. HANDOFF    — "the main orama agent reviews all output before acting"
```

### Minimal Compliant Prompt Template

```
Goal: <one-sentence outcome>.

Constraints:
- Do NOT commit, delete, deploy, or change account settings.
- Do NOT copy raw ~/.hermes exports or private workspace state.
- Do NOT echo secrets or tokens in output.
- Cite canonical skills before reading code: <path/SKILL.md>.

Scope: <file or skill path(s) to inspect>.

Output format (JSON):
{
  "assumptions": [],
  "findings": [],
  "proposed_edits": [],
  "tests": [],
  "risks": []
}

The main orama agent (Claude Code) reviews all output before any action is taken.
```

## Tool-Specific Invocation

### Hermes (one-shot)

```powershell
hermes chat --query "<prompt>" --quiet --safe-mode `
  --provider nous --model nvidia/nemotron-3-ultra:free --max-turns 1
```

`--safe-mode` disables autonomous file writes. `--max-turns 1` prevents
open-ended turns. Always pass `--provider` + `--model` explicitly to avoid
slow LM Studio default dispatch.

### AGY (non-interactive)

```bash
agy --print "<prompt>"

# With explicit workspace directory
agy --dir /path/to/repo --print "<prompt>"

# In non-TTY orchestrators (required when stdin is not a terminal)
agy -p "<prompt>" --dangerously-skip-permissions
```

AGY output is advisory: read it in full before acting. Treat any file-write
proposal as a `proposed_edit` requiring main-agent review.

### Codex (bounded mechanical edits only)

```bash
codex --approval-mode approve-all "<bounded task>"
```

Only use `--approval-mode approve-all` for tasks where the scope is already
verified by the main agent (never for open-ended exploration).

## Readiness Gate (must pass before dispatch)

1. Run the appropriate partner canary (see
   [`hermes-windows-partner-readiness.md`](hermes-windows-partner-readiness.md)).
2. Confirm hardware policy has been checked for any LM Studio model
   (see [`../commands/pt-hardware-policy/SKILL.md`](../commands/pt-hardware-policy/SKILL.md)).
3. Confirm no sensitive files are in scope (no `.env`, `secrets.*`, keys).

## Review Gate (must pass after dispatch)

The main agent reviews every partner output before any file is modified:

- [ ] Assumptions are accurate
- [ ] Findings are grounded in cited files (not hallucinated paths)
- [ ] Proposed edits are in scope (no out-of-scope deletions or rewrites)
- [ ] Risks have a mitigation plan or are explicitly accepted

**Never batch-apply partner output without this review.**
