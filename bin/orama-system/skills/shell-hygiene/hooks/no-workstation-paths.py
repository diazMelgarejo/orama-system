#!/usr/bin/env python3
"""PreToolUse guard: block Write/Edit that injects workstation/absolute paths
into a TRACKED (git) file. Mirrors orama/PT scripts/review/repo_hygiene.py intent
so the leak is caught at write-time, not just at commit/CI.

Exit 2 => block the tool call (Claude must fix). Exit 0 => allow.
Registered as a PreToolUse hook (matcher: Write|Edit) in the user-level Claude settings.
"""
import sys, json, re, subprocess
from pathlib import Path


def repository_target(file_path: str) -> tuple[str, str] | None:
    """Find the Git root and full target path, including missing directories."""
    target = Path(file_path)
    directory = target.parent.resolve()
    ancestor = directory
    while not ancestor.is_dir() and ancestor != ancestor.parent:
        ancestor = ancestor.parent
    probe = subprocess.run(
        ["git", "-C", str(ancestor), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, timeout=5,
    )
    if probe.returncode != 0:
        return None
    root = probe.stdout.rstrip("\n")
    return root, (directory / target.name).relative_to(root).as_posix()

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    ti = data.get("tool_input", {}) or {}
    fp = ti.get("file_path", "") or ""
    if not fp:
        return 0
    # content being introduced (Write=content, Edit=new_string, MultiEdit handled loosely)
    content = ti.get("content") or ti.get("new_string") or ""
    if not content and ti.get("edits"):
        content = "\n".join(e.get("new_string", "") for e in ti.get("edits", []))
    if not content:
        return 0
    # only enforce inside a git work tree (tracked area); skip ~/.claude, /tmp, scratch docs
    try:
        location = repository_target(fp)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        return 0
    if location is None:
        return 0
    root, relative_path = location
    # gitignored files (e.g. .env, pyvenv.cfg) are exempt
    try:
        ignored = subprocess.run(
            ["git", "-C", root, "check-ignore", "--", relative_path],
            capture_output=True, text=True, timeout=5
        ).returncode == 0
        if ignored:
            return 0
    except Exception:
        pass
    # workstation/absolute-path patterns that must not enter tracked files
    # NOTE: home segment must START WITH A LETTER so doc placeholders like
    # /Users/<name>/ or /Users/.../ do NOT match (mirrors repo_hygiene.py).
    # code/OpenClaw only flags when clearly an absolute home path (~/ or /Users/<name>/),
    # not the bare relative string in prose.
    patterns = {
        "absolute mac home (/Users/<realname>/)": r"/Users/[A-Za-z][^/\s\"']*/",
        "iCloud OpenClaw tree": r"Documents/Terminal[ \\]+xCode/claude/OpenClaw",
        "home code/OpenClaw path": r"(?:~|/Users/[A-Za-z][^/\s\"']*)/code/OpenClaw",
    }
    hits = [name for name, pat in patterns.items() if re.search(pat, content)]
    if hits:
        sys.stderr.write(
            "BLOCKED by no-workstation-paths guard.\n"
            f"  File (tracked): {fp}\n"
            f"  Leaked: {', '.join(hits)}\n"
            "  Fix: use repo-relative paths — \"$(git rev-parse --show-toplevel)/…\" or a\n"
            "  sibling-relative \"../../<repo>/…\" — never literal /Users/<name>/ or the OpenClaw\n"
            "  tree. Backstop: scripts/review/repo_hygiene.py (CI/pre-commit).\n"
        )
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
