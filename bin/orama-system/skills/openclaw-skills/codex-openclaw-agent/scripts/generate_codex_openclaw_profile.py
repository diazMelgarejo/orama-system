#!/usr/bin/env python3
"""Reconcile marker-owned Codex workspace defaults without overwriting operator text."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile


START = "<!-- oramaclaw:generated:start -->"
END = "<!-- oramaclaw:generated:end -->"
CANONICAL_WORKSPACE = Path.home() / ".openclaw" / "agents" / "codex-agent"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=CANONICAL_WORKSPACE)
    parser.add_argument("--effort", choices=("medium", "high", "xhigh"), default="medium")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def merge_generated_region(existing: str, heading: str, generated: str) -> str:
    block = f"{START}\n{generated.rstrip()}\n{END}\n"
    has_start = START in existing
    has_end = END in existing
    if has_start != has_end:
        raise ValueError("found an incomplete oramaclaw generated marker pair")
    if has_start:
        first = existing.index(START)
        last = existing.index(END, first) + len(END)
        if START in existing[first + len(START):last] or END in existing[last:] or START in existing[last:]:
            raise ValueError("found duplicate oramaclaw generated marker pairs")
        return existing[:first] + block + existing[last:].lstrip("\n")
    prefix = existing.rstrip()
    if not prefix:
        prefix = f"# {heading}"
    return f"{prefix}\n\n{block}"


def atomic_write_if_changed(path: Path, content: str, dry_run: bool) -> bool:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current == content:
        return False
    if dry_run:
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)
    return True


def ensure_scaffold(path: Path, content: str, dry_run: bool) -> bool:
    if path.exists():
        return False
    return atomic_write_if_changed(path, content, dry_run)


def main() -> None:
    args = parse_args()
    workspace = args.workspace.expanduser().resolve()
    agent_dir = workspace / "agent"
    workspace_ref = "~/.openclaw/agents/codex-agent" if workspace == CANONICAL_WORKSPACE else str(workspace)
    agent_dir_ref = f"{workspace_ref}/agent"

    if not args.dry_run:
        for directory in (workspace / "memory" / "archives", workspace / "refs", workspace / "scripts" / "lib"):
            directory.mkdir(parents=True, exist_ok=True)

    managed = {
        "CODEX.md": (
            "Codex Agent Profile",
            "\n".join(
                (
                    "agent_id: codex-agent",
                    f"workspace: {workspace_ref}",
                    f"agent_dir: {agent_dir_ref}",
                    "model: codex/gpt-5.5",
                    f"thinking_default: {args.effort}",
                    "tools_profile: coding",
                    "delegation_path: agents.defaults.subagents.allowAgents",
                    "auth_provider: openai-codex",
                    "auth_command: openclaw models auth login --provider openai-codex",
                )
            ),
        ),
        "IDENTITY.md": (
            "IDENTITY.md",
            "\n".join(
                (
                    "## Codex Identity",
                    "- Name: Codex Agent",
                    "- Role: dedicated OpenAI Codex execution sub-agent",
                    "- Model: `codex/gpt-5.5`",
                    f"- Thinking: `{args.effort}`",
                )
            ),
        ),
        "AGENTS.md": (
            "AGENTS.md",
            "\n".join(
                (
                    "## Codex Defaults",
                    "- Use `codex/gpt-5.5` with the configured thinking level and no implicit fallback.",
                    "- Start only through an explicit task or approved sub-agent delegation.",
                    "- Preserve the Main Agent, global defaults, `coder`, and gateway service settings unless explicitly directed.",
                    "- Keep credentials and raw authorization material out of workspace files and memory.",
                )
            ),
        ),
        "TOOLS.md": (
            "TOOLS.md",
            "\n".join(
                (
                    "## Codex Execution",
                    "- Use OpenClaw's `coding` tool profile.",
                    "- Use the managed `openai-codex` authentication flow; never copy credentials into this workspace.",
                    "- Treat remote writes, deployments, and public communication as approval-required operations.",
                )
            ),
        ),
    }

    changed: list[str] = []
    for relative, (heading, generated) in managed.items():
        path = workspace / relative
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        rendered = merge_generated_region(existing, heading, generated)
        if atomic_write_if_changed(path, rendered, args.dry_run):
            changed.append(relative)

    security = """# Security Contract\n\n- Use managed OpenClaw/Codex authentication only.\n- Never write API keys, OAuth tokens, bearer headers, cookies, or credential-store contents here.\n- Require explicit approval for external communication, remote writes, deployments, and credential changes.\n"""
    if ensure_scaffold(workspace / "SECURITY.md", security, args.dry_run):
        changed.append("SECURITY.md")

    print(json.dumps({
        "status": "dry-run" if args.dry_run else "ok",
        "workspace": str(workspace),
        "agent_dir": str(agent_dir),
        "changed": changed,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
