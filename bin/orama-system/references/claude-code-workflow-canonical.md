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

## Model Tiering (mandatory — never inherit the parent's model/effort)

`Workflow`'s `agent()` call inherits the session's resolved model when
`opts.model` is omitted. **MODE 3 must never rely on that default.** Every
`agent()` call in a MODE 3 script sets `model`/`effort` explicitly, per
this three-tier frugality policy — cheapest tier that can do the job,
escalate only when the tier below genuinely can't:

**Tier 1 — Dispatch/control: Haiku (`claude-haiku-4-5-20251001`).**
Job: spawn, direct, and operate every NON-Claude model/CLI this repo
dispatches to and wants tightly controlled — Codex, Cline, Kimi, Cursor,
Grok, Perplexity, OpenClaw, Hermes, and any other external agent. Haiku's
job here is orchestration and control, not deep reasoning — it drives the
dispatch, it doesn't do the thinking.

**Tier 2 — Evaluate/integrate: Sonnet 5, effort medium.**
Job: ONLY evaluating and integrating tier 1's work output — grading,
merging, synthesizing, deciding pass/fail. Never used for dispatch/control
itself; never skipped when tier-1 output needs judgment before landing.

**Tier 3 — Escalation only: Opus (`claude-opus-4-8`) and/or Fable 5
(`claude-fable-5`).**
NEVER automated. Exactly two legitimate triggers:
1. The user explicitly named Opus or Fable 5 for this task.
2. A genuine escalation where tier 2 (Sonnet Medium) could not resolve the
   work — raise an `AskUserQuestion` confirming the escalation **before**
   spawning any Opus/Fable-5 `agent()` call. Never auto-escalate silently.

Escalation is strictly ordered: tier 1 → tier 2 → tier 3, matched to
actual task complexity. Never skip a tier "to be safe," and never reach
for tier 3 because tier 1 was merely inconvenient — only because tier 2
genuinely couldn't close it.

```js
// Tier 1 — dispatch/control (cheap, high fan-out)
const codexResult = await agent('Run codex exec on: ...', {
  model: 'claude-haiku-4-5-20251001', effort: 'low',
})

// Tier 2 — evaluate/integrate (judgment on tier-1 output, not dispatch)
const verdict = await agent(`Evaluate and integrate: ${codexResult}`, {
  model: 'claude-sonnet-5', effort: 'medium',
})

// Tier 3 — escalation only, gated behind AskUserQuestion, never automatic
// (omit unless the user named Opus/Fable 5, or verdict confirms tier 2
// couldn't resolve it AND the user confirmed escalation)
```

**Anti-pattern this replaces:** shipping a MODE 3 `Workflow` whose
`agent()` calls omit `model`/`effort` and silently inherit the parent
session's tier for every spawned agent — including cheap dispatch/control
work that never needed it. An unset `model` on a dispatch-tier call in a
MODE 3 script is a bug, not an acceptable default.

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
