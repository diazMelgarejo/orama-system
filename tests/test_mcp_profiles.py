"""Tests for MCP profile stack selection (security fix 6)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ORAMA_ROOT = Path(__file__).resolve().parents[1]
SYNC_SH = ORAMA_ROOT / "bin/orama-system/scripts/sync-cursor-mcp.sh"
STACK_READONLY = ORAMA_ROOT / "bin/orama-system/config/cursor-mcp.stack.readonly.json"
STACK_ELEVATED = ORAMA_ROOT / "bin/orama-system/config/cursor-mcp.stack.json"


def test_readonly_stack_has_crg_only() -> None:
    data = json.loads(STACK_READONLY.read_text(encoding="utf-8"))
    servers = set(data["mcpServers"].keys())
    assert servers == {"code-review-graph"}


def test_elevated_stack_includes_ai_cli() -> None:
    data = json.loads(STACK_ELEVATED.read_text(encoding="utf-8"))
    servers = set(data["mcpServers"].keys())
    assert "code-review-graph" in servers
    assert "ai-cli-mcp" in servers


def test_sync_script_readonly_profile_dry_run() -> None:
    proc = subprocess.run(
        ["bash", str(SYNC_SH), "--profile", "readonly", "--dry-run"],
        cwd=str(ORAMA_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Profile: readonly" in proc.stdout
    assert "server: code-review-graph" in proc.stdout
    assert "server: ai-cli-mcp" not in proc.stdout


def test_tracked_cursor_mcp_json_is_readonly_safe() -> None:
    data = json.loads((ORAMA_ROOT / ".cursor/mcp.json").read_text(encoding="utf-8"))
    servers = set(data["mcpServers"].keys())
    assert "ai-cli-mcp" not in servers
    assert "code-review-graph" in servers


def test_sync_script_elevated_profile_dry_run() -> None:
    proc = subprocess.run(
        ["bash", str(SYNC_SH), "--profile", "elevated", "--dry-run"],
        cwd=str(ORAMA_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Profile: elevated" in proc.stdout
    assert "server: ai-cli-mcp" in proc.stdout


def test_ensure_control_plane_token_persists_when_enforced(monkeypatch, tmp_path):
    from utils.control_plane_auth import ensure_control_plane_token

    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN", raising=False)
    monkeypatch.delenv("ORAMA_INSECURE_DEV", raising=False)
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(tmp_path))
    monkeypatch.setattr("utils.control_plane_auth.persisted_control_plane_token", lambda: "")

    token = ensure_control_plane_token()
    assert token
    token_path = tmp_path / ".state" / "control_plane_token"
    assert token_path.is_file()
    assert token_path.read_text(encoding="utf-8").strip() == token
