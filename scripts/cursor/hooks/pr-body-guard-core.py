#!/usr/bin/env python3
"""Central PR-body guard decisions for Cursor hooks (Layer 0 + fallback layers).

Layer 0 (default): Cursor agents NEVER mutate an existing PR description.
                  Use ManagePullRequest post_comment or gh pr comment only.

Human override: operator creates ~/.cursor/pr-body-human-override-ack and sets
CURSOR_PR_BODY_HUMAN_OVERRIDE_ACK=1, then append-only rules (Layers 1–6) apply.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

DENY_LAYER0_AGENT = (
    "LAYER-0 BLOCK: Cursor agents must NOT change PR descriptions automatically. "
    "Use ManagePullRequest post_comment or `gh pr comment` only. "
    "Never ManagePullRequest update_pr with body=, gh pr edit, or append-pr-body.sh "
    "unless the human explicitly authorized a body edit — then "
    "follow append-only rules in bin/orama-system/skills/cursor-pr-body/SKILL.md."
)

DENY_APPEND_ONLY = (
    "APPEND-ONLY BLOCK: PR body writes require READ→BACKUP→MERGE→WRITE. "
    "Use scripts/cursor/append-pr-body.sh with a full integrative merged body, "
    "never delta-only update_pr body=."
)

def _human_override_active() -> bool:
    if os.environ.get("CURSOR_PR_BODY_HUMAN_OVERRIDE_ACK") != "1":
        return False
    ack_home = Path.home() / ".cursor" / "pr-body-human-override-ack"
    ack_repo: Path | None = None
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        if top:
            ack_repo = Path(top) / ".git" / "pr-body-backups" / ".human-override-ack"
    except (OSError, subprocess.CalledProcessError):
        ack_repo = None
    return ack_home.is_file() or (ack_repo is not None and ack_repo.is_file())


def _normalize_github_repo_slug(remote: str) -> str:
    repo = re.sub(
        r"^(?:https?://github\.com/|git@github\.com:|ssh://git@github\.com/)",
        "",
        remote.strip(),
    )
    if repo.endswith(".git"):
        repo = repo[:-4]
    return repo.strip("/")


def _parse_input(raw: str) -> dict[str, Any]:
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _tool_input(data: dict[str, Any]) -> dict[str, Any]:
    tool_input = (
        data.get("tool_input")
        or data.get("arguments")
        or data.get("input")
        or {}
    )
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except json.JSONDecodeError:
            tool_input = {}
    return tool_input if isinstance(tool_input, dict) else {}


def _manage_pr_decision(data: dict[str, Any]) -> tuple[str, str | None]:
    tool = str(data.get("tool_name") or data.get("toolName") or "")
    if "managepullrequest" not in tool.lower() and tool != "ManagePullRequest":
        return "ALLOW", None

    ti = _tool_input(data)
    action = str(ti.get("action") or "")

    if action == "post_comment":
        return "ALLOW", None

    if action == "update_pr" and "body" in ti:
        if not _human_override_active():
            return "DENY", DENY_LAYER0_AGENT
        return "ALLOW", None

    if action == "create_pr" and ti.get("body") and ti.get("draft") is not False:
        # Initial PR creation may include body; existing-PR updates are the pain point.
        return "ALLOW", None

    return "ALLOW", None


def _shell_decision(command_line: str) -> tuple[str, str | None]:
    cmd = command_line.strip()
    if not cmd:
        return "ALLOW", None

    # Comments always OK.
    if re.search(r"\bgh\s+pr\s+comment\b", cmd):
        return "ALLOW", None

    if "append-pr-body.sh" in cmd:
        if not _human_override_active():
            return "DENY", DENY_LAYER0_AGENT
        return "ALLOW", None

    if re.search(r"\bgh\s+pr\s+edit\b", cmd):
        if re.search(r"--body\b", cmd) and "--body-file" not in cmd:
            return "DENY", DENY_APPEND_ONLY
        if "--body-file" in cmd and not _human_override_active():
            return "DENY", DENY_LAYER0_AGENT
        if "--body-file" in cmd:
            return "ALLOW", None
        return "ALLOW", None

    if re.search(r"\bgh\s+api\b", cmd):
        lowered = cmd.lower()
        is_pr_mutation = any(
            token in lowered
            for token in (
                "pulls",
                "updatepullrequest",
                "pullrequestid",
                "pullrequest",
            )
        )
        if is_pr_mutation and ("body" in lowered or "description" in lowered):
            if not _human_override_active():
                return "DENY", DENY_LAYER0_AGENT
            return "ALLOW", None

    return "ALLOW", None


def backup_target(data: dict[str, Any]) -> tuple[str, str] | None:
    ti = _tool_input(data)
    remote = str(ti.get("remote_url") or ti.get("remoteUrl") or "")
    pr_number = ti.get("pr_number") or ti.get("prNumber")
    if remote and pr_number and str(pr_number).isdigit():
        repo = _normalize_github_repo_slug(remote)
        if repo:
            return repo, str(pr_number)
    return None


def shell_backup_target(command_line: str) -> tuple[str, str] | None:
    cmd = command_line
    repo = ""
    pr = ""
    m = re.search(r"--repo\s+([^\s]+)", cmd)
    if m:
        repo = _normalize_github_repo_slug(m.group(1))
    m = re.search(r"gh\s+pr\s+view\s+([0-9]+)", cmd)
    if m:
        pr = m.group(1)
    if not repo:
        m = re.search(r"github\.com/([^/\s]+/[^/\s]+)", cmd)
        if m:
            repo = _normalize_github_repo_slug(m.group(1))
    if repo and pr:
        return repo, pr
    return None


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "manage_pr"
    raw = sys.stdin.read()
    data = _parse_input(raw)

    if mode == "shell":
        command_line = str(data.get("command") or data.get("cmd") or "")
        decision, msg = _shell_decision(command_line)
        if decision == "ALLOW" and re.search(r"\bgh\s+pr\s+view\b", command_line) and "body" in command_line:
            target = shell_backup_target(command_line)
            if target:
                print(f"BACKUP|{target[0]}|{target[1]}")
        print(decision if not msg else f"{decision}|{msg}")
        return

    target = backup_target(data)
    if target:
        print(f"BACKUP|{target[0]}|{target[1]}")

    decision, msg = _manage_pr_decision(data)
    print(decision if not msg else f"{decision}|{msg}")


if __name__ == "__main__":
    main()
