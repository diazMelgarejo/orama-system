# Claude Code Workflow + ultracode — canonical execution layer for Mode 3

> Referenced by: `bin/orama-system/SKILL.md` MODE 3, `oramasys-method/SKILL.md`
> Step 0/Step 2, `references/collaborative-reasoning-safety.md`.

## The rule

On Claude Code specifically, orama-system's MODE 3 "Full Multi-Agent
Network" is **not** a separate runtime to build or reimplement. Claude
Code's own `Workflow` tool (deterministic multi-agent orchestration:
`agent()`/`parallel()`/`pipeline()`/`phase()`) is the canonical execution
layer, and the `ultracode` keyword (or an explicit "use a workflow" /
"run this with subagents" ask, or a named saved workflow) is the canonical
opt-in gate. orama's own MODE 3 content — the Orchestrator/Context/
Architect/Refiner/Executor/Verifier/Crystallizer roles, the four mandatory
Builder/Critic/Adversary/Judge roles, the resource-cost caution already in
`bin/orama-system/SKILL.md`'s "Ask First" boundaries — is the **domain-
specific policy layer** on top of that primitive: what stages exist, what
each does, what safety rules apply. Extend and configure it; never fork a
parallel dispatch mechanism that duplicates what `Workflow` already does.

This does not change MODE 3 on other harnesses (Codex, gemini-cli, Cursor,
ECC) — oramasys-method is deliberately agent-neutral (see its "Agent
Harness Compatibility" section) and those harnesses don't have `Workflow`/
`ultracode`. This mapping applies only when the current harness is Claude
Code.

## Why this wasn't explicit before

orama-system predates the `Workflow` tool and was written harness-neutral
by design, so MODE 3 stayed described in the abstract (an ASCII diagram of
agent roles, `config/agent_registry.json` + `config/routing_rules.json`)
without naming a concrete Claude Code execution mechanism. That was correct
when no such mechanism existed in-harness; now that Claude Code has one, a
literal reading of the mother skill's MODE 3 section could be read as
instructing a bespoke dispatch loop instead of using it — this file exists
to remove that ambiguity, added 2026-07-22.

## Concrete mapping

| orama-system MODE 3 concept | Claude Code `Workflow` primitive |
| --- | --- |
| Orchestrator | The script body itself (`export const meta = {...}` + control flow) |
| Context Agent (Stage 1, parallel doc scanner + git historian) | `parallel([...])` of two `agent()` calls tagged to a `phase('Context')` |
| Architect Agent (Stage 2) | `agent()` call, `phase('Architect')` |
| Refiner Agent (Stage 3, elegance loops, max 3, threshold 0.8) | `pipeline()`/loop-until pattern re-invoking `agent()` up to 3 times, judged against a threshold |
| Executor Agents x5 (Stage 4, parallel TDD) | `parallel()` of 5 `agent()` calls, each running CIDF `decide()` before its own write |
| Verifier Agent (Stage 4.5, blocks until PASS) | A verify-stage `agent()` (or adversarial-verify pattern) gating the pipeline before Crystallize |
| Crystallizer Agent (Stage 5) | Final `agent()` call, or plain script code, updating lessons |
| Four mandatory roles (Builder/Critic/Adversary/Judge, `collaborative-reasoning-safety.md`) | `Workflow`'s "Adversarial verify" pattern (N independent skeptics via `parallel()`, kill on majority refute) and "Judge panel" pattern (score N independent attempts, synthesize) |
| "Switching Mode 2 → Mode 3 is an Ask First boundary (resource cost)" | `Workflow`'s own strict opt-in policy: only invoke on explicit "ultracode", explicit user ask, a skill/command that says to, or a named saved workflow — never invoke speculatively |

## Model selection (mandatory — never inherit the parent's model/effort)

This file is the **Anthropic-path** mapping for MODE 3 on Claude Code.
It does not apply Claude-only defaults to Cursor, Grok Bot, or other
harnesses. Canonical rules are Alexandria PR #1 (tip `e7ee9db6`) and
`docs/standards/model-governance.md`.

`Workflow`'s `agent()` call inherits the session's resolved model when
`opts.model` is omitted. **MODE 3 must never rely on that default** —
Claude Code `default` resolves to Opus 5.5. Every `agent()` call sets
`model`/`effort` explicitly.

**Default — Sonnet 5.5, effort medium (`claude-sonnet-5-5`).**
Vendor default effort is `high`; set `medium` explicitly. `claude-sonnet-5`
is allowed only as a legacy pin.

**Escalation A — Opus 5.5 (`claude-opus-5-5`), effort high.**
Requires an escalation token (Alexandria standard, "Escalation token")
(S-AuthZ bearer **and** a fresh signed HITL approval, ≤24h). `AskUserQuestion`
alone is not a token. Config flags, env vars, agent-writable files, and
cached approvals are not a token.

**Escalation B — Fable 5.1 (`claude-fable-5-1`).**
Requires an escalation token **and** a hard budget cap named in the
approval. Effort medium unless the approval names another level. Keep
Fable in Claude Code `deniedModels` unless that token covers the task.

Agents never raise effort, enable fast mode, or switch models on their own.

```js
// Default Anthropic-path launch (set explicitly; never omit model/effort)
const verdict = await agent(`Evaluate and integrate: ${codexResult}`, {
  model: 'claude-sonnet-5-5', effort: 'medium',
})

// Opus / Fable: omit unless a current escalation token names that model,
// effort, fast setting, task, budget cap (Fable), and expiry.
```

**Anti-pattern this replaces:** shipping a MODE 3 `Workflow` whose
`agent()` calls omit `model`/`effort` and silently inherit Opus, or that
treat a chat confirmation as an escalation token.

## What this does NOT mean

- Do not remove or flatten MODE 3's own content (the role table, the
  Builder/Critic/Adversary/Judge doctrine, the resource-cost caution) —
  that content is the policy `Workflow` scripts should encode, not
  redundant with it.
- Do not call `Workflow` for MODE 2 (Mode 2 stays inline + Task-tool
  subagents, per the mother skill's own Router Decision Table) — this
  mapping is Mode 3 only.
- Do not auto-invoke `Workflow` without the same opt-in gate the tool
  itself requires. Reaching MODE 3 in orama's own router table is
  necessary but not sufficient — the ultracode/explicit-ask gate still
  applies on top of it.

## Re-verification

If Claude Code's own `Workflow` tool contract changes (opt-in rule, hook
names, concurrency caps), re-read the tool's own description in the
current system context — this file is a mapping, not a copy, and should
never drift into being a second source of truth for that contract.
