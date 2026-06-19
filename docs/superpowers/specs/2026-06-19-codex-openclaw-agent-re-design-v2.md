# Codex OpenClaw Agent - Re-Design v2

**Date:** 2026-06-19
**Scope:** orama-system skill design plus Codex backend-binding substrate
**Status:** Corrected scope after backend-binding decision and Eng/DX review
**Primary skill name:** `codex-openclaw-agent`
**Skill location:** `bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/`

---

## Goal

Create a composable OpenClaw meta-skill that initializes a real Codex-backed
OpenClaw coding agent, not only a Codex-flavored profile.

The skill is a first-class OpenClaw agent initializer. It should feel like
`hermes-harness`: a thin operator harness that composes durable repo skills,
profile sources, and local runtime bindings without copying their bodies into a
new source of truth.

The v2 correction is explicit:

- `codex-openclaw-agent` owns the Codex binding as a core substrate.
- The binding substrate is a peer module, companion and equal in importance to
  `hermes-harness`.
- The primary substrate is the native Codex app-server plugin path.
- The fallback substrate is Codex's already-running app-server exposed to
  OpenClaw as an OpenAI-compatible provider.
- The resolver is opportunistic: probe, use what works first, install
  idempotently if the primary plugin is absent, then verify backend identity.
- `CODEX.md` is the generated binding/spec sheet that records how the agent is
  actually bound to Codex. It is not one of OpenClaw's native six directive
  files.

The underlying purpose is to make Codex a first-class OpenClaw worker that
inherits OpenClaw's runtime rules, Orama's skill discipline, and the code-review
profile stack without forcing every agent harness to rediscover the contract.

## Local Ground Truth

This v2 design is grounded in the current local stack:

| Fact | Evidence |
|------|----------|
| `openclaw-new-agent` currently creates the six OpenClaw directive files only | `SOUL.md`, `IDENTITY.md`, `USER.md`, `AGENTS.md`, `TOOLS.md`, `SECURITY.md` are created by `bin/orama-system/skills/openclaw-skills/skills/openclaw-new-agent/SKILL.md` |
| `openclaw-new-agent` currently defaults to Ollama | `model_primary` defaults to `ollama/qwen3.5:9b-nvfp4` in the overlay |
| Codex CLI is installed locally | `codex --version` reports `codex-cli 0.135.0` |
| Codex config already targets GPT-5.5 | `~/.codex/config.toml` contains `model = "gpt-5.5"`; secret values must remain redacted |
| Codex reasoning effort exists in config | `~/.codex/config.toml` contains `model_reasoning_effort = "high"` locally; v2 defaults medium and allows xhigh opt-in |
| Codex app-server reconciliation state exists | `~/.codex/.app-server-state-reconciled-v1` exists |
| Codex app-server artifacts exist | `~/.codex/cache/codex_apps_server_info`, `~/.codex/plugins/.plugin-appserver`, and `~/.codex/.tmp/app-server-remote-plugin-sync-v1` exist |
| gstack already shells Codex | `gstack` wraps `codex exec` and `codex review`, with `gstack-codex-probe` for auth/version/timeout helpers |

These facts do not prove every proposed OpenClaw plugin command exists. The
resolver must detect that at runtime and degrade to the OpenAI-compatible
fallback if the native plugin path is unavailable.

## Approved Defaults

- Use generated profile files with source-path and source-hash headers.
- Name the skill `codex-openclaw-agent`.
- Place the skill under
  `bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/`.
- Treat backend binding as a first-class peer module:
  `references/codex-backend-binding.md` plus `scripts/bind_codex_backend.sh`.
- Use native Codex app-server plugin binding as the primary path.
- Use Codex app-server-as-OpenAI-compatible-provider as fallback.
- Resolve opportunistically: use what works first; install primary plugin
  idempotently if missing and installable.
- Default Codex reasoning effort is `medium`; `xhigh` is opt-in because it is
  high cost and high latency.
- Default regeneration behavior is merge marked generated sections while
  preserving operator-authored sections.
- Generate substantive marked sections in `CODEX.md`, `AGENTS.md`, `TOOLS.md`,
  and `SECURITY.md`.
- Also write or update the real OpenClaw runtime files and `openclaw.json` so
  the runtime invokes Codex, not Ollama.
- On source-hash drift, warn, continue, and auto-regenerate marked sections
  when safe.
- Support standalone agents, sub-agents under an orchestrator, and ask-each-time
  interactive selection.
- Expose interactivity through the active surface: interrupt envelopes for
  agent/harness runtimes, `AskUserQuestion` on desktop apps, CLI flags/prompts
  in terminal/cmd, and portal GUI controls when running through the portal.

## Non-Goals

- Do not mutate `.claude/skills`.
- Do not copy Codex bearer tokens, OpenAI keys, or OAuth material into generated
  files, refs, logs, prompts, or committed docs.
- Do not assume `CODEX.md` is an OpenClaw native directive file.
- Do not rely on profile text as proof of backend binding.
- Do not make a portal GUI a blocker for v1. The envelope should be defined now;
  GUI rendering can follow after the CLI and agent surfaces work.
- Do not let the generator write directly into a stow target. Write to the
  openclaw-home source repo, then stow.

## Target Skill Shape

```text
bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/
  SKILL.md
  references/
    codex-backend-binding.md
    profile-composition.md
  scripts/
    bind_codex_backend.sh
    generate_codex_openclaw_profile.py
```

### `SKILL.md`

The top-level skill should stay thin. It should:

1. Load the OpenClaw mother skill first.
2. Ensure `cc-openclaw` is initialized through `scripts/install-openclaw-skills.sh`.
3. Resolve missing operator choices through the active interaction surface.
4. Invoke `openclaw-new-agent` through the Orama overlay.
5. Run `scripts/bind_codex_backend.sh`.
6. Run `scripts/generate_codex_openclaw_profile.py`.
7. Stow, restart, status-check, and assert backend identity.

### `references/codex-backend-binding.md`

This is the binding doctrine. It should define:

- Resolution ladder.
- Provider strings.
- Required probes.
- Auth-by-reference rule.
- OpenAI-compatible fallback provider shape.
- Verification requirements.
- Failure messages and manual recovery commands.

### `scripts/bind_codex_backend.sh`

This is the operational substrate. It must be idempotent and safe to re-run.

Inputs:

- `--openclaw-home`
- `--agent-id`
- `--model gpt-5.5` by default
- `--effort medium|high|xhigh` with `medium` default
- `--mode probe|bind|verify` or a combined default flow
- `--prefer plugin|compat|auto` with `auto` default

Outputs:

- JSON on stdout.
- Diagnostics on stderr.
- A binding record consumable by the profile generator.

### `scripts/generate_codex_openclaw_profile.py`

This generator consumes the binding record and source profiles. It writes
generated sections into `CODEX.md`, `AGENTS.md`, `TOOLS.md`, and `SECURITY.md`
while preserving operator-authored sections.

## Backend Binding Substrate

The binding resolver is a fail-forward ladder.

### Stage 0: Probe Only

No mutation. Gather evidence:

- Is the native `openclaw-codex-app-server` plugin installed?
- Is the plugin install command available?
- Is Codex CLI installed?
- Does `gstack-codex-probe` report auth OK?
- Does Codex app-server reconciliation state exist?
- Is the app-server endpoint reachable?
- Does `openclaw.json` already contain a Codex provider or Codex primary model?
- Is the requested model/effort represented by local Codex config structure?

The probe must redact secrets. It may report that an auth file or env reference
exists, but never the value.

### Stage 1: Primary - Native Plugin Binding

If the native plugin path is present:

1. Bind through the native `openclaw-codex-app-server` plugin.
2. Reuse local Codex auth by reference.
3. Bind or resume the app-server session.
4. Set the target OpenClaw agent's model primary to the native Codex provider.
5. Record provider, model, effort, auth source reference, endpoint, and verify
   plan in the binding record.

Design names currently approved for the primary path:

- Plugin: `openclaw-codex-app-server`
- Auth choice: `openai-codex`
- Session bind/resume: `/cas_resume`
- Model: `gpt-5.5`
- Effort: `medium` default, `xhigh` opt-in

Because those names may be ahead of the currently installed OpenClaw CLI, the
resolver must verify them locally before invoking them.

### Stage 2: Idempotent Install

If the plugin is absent but installable:

1. Check whether a plugin manager exists.
2. Check whether the plugin is available.
3. Install only if absent.
4. Re-run Stage 1.

The install path must be safe on repeated runs. If a partial install is
detected, the resolver should report the partial state and either repair it
idempotently or stop with a precise manual recovery command.

### Stage 3: Fallback - OpenAI-Compatible Provider

If the native plugin path cannot be used, register Codex's already-running
local app-server as an OpenAI-compatible provider in OpenClaw gateway config.

The fallback should:

- Use the local Codex app-server endpoint discovered by probe.
- Reuse `~/.codex` auth by reference.
- Set `model.primary` to a Codex provider string such as `codex/gpt-5.5`.
- Preserve existing non-target provider settings.
- Avoid replacing global defaults unless the operator passed `--force-primary`
  or is creating the new Codex agent where Codex primary is expected.

This fallback is a real substrate, not a second-class escape hatch. It allows
the feature to work before the native plugin exists everywhere.

### Stage 4: Verify

Verification is the gate that proves "Codex-backed" rather than
"Codex-profiled."

Required checks:

1. Start or resume an OpenClaw session for the target agent.
2. Run a harmless task.
3. Capture backend identity from the OpenClaw/gateway trace.
4. Assert backend family is Codex/OpenAI-compatible Codex and not Ollama.
5. Assert model resolves to the requested Codex model.
6. Record verification result in the binding record.

If verification fails, the skill must fail loudly with:

- Chosen binding path.
- Expected provider/model.
- Actual provider/model.
- Redacted auth source reference.
- Endpoint reference.
- Manual recovery command.

### Stage 5: Record

The resolver writes a binding record for the generator. The generated `CODEX.md`
must include:

- Winning path: `plugin` or `openai-compatible-fallback`.
- Provider string.
- Model and effort.
- Auth source by reference only.
- Endpoint reference.
- Verification result.
- Timestamp.
- Generator version.
- Source hashes of the profile inputs.

## `CODEX.md` Contract

`CODEX.md` is not a native OpenClaw directive file. It is the generated
Codex-binding/spec sheet owned by `codex-openclaw-agent`.

It grounds:

- Which Codex backend was resolved.
- How the OpenClaw agent is configured to invoke Codex.
- Which profile sources produced the Codex behavior profile.
- Which verification proved the runtime backend.

The runtime still reads the native OpenClaw files:

- `SOUL.md`
- `IDENTITY.md`
- `USER.md`
- `AGENTS.md`
- `TOOLS.md`
- `SECURITY.md`
- `openclaw.json`

Therefore the generator must update both:

1. `CODEX.md` as the binding/spec record.
2. The OpenClaw runtime files and `openclaw.json` as the actual execution
   surface.

## Generated Artifact Layout

For an agent id `codex-agent`, write into the openclaw-home source repo:

```text
$OPENCLAW_HOME/agents/codex-agent/
  SOUL.md
  IDENTITY.md
  USER.md
  AGENTS.md
  TOOLS.md
  SECURITY.md
  CODEX.md
  refs/
    codex-profile-sources.md
    codex-backend-binding.json
```

Generated responsibilities:

| File | Generated responsibility |
|------|--------------------------|
| `CODEX.md` | Binding/spec sheet: resolved backend, provider string, model/effort, auth reference, endpoint, verification, source hashes |
| `IDENTITY.md` | Agent identity and primary Codex model summary visible to OpenClaw operators |
| `AGENTS.md` | Startup sequence, sub-agent routing, parent/orchestrator handoff, backend verification reminder |
| `TOOLS.md` | Codex CLI, OpenClaw skill commands, binding script, verification commands, allowed local tooling |
| `SECURITY.md` | Auth-by-reference, sandbox/approval policy, generated-section ownership, disclosure prevention |
| `openclaw.json` | Actual model/provider binding for the target agent |
| `refs/codex-profile-sources.md` | Source path, SHA-256, role, timestamp, generator version |
| `refs/codex-backend-binding.json` | Machine-readable binding result, redacted and repo-safe |

Existing files should be updated by merging only marked generated sections:

```markdown
<!-- BEGIN GENERATED: codex-openclaw-agent CODEX.md -->
...
<!-- END GENERATED: codex-openclaw-agent CODEX.md -->
```

Unmarked operator-authored content must be preserved. If a target file exists
without expected generated markers, append a generated section and report that
the existing body was preserved.

`--force` may replace an entire target file, but it must be opt-in and report
the full list of replaced files.

## Source Inputs

The harness composes these sources:

| Source | Role |
|--------|------|
| `bin/orama-system/skills/openclaw-skills/SKILL.md` | Mother OpenClaw skill pack and routing policy |
| `bin/orama-system/skills/openclaw-skills/skills/openclaw-new-agent/SKILL.md` | Orama-normalized agent creation overlay |
| `bin/orama-system/skills/openclaw-skills/cc-openclaw/.claude/skills/openclaw-new-agent/SKILL.md` | Upstream cc-openclaw baseline |
| `bin/orama-system/skills/hermes-harness/SKILL.md` | Harness shape and cross-harness boundary model |
| `bin/orama-system/skills/code-review/profiles/J-drona23-v5/CLAUDE.md` | Governing profile router and constraint source |
| `bin/orama-system/skills/code-review/profiles/J-drona23-v5/rules/workflow.md` | Hard workflow rules |
| `bin/orama-system/skills/code-review/profiles/J-drona23-v5/agents/builder.md` | Builder agent budget and execution contract |
| `bin/orama-system/skills/code-review/profiles/CLAUDE.agents.md` | Multi-agent output and automation discipline |
| `bin/orama-system/skills/code-review/profiles/CLAUDE.coding.md` | Coding, review, debugging, and refactor discipline |
| `~/.agents/skills/gstack/codex/SKILL.md` | Existing Codex CLI usage pattern and second-opinion modes; use as reference, not copied body |
| `gstack-codex-probe` | Existing auth/version/timeout helper pattern; reuse or wrap rather than reimplement when available |

## Composition Rules

Profile composition must be iterative and filtered, not a blind concatenation.

Precedence:

1. `openclaw-skills/SKILL.md` supplies OpenClaw operational rules, universal
   invocation, model routing, and cross-harness boundaries.
2. `codex-backend-binding.md` supplies the backend substrate contract.
3. `openclaw-new-agent` supplies file layout, registration, stow, restart, and
   verification behavior.
4. `J-drona23-v5/CLAUDE.md` defines profile scope.
5. `J-drona23-v5/rules/workflow.md` supplies hard MUST and NEVER rules.
6. `J-drona23-v5/agents/builder.md` supplies budget and builder protocol.
7. `CLAUDE.coding.md` supplies coding/review/debugging style.
8. `CLAUDE.agents.md` supplies multi-agent and structured-output discipline.
9. gstack Codex references supply CLI invocation patterns, auth probe reuse, and
   timeout behavior.

When sources conflict, the generator keeps the stricter runtime-safe rule.
Examples:

- If profile text implies Codex but binding verification says Ollama, fail
  instead of generating a misleading `CODEX.md`.
- If one file permits defaults and another requires explicit write inputs,
  require explicit inputs for file writes and use defaults only for
  non-destructive configuration values.
- If one source is Claude-only, remove or down-rank it unless it is genuinely
  harness-neutral.

## Spawn Mode Policy

`codex-openclaw-agent` supports all three relationship modes:

| Mode | Use |
|------|-----|
| `sub-agent` | Create a Codex coding agent under an existing orchestrator and wire `allowAgents` |
| `standalone` | Create a top-level Codex-backed OpenClaw agent for independent operation |
| `ask` | Ask the operator which relationship to use before creation |

Default interactive behavior is `ask`. Non-interactive runs must pass
`--mode sub-agent` or `--mode standalone`. A future autoplan layer may choose
the mode from task context before invoking this skill.

## Interaction Surface Policy

The same decisions must flow through different surfaces without forking
behavior:

| Surface | Interaction mechanism |
|---------|-----------------------|
| Agent or harness runtime | Return an interrupt envelope with required fields and choices |
| Codex or Claude desktop apps | Use `AskUserQuestion` when available |
| Terminal/cmd | Use CLI flags first; prompt on stdin only when interactive |
| Portal GUI | Render the same fields as form controls and submit a normalized envelope |

Required normalized fields:

- `agent_id`
- display name
- spawn mode: `ask`, `sub-agent`, or `standalone`
- parent orchestrator when mode is `sub-agent`
- profile regeneration mode
- channel wiring preference
- Codex effort: `medium`, `high`, or `xhigh`
- binding preference: `auto`, `plugin`, or `compat`
- strict verification: boolean

## Data Flow

```text
operator
  -> codex-openclaw-agent
  -> interaction surface resolves missing choices
  -> scripts/install-openclaw-skills.sh
  -> openclaw-new-agent overlay
  -> bind_codex_backend.sh
       probe
       -> primary native plugin
       -> idempotent install if absent and installable
       -> fallback OpenAI-compatible Codex app-server provider
       -> verify backend identity
       -> write redacted binding record
  -> generate_codex_openclaw_profile.py
  -> CODEX.md + OpenClaw runtime files + openclaw.json
  -> openclaw-stow
  -> openclaw-restart
  -> openclaw-status
  -> final backend identity assert
```

## Error Handling

Stop before writes if:

- `cc-openclaw` is not initialized and cannot be initialized.
- Any required source file is missing.
- `openclaw_home` is not absolute.
- `agent_id` is invalid.
- An interactive choice is required but no surface can ask and no explicit flag
  was provided.
- Generated markers are malformed.
- Binding verification would write into a stow target.
- Codex auth is unavailable.
- The selected provider resolves to Ollama after binding.

Report:

- What failed.
- Which stage failed.
- Which source or target path was involved.
- Whether any files were modified.
- The next safe recovery command.
- The redacted binding context.

## Testing Plan

Implementation should include targeted checks:

1. Run `bash scripts/install-openclaw-skills.sh`.
2. Run `bind_codex_backend.sh --mode probe` with no writes.
3. Unit-test plugin-present, plugin-absent-installable, plugin-absent-offline,
   app-server-down, auth-missing, partial-install, and provider-already-bound
   cases.
4. Unit-test OpenAI-compatible fallback config generation.
5. Assert no generated file contains API keys, bearer tokens, or absolute
   workstation paths.
6. Run generator in dry-run mode against a temporary OpenClaw home.
7. Assert generated files include source paths and SHA-256 hashes.
8. Assert existing operator-authored content is preserved by default.
9. Assert generated markers are replaced idempotently on regeneration.
10. Assert source-hash drift warns, continues, and regenerates marked sections
    when safe.
11. Assert `--mode sub-agent`, `--mode standalone`, and interactive ask mode
    produce the expected `openclaw-new-agent` inputs.
12. Assert interrupt, desktop, CLI, and portal input surfaces normalize to the
    same envelope.
13. End-to-end smoke: create agent, bind Codex, stow, restart, run harmless
    task, and assert backend identity is Codex/GPT-5.5, not Ollama.
14. Run `scripts/review/repo_hygiene.py`.
15. Run skill validation for the new skill folder.

## Resumed Eng Review Against Corrected Scope

The Eng phase is now reviewing a different scope than v1. The central question
is no longer "can generated profile files describe Codex?" It is "can the
binding substrate reliably cause OpenClaw to invoke Codex at runtime?"

### Eng Finding 1: Binding Must Be a Peer Module

Severity: high.

The binding flow should not be hidden inside the generator. It changes runtime
provider state, depends on local Codex auth, and owns verification. Keeping it
as `references/codex-backend-binding.md` plus `scripts/bind_codex_backend.sh`
makes it reusable by Hermes/Gemini harnesses and testable without profile
generation.

Fix: Implement and test the binding script before the profile generator.

### Eng Finding 2: Primary Plugin Names Are Approved Design Names, Not Yet Proven Local Commands

Severity: high.

The native plugin path is the preferred design, but local search did not prove
that the current OpenClaw skill tree already exposes
`openclaw-codex-app-server`, `openclaw onboard --auth-choice openai-codex`, or
`/cas_resume`.

Fix: Treat the primary path as probe-gated. If the commands are absent, install
idempotently if possible; otherwise use the OpenAI-compatible fallback.

### Eng Finding 3: Fallback Is Required for V1 Viability

Severity: high.

Because Codex app-server state exists locally and gstack already shells Codex,
the OpenAI-compatible fallback is the shortest path to a real Codex-backed
agent before a universal OpenClaw plugin exists.

Fix: Make fallback a first-class tested path, not an exceptional path.

### Eng Finding 4: Verification Must Inspect Runtime Backend Identity

Severity: critical.

File generation and `openclaw.json` edits are insufficient. The existing
OpenClaw overlay defaults to Ollama, so the implementation must prove that the
runtime agent used Codex/GPT-5.5.

Fix: Verification must run after stow/restart and assert actual provider/model.

### Eng Finding 5: Writes Must Stay Source-Repo First

Severity: high.

The generator and binder must write to the openclaw-home source repository and
then call `openclaw-stow`. Direct writes into stow targets create drift and
make rollback/audit difficult.

Fix: Block stow-target paths unless an explicit future escape hatch is added.

## Resumed DX Review Against Corrected Scope

The DX phase focuses on operator confidence: a user should know whether they
created a real Codex worker, which path won, and what to do if binding failed.

### DX Finding 1: "Invisible When It Works" Requires a Visible Binding Summary

Severity: medium.

The happy path should be short, but it must print the resolved path, provider,
model, effort, verification status, and generated files.

Fix: End with a compact table:

| Field | Value |
|-------|-------|
| Binding path | plugin or compat |
| Provider | redacted provider string |
| Model | gpt-5.5 |
| Effort | medium/high/xhigh |
| Auth | reference only |
| Verify | pass/fail |

### DX Finding 2: Recovery Messages Need Exact Commands

Severity: high.

Resolver failures are otherwise hard to distinguish: plugin missing, app-server
down, auth missing, provider config malformed, and backend identity mismatch can
all look like "Codex failed."

Fix: Every failure includes the next safe command, for example:

- `codex login`
- `codex --version`
- `codex-openclaw-agent --agent-id <id> --prefer compat --refresh`
- `codex-openclaw-agent --agent-id <id> --bind-only --verify`

### DX Finding 3: `ask` Mode Should Not Block Non-Interactive Runs

Severity: medium.

The interactive default is correct, but agents and CI need explicit flags.

Fix: If stdin is not interactive and no desktop/interrupt/portal surface exists,
require explicit `--mode`, `--agent-id`, and `--openclaw-home`.

### DX Finding 4: CODEX.md Must Explain Its Own Status

Severity: medium.

Because `CODEX.md` is not an OpenClaw native directive file, future maintainers
could mistake it for a runtime input.

Fix: Put this banner at the top of generated `CODEX.md`:

```markdown
> Generated by codex-openclaw-agent. This file records the Codex backend
> binding and profile source hashes. OpenClaw runtime behavior is applied
> through openclaw.json and the native directive files.
```

## Recommendation

Proceed with `codex-openclaw-agent` v2 using:

1. `codex-backend-binding` as a first-class substrate and peer to
   `hermes-harness`.
2. Native Codex app-server plugin as primary.
3. Codex app-server OpenAI-compatible provider as fallback.
4. Opportunistic probe-first resolver.
5. Idempotent install if the plugin is absent but installable.
6. Runtime backend identity verification as the release gate.
7. `CODEX.md` as binding/spec sheet, not as a native OpenClaw directive.
8. Generated marked sections in `CODEX.md`, `AGENTS.md`, `TOOLS.md`, and
   `SECURITY.md`, plus actual `openclaw.json` provider binding.

This resolves the previous design blockers:

- No-backend blocker: fixed by the binding substrate.
- `CODEX.md` phantom blocker: fixed by defining it as generated binding/spec
  record while still updating actual runtime files.
- File-contract blocker: fixed by separating OpenClaw native files from the
  Codex spec sheet.
- Test gap: fixed by backend identity verification.

## Multi-Model Pressure-Test Findings (2026-06-19)

Source: a frugal direct-orchestrator panel (no Claude agents — run under an
Anthropic spend cap), one bounded call per live lane: Codex CLI (`gpt-5.5`),
Ollama (`qwen3-coder:480b-cloud`), and AGY/Antigravity. Gemini lane retired
mid-run (see Operational); OpenRouter deferred (local SSL CA). Findings below are
NEW beyond the Resumed Eng/DX Review above; corroboration is shown as `[n/3]`.

### PT-MM1 — Stage 4 backend-identity signal may not be observable [critical, 3/3]

The release gate assumes the OpenClaw/gateway trace exposes
provider/baseUrl/backend-family. If it exposes only agent+model, "assert Codex
not Ollama" cannot be implemented and verification can silently pass while the
runtime routes to Ollama. The whole "Codex-backed not Codex-profiled" guarantee
rests on a signal that is asserted, not proven.

Fix: before building Stage 4, spike whether the gateway emits a parseable
backend-identity field; if absent, add explicit backend tagging
(provider+baseUrl response header or a debug-log marker) and assert on that.
Stage 4 design is BLOCKED on this probe.

### PT-MM2 — Stage 3 fallback provider schema undefined / likely invalid [critical, 3/3]

`model.primary = codex/gpt-5.5` alone will not route. OpenClaw needs the exact
gateway provider record (`base_url`/`api_base`, `api_type`, key-by-reference,
model id). The spec asserts the fallback works but never defines the schema
OpenClaw actually accepts, so v1 viability rests on an unverified config shape.

Fix: pin the exact `openclaw` provider-registration schema for an
OpenAI-compatible endpoint; canary `GET /v1/models` against the codex
app-server; unit-test that the generated provider record loads.

### PT-MM3 — Probe accepts stale Codex artifacts -> false positives [high, 3/3]

`~/.codex/.app-server-state-reconciled-v1` and cache files can outlive the live
app-server/auth/session, so Stage 0 can report ready when it is not.

Fix: replace file-presence checks with a live authenticated canary plus
PID/port freshness; treat state files as hints only.

### PT-MM4 — `/cas_resume` is wrong for a fresh agent [high, 3/3]

`/cas_resume` resumes an EXISTING session; a newly created agent has none, so
Stage 1 will error if it calls resume during initial onboarding.

Fix: create/bind the session first; use `/cas_resume` only after session
discovery, otherwise a sessionless bind/ping.

### PT-MM5 — No lock / atomicity boundary -> partial-write corruption [high, 3/3]

Writing 6 native files + `CODEX.md` + `openclaw.json` + refs lacks a
transaction; a mid-run failure or concurrent bind/generate/stow leaves a
split-state agent. v2 mentions partial-write only in the testing plan, not the
design body.

Fix: take a per-`openclaw-home` flock for the whole bind+generate pass; write to
a temp dir, atomic-rename into the source repo, write `refs/codex-backend-binding.json`
last; roll back on failure.

### PT-MM6 — Auth-reference leak paths beyond bearer tokens [high, 1/3 Codex]

Gateway traces and copied app-server server-info
(`~/.codex/cache/codex_apps_server_info`) can expose prompts, env refs,
endpoints, and workspace paths even when the token itself is referenced.

Fix: redact logs/traces; forbid copying raw server-info into refs; strip
upstream auth from any captured trace.

### PT-MM7 — Cross-OS path/hash determinism [medium, 1/3 Ollama]

Windows vs Mac path separators and line endings perturb generated files and
break source-hash stability and stow.

Fix: normalize to POSIX separators + LF in the generator; golden-file
determinism test Mac vs Windows.

### Operational (toolchain)

- Gemini CLI lane is DEAD: `IneligibleTierError` — Google deprecated Code Assist
  for individuals; migrate to Antigravity. Use AGY/Antigravity as the
  Gemini-family lane and update `code-review/references/orchestration-dispatch.md`,
  which still marks gemini "verified 2026-06-14".
- OpenRouter lane failed on a local Python SSL CA (`CERTIFICATE_VERIFY_FAILED`),
  not on OpenRouter; use `curl` (system CAs) or `certifi` for that lane.

### Net

PT-MM1 and PT-MM2 are gating. The v2 release gate (Stage 4 verify) and the
v1-viability path (Stage 3 fallback) both rest on OpenClaw capabilities that are
asserted but unproven. Implementation MUST start with two spikes — (a) does the
gateway expose backend identity? (b) what is the real OpenAI-compatible provider
schema? — before `bind_codex_backend.sh` is written.

