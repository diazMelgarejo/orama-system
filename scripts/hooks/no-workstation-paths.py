#!/usr/bin/env python3
"""PreToolUse guard: block Write/Edit that injects workstation/absolute paths
into a TRACKED (git) file. Mirrors orama/PT scripts/review/repo_hygiene.py intent
so the leak is caught at write-time, not just at commit/CI.

Exit 2 => block the tool call (Claude must fix). Exit 0 => allow.
Registered as a PreToolUse hook (matcher: Write|Edit) in ~/.claude/settings.json.
"""
import sys, json, os, re, subprocess

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
    d = os.path.dirname(fp) or "."
    try:
        inrepo = subprocess.run(
            ["git", "-C", d, "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip() == "true"
    except Exception:
        inrepo = False
    if not inrepo:
        return 0
    # gitignored files (e.g. .env, pyvenv.cfg) are exempt
    try:
        ignored = subprocess.run(
            ["git", "-C", d, "check-ignore", os.path.basename(fp)],
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
