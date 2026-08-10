#!/usr/bin/env python3
"""Ensure the pinned ai-cli-mcp package is installed and runnable.

Cross-platform source of truth for macOS/Linux/Windows requirement gates.
Provider login, terms acceptance, and permission bypasses are deliberately out
of scope: package readiness and provider authorization are different states.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from typing import Sequence

AI_CLI_MCP_VERSION = "2.22.0"
AI_CLI_MCP_PACKAGE = f"ai-cli-mcp@{AI_CLI_MCP_VERSION}"
CLAUDE_MCP_NAME = "ai-cli"


@dataclass
class Readiness:
    core: str = "FAILED"
    package_version: str | None = None
    claude_registration: str = "NOT_INSTALLED"
    checks: list[str] = field(default_factory=list)
    remediation: list[str] = field(default_factory=list)


class CommandError(RuntimeError):
    pass


def parse_node_version(raw: str) -> tuple[int, int, int] | None:
    match = re.search(r"v?(\d+)\.(\d+)\.(\d+)", raw)
    return tuple(map(int, match.groups())) if match else None


def node_version_supported(version: tuple[int, int, int]) -> bool:
    """Match ai-cli-mcp 2.22.0 engines: ^20.19.0 || >=22.12.0."""
    major, minor, patch = version
    if major == 20:
        return (minor, patch) >= (19, 0)
    if major == 22:
        return (minor, patch) >= (12, 0)
    return major > 22


def run(args: Sequence[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(args),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CommandError(f"timed out: {' '.join(args)}") from exc
    except OSError as exc:
        raise CommandError(f"could not execute {' '.join(args)}: {exc}") from exc


def require_success(args: Sequence[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    proc = run(args, timeout=timeout)
    if proc.returncode:
        detail = (proc.stderr or proc.stdout).strip()
        raise CommandError(
            f"{' '.join(args)} exited {proc.returncode}"
            + (f": {detail}" if detail else "")
        )
    return proc


def installed_package_version() -> str | None:
    proc = run(["npm", "list", "-g", "ai-cli-mcp", "--depth=0", "--json"], timeout=20)
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return None
    return payload.get("dependencies", {}).get("ai-cli-mcp", {}).get("version")


def ensure_package(result: Readiness, *, check_only: bool, force: bool) -> bool:
    current = installed_package_version()
    result.package_version = current
    if current == AI_CLI_MCP_VERSION and not force:
        result.checks.append(f"ai-cli-mcp {current} installed")
        return True
    if check_only:
        result.remediation.append(
            f"run: npm install -g {AI_CLI_MCP_PACKAGE} "
            f"(found {current or 'missing'})"
        )
        return False

    require_success(["npm", "install", "-g", AI_CLI_MCP_PACKAGE], timeout=300)
    current = installed_package_version()
    result.package_version = current
    if current != AI_CLI_MCP_VERSION:
        result.remediation.append(
            f"expected ai-cli-mcp {AI_CLI_MCP_VERSION} after install; "
            f"found {current or 'missing'}"
        )
        return False
    result.checks.append(f"ai-cli-mcp {current} installed")
    return True


def ensure_claude_registration(result: Readiness, *, check_only: bool, force: bool) -> None:
    """Repair the Claude client registration when Claude exists.

    Claude is one MCP client among several. Its absence or login state never
    changes package-level core health.
    """
    if not shutil.which("claude"):
        result.checks.append("Claude Code absent; client registration skipped")
        return

    listed = run(["claude", "mcp", "list"], timeout=20)
    registered = listed.returncode == 0 and bool(
        re.search(r"(?m)^\s*ai-cli(?:\s|:|$)", listed.stdout)
    )
    if registered and not force:
        result.claude_registration = "READY"
        result.checks.append("Claude MCP registration 'ai-cli' present")
        return
    if check_only:
        result.claude_registration = "DEGRADED"
        result.remediation.append(
            "run: claude mcp add -s user ai-cli -- "
            f"npx -y {AI_CLI_MCP_PACKAGE}"
        )
        return

    added = run(
        [
            "claude", "mcp", "add", "-s", "user", CLAUDE_MCP_NAME,
            "--", "npx", "-y", AI_CLI_MCP_PACKAGE,
        ],
        timeout=30,
    )
    if added.returncode:
        result.claude_registration = "DEGRADED"
        result.remediation.append(
            "Claude MCP registration repair failed; core package remains ready"
        )
        return
    result.claude_registration = "READY"
    result.checks.append("Claude MCP registration 'ai-cli' repaired")


def ensure_readiness(*, check_only: bool = False, force: bool = False) -> Readiness:
    result = Readiness()

    node = shutil.which("node")
    if not node:
        result.remediation.append(
            "install Node.js matching ai-cli-mcp engines: ^20.19.0 or >=22.12.0"
        )
        return result
    if not shutil.which("npm") or not shutil.which("npx"):
        result.remediation.append("npm and npx must both be available on PATH")
        return result

    node_proc = run([node, "--version"], timeout=10)
    version = parse_node_version(node_proc.stdout or node_proc.stderr)
    if not version or not node_version_supported(version):
        shown = (node_proc.stdout or node_proc.stderr).strip() or "unknown"
        result.remediation.append(
            f"unsupported Node.js {shown}; ai-cli-mcp {AI_CLI_MCP_VERSION} "
            "requires ^20.19.0 or >=22.12.0"
        )
        return result
    result.checks.append(f"Node.js {'.'.join(map(str, version))} supported")

    try:
        if not ensure_package(result, check_only=check_only, force=force):
            return result
    except CommandError as exc:
        result.remediation.append(str(exc))
        return result

    missing = [name for name in ("ai-cli", "ai-cli-mcp") if not shutil.which(name)]
    if missing:
        result.remediation.append(
            "expected command(s) not on PATH after package check: " + ", ".join(missing)
        )
        return result

    for command in (("ai-cli", "models"), ("ai-cli", "doctor")):
        try:
            require_success(command, timeout=20)
        except CommandError as exc:
            result.remediation.append(str(exc))
            return result
        result.checks.append(f"{' '.join(command)} succeeded")

    # Upstream doctor checks binary/path availability only. We never run login,
    # browser, consent, or --dangerously-skip-permissions flows here.
    try:
        ensure_claude_registration(result, check_only=check_only, force=force)
    except CommandError as exc:
        result.claude_registration = "DEGRADED"
        result.remediation.append(str(exc))

    result.core = "READY"
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="probe only; do not repair")
    parser.add_argument("--force", action="store_true", help="reinstall/refresh registrations")
    parser.add_argument("--json", action="store_true", help="emit one JSON object")
    parser.add_argument("--quiet", action="store_true", help="suppress successful text output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = ensure_readiness(check_only=args.check, force=args.force)

    if args.json:
        print(json.dumps(asdict(result), separators=(",", ":"), sort_keys=True))
    elif not args.quiet or result.core != "READY":
        print(
            f"[mcp-readiness] core={result.core} "
            f"package={result.package_version or 'missing'} "
            f"claude={result.claude_registration}"
        )
        for check in result.checks:
            print(f"[mcp-readiness] ok: {check}")
        for remediation in result.remediation:
            print(f"[mcp-readiness] remediation: {remediation}", file=sys.stderr)

    return 0 if result.core == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
