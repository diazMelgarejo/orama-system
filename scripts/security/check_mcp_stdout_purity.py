#!/usr/bin/env python3
"""Validate MCP stdio server entry points keep stdout JSON-RPC-pure.

Rec #1 in docs/distill-fable-5/2026-07-03-session/AUTOMATION_RECOMMENDATIONS.md.
Prevents the "Unexpected token" failure in
docs/distill-fable-5/2026-07-03-session/DEBUG_TRACE.md: MCP stdio clients parse
stdout as newline-delimited JSON-RPC, so any non-JSON stdout byte (banner,
warning, log line) breaks the parser. Every entry point must keep JSON-RPC (or
nothing) on stdout, everything else on stderr.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()
ALLOWLIST_PATH = ROOT / "scripts" / "security" / "mcp_stdout_purity_allow.txt"

MCP_JSON = ROOT / ".mcp.json"

SH_BARE_CLI_MARKER = "openclaw mcp serve"
CONSOLE_LOG_RE = re.compile(r"console\.log\(\s*(['\"`])")
PY_PRINT_RE = re.compile(r"(?<![.\w])print\(\s*(['\"])")


def load_allowlist() -> set[str]:
    if not ALLOWLIST_PATH.exists():
        return set()
    allowed = set()
    for line in ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        allowed.add(line)
    return allowed


def discover_mcp_json_entries() -> list[Path]:
    """Resolve script-like args from .mcp.json commands, if present."""
    entries: list[Path] = []
    if not MCP_JSON.exists():
        return entries
    try:
        data = json.loads(MCP_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return entries
    servers = data.get("mcpServers", {}) if isinstance(data, dict) else {}
    for cfg in servers.values():
        if not isinstance(cfg, dict):
            continue
        for arg in [cfg.get("command", ""), *(cfg.get("args", []) or [])]:
            if not isinstance(arg, str) or not arg.endswith((".mjs", ".js", ".py", ".sh")):
                continue
            candidate = (ROOT / arg).resolve()
            if candidate.exists():
                entries.append(candidate)
    return entries


def discover_skill_scripts() -> list[Path]:
    entries: list[Path] = []
    skills_root = ROOT / "bin" / "orama-system" / "skills"
    if not skills_root.exists():
        return entries
    for pattern in ("*mcp*server*.mjs", "*mcp*server*.js", "*mcp*server*.py", "*mcp*.sh"):
        entries.extend(sorted(skills_root.glob(f"*/scripts/{pattern}")))
    return entries


def check_shell_wrapper(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    findings = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        # Skip comments; only flag literal executable invocations, not the
        # variable-driven pattern ("$OPENCLAW_BIN" ... mcp serve) used by the
        # canonical stdio-clean wrapper. PASS if piped through a line filter
        # or stdout is redirected (banner suppression).
        if stripped.startswith("#") or SH_BARE_CLI_MARKER not in stripped:
            continue
        if "| grep" in line or ">&2" in line or "2>" in line:
            continue
        findings.append(f"{path.relative_to(ROOT)}:{lineno}: bare '{SH_BARE_CLI_MARKER}' with no stdout filter/redirect")
    return findings


def check_js_server(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    findings = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = CONSOLE_LOG_RE.search(line)
        if not match:
            continue
        rest = line[match.end():].lstrip()  # content right after opening quote
        if rest.startswith("{") or rest.startswith(match.group(1) + "{"):
            continue
        findings.append(f"{path.relative_to(ROOT)}:{lineno}: console.log( with non-JSON string literal (use console.error or JSON payload)")
    return findings


def check_py_server(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    findings = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = PY_PRINT_RE.search(line)
        if not match:
            continue
        rest = line[match.end():].lstrip()
        if rest.startswith("{") or "json.dumps(" in line:
            continue
        findings.append(f"{path.relative_to(ROOT)}:{lineno}: print( with non-JSON string literal (use sys.stderr or json.dumps)")
    return findings


def main() -> int:
    allowlist = load_allowlist()
    candidates: list[Path] = []
    for entry in discover_mcp_json_entries() + discover_skill_scripts():
        resolved = entry.resolve()
        if resolved == SELF:
            continue
        if resolved not in candidates:
            candidates.append(resolved)

    all_findings: list[str] = []
    for path in candidates:
        rel = str(path.relative_to(ROOT))
        if rel in allowlist:
            continue
        if path.suffix == ".sh":
            all_findings.extend(check_shell_wrapper(path))
        elif path.suffix in (".mjs", ".js"):
            all_findings.extend(check_js_server(path))
        elif path.suffix == ".py":
            all_findings.extend(check_py_server(path))

    if all_findings:
        print(json.dumps({"mcp_stdout_purity_violations": all_findings}, indent=2))
        return 2

    print(f"mcp stdout purity gate passed ({len(candidates)} entry point(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
