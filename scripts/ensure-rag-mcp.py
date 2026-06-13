#!/usr/bin/env python3
"""ensure-rag-mcp — single source of truth for RAG MCP wiring.

Guarantees the two RAG semantic-search servers — **gbrain** (memory + code) and
**code-review-graph** (CRG, graph + semantic) — are registered in BOTH places that
matter, so RAG works whether you're in the Claude Code CLI or the Claude Desktop app:

  1. CLI scope   — Claude Code (`claude mcp` / ~/.claude.json or project .mcp.json)
  2. Desktop app — ~/Library/Application Support/Claude/claude_desktop_config.json

Skills MUST NOT re-implement this check — call this script. It is the canonical
enforcer (mirrors the attribution-guard single-source pattern). Idempotent.

Usage:
  ensure-rag-mcp.py            # check only; exit 1 if any server missing anywhere
  ensure-rag-mcp.py --apply    # repair: add missing servers to both targets
  ensure-rag-mcp.py --json     # machine-readable status

Why both: CRG semantic search (semantic_search_nodes / query_graph / impact_radius)
is MCP-only — no CLI fallback — so a missing registration silently disables the
semantic lane in that surface. gbrain shares CRG's bge-m3 vector space and is the
degradation path, but only if it too is wired.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
DESKTOP_CFG = HOME / "Library/Application Support/Claude/claude_desktop_config.json"


def _bin(name: str, *fallbacks: str) -> str:
    """Resolve an absolute binary path — Desktop's GUI PATH is minimal, so never
    rely on a bare name there."""
    found = shutil.which(name)
    if found:
        return found
    for fb in fallbacks:
        if Path(fb).exists():
            return fb
    return name  # last resort; check mode will still flag if it can't launch


def _gbrain_bin() -> str:
    return _bin("gbrain", str(HOME / ".bun/bin/gbrain"), str(HOME / ".gbrain/bin/gbrain"))


def _uvx_bin() -> str:
    return _bin("uvx", "/opt/homebrew/bin/uvx", "/usr/local/bin/uvx")


def _python_bin() -> str:
    return _bin("python3.13", "/opt/homebrew/bin/python3.13", sys.executable)


def canonical_servers() -> dict:
    """The ONE definition of the RAG servers. Absolute paths, runtime-resolved."""
    return {
        "gbrain": {
            "type": "stdio",
            "command": "/bin/sh",
            # source ~/.gbrain/.env (holds GBRAIN_DATABASE_URL — never inline a secret)
            "args": ["-c", f'. "$HOME/.gbrain/.env"; exec {_gbrain_bin()} serve'],
            "env": {},
        },
        "code-review-graph": {
            "command": _uvx_bin(),
            "args": ["code-review-graph", "serve"],
            "env": {
                "CRG_ACCEPT_CLOUD_EGRESS": "1",
                "CRG_OPENAI_API_KEY": "ollama",
                "CRG_OPENAI_BASE_URL": "http://localhost:11434/v1",
                "CRG_OPENAI_MODEL": "bge-m3",
                "CRG_OPENAI_DIMENSION": "1024",
                "PYTHON": _python_bin(),
            },
        },
    }


# ── CLI scope (Claude Code) ──────────────────────────────────────────────────

def cli_present(name: str) -> bool:
    """True if Claude Code already knows this server (any scope: user or project)."""
    try:
        out = subprocess.run(
            ["claude", "mcp", "list"], capture_output=True, text=True, timeout=40
        ).stdout
    except Exception:
        return False
    return any(line.split(":", 1)[0].strip() == name for line in out.splitlines())


def cli_apply(name: str, spec: dict) -> bool:
    """Register the server with Claude Code at user scope (idempotent: skip if present)."""
    if cli_present(name):
        return False
    cmd = ["claude", "mcp", "add", name, "-s", "user"]
    for k, v in spec.get("env", {}).items():
        cmd += ["-e", f"{k}={v}"]
    cmd += ["--", spec["command"], *spec["args"]]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  cli add failed for {name}: {exc}", file=sys.stderr)
        return False


# ── Desktop app scope ────────────────────────────────────────────────────────

def desktop_load() -> dict:
    if DESKTOP_CFG.is_file():
        try:
            return json.loads(DESKTOP_CFG.read_text())
        except Exception:
            return {}
    return {}


def desktop_present(cfg: dict, name: str) -> bool:
    return name in cfg.get("mcpServers", {})


def desktop_apply(servers: dict) -> bool:
    if not DESKTOP_CFG.parent.is_dir():
        print(f"  Desktop config dir absent ({DESKTOP_CFG.parent}); is Claude Desktop installed?", file=sys.stderr)
        return False
    cfg = desktop_load()
    cfg.setdefault("mcpServers", {})
    changed = False
    for name, spec in servers.items():
        if cfg["mcpServers"].get(name) != spec:
            cfg["mcpServers"][name] = spec
            changed = True
    if changed:
        if DESKTOP_CFG.is_file():
            DESKTOP_CFG.with_suffix(".json.bak-ensure-rag").write_text(DESKTOP_CFG.read_text())
        DESKTOP_CFG.write_text(json.dumps(cfg, indent=2))
    return changed


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Ensure RAG MCP servers wired in CLI + Desktop")
    ap.add_argument("--apply", action="store_true", help="repair missing registrations")
    ap.add_argument("--json", action="store_true", help="machine-readable status")
    args = ap.parse_args()

    servers = canonical_servers()
    desktop_cfg = desktop_load()
    status, missing = {}, False
    for name, spec in servers.items():
        in_cli = cli_present(name)
        in_desktop = desktop_present(desktop_cfg, name)
        status[name] = {"cli": in_cli, "desktop": in_desktop}
        if not (in_cli and in_desktop):
            missing = True

    if args.apply and missing:
        for name, spec in servers.items():
            if not status[name]["cli"] and cli_apply(name, spec):
                status[name]["cli"] = True
        if desktop_apply({n: s for n, s in servers.items() if not status[n]["desktop"]}):
            for name in servers:
                status[name]["desktop"] = True
        print("Applied. Restart Claude Desktop to load new servers (CLI: /mcp reconnect).")
        # re-evaluate
        missing = any(not (v["cli"] and v["desktop"]) for v in status.values())

    if args.json:
        print(json.dumps(status, indent=2))
    else:
        for name, st in status.items():
            print(f"  {name:18} CLI={'ok' if st['cli'] else 'MISSING':7} Desktop={'ok' if st['desktop'] else 'MISSING'}")
        print("RAG wiring:", "OK (CLI + Desktop)" if not missing else "INCOMPLETE — run with --apply")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
