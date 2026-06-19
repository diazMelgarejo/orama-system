#!/usr/bin/env python3
"""
generate_codex_openclaw_profile.py

Reads the resolved binding result from bind_codex_backend.sh and writes:
  - CODEX.md        -- spec sheet recording the binding (not an OpenClaw directive)
  - agents/codex-agent/AGENTS.md  -- OpenClaw directive: sub-agent wiring
  - agents/codex-agent/TOOLS.md   -- OpenClaw directive: tool profile

Auth is NEVER written into generated files. Only path references.

Usage:
    python3 generate_codex_openclaw_profile.py [--binding-path primary|idempotent-install|fallback]
                                               [--effort medium|high]
                                               [--openclaw-home PATH]
                                               [--dry-run]
"""

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import sys

GENERATOR_VERSION = "1.0.0"


def sha256_of_file(path: pathlib.Path) -> str:
    if not path.exists():
        return "NOT_FOUND"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--binding-path", default="primary",
                   choices=["primary", "idempotent-install", "fallback", "dry-run-primary"])
    p.add_argument("--effort", default="high", choices=["medium", "high"])
    p.add_argument("--openclaw-home", default=str(pathlib.Path.home()))
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def write_or_preview(path: pathlib.Path, content: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] would write {path} ({len(content)} chars)")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"wrote: {path}")


def main() -> None:
    args = parse_args()

    openclaw_home = pathlib.Path(args.openclaw_home)
    oc_json = openclaw_home / ".openclaw" / "openclaw.json"
    codex_config = pathlib.Path.home() / ".codex" / "config.toml"

    # Source hashes for integrity, not provenance
    oc_json_hash = sha256_of_file(oc_json)
    codex_cfg_hash = sha256_of_file(codex_config)
    skill_hash = sha256_of_file(
        pathlib.Path(__file__).parent.parent / "SKILL.md"
    )

    ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

    # ── CODEX.md (spec sheet, not an OpenClaw directive) ─────────────────────
    codex_md = f"""\
<!-- source-hash: skill={skill_hash} openclaw.json={oc_json_hash} codex-config={codex_cfg_hash} -->
<!-- generated: {ts} generator-version: {GENERATOR_VERSION} -->

# CODEX — Codex/GPT-5.5 Binding Spec Sheet

> This file is a **generated spec sheet**, not one of OpenClaw's six native
> directive files (SOUL / IDENTITY / USER / AGENTS / TOOLS / SECURITY).
> The real directives live in `agents/codex-agent/`.

## Resolved binding

| Field | Value |
|---|---|
| Binding path | `{args.binding_path}` |
| Provider string | `codex/gpt-5.5` |
| Model | `gpt-5.5` |
| Reasoning effort | `{args.effort}` |
| Auth source | `~/.codex/config.toml` (by path reference only) |
| Endpoint | `http://127.0.0.1:61234/v1` |
| Generated | `{ts}` |
| Generator version | `{GENERATOR_VERSION}` |

## Binding path rationale

| Path | Condition |
|---|---|
| `primary` | `openclaw-codex-app-server` plugin present AND app-server health ping OK |
| `idempotent-install` | Plugin was absent, installed successfully, then primary succeeded |
| `fallback` | Plugin unavailable or install failed; codex app-server registered as openai-completions provider directly |

Winning path: **`{args.binding_path}`**

## Preserved routing invariants (verified after binding)

```
agents.defaults.model.primary  →  ollama/qwen3.5:9b-nvfp4      (unchanged)
agents.list[main].model.primary  →  lmstudio-mac/qwen3.5-9b-mlx (unchanged)
agents.list[coder].model.primary →  lmstudio-win/qwen3.5-27b-... (unchanged)
LaunchAgent plist                →  not touched
```

## Verify result

Run `openclaw run codex-agent --task "reply with exactly: CODEX_BACKEND_OK"`
to confirm live backend identity. The binding script asserts this before
declaring success.

## Source integrity

| File | SHA-256 (first 16 chars) |
|---|---|
| `SKILL.md` | `{skill_hash}` |
| `openclaw.json` | `{oc_json_hash}` |
| `~/.codex/config.toml` | `{codex_cfg_hash}` |

## Regeneration

```bash
python3 bin/orama-system/skills/codex-openclaw-agent/scripts/generate_codex_openclaw_profile.py \\
    --binding-path {args.binding_path} \\
    --effort {args.effort}
```

Add `--dry-run` to preview without writing.
"""

    # ── agents/codex-agent/AGENTS.md (OpenClaw directive) ────────────────────
    agents_md = f"""\
# AGENTS

<!-- source-hash: {skill_hash} generated: {ts} -->

## Agent identity

- Agent ID: `codex-agent`
- Role: OpenAI Codex CLI sub-agent, GPT-5.5 backend
- Spawn modes: `sub-agent` (default) | `standalone` (explicit only)

## Spawn modes

### sub-agent (default)
Invoked by the `main` agent or an operator via:
```bash
openclaw run codex-agent --task "..."
```
The `main` agent has `codex-agent` in its `allowAgents` binding.

### standalone
```bash
openclaw run codex-agent --standalone --task "..."
```
Use for isolated Codex-native tasks that should not share context with
the main agent session.

### ask mode (default for new tasks)
The agent asks for operator confirmation before executing file edits,
running commands, or making commits.

## Parent binding

```json
"agents.bindings.main.allowAgents": ["codex-agent"]
```

This is the ONLY agent allowed to call `codex-agent` automatically.
All other calls require explicit `openclaw run codex-agent`.

## What this agent does

- Executes coding tasks via OpenAI Codex CLI (GPT-5.5).
- Reads and edits files in the active workspace.
- Runs tests and build commands (with approval).
- Returns structured results to the parent agent or operator.

## What this agent does NOT do

- It is not the default coding backend (that is `lmstudio-win/coder`).
- It does not inherit the Ollama orchestrator's model or session.
- It does not route tasks through the LaunchAgent default path.

## Interaction surfaces

| Surface | Command |
|---|---|
| CLI | `openclaw run codex-agent --task "..."` |
| Telegram | `/agent codex-agent <task>` (owner-only) |
| WhatsApp | Same command pattern (owner-only) |
| Sub-agent call from `main` | Automatic via allowAgents binding |
"""

    # ── agents/codex-agent/TOOLS.md (OpenClaw directive) ─────────────────────
    tools_md = f"""\
# TOOLS

<!-- source-hash: {skill_hash} generated: {ts} -->

## Tool profile: `coding`

Inherits the `coding` tool profile, which enables:

| Tool | Enabled | Notes |
|---|---|---|
| File read | ✅ | All files in workspace |
| File edit | ✅ | Requires approval by default |
| Bash execution | ✅ | Requires approval; sandboxed |
| Git operations | ✅ | Requires approval for commits |
| Web search | ❌ | Use `main` agent's web search tools |
| Memory write | ✅ | Session memory only |

## Codex-specific tools

These are loaded by the Codex CLI runtime, not by OpenClaw directly:

| Tool | Notes |
|---|---|
| `codex:file_read` | Codex-native file reading |
| `codex:file_edit` | Codex-native diff-based editing |
| `codex:run_command` | Shell execution inside Codex sandbox |
| `codex:search` | Codebase search (no web) |

## Disabled by policy

- `ollama_web_search` — not available to this agent
- `ollama_web_fetch` — not available to this agent
- Any tool that would change the default model routing

## MCP servers

Inherits the MCP servers registered in `mac-orchestrator.json`:
- `ai-cli-mcp` — available
- `gemini-cli` — available (for research sub-tasks only)
"""

    # ── Write files ──────────────────────────────────────────────────────────
    write_or_preview(pathlib.Path("CODEX.md"), codex_md, args.dry_run)
    write_or_preview(pathlib.Path("agents/codex-agent/AGENTS.md"), agents_md, args.dry_run)
    write_or_preview(pathlib.Path("agents/codex-agent/TOOLS.md"), tools_md, args.dry_run)

    result = {
        "status": "ok" if not args.dry_run else "dry-run",
        "files_written": ["CODEX.md", "agents/codex-agent/AGENTS.md", "agents/codex-agent/TOOLS.md"],
        "source_hashes": {
            "skill_md": skill_hash,
            "openclaw_json": oc_json_hash,
            "codex_config": codex_cfg_hash,
        },
        "generated_at": ts,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
