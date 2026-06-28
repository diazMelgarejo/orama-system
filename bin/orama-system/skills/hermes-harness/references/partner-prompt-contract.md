# Partner Prompt Contract

> **Source:** `ecc-hermes-cross-harness.md` § Partner Prompt Contract  
> **Role:** bounded worker contract for Hermes, AGY, Codex CLI, and LM Studio partners  
> **Size contract:** ≤150 lines.

---

## Prompt Shape (copy-paste template)

```text
ROLE: coding partner for PT-orama
GOAL: <specific, single outcome — one task per call>
CONSTRAINTS:
  - do not commit, deploy, delete, or change account settings
  - do not reveal or request secrets
  - do not import raw Hermes / OpenClaw local state
  - do not invent model names — only use IDs returned by /v1/models
  - cite files, tests, and line numbers used as evidence
OUTPUT (structured):
  assumptions:        <what you took as given>
  findings:           <what you observed, with citations>
  proposed_actions:   <specific edits or commands>
  tests:              <how to verify correctness>
  risks:              <what could go wrong>
  handoff_notes:      <what the main agent needs to decide>
```

The main orama agent owns **final synthesis, CIDF write discipline, and merge readiness**.
No partner lane has veto authority or autonomous write access.

---

## Per-Partner Invocation Flags

| Partner | One-shot flag | Non-TTY flag | Notes |
|---|---|---|---|
| Hermes | `--max-turns 1` | `--safe-mode` | Always specify `--provider` + `--model` explicitly |
| AGY | `--print` or `-p` | `--dangerously-skip-permissions` | Required to prevent silent hang in subagent context |
| Codex | `--print` | `--dangerously-skip-permissions` | Non-interactive; no TTY stall |
| LM Studio | HTTP POST to `/v1/chat/completions` | `--no-stream` | Must verify `/v1/models` first |

---

## Readiness Check Before Dispatch

Always run the partner's canary before sending it a bounded task:

```powershell
# Hermes
hermes chat --query "Reply with exactly: HERMES_READY" --safe-mode --provider nous --model stepfun/step-3.7-flash:free --max-turns 1

# AGY
agy --print "Reply with exactly: AGY_READY"

# Codex
codex --version

# LM Studio
Invoke-RestMethod -Uri "http://localhost:1234/v1/models"
```

If the canary fails → mark lane UNAVAILABLE → continue without it.
See full timeout + degraded-path table in `../SKILL.md` § Verification Gates.

---

## Output Validation

Before accepting a partner's `proposed_actions`:

1. Does every proposed edit cite a specific file + line?
2. Are all tests listed runnable right now (no stubs)?
3. Does the output contain any absolute paths or credentials? If yes, reject.
4. Does it propose a commit, deploy, or account change? If yes, reject.

---

## Related

- [`cross-harness-protocol.md`](cross-harness-protocol.md) — authority and harness boundaries
- [`ecc-migration-rules.md`](ecc-migration-rules.md) — what belongs in canonical vs local
- [`../SKILL.md`](../SKILL.md) § Verification Gates — canary table with timeouts

---

## Mandatory Prompt Elements

Every partner task prompt must include all five elements:

```text
1. GOAL       — one sentence: what outcome is expected
2. CONSTRAINTS — forbid commits / deletes / deploys / secrets
3. SCOPE      — cite the canonical skills or files to inspect
4. OUTPUT     — request JSON with: assumptions, findings, proposed_edits, tests, risks
5. HANDOFF    — "the main orama agent reviews all output before acting"
```

### Minimal Compliant Prompt Template

```text
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

---

## Tool-Specific Invocation

### Hermes (one-shot)

```powershell
hermes chat --query "<prompt>" --quiet --safe-mode `
  --provider nous --model stepfun/step-3.7-flash:free --max-turns 1
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

---

## Readiness Gate (must pass before dispatch)

1. Run the appropriate partner canary (see
   [`hermes-windows-partner-readiness.md`](hermes-windows-partner-readiness.md)).
2. Confirm hardware policy has been checked for any LM Studio model
   (see [`../commands/pt-hardware-policy/SKILL.md`](../commands/pt-hardware-policy/SKILL.md)).
3. Confirm no sensitive files are in scope (no `.env`, `secrets.*`, keys).

---

## Review Gate (must pass after dispatch)

The main agent reviews every partner output before any file is modified:

- [ ] Assumptions are accurate
- [ ] Findings are grounded in cited files (not hallucinated paths)
- [ ] Proposed edits are in scope (no out-of-scope deletions or rewrites)
- [ ] Risks have a mitigation plan or are explicitly accepted

**Never batch-apply partner output without this review.**
