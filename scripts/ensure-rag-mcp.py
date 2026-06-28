#!/usr/bin/env python3
"""ensure-rag-mcp — single source of truth for RAG MCP wiring.

Guarantees the two RAG semantic-search servers — **gbrain** (memory + code) and
**code-review-graph** (CRG, graph + semantic) — are registered in every agent
surface that needs them:

  1. Claude CLI scope — `claude mcp` / ~/.claude.json or project .mcp.json
  2. Claude Desktop   — ~/Library/Application Support/Claude/claude_desktop_config.json
  3. Codex direct     — ~/.codex/config.toml `[mcp_servers.*]`
  4. OpenClaw project — $OPENCLAW_ROOT/.mcp.json

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
CODEX_CFG = HOME / ".codex" / "config.toml"


def _openclaw_root() -> Path:
    env_root = os.environ.get("OPENCLAW_ROOT", "").strip()
    if env_root:
        return Path(env_root).expanduser()
    # This script lives at <OpenClaw>/orama-system/scripts/ensure-rag-mcp.py.
    return Path(__file__).resolve().parents[2]


OPENCLAW_MCP = _openclaw_root() / ".mcp.json"


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


def codex_server_spec(name: str, spec: dict) -> dict:
    """Translate the canonical JSON MCP shape into Codex config.toml shape."""
    translated = {
        "transport": "stdio",
        "command": spec["command"],
        "args": list(spec.get("args", [])),
    }
    if spec.get("env"):
        translated["env"] = dict(spec["env"])
    return translated


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

def _load_json_config(path: Path, label: str) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {label} config {path}: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(f"Failed reading {label} config {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"Invalid JSON in {label} config {path}: expected an object")
    return data


def desktop_load() -> dict:
    return _load_json_config(DESKTOP_CFG, "Claude Desktop")


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


# ── Codex direct scope ───────────────────────────────────────────────────────

def _toml_quote(value: str) -> str:
    return json.dumps(value)


def _toml_array(values: list[str]) -> str:
    return "[" + ", ".join(_toml_quote(v) for v in values) + "]"


def _section_bounds(lines: list[str], header: str) -> tuple[int, int] | None:
    start = None
    for i, line in enumerate(lines):
        if line.strip() == header:
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        stripped = lines[j].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            end = j
            break
    return start, end


def _codex_block(name: str, spec: dict) -> list[str]:
    c = codex_server_spec(name, spec)
    lines = [
        f"[mcp_servers.{name}]\n",
        f"transport = {_toml_quote(c['transport'])}\n",
        f"command = {_toml_quote(c['command'])}\n",
        f"args = {_toml_array(c['args'])}\n",
    ]
    env = c.get("env", {})
    if env:
        lines.append("\n")
        lines.append(f"[mcp_servers.{name}.env]\n")
        for key in sorted(env):
            lines.append(f"{key} = {_toml_quote(str(env[key]))}\n")
    return lines


def codex_load() -> str:
    if CODEX_CFG.is_file():
        return CODEX_CFG.read_text()
    return ""


def codex_present(text: str, name: str) -> bool:
    return f"[mcp_servers.{name}]" in text


def codex_apply(servers: dict) -> bool:
    CODEX_CFG.parent.mkdir(parents=True, exist_ok=True)
    original = codex_load()
    lines = original.splitlines(keepends=True)
    changed = False
    for name, spec in servers.items():
        desired = _codex_block(name, spec)
        main_header = f"[mcp_servers.{name}]"
        env_header = f"[mcp_servers.{name}.env]"
        main_bounds = _section_bounds(lines, main_header)
        env_bounds = _section_bounds(lines, env_header)
        if main_bounds:
            start = main_bounds[0]
            end = env_bounds[1] if env_bounds else main_bounds[1]
            if lines[start:end] != desired:
                lines[start:end] = desired
                changed = True
        else:
            if lines and lines[-1].strip():
                lines.append("\n")
            lines.extend(desired)
            changed = True
    if changed:
        if CODEX_CFG.is_file():
            CODEX_CFG.with_suffix(".toml.bak-ensure-rag").write_text(original)
        CODEX_CFG.write_text("".join(lines))
    return changed


# ── OpenClaw project MCP scope ───────────────────────────────────────────────

def openclaw_load() -> dict:
    return _load_json_config(OPENCLAW_MCP, "OpenClaw MCP")


def openclaw_present(cfg: dict, name: str) -> bool:
    return name in cfg.get("mcpServers", {})


def openclaw_apply(servers: dict) -> bool:
    OPENCLAW_MCP.parent.mkdir(parents=True, exist_ok=True)
    cfg = openclaw_load()
    cfg.setdefault("mcpServers", {})
    changed = False
    for name, spec in servers.items():
        if cfg["mcpServers"].get(name) != spec:
            cfg["mcpServers"][name] = spec
            changed = True
    if changed:
        if OPENCLAW_MCP.is_file():
            OPENCLAW_MCP.with_suffix(".json.bak-ensure-rag").write_text(OPENCLAW_MCP.read_text())
        OPENCLAW_MCP.write_text(json.dumps(cfg, indent=2) + "\n")
    return changed


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Ensure RAG MCP servers wired in CLI + Desktop")
    ap.add_argument("--apply", action="store_true", help="repair missing registrations")
    ap.add_argument("--json", action="store_true", help="machine-readable status")
    args = ap.parse_args()

    servers = canonical_servers()
    desktop_cfg = desktop_load()
    codex_text = codex_load()
    openclaw_cfg = openclaw_load()
    status, missing = {}, False
    for name, spec in servers.items():
        in_cli = cli_present(name)
        in_desktop = desktop_present(desktop_cfg, name)
        in_codex = codex_present(codex_text, name)
        in_openclaw = openclaw_present(openclaw_cfg, name)
        status[name] = {
            "claude_cli": in_cli,
            "claude_desktop": in_desktop,
            "codex": in_codex,
            "openclaw_project": in_openclaw,
        }
        if not all(status[name].values()):
            missing = True

    if args.apply and missing:
        for name, spec in servers.items():
            if not status[name]["claude_cli"] and cli_apply(name, spec):
                status[name]["claude_cli"] = True
        if desktop_apply({n: s for n, s in servers.items() if not status[n]["claude_desktop"]}):
            for name in servers:
                status[name]["claude_desktop"] = True
        if codex_apply({n: s for n, s in servers.items() if not status[n]["codex"]}):
            for name in servers:
                status[name]["codex"] = True
        if openclaw_apply({n: s for n, s in servers.items() if not status[n]["openclaw_project"]}):
            for name in servers:
                status[name]["openclaw_project"] = True
        print("Applied. Restart/reconnect agent surfaces: Claude Desktop, Claude CLI /mcp, Codex, and OpenClaw.")
        # re-evaluate
        missing = any(not all(v.values()) for v in status.values())

    if args.json:
        print(json.dumps(status, indent=2))
    else:
        for name, st in status.items():
            print(
                f"  {name:18} "
                f"ClaudeCLI={'ok' if st['claude_cli'] else 'MISSING':7} "
                f"ClaudeDesktop={'ok' if st['claude_desktop'] else 'MISSING':7} "
                f"Codex={'ok' if st['codex'] else 'MISSING':7} "
                f"OpenClaw={'ok' if st['openclaw_project'] else 'MISSING'}"
            )
        print("RAG wiring:", "OK (Claude + Codex + OpenClaw)" if not missing else "INCOMPLETE — run with --apply")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
