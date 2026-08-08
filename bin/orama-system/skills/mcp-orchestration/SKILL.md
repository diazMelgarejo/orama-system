---
name: mcp-orchestration
description: >-
  Use when setting up Claude Code MCP tools, adding Claude Skills, using Gemini as a
  large-context reader, dispatching parallel AI CLI agents, connecting MCP tools to
  OpenClaw, or routing tasks to local/OpenRouter/Codex/Gemini agents. Activates when
  the user mentions MCP JSON, SKILL.md, ai-cli-mcp, OpenClaw MCP, or tool setup failures.
version: 2.1.0
canonical_path: bin/orama-system/skills/mcp-orchestration/SKILL.md
compatibility: claude-code, cursor, codex, gemini, openclaw, hermes
allowed-tools: bash, file-operations, web-search
triggers:
  - mcp orchestration
  - claude mcp setup
  - ai-cli-mcp
  - gemini mcp tool
  - openclaw mcp
  - skill.md claude skills
  - parallel agent dispatch
supersedes:
  - OpenClaw/MCP_ORCHESTRATION_SKILL.md
  - OpenClaw/MCP_ORCHESTRATION_SKILL_v2.md
  - ~/.claude/skills/mcp-orchestration/SKILL.md
last_updated: 2026-07-22
---

# MCP Orchestration Skill (canonical)

## Purpose

Route MCP tools, Claude Skills, and parallel CLI agents to the cheapest layer that can succeed.

## When to Use

- Registering or debugging MCP servers in Claude Code, Codex, Gemini, or OpenClaw
- Choosing between Gemini large-context reads, ai-cli-mcp workers, or local ollama
- Encoding repeatable orchestration procedures as durable skills

> **Canonical location:** `bin/orama-system/skills/mcp-orchestration/SKILL.md` — other copies are redirect stubs.

## Load First

Install/setup detail (read on demand): [`references/install-baseline.md`](references/install-baseline.md), [`references/gemini-and-ai-cli-mcp-setup.md`](references/gemini-and-ai-cli-mcp-setup.md), [`references/custom-mcp-server-authoring.md`](references/custom-mcp-server-authoring.md), [`references/troubleshooting.md`](references/troubleshooting.md), [`references/legacy-file-disposition.md`](references/legacy-file-disposition.md), [`examples/good/parallel-dispatch.md`](examples/good/parallel-dispatch.md).

## Executive Rule

Use the right tool for the right layer. Use the cheapest agent that can succeed.

| Layer | Tool | Job |
| --- | --- | --- |
| Main reasoning + judgment | Claude Sonnet 4.6 medium + prompt caching | Decide, edit, review, synthesize, content insertion |
| **Default coding agent** | **`cline` CLI via `cline-pass/glm-5.2` (Cline Credits)** | **Agentic coding, refactoring, tool loops — 1M ctx, no rate limits** |
| Lightweight routing/triage | OpenRouter free-model stack (`openrouter/free` auto-router) | Quick replies, routing decisions, summarization — free but rate-limited (50 req/day) |
| Large-context reading, when explicitly requested | `gemini-mcp-tool` | Gemini-Analyzer use-cases only, architecture mapping, visual diff, screenshot comparison, multi-file audit |
| Parallel workers | `ai-cli-mcp` | Run background CLI agents (Codex, Gemini, ollama) with PID tracking |
| Local-only workloads | ollama (Mac, `localhost:11434`) | Lint, format, bash scripts, local validation — free + private |
| Runtime orchestration | OpenClaw | Route tools into agent workflows, gateway, auth |
| Repeatable procedure | Claude Skill | Encode durable operating knowledge (this file) |

> **ClinePass default for coding:** `cline-pass/glm-5.2` (1M ctx, tool loops). OpenRouter free only for lightweight triage. See [cline-openclaw-agent/SKILL.md](../cline-openclaw-agent/SKILL.md).

**Two routing rules below override the legacy "Gemini = default reader" pattern.** See §2.

---

## Hermes Operator Shell

Use [`../hermes-harness/SKILL.md`](../hermes-harness/SKILL.md) when Hermes is
the chat, CLI, cron, or workspace-state surface consuming canonical ECC/orama
skills. Hermes is a harness edge; keep durable behavior in skills and keep
OpenClaw operations on `openclaw-skills`.

## 1. MCP Fundamentals

MCP lets Claude and other agents call external tools through a standard tool protocol. Most local MCP tools here use `stdio` — the MCP client starts the tool as a local subprocess and talks to it over stdin/stdout.

Claude Desktop and many MCP clients:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "package-name"]
    }
  }
}
```

OpenClaw outbound MCP registry:

```json
{
  "mcp": {
    "servers": {
      "server-name": {
        "command": "npx",
        "args": ["-y", "package-name"]
      }
    }
  }
}
```

Claude Code verification: `/mcp` inside Claude Code, or `claude mcp list` from the CLI.

---

## 2. Routing strategy (READ FIRST)

### Rule 0 — Default coding: ClinePass (Cline Credits)

**For coding tasks (refactoring, file editing, agentic tool loops), use the
`cline` CLI via `cline-pass/glm-5.2` (Cline Credits) as the default.** This is
the preferred path over OpenRouter free because:

- **No rate limits** — OpenRouter free is limited to 50 req/day, 20 RPM
- **1M context** — full GLM-5.2 capability with reasoning + structured output
- **Dedicated billing** — Cline Credits are separate from OpenRouter credits
- **Full tool loops** — the `cline` CLI runs agentic coding with auto-approve

```bash
cline "<task>" --json --auto-approve true -c <dir> \
  --thinking medium -P cline-pass -m cline-pass/glm-5.2 \
  --timeout 600 --retries 3
```

From Claude: use the `cline_exec` MCP tool (defaults to `cline-pass/glm-5.2`).
See [cline-openclaw-agent/SKILL.md](../cline-openclaw-agent/SKILL.md).

### Rule 1 — Lightweight routing: OpenRouter free-model stack (fallback)

For lightweight routing/triage/quick replies that don't need tool loops, route
to OpenRouter free models in fallback order:

```text
1. openrouter/nvidia/nemotron-3-super-120b-a12b:free   (1M ctx, agent-strong)
2. openrouter/minimax/minimax-m2.5:free                (205K, 80.2% SWE-Bench)
3. openrouter/deepseek/deepseek-v4-flash:free          (1M, fast triage)
4. openrouter/openai/gpt-oss-120b:free                 (131K, tool-use)
5. openrouter/z-ai/glm-4.5-air:free                    (131K, agentic backup)
6. openrouter/inclusionai/ling-2.6-flash:free          (262K, lightweight)
7. openrouter/openrouter/free                          (auto-router, last resort)
```

For local-machine workloads where no network is needed, prefer `ollama qwen3.5` on Mac (`localhost:11434`) FIRST. Then fall through to OpenRouter.

See `docs/OPENROUTER_FREE_MODELS.md` for the full policy and `scripts/apply-openrouter-free-defaults.sh` for applying it to `openclaw.json` configs.

### Rule 2 — Gemini-Analyzer use-case routing (when specified)

**Gemini is NOT the default reader.** Gemini has unique strengths but also access constraints (GitHub auth issues, rate limits). Reserve it for explicitly-specified "Gemini-Analyzer use-cases":

| Use-case | Why Gemini |
| ---------- | ------------ |
| **Visual diff / screenshot comparison** | 2M-token vision context, sandbox testing |
| **Whole-repo architecture mapping** | Largest single-shot context window available |
| **Multi-file stale-doc detection** | Reads entire `docs/` + `src/` in one pass |
| **Second-opinion code review of >5000-line diffs** | Pro model handles size comfortably |

For ANY OTHER reading task (single file, narrow audit, dependency scan), route to OpenRouter Nemotron 3 Super (1M ctx, free) instead.

```text
# Default reader call (uses OpenRouter):
"Read @path/to/file and report X"

# Gemini-Analyzer call (explicit):
"GEMINI-ANALYZER: visual-diff between @screenshot.png and live dev server"
```

### Rule 3 — Claude Sonnet 4.6 medium for judgment + prompt caching

Reserve Claude Sonnet 4.6 (this session's main agent) for:

- Final judgment, taste calls, conflict resolution
- Reviewing worker outputs and detecting drift
- Content insertion decisions (CIDF gate)
- Writing commit messages, summaries, designs

**Prompt caching policy (Goal 2 from RC-1 plan):**

When using Claude Sonnet 4.6 via the Anthropic SDK:

- `model: claude-sonnet-4-6`
- `thinking.effort: medium`
- Set `cache_control` on **stable** system prompts, tool definitions, and context prefixes
- **Simplest option — automatic placement:** pass a single `cache_control` field at the **top level** of the `messages.create()` request and the SDK auto-places the breakpoint on the last cacheable block. Reach for explicit per-block `cache_control` only when you need fine-grained control over multiple breakpoints (max 4).
- Sonnet 4.6 minimum cacheable prompt: **1,024 tokens** (anything smaller is not cached)
- TTL: 5 minutes default (90 minutes with `ttl: "extended"`)
- **NEVER cache** changing suffixes — timestamps, per-run user payloads, request IDs, response IDs

Example (Python SDK):

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    thinking={"type": "enabled", "budget_tokens": 8000},
    system=[
        {
            "type": "text",
            "text": LARGE_STABLE_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},  # ← cache this
        }
    ],
    messages=[
        {"role": "user", "content": ephemeral_user_input}  # ← do NOT cache
    ],
)
```

Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-caching>

### Rule 4 — Use ai-cli-mcp as the parallel worker pool

Use ai-cli-mcp when tasks are independent (different files, different concerns), multiple models should inspect the same repo, you need background agents with PID tracking, or you want session reuse across subtasks. Do not let worker agents commit or deploy without explicit user confirmation. See `references/gemini-and-ai-cli-mcp-setup.md` for the core tool table and `examples/good/parallel-dispatch.md` for the golden-path pattern.

### Rule 5 — OpenClaw as the runtime router

OpenClaw routes tools into agent workflows, holds gateway/auth, registers outbound MCP servers, and keeps security/policy around agent execution.

---

## 6. OpenClaw Integration

### Two roles

| Role | Command | Meaning |
| --- | --- | --- |
| OpenClaw as MCP server | `openclaw mcp serve` | Claude or Codex talks to OpenClaw |
| OpenClaw as MCP client registry | `openclaw mcp set/list/show/unset` | OpenClaw stores outbound MCP servers |

### Add ai-cli-mcp + Gemini to OpenClaw outbound registry

```bash
openclaw mcp set ai-cli-mcp '{"command":"npx","args":["-y","ai-cli-mcp@latest"],"env":{"MCP_CLAUDE_DEBUG":"false"}}'
openclaw mcp set gemini-cli '{"command":"npx","args":["-y","gemini-mcp-tool"]}'
openclaw mcp list
```

### OpenClaw model policy (uses OpenRouter free-model stack per Rule 1)

The default OpenClaw model policy points at OpenRouter free fallbacks. Apply with:

```bash
scripts/apply-openrouter-free-defaults.sh --repo-only
scripts/apply-openrouter-free-defaults.sh --apply-live   # patches ~/.openclaw/openclaw.json
```

Full config shape lives in `deployments/macbook-pro-head/openclaw/openclaw.model-policy.jsonc`. See `docs/OPENROUTER_FREE_MODELS.md`.

### OpenClaw config shape (combined)

```json
{
  "env": {
    "OPENROUTER_API_KEY": "${OPENROUTER_API_KEY}"
  },
  "mcp": {
    "servers": {
      "ai-cli-mcp": {
        "command": "npx",
        "args": ["-y", "ai-cli-mcp@latest"],
        "env": { "MCP_CLAUDE_DEBUG": "false" }
      },
      "gemini-cli": {
        "command": "npx",
        "args": ["-y", "gemini-mcp-tool"]
      }
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
        "fallbacks": ["openrouter/minimax/minimax-m2.5:free", "openrouter/openrouter/free"]
      }
    }
  }
}
```

### Dispatch rule (embed in OpenClaw instructions)

```text
Use OpenRouter free-model stack as the default agent.
Use Gemini only for Gemini-Analyzer use-cases (visual diff, whole-repo, multi-file audits).
Use ai-cli-mcp for isolated parallel work.
Never write, delete, deploy, or commit unless the user explicitly confirms YES.
After workers finish, summarize by PID and cite each worker result.
```

---

## 7. Build a New Claude Skill

- Personal: `~/.claude/skills/<skill-name>/SKILL.md`
- Project: `.claude/skills/<skill-name>/SKILL.md`
- Repo-canonical (orama-system pattern): `bin/orama-system/<skill-name>/SKILL.md`

Minimal template:

```markdown
---
name: build-optimizer
description: Diagnoses and fixes build failures. Use when the user mentions ENOTEMPTY, npm install failures, package manager errors, macOS file locks, or failing builds.
---

# Build Optimizer

## Instructions

1. Identify the package manager.
2. Capture the exact error.
3. Check for file locks.
4. Remove only generated folders.
5. Reinstall dependencies.
6. Run the smallest proof test.

## Safety

Do not delete source files.
Ask before deleting unknown folders.
```

The `description` is the trigger surface — be specific.

Good: `description: Diagnoses MCP setup issues for Claude Code, Gemini MCP Tool, ai-cli-mcp, and OpenClaw. Use when MCP servers fail, tools do not appear in /mcp, JSON parse errors occur, or background agents hang.`

Bad: `description: Helps with MCP.`

For a custom MCP server when no existing tool covers the need, see `references/custom-mcp-server-authoring.md`.

---

## 9. Tool Search

Use tool search when many MCP servers or tools are configured:

```bash
ENABLE_TOOL_SEARCH=auto claude
ENABLE_TOOL_SEARCH=auto:5 claude
```

| Tool count | Setting |
| --- | --- |
| < 10 tools | default usually fine |
| Many tools | `ENABLE_TOOL_SEARCH=auto` |
| Proxy / custom backend | configure explicitly if supported |

---

## 11. learnings.md Pattern

Create `learnings.md` next to this SKILL.md (skill-local, distinct from the
repo-wide `docs/LESSONS.md`) for fixes specific to this skill's domain.
Append:

```markdown
## YYYY-MM-DD: Short title

Problem:
Cause:
Fix:
Verification:
Promote to skill:
- no
```

Promotion rule:

| Repetitions | Action |
| --- | --- |
| 1 | Store in `learnings.md` |
| 2–3 | Add checklist item |
| 4+ | Promote into `SKILL.md` |

---

## 12. Verification Checklist

```bash
node -v
npm -v
claude doctor
claude mcp list
gemini --version
ai-cli doctor
ai-cli models
ollama list
openclaw mcp list
```

Inside Claude Code: `/mcp`

Pass criteria:

- `gemini-cli` appears (if installed) — used for Gemini-Analyzer use-cases only
- `ai-cli-mcp` appears and is active
- ollama `qwen3.5:9b-nvfp4` listed (Mac default)
- Claude CLI first-run prompt has been accepted
- ai-cli doctor detects installed CLIs
- OpenClaw lists outbound MCP servers
- `OPENROUTER_API_KEY` is set in env
- No secrets appear in logs

---

## 13. Agent Instruction Block

Use this in `CLAUDE.md`, OpenClaw instructions, or project agent docs:

```markdown
# MCP Orchestration Policy

1. Default to OpenRouter free-model stack (Nemotron → MiniMax → DeepSeek → …) for generic worker calls.
2. Use ollama (local Mac) FIRST when no network/API is required (lint, format, bash scripts).
3. Use Gemini ONLY for Gemini-Analyzer use-cases: visual diff, whole-repo architecture, multi-file stale-doc detection, large-diff code review.
4. Use Claude Sonnet 4.6 medium + prompt caching for judgment, final synthesis, taste calls, content insertion.
5. Use ai-cli-mcp only for isolated parallel work with PID tracking.
6. Use absolute workFolder paths.
7. Never let worker agents commit, deploy, delete, or change account settings without explicit confirmation.
8. Verify every MCP server with `/mcp` or matching CLI status commands.
9. Keep MCP configs minimal.
10. Prefer allowlisted tools over broad permission bypass.
11. Record repeated fixes into learnings.md.
12. Promote repeated fixes into SKILL.md only after recurrence.
```

---

## 14. Decision Table

| Need | Use |
| --- | --- |
| One-time direct task | Claude Code (this session) |
| Generic worker reading or coding | OpenRouter Nemotron / MiniMax (per fallback chain) |
| Local-only lint, format, bash | ollama qwen3.5 (Mac) |
| Visual diff / screenshot comparison | Gemini Pro (Gemini-Analyzer) |
| Whole-repo architecture review | Gemini Pro (Gemini-Analyzer) |
| Multi-file stale-doc detection | Gemini Pro (Gemini-Analyzer) |
| Mechanical search-replace across many files | Codex CLI via ai-cli-mcp |
| Multiple independent worker tasks in parallel | ai-cli-mcp dispatch |
| Messaging or channel-based routing | OpenClaw |
| Judgment / content insertion / final synthesis | Claude Sonnet 4.6 + prompt cache |
| Repeated procedure to encode | Claude Skill |
| Missing capability | Custom MCP server (`references/custom-mcp-server-authoring.md`) |

---

## Final Rule

MCP is a tool layer. Do not turn every workflow into an MCP problem.

For one-time tasks, act directly.
For repeated tasks, create a skill.
For external capabilities, add an MCP server.
For parallel work, use ai-cli-mcp.
For Gemini-Analyzer use-cases (visual, large-context), use Gemini.
For everything else, use OpenRouter free models or local ollama.
For judgment, use Claude Sonnet 4.6 medium with prompt caching.

**Applied pattern — multi-channel steelman:** for a small but high-stakes change, fan the design out to a heterogeneous model panel (verify reachability first) for adversarial review. Recipe: [`docs/reference/multi-channel-steelman.md`](../../../../docs/reference/multi-channel-steelman.md).

---

Legacy file disposition (redirect stubs, superseded paths): [`references/legacy-file-disposition.md`](references/legacy-file-disposition.md)

## D14 Mirror Enforcement

Before dispatching a worker, verify the backend does not route a `windows_only` spec to `lmstudio-mac`. `resolve_backend_for_spec` in `orchestrator/backend_resolver.py` raises `PolicyUnavailable` on this. NEVER catch and silently fall back — fail closed.

Extended setup and review doctrine: [`references/interactive-provider-setup.md`](../../references/interactive-provider-setup.md), [`references/post-review-micro-remediation.md`](../../references/post-review-micro-remediation.md).

## Boundaries

### Always Do

- Use the cheapest agent that can succeed; escalate layer only when needed.
- Keep durable behavior in skills; use MCP for external capabilities.
- Verify D14 mirror routing before dispatching tier-specific workers.

### Ask First

- Adding a new default coding agent or changing OpenRouter/Cline routing policy.
- Authoring a custom MCP server when an existing tool already covers the need.

### Never Do

- Turn every one-time task into a new MCP server or skill.
- Use Gemini as the default reader when OpenRouter free or local ollama suffices.
- Silently catch `PolicyUnavailable` or cross-tier mirror routing failures.
