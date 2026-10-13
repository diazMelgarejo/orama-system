---
name: cursor-agent
description: >-
  Install, configure, and operate the Cursor Agent CLI (`cursor-agent`) for
  fanning out light tasks in parallel. Default launch is grok-4.6 at medium
  effort with fast off. Auto is editor-only. Never launch grok-4.5.
  Cross-platform: macOS/Linux via bash installer, Windows via PowerShell.
  DO NOT confuse with `agent` (Grok Build TUI at ~/.grok/bin/agent) — different tool.
version: 1.2.0
license: Apache 2.0
compatibility: darwin, linux, windows, orama-system, openclaw, hermes-harness
parent_skill: orama-system
triggers:
  - cursor agent
  - cursor-agent
  - fan out tasks
  - cursor cli
  - cursor background agent
allowed-tools: bash, file-operations
---

# Cursor Agent Skill

## Disambiguation

**`cursor-agent`** (`~/.local/bin/cursor-agent`) is Cursor's native background agent CLI.
It is **NOT** the same as `agent` (`~/.grok/bin/agent`, the Grok Build TUI).
Always invoke Cursor agents as `cursor-agent`, never as bare `agent`.

| Command | Binary | What it is |
|---------|--------|------------|
| `cursor-agent` | `~/.local/bin/cursor-agent` | Cursor's background agent — use this |
| `agent` | `~/.grok/bin/agent` | Grok Build TUI — separate product |

## Install

### macOS / Linux

```bash
# Private mode-700 temp dir — see shell-hygiene §7 and integrative-editing-examples §3.
install_dir="$(mktemp -d -t cursor-install.XXXXXX)"
chmod 700 "$install_dir"
install_script="${install_dir}/install.sh"
trap 'rm -rf "$install_dir"' EXIT
curl https://cursor.com/install -fsS -o "$install_script" && bash "$install_script"
# Installs to ~/.local/bin/cursor-agent; adds ~/.local/bin to PATH
```

Verify:

```bash
cursor-agent --version    # e.g. 2026.06.24-00-45-58-9f61de7
cursor-agent models       # list available models
```

### Windows (PowerShell 5+)

```powershell
iwr -UseBasicParsing https://cursor.com/install.ps1 | iex
# Installs to %LOCALAPPDATA%\cursor-agent\ (versioned shims under versions\)
```

Canonical paths (cross-platform):

| OS | `cursor-agent` binary | Permanent PATH entry |
|----|----------------------|----------------------|
| macOS / Linux | `~/.local/bin/cursor-agent` | `~/.local/bin` |
| Windows | `%LOCALAPPDATA%\cursor-agent\cursor-agent.cmd` | `%LOCALAPPDATA%\cursor-agent` |

Idempotent PATH bootstrap (orama-system repo root):

```powershell
.\platform\windows\ensure-partner-cli-paths.ps1
```

Verify (PowerShell):

```powershell
cursor-agent --version
cursor-agent models
```

### Authentication

```bash
cursor-agent login          # browser OAuth flow; tokens stored in OS keychain
cursor-agent status         # verify login, show account info
```

Set API key via env var instead of browser flow:

```bash
export CURSOR_API_KEY="sk-..."   # never commit; load from macOS Keychain or .env
cursor-agent models              # confirms key is accepted
```

## Available Models

Canonical rules: [Alexandria model-governance](https://github.com/oramasys/alexandria/blob/docs/mig-pack-ingest-20260925/docs/standards/model-governance.md)
and `docs/standards/model-governance.md`. Always set effort and fast explicitly.

| Model string | Display name | When to use |
|---|---|---|
| `grok-4.6` | Grok 4.6 | **Default for agents.** Launch `{effort: medium, fast: false}` (usage `cursor-grok-4.6-medium`) |
| `composer-2.5` | Composer 2.5 | Allowed alternative. Launch `{fast: false}`. Fast on only if the operator asks. |
| `grok-4.7` | Grok 4.7 | Escalation token required; still `{reasoning_effort: medium, fast: false}` |
| `claude-sonnet-5-5` | Sonnet 5.5 | Anthropic-path default inside Cursor: `{reasoning_effort: medium}` |
| `claude-opus-5-5` | Opus 5.5 | Escalation token required; `{effort: high, fast: false}` |
| `claude-fable-5-1` | Fable 5.1 | Escalation token **and** hard budget cap |

`auto` / `default` is **editor-only**. Never launch it for agent work (it can
route to gated Claude models with the choice hidden). `grok-4.5` is **banned**.

Parameterised model override syntax (bracket notation):

```bash
cursor-agent --model 'grok-4.6[effort=medium,fast=false]' ...
cursor-agent --model 'composer-2.5[fast=false]' ...
```

## Model Selection Policy

| Tier | Model | When |
|------|-------|------|
| 1 — Default | `grok-4.6` medium, fast off | All agent and coding fan-out unless the operator names another allowed model |
| 2 — Allowed | `composer-2.5` fast off | Explicit operator pick, or grok-4.6 unavailable |
| 3 — Gated | `grok-4.7`, Opus 5.5, Fable 5.1 | Only with an escalation token (S-AuthZ bearer + fresh signed HITL, ≤24h). Config/env/cache is not a token. |

Never use `auto` as a fallback. Never default to Opus, Fable, or grok-4.5.

## Key Options (from `cursor-agent --help`)

| Option | Purpose |
|--------|---------|
| `--print` / `-p` | Headless single-turn — prints result to stdout (all tools: write, shell) |
| `--model <id>` | Override model |
| `--output-format <fmt>` | `text` \| `json` \| `stream-json` (with `--print`) |
| `--mode plan` | Read-only planning mode (no file edits) |
| `--mode ask` | Q&A explanations, read-only |
| `--auto-review` | Smart Auto: auto-run safe tool calls, prompt on risky ones |
| `--force` / `--yolo` | Auto-approve all tool calls (trusted CI only) |
| `--worktree [-w] [name]` | Isolated git worktree at `~/.cursor/worktrees/<repo>/<name>` |
| `--worktree-base <ref>` | Branch/ref to base new worktree on |
| `--trust` | Trust workspace without prompting (headless mode only) |
| `--sandbox enabled\|disabled` | Override sandbox mode |
| `--resume [chatId]` | Resume a previous session |
| `--continue` | Continue most recent session |

## Light Task Fanout Pattern

**Grok 4.6 medium / fast off** is the default for parallelising light work.
`composer-2.5` with fast off is the allowed alternative. Never fall back to `auto`.

```bash
# Parallel single-turn jobs (background) -- write to a repo-relative
# artifact dir, not /tmp: Fan-out Safety § 2 below only permits verifying
# repository-relative paths.
mkdir -p .cursor-agent-artifacts
cursor-agent --print --model 'grok-4.6[effort=medium,fast=false]' \
  "Add type annotations to scripts/discover.py; only functions, no variables" \
  --output-format json > .cursor-agent-artifacts/task-a.json &

cursor-agent --print --model gpt-5.3-codex-low \
  "Rename all snake_case variables in tests/test_foo.py to camelCase" \
  --output-format json > .cursor-agent-artifacts/task-b.json &

wait   # collect when done
```

**Division of labour:**

| Main session (harness default; Cursor = grok-4.6 medium / fast off) | cursor-agent (same default) |
|----------------------------------------------|-------------------------------------|
| Architecture decisions | Mechanical file edits |
| CIDF write discipline | Grep-and-replace tasks |
| Cross-repo synthesis | Doc generation |
| Security & policy review | Test scaffolding |
| Final crystallisation | Format / lint fixes |
| AFRP gate | Single-file refactors |

**Budget note:** `cursor-agent` consumes Cursor credits (not Anthropic API tokens).
Light tasks = `--model 'grok-4.6[effort=medium,fast=false]'` (default) or `--model 'composer-2.5[fast=false]'`. Never `--model auto`.

## Fan-out Safety

Three practices proven across a multi-day cross-repo session running many
concurrent cursor-agent/codex/Cline dispatches — apply all three whenever
`wait`-collecting parallel jobs, not just when something visibly goes wrong:

1. **File-disjoint clustering.** Before fanning out, partition tasks so no
   two concurrent jobs write the same file or overlapping region of the
   same file. Two agents editing the same file concurrently is not a "merge
   it later" problem — it silently produces whichever write lands last, with
   no conflict marker and no error, and the loser's fix simply disappears.
   If two tasks genuinely must touch the same file, run them sequentially
   (pipeline, not parallel) instead of trusting a post-hoc merge.
2. **Verify self-reports, don't trust them.** A cursor-agent job's own
   `--output-format json` summary ("done", "3 tests added", "fixed") is a
   claim, not a result. After `wait`, re-check the actual artifact directly
   — but only from **repository-owned, repository-relative** paths. Reject
   absolute paths and any path containing `..`. `git ls-files
   --error-unmatch` alone is not sufficient — it accepts tracked symlinks
   that resolve outside the repo. Canonicalize each claimed path
   (`realpath`) and require the resolved path to remain under
   `$REPO_ROOT` before treating it as verified, in addition to checking it
   with `git ls-files --error-unmatch -- <path>` (or confining reads to an
   explicitly approved output directory under the repo) before `cat`,
   `git diff`, or re-running tests on it. This mirrors the session-wide
   discipline of verifying claims over labels (`lesson_70713965dc1b` in
   Perpetua-Tools `.agent/memory` — originally about a merge tool's
   "clean" label, the same principle applies to any subagent's own
   completion report).
3. **Concurrent-job-race awareness.** Two cursor-agent (or cursor-agent +
   Cline/codex) jobs dispatched in the same fan-out round can both open a
   PR, both edit the same lesson/config file, or both act on the same
   GitHub issue within the same minute — seen repeatedly this session as
   PR sprawl (a stacked PR merged by one run while another run opened a
   duplicate against `main` for the identical fix). Before merging or
   closing anything a fan-out job produced: `git fetch --prune`, then
   `gh pr list --state all` (open alone misses siblings that already
   merged or closed), and compare changed files + commits against every
   sibling. Overlap is **blocking** — stop the merge/close and reconcile
   through the merge protocol below; don't assume the dispatch list from
   when you kicked off the round is still accurate.

See [`../git-history-surgery/SKILL.md` § Multi-Agent Branch Merge](../git-history-surgery/SKILL.md)
for the full simulate-before-touching protocol once two fanned-out branches
need reconciling, and Perpetua-Tools `perpetua-memory` skill § Concurrent-agent
collisions for the memory-file-specific version of practice 3.

## Worktree Isolation

For tasks that write files and must not collide with the main session:

```bash
cursor-agent -w cursor-fix-$(date +%s) \
  --print --model 'grok-4.6[effort=medium,fast=false]' \
  "Refactor scripts/foo.py to add structured logging"
# Runs in ~/.cursor/worktrees/<repo>/cursor-fix-<ts>/
# Review and merge back with git after the agent completes
```

## orama-system Stage 4 Integration

In Stage 4 (Masterful Execution), dispatch mechanical subtasks as cursor-agent
headless jobs while the main session handles judgment work:

```bash
# Example Stage 4 parallel dispatch -- repo-relative artifact dir, see § Fan-out Safety
mkdir -p .cursor-agent-artifacts
_JOBS=()

cursor-agent --print --model 'grok-4.6[effort=medium,fast=false]' \
  "Scan bin/ for TODO comments; output as JSON list" \
  --output-format json > .cursor-agent-artifacts/todos.json &
_JOBS+=($!)

cursor-agent --print --model gpt-5.3-codex-low \
  "Generate pytest stubs for every function in scripts/new_module.py" \
  --trust > .cursor-agent-artifacts/test-stubs.py &
_JOBS+=($!)

# Main session does judgment work here ...

wait "${_JOBS[@]}"
```

## MCP Integration

Cursor agents inherit the MCP servers configured in the workspace `.cursor/mcp.json`.
**CRG (`code-review-graph`) endpoint is platform-specific** — macOS/Linux use Ollama
`:11434`; Windows uses LM Studio `:1234`. See
[`../code-review/references/crg-platform-endpoints.md`](../code-review/references/crg-platform-endpoints.md).
On Windows after ECC install, run `bash bin/orama-system/scripts/sync-cursor-mcp.sh`.

Manage MCP servers:

```bash
cursor-agent mcp list
# Register via MCP UI: command npx, args ["-y", "ai-cli-mcp@<PINNED_VERSION>"]
# Never bare @latest — registry contents can change between installs (rug-pull).
# Pin after explicit review; bump deliberately (see firecrawl-cli pin pattern).
```

Approve all MCPs automatically in headless mode:

```bash
cursor-agent --print --approve-mcps --model 'grok-4.6[effort=medium,fast=false]' "..."
```

## Windows / Hermes Harness

On Windows, invoke from PowerShell or Git Bash:

```powershell
cursor-agent --print --model 'grok-4.6[effort=medium,fast=false]' "task here" --trust
```

From a Hermes-scripted workflow:

```bash
# In Git Bash on Windows
cursor-agent --print --model gpt-5.3-codex-low \
  "List all .py files modified in the last 24h" --output-format json
```

## Update

```bash
cursor-agent update      # update to latest version
cursor-agent about       # show version + system info
```

## Commands Summary

| Command | Purpose |
|---------|---------|
| `cursor-agent login` | Authenticate via browser OAuth |
| `cursor-agent logout` | Sign out and clear stored auth |
| `cursor-agent status` | Show auth status and account |
| `cursor-agent models` | List available models |
| `cursor-agent mcp` | Manage MCP servers |
| `cursor-agent worker` | Start private cloud worker |
| `cursor-agent update` | Update to latest version |
| `cursor-agent about` | Version + system info |
| `cursor-agent ls` | Resume a chat session |
| `cursor-agent resume` | Resume latest chat session |

## PR body updates (Cloud agents)

When a Cloud agent updates an **existing** PR after harmonization, review fixes, or CI notes:

1. **Default:** `post_comment` / `gh pr comment` only (Layer 0).
2. **Body append:** only after the **operator** minted `operator-grant-v2` (HMAC + digest bind)
   via `grant-pr-body-human-override.sh` in an operator terminal.
3. Run **only** `append-pr-body.sh` with the same `--file` or `--message` as the grant.

Load: [`../cursor-pr-body/SKILL.md`](../cursor-pr-body/SKILL.md)  
Rules: `.cursor/rules/pr-body-comment-only.mdc`, `.cursor/rules/append-only-pr-body.mdc`  
Scripts: `scripts/cursor/grant-pr-body-human-override.sh`, `scripts/cursor/append-pr-body.sh`

## References

- Platform affinity (when to use cursor-agent vs Hermes vs OpenClaw): [`../hermes-harness/references/platform-affinity-routing.md`](../hermes-harness/references/platform-affinity-routing.md)
- orama-system Stage 4: [`../../../SKILL.md § MODE 2 Stage 4`](../../../SKILL.md)
- Win PATH bootstrap: [`../hermes-harness/SKILL.md § Windows Bring-Up`](../hermes-harness/SKILL.md)
- [`../git-history-surgery/SKILL.md`](../git-history-surgery/SKILL.md) § Multi-Agent Branch Merge —
  reconciliation protocol once fanned-out branches need merging; § Decision Flow,
  item 13 — patch-equivalence rebase recovery for a stacked fan-out family


## Optional: Interactive Provider Setup

Idempotent, opt-in onboarding for provider selection (Claude, Codex,
Antigravity/Gemini, Cline, BigModel, Perplexity API) — same pattern vanilla
OpenClaw/Hermes onboarding uses.

- **Agent-mediated run:** use `AskUserQuestion` to pick a primary provider;
  already-configured providers are auto-added as fallback.
- **Human terminal:** `bash bin/orama-system/scripts/interactive-provider-setup.sh`
  (60s opt-in prompt, `[ -t 0 ]`-gated).
- **Non-interactive (CI/subagent):** skipped automatically; unset providers
  get `null` placeholders, never a blocking prompt.

Full doctrine: [`references/interactive-provider-setup.md`](../../references/interactive-provider-setup.md)
