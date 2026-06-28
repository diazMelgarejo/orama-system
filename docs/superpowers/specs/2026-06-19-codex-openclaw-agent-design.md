# Codex OpenClaw Agent - Draft Design Spec

**Date:** 2026-06-19
**Scope:** orama-system skill design only
**Status:** Approved design inputs captured; ready for implementation planning
**Primary skill name:** `codex-openclaw-agent`
**Skill location:** `bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/`

---

## Goal

Create a composable meta-skill that initializes a fresh OpenClaw coding agent
with a Codex backend. The skill should feel like `hermes-harness`: a thin
operator harness that wires existing durable skills and profiles together,
rather than copying their bodies into a new source of truth.

The underlying purpose is not only "make an agent." It is to make Codex a
first-class OpenClaw worker that inherits OpenClaw's runtime rules, Orama's
skill discipline, and the code-review profile stack without forcing each
harness to rediscover that contract. The skill is an adapter between intent
and operating substrate: it turns a request for a Codex coding worker into a
versioned OpenClaw agent with auditable prompts, predictable interaction
surfaces, and generated files that can be refreshed as the source profiles
improve.

The first supported workflow is:

1. Ensure the cc-openclaw upstream submodule is initialized.
2. Invoke the Orama-normalized `openclaw-new-agent` overlay.
3. Compose a Codex coding profile from the existing code-review profile sources.
4. Materialize the composed Codex profile into the new OpenClaw agent directory.
5. Register, stow, restart, and verify the agent through existing OpenClaw skills.

## Approved Defaults

- Use generated profile files with source-path and source-hash headers.
- Name the skill `codex-openclaw-agent`.
- Place the skill under
  `bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/` because it is
  an OpenClaw agent initializer, not a generic top-level Orama harness.
- Default regeneration behavior is merge marked generated sections while
  preserving operator-authored sections.
- Generate substantive marked sections in all four OpenClaw directive files:
  `CODEX.md`, `AGENTS.md`, `TOOLS.md`, and `SECURITY.md`.
- On source-hash drift, warn, continue, and auto-regenerate marked sections.
- Support standalone agents, sub-agents under an orchestrator, and ask-each-time
  interactive selection; default interactive behavior is ask-each-time, and
  future autoplan may select a mode explicitly.
- Expose interactivity through the active surface: interrupt envelopes for
  agent/harness runtimes, `AskUserQuestion` on desktop apps, CLI prompts or
  flags in terminal/cmd, and portal GUI controls when running through the
  portal.

## Non-Goals

- Do not implement the skill until this design is approved.
- Do not copy full profile bodies into `SKILL.md`.
- Do not replace `openclaw-new-agent`; call it as the creation primitive.
- Do not mutate `.claude/skills`; this is an Orama/OpenClaw/Codex harness.
- Do not create a general OpenClaw UI or runtime manager.
- Do not hardcode a single interaction mechanism. User choice must flow through
  the surface the operator is actually using.

## Source Inputs

The harness composes these sources:

| Source | Role |
|--------|------|
| `bin/orama-system/skills/openclaw-skills/SKILL.md` | Master OpenClaw skill pack and routing policy |
| `bin/orama-system/skills/openclaw-skills/skills/openclaw-new-agent/SKILL.md` | Orama-normalized agent creation overlay |
| `bin/orama-system/skills/openclaw-skills/cc-openclaw/.claude/skills/openclaw-new-agent/SKILL.md` | Upstream cc-openclaw baseline |
| `bin/orama-system/skills/hermes-harness/SKILL.md` | Harness shape and cross-harness boundary model |
| `bin/orama-system/skills/code-review/profiles/J-drona23-v5/CLAUDE.md` | Governing profile router and constraint source |
| `bin/orama-system/skills/code-review/profiles/J-drona23-v5/rules/workflow.md` | Hard workflow rules |
| `bin/orama-system/skills/code-review/profiles/J-drona23-v5/agents/builder.md` | Builder agent budget and execution contract |
| `bin/orama-system/skills/code-review/profiles/CLAUDE.agents.md` | Multi-agent output and automation discipline |
| `bin/orama-system/skills/code-review/profiles/CLAUDE.coding.md` | Coding, review, debugging, and refactor discipline |

## Recommended Approach

Use a thin harness skill plus a deterministic profile generator.

`codex-openclaw-agent/SKILL.md` should remain concise. It should describe
when to use the harness, which source files to read, what command/script to run,
and how to verify the resulting OpenClaw agent.

The mother skill remains the first filter. The new skill lives under
`openclaw-skills/` so agents discover it through the OpenClaw skill pack, then
it composes code-review profiles only after `openclaw-skills/SKILL.md` has set
the operational rules, model routing, invocation envelope, and OpenClaw safety
constraints.

A bundled script should generate the Codex profile artifacts for the target
OpenClaw agent. The generated files should include source-path and source-hash
headers so the operator can audit exactly which profile versions created the
agent.

This gives spawned agents stable behavior while preserving the current profile
files as canonical.

## Alternatives Considered

### Option A: Live Composition at Agent Startup

The agent reads the profile source files every time it starts.

Pros:
- No generated profile drift.
- Source edits affect new sessions immediately.

Cons:
- Startup depends on source repo availability and path stability.
- Harder to audit what profile version a past agent used.
- Agent behavior can change without an explicit regeneration event.

### Option B: Generated Profile Files

The harness reads the source files once and writes generated profile files into
the OpenClaw agent directory with source hashes.

Pros:
- Deterministic and auditable per spawned agent.
- Easy to diff and review.
- Keeps source files canonical without requiring live reads at startup.

Cons:
- Requires a regeneration command when sources change.
- Needs a small script and validation test.

### Option C: Copy Prompt Body Into New Skill

The new skill embeds the harmonized profile text directly.

Pros:
- Simple first implementation.

Cons:
- Creates a new source of truth.
- Drifts quickly.
- Violates the existing thin-wrapper and progressive-disclosure pattern.

Decision: Option B.

## Proposed Skill Shape

```
bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/
  SKILL.md
  scripts/
    generate_codex_openclaw_profile.py
  references/
    profile-composition.md
```

`SKILL.md` should cover:

- Use when spawning or refreshing a Codex-backed OpenClaw coding agent.
- Ensure cc-openclaw exists through `scripts/install-openclaw-skills.sh`.
- Load `openclaw-new-agent` through the Orama overlay path.
- Route operator choices through the active interaction surface.
- Compose profiles using the source precedence below.
- Run verification and report generated files.

`references/profile-composition.md` should cover:

- Source precedence.
- Conflict-resolution rules.
- Generated file layout.
- Source-hash format.
- Regeneration behavior.
- Interaction-surface mapping.

`scripts/generate_codex_openclaw_profile.py` should:

- Accept `--openclaw-home`, `--agent-id`, and `--repo-root`.
- Accept `--mode ask|sub-agent|standalone`, with `ask` as the interactive
  default and explicit mode required for non-interactive runs.
- Read the source profile files.
- Validate all required sources exist.
- Generate deterministic markdown files under the target agent directory.
- Include source-path and SHA-256 headers.
- Merge marked generated sections by default while preserving unmarked operator
  content.
- Exit nonzero if source paths are missing or generated output is incomplete.

## Composition Rules

Profile composition must be iterative and filtered, not a blind concatenation.
The generator should apply the mother skill first, then the OpenClaw overlay,
then the code-review profiles, keeping only content that serves the Codex
OpenClaw agent's runtime contract.

Profile precedence should be:

1. `openclaw-skills/SKILL.md` supplies OpenClaw operational rules, universal
   invocation, model routing, and cross-harness boundaries.
2. `openclaw-new-agent` supplies OpenClaw file layout, registration, stow, restart,
   and verification behavior.
3. `J-drona23-v5/CLAUDE.md` defines what must be read and constrains profile scope.
4. `J-drona23-v5/rules/workflow.md` supplies hard MUST and NEVER rules.
5. `J-drona23-v5/agents/builder.md` supplies budget and builder protocol.
6. `CLAUDE.coding.md` supplies coding, review, debugging, and architecture style.
7. `CLAUDE.agents.md` supplies multi-agent and structured-output discipline.

When sources conflict, the generator should keep the stricter rule. Examples:

- If one file says to avoid status prose and another requires human-readable
  review output, generated output should distinguish machine mode from human
  report mode.
- If one file allows defaults and another requires explicit requirements, the
  generated profile should require explicit inputs for file writes and use
  defaults only for non-destructive configuration values.

The generator should also remove or down-rank content that belongs to Claude
only, raw `.claude/skills` install flows, or generic coding advice that is
already enforced by the OpenClaw mother skill.

## Generated Artifact Layout

For an agent id `codex-agent`, the harness should generate:

```
$OPENCLAW_HOME/.openclaw/agents/codex-agent/
  CODEX.md
  AGENTS.md
  TOOLS.md
  SECURITY.md
  refs/
    codex-profile-sources.md
```

`CODEX.md` should be the primary generated behavior profile.

All four generated directive files should contain substantive generated
sections, filtered through the mother `orama-system` skill and the source
precedence rules:

| File | Generated responsibility |
|------|--------------------------|
| `CODEX.md` | Primary Codex behavior profile, coding workflow, output discipline, and source-hash policy |
| `AGENTS.md` | OpenClaw startup sequence, parent/sub-agent routing instructions, and orchestrator handoff rules |
| `TOOLS.md` | Codex CLI, OpenClaw skill commands, verification commands, and allowed local tooling |
| `SECURITY.md` | Secrets boundaries, sandbox/approval policy, source-hash drift behavior, and disclosure prevention |

`refs/codex-profile-sources.md` should list:

- source path
- SHA-256
- role in composition
- generation timestamp
- generator version

Existing files should be updated by merging only marked generated sections:

```markdown
<!-- BEGIN GENERATED: codex-openclaw-agent CODEX.md -->
...
<!-- END GENERATED: codex-openclaw-agent CODEX.md -->
```

Unmarked operator-authored content must be preserved. If a target file exists
without expected generated markers, the generator should append a new generated
section and report that it preserved the existing body.

`--force` may replace an entire target file, but it must be opt-in and report
the full list of replaced files.

## Source-Hash Drift Policy

On each refresh or startup check, compare `refs/codex-profile-sources.md`
against current source file SHA-256 values.

If hashes differ:

1. Warn with the changed source paths.
2. Continue operation rather than blocking the agent.
3. Auto-regenerate marked generated sections when the target files are writable
   and generated markers are well-formed.
4. If auto-regeneration cannot run safely, preserve existing files and report
   the exact manual regeneration command.

This keeps agent behavior current without making normal OpenClaw operation
fragile. Refuse-to-run behavior should remain an optional future strict mode.

## Spawn Mode Policy

`codex-openclaw-agent` should support all OpenClaw relationship modes:

| Mode | Use |
|------|-----|
| `sub-agent` | Create a Codex coding agent under an existing orchestrator and wire `allowAgents` |
| `standalone` | Create a top-level Codex-backed OpenClaw agent for independent operation |
| `ask` | Ask the operator which relationship to use before creation |

Default interactive behavior is `ask`. Non-interactive runs must pass
`--mode sub-agent` or `--mode standalone`. A future autoplan layer may choose
the mode from task context before invoking this skill.

## Interaction Surface Policy

The skill must express the same decisions through different operator surfaces:

| Surface | Interaction mechanism |
|---------|-----------------------|
| Agent or harness runtime | Return an interrupt envelope with required fields and choices |
| Codex or Claude desktop apps | Use `AskUserQuestion` when available |
| Terminal/cmd | Use CLI flags first; if missing, prompt on stdin only when interactive |
| Portal GUI | Render the same fields as form controls and submit a normalized envelope |

Required choices should be stable across surfaces:

- `agent_id`
- display name
- spawn mode: `ask`, `sub-agent`, or `standalone`
- parent orchestrator when mode is `sub-agent`
- profile regeneration mode
- channel wiring preference

The normalized answer shape should feed the same downstream generator and
`openclaw-new-agent` invocation regardless of source. Portal GUI, CLI, desktop,
and interrupt flows must not fork behavior.

## Data Flow

```text
operator
  -> codex-openclaw-agent
  -> interaction surface resolves missing choices
  -> scripts/install-openclaw-skills.sh
  -> openclaw-new-agent overlay
  -> generate_codex_openclaw_profile.py
  -> OpenClaw agent files
  -> openclaw-stow
  -> openclaw-restart
  -> openclaw-status
```

## Error Handling

The harness should stop before file writes if:

- cc-openclaw is not initialized and cannot be initialized.
- any required profile source is missing.
- `openclaw_home` is not absolute.
- target `agent_id` is invalid.
- an interactive choice is required but no interrupt, desktop question, CLI
  prompt, portal GUI, or explicit flag is available.
- target files cannot be merged safely because generated markers are malformed.

The harness should report:

- what failed
- which source or target path was involved
- whether any files were modified
- the next safe recovery action

## Testing Plan

Implementation should include targeted checks:

1. Run `bash scripts/install-openclaw-skills.sh`.
2. Run generator in dry-run mode against a temporary OpenClaw home.
3. Assert generated files include source paths and SHA-256 hashes.
4. Assert missing source files fail with a clear error.
5. Assert existing operator-authored content is preserved by default.
6. Assert generated markers are replaced idempotently on regeneration.
7. Assert hash drift warns, continues, and regenerates marked sections when safe.
8. Assert `--mode sub-agent`, `--mode standalone`, and interactive ask mode
   produce the expected `openclaw-new-agent` inputs.
9. Assert interrupt, desktop, CLI, and portal input surfaces normalize to the
   same envelope.
10. Run skill validation for the new skill folder.

## Recommendation

Proceed with `codex-openclaw-agent`, generated profile files, source hashes, and
merge-marked regeneration. Generate substantive sections in all four OpenClaw
directive files, warn and auto-regenerate on source drift, and keep spawn mode
flexible with ask-each-time as the interactive default. Keep the skill under
`openclaw-skills/` so it is governed by the OpenClaw mother skill before it
composes code-review profile material.
