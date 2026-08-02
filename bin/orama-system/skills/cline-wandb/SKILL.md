---
name: cline-wandb
description: Run Cline CLI as a non-interactive fan-out worker using DeepSeek-V4-Flash via wanDB.ai (Weave/W&B inference), high reasoning. Use when the user asks for wanDB-routed Cline bot fan-out, headless Cline review via wanDB, EXA plus Firecrawl verification for Cline usage on this route, or a parallel Cline route that does not replace ClinePass DeepSeek Flash or the GLM ClinePass skill. Includes a mandatory harmonized TDD reference card extending docs/TDD.md, and a mandatory generalized self-review discipline.
---

# Cline wanDB (DeepSeek-V4-Flash)

Use this skill to dispatch Cline as a headless worker on the
wanDB.ai-routed DeepSeek-V4-Flash model. This is a parallel route to
ClinePass DeepSeek Flash and the GLM ClinePass skill, not a replacement
for either.

## Disambiguation

Same client binary (`cline`) as the other Cline agents in this
ecosystem, different provider underneath: this route goes through
wanDB.ai's OpenAI-compatible inference endpoint (with Weave tracing),
not ClinePass's account-based auth. Mirror the Kimi/Codex/ClinePass
pattern:

- main session: owns architecture, security policy, repo history
  surgery, and final commits;
- Cline wanDB: does constrained review, plan drafts, mechanical
  implementation passes, and independent second opinions;
- OpenClaw agent registry: unchanged unless the user explicitly asks
  for a named OpenClaw subagent binding.

If this route authors commits later, use a public bot identity
approved by the repository attribution policy before committing. Do
not invent a private operator identity.

## Contract

- Model: `deepseek-ai/DeepSeek-V4-Flash`
- Provider: wanDB.ai inference (`https://api.inference.wandb.ai/v1`),
  OpenAI-compatible
- Team/Project: `diazmelgarejo-org/deepseek_v4_flash_wandb_agent`
- Reasoning: high
- Access policy: wanDB-only for this route. Do not silently fall back
  to ClinePass, GLM, Pro, Kimi, OpenRouter, or any other provider key
  path.
- Auth: `DEEPSEEK_V4_FLASH_WANDB` environment variable. Do not request
  or print the key's value.
- Privacy: do not pass secrets, private identity literals, LAN
  topology, device names, or workstation-specific paths into prompts
  or outputs.
- Workspace: default to `/private/tmp` for read-only or sensitive
  fan-out. Add repository access only when the task needs file reads
  or edits.

## ⚠️ Needs local verification before first real use

Cline CLI's exact flag shape for a custom OpenAI-compatible provider
(base URL + API key, as opposed to a named provider like `clinepass`)
was **not verified against a live `cline` CLI in this drafting pass** —
unlike ClinePass, where the sibling skill's flags were confirmed
against an actual installed CLI version. This entire skill's real-world
review and results verification is deferred until a macOS and/or
Windows machine with `cline` installed is available. Before relying on
this route for anything beyond a dry read of its instructions:

```bash
cline --version
cline auth --help
cline task --help
```

Confirm whether `cline auth` supports a custom base URL + bearer key
directly, or whether wanDB.ai needs to be added as a named provider
first. The dispatch patterns below use a plausible, ClinePass-pattern-
consistent flag shape as a starting point — verify and correct against
real `--help` output the same way the ClinePass skill's own "Verify
Current CLI Shape" section does, and update this section once
confirmed.

## Quick Start (flags to verify, see above)

```bash
cline auth --provider openai-compatible \
  --baseurl https://api.inference.wandb.ai/v1 \
  --apikey "$DEEPSEEK_V4_FLASH_WANDB" \
  --modelid deepseek-ai/DeepSeek-V4-Flash
```

```bash
cline task \
  --json \
  --auto-approve-all \
  --reasoning-effort high \
  -m deepseek-ai/DeepSeek-V4-Flash \
  -c /private/tmp \
  -t 180 \
  "Reply with exactly: CLINE_WANDB_READY"
```

## Provider Auth Gate

Before real work, run the smoke prompt above. If the JSON output
reports a provider other than wanDB.ai, or rejects the model id, stop
and fix Cline auth/config first — same failure mode as ClinePass: the
CLI can accept the command shape while still routing through the
wrong provider.

Use the key from `DEEPSEEK_V4_FLASH_WANDB`. Never paste it into
prompts, tracked files, shared command history, or logs.

## Dispatch Patterns

Read-only review:

```bash
cline task \
  --json \
  --auto-approve-all \
  --reasoning-effort high \
  -m deepseek-ai/DeepSeek-V4-Flash \
  -c /private/tmp \
  -t 300 \
  "Review this sanitized summary. Do not access files. Return risks and tests."
```

Plan-first review:

```bash
cline task \
  -p \
  --json \
  --auto-approve-all \
  --reasoning-effort high \
  -m deepseek-ai/DeepSeek-V4-Flash \
  -c /private/tmp \
  -t 300 \
  "Create a concise implementation plan from this sanitized summary."
```

Repo-bound implementation, only on a clean branch:

```bash
git status --short --branch
cline task \
  -a \
  --json \
  --auto-approve-all \
  --reasoning-effort high \
  -m deepseek-ai/DeepSeek-V4-Flash \
  -c "$PWD" \
  -t 900 \
  "Implement the requested scoped change. Preserve unrelated local changes."
```

## Mandatory: TDD for every spawned agent

**Every agent this skill spawns MUST follow
[`references/tdd-reference-card.md`](references/tdd-reference-card.md)
for any task that writes or modifies code.** This is not optional
guidance the worker can skip under time pressure — write the failing
test first, watch it fail for the right reason, write minimal code,
watch it pass, refactor only with tests green. A worker that produces
code without following this card has not completed the task correctly,
regardless of whether the code looks right.

## Mandatory: generalized self-review before reporting done

Every dispatch under this skill — not just code changes, any
non-trivial output — reviews its own work before returning control,
using the **same thinking process** the
[`code-review` skill](../code-review/SKILL.md) applies to PRs, adapted
to whatever the task actually is rather than requiring PR-specific
tooling:

1. **Context before output** — the code-review skill builds a
   dependency/blast-radius graph before reading code
   ([`code-review` § Phase A](../code-review/SKILL.md#phase-a--graph-code-review-graph-mcp)).
   This skill's workers don't have `gbrain` or `code-review-graph`
   available, so the equivalent step is: before producing a final
   answer, re-read what the task actually asked for and what's
   actually been produced, side by side — not from memory of what you
   intended, from the literal request and the literal output.
2. **Review the delta, not just the destination** — the code-review
   skill has a dedicated delta-review phase
   ([`code-review` § Phase D](../code-review/SKILL.md#phase-d--review)).
   For this skill's workers: re-read your own draft/diff/answer once,
   specifically looking for the same class of thing a reviewer would
   flag — unverified claims, unstated assumptions, edge cases the
   request implied but the output doesn't cover.
3. **Structured report, not just an answer** — the code-review skill
   ends with an explicit report phase
   ([`code-review` § Phase E](../code-review/SKILL.md#phase-e--report)).
   This skill's workers close out with a short, explicit summary of
   what was actually verified (tests run and their result, sources
   checked, assumptions made) — not a bare answer with no trace of how
   it was checked.
4. **Red flags stop the worker, not just slow it down** — the
   code-review skill has explicit skill-violation red flags
   ([`code-review` § Red flags](../code-review/SKILL.md#red-flags-skill-violation)).
   The generalized equivalent here: if a worker notices it's about to
   report something as done without having actually run/verified it,
   that's the same category of violation — stop and verify, don't
   report first and caveat later.
5. **Use orama-system's own methodology for internal state, not just
   the deliverable** — apply the 5-stage
   [orama-system methodology](../../SKILL.md) (Context Immersion →
   Visionary Architecture → Ruthless Refinement → Masterful Execution →
   Crystallize) to the worker's own reasoning process for
   non-trivial tasks, the same way the main session does, not just to
   the code it produces. A worker that jumps straight to output without
   this internal structure is skipping the same discipline the main
   session is held to.

This applies regardless of task type — a plan draft, a review, a
mechanical implementation pass, or "other agentic tasks" more broadly.
The tools differ from `code-review`'s (no graph MCP, no gbrain); the
underlying discipline — gather real context, review your own delta
before calling it done, report what was actually verified, treat a
premature "done" as a stop condition — does not.

## Output Handling

`--json` produces newline-delimited message objects. Parse
defensively: keep `type == "say"` messages, ignore partials when a
final answer exists, don't treat every line as final output, don't log
prompts that may contain sensitive summaries.

## Monitoring

```bash
pgrep -af 'cline|deepseek-v4-flash|wandb'
ps -p <pid> -o pid,ppid,stat,lstart,etime,command
```

## Boundaries

- Do not replace ClinePass DeepSeek Flash or the GLM ClinePass skill.
- Do not install new providers or call wanDB.ai's API directly
  (bypassing the `cline` CLI) unless explicitly asked.
- Do not pass unredacted repository secrets, local-only config, or
  private literals to a cloud worker.
- Do not force-push, merge, or close PRs from this route. The main
  session owns repository state changes.
- Do not report a task complete without having followed the
  self-review discipline above — a fast answer that skipped review is
  not a complete answer.

## References

- [`references/tdd-reference-card.md`](references/tdd-reference-card.md)
  — harmonized TDD reference card (extends
  [`docs/TDD.md`](https://github.com/diazMelgarejo/orama-system/blob/main/docs/TDD.md);
  mandatory for any code-writing dispatch under this skill).
- Sibling route:
  [`../clinepass-deepseek-flash/SKILL.md`](../clinepass-deepseek-flash/SKILL.md)
- Self-review pattern source:
  [`../code-review/SKILL.md`](../code-review/SKILL.md)
