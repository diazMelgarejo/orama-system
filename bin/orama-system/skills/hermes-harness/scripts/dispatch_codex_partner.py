#!/usr/bin/env python3
"""dispatch_codex_partner.py — bounded Codex dispatch with runtime path resolution.

Resolves the Codex binary and orama-system repo root at run time. Never embeds
host-specific absolute paths in prompts or committed examples.

Usage:
    python dispatch_codex_partner.py --pytest tests/test_verify_partner_canaries.py
    python dispatch_codex_partner.py --dry-run --pytest tests/test_verify_partner_canaries.py
    python dispatch_codex_partner.py --profile interactive "Summarize repo layout"

Canonical flag profiles: bin/orama-system/references/codex-cli-v142-dispatch.md
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import verify_partner_canaries as canaries  # noqa: E402


def resolve_orama_repo_root() -> Path:
    """orama-system git toplevel — env override first, then git, then script anchor."""
    for key in ("ORAMA_SYSTEM_PATH", "ORAMA_SYSTEM_ROOT", "ORAMA_REPO_ROOT"):
        raw = os.environ.get(key, "").strip()
        if raw:
            candidate = Path(raw).expanduser()
            if candidate.is_dir():
                return candidate.resolve()
    script = Path(__file__).resolve()
    try:
        top = subprocess.check_output(
            ["git", "-C", str(script.parent), "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return Path(top).resolve()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return script.parents[5].resolve()


def build_pytest_prompt(test_paths: list[str]) -> str:
    rel = " ".join(Path(p).as_posix() for p in test_paths)
    return f"Run only: python -m pytest {rel} -q. Report pass count only."


def build_codex_command(
    codex: str,
    repo_root: Path,
    prompt: str,
    *,
    profile: str,
) -> list[str]:
    """Assemble Codex argv for v0.142.x (no legacy --approval-mode)."""
    root = str(repo_root)
    if profile == "interactive":
        # Top-level non-exec: works in TTY sessions (Codex v0.142.3+).
        return [
            codex,
            "--sandbox",
            "danger-full-access",
            "--ask-for-approval",
            "never",
            "-C",
            root,
            prompt,
        ]
    if profile == "bounded":
        return [codex, "exec", "-C", root, "-s", "workspace-write", prompt]
    # fanout (default): non-interactive orchestrator dispatch
    return [
        codex,
        "exec",
        "-C",
        root,
        "-s",
        "workspace-write",
        "--dangerously-bypass-approvals-and-sandbox",
        prompt,
    ]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("prompt", nargs="?", help="Bounded task prompt (omit when using --pytest)")
    p.add_argument(
        "--pytest",
        nargs="+",
        metavar="PATH",
        help="Repo-relative pytest paths (resolved via -C repo root, not absolute paths)",
    )
    p.add_argument(
        "--profile",
        choices=("fanout", "bounded", "interactive"),
        default="fanout",
        help="fanout=exec+bypass (orchestrators); bounded=exec+workspace-write; interactive=TTY",
    )
    p.add_argument("--dry-run", action="store_true", help="Print resolved command only")
    p.add_argument("--timeout", type=int, default=0, help="Optional wall-clock cap (0=none)")
    args = p.parse_args(argv)

    if not args.prompt and not args.pytest:
        p.error("provide a prompt or --pytest PATH [PATH ...]")

    canaries._ensure_windows_partner_path()
    codex = canaries._resolve_partner_cli("codex")
    if not codex:
        print("codex: not found — run platform/windows/ensure-partner-cli-paths.ps1", file=sys.stderr)
        return 1

    repo_root = resolve_orama_repo_root()
    prompt = args.prompt or build_pytest_prompt(args.pytest or [])
    cmd = build_codex_command(codex, repo_root, prompt, profile=args.profile)

    if args.dry_run:
        print(f"codex={codex}")
        print(f"repo_root={repo_root}")
        print("command=" + subprocess.list2cmdline(cmd))
        return 0

    try:
        completed = subprocess.run(
            cmd,
            cwd=repo_root,
            timeout=args.timeout or None,
        )
        return int(completed.returncode)
    except subprocess.TimeoutExpired:
        print("codex dispatch timed out", file=sys.stderr)
        return 124


if __name__ == "__main__":
    raise SystemExit(main())
