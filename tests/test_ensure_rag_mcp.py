from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ensure-rag-mcp.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("ensure_rag_mcp_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_codex_apply_writes_stdio_mcp_blocks(tmp_path, monkeypatch):
    mod = _load_module()
    cfg = tmp_path / "config.toml"
    cfg.write_text('[mcp_servers.github]\ncommand = "npx"\n', encoding="utf-8")
    monkeypatch.setattr(mod, "CODEX_CFG", cfg)

    servers = {"code-review-graph": mod.canonical_servers()["code-review-graph"]}

    assert mod.codex_apply(servers) is True
    out = cfg.read_text(encoding="utf-8")
    assert "[mcp_servers.github]" in out
    assert "[mcp_servers.code-review-graph]" in out
    assert 'transport = "stdio"' in out
    assert 'command = "' in out and "uvx" in out
    assert 'args = ["code-review-graph", "serve"]' in out
    assert "[mcp_servers.code-review-graph.env]" in out
    assert 'CRG_OPENAI_MODEL = "bge-m3"' in out


def test_openclaw_apply_merges_missing_server(tmp_path, monkeypatch):
    mod = _load_module()
    mcp_json = tmp_path / ".mcp.json"
    mcp_json.write_text(json.dumps({"mcpServers": {"existing": {"command": "x"}}}), encoding="utf-8")
    monkeypatch.setattr(mod, "OPENCLAW_MCP", mcp_json)

    servers = {"gbrain": mod.canonical_servers()["gbrain"]}

    assert mod.openclaw_apply(servers) is True
    data = json.loads(mcp_json.read_text(encoding="utf-8"))
    assert "existing" in data["mcpServers"]
    assert data["mcpServers"]["gbrain"]["command"] == "/bin/sh"
    assert "gbrain serve" in data["mcpServers"]["gbrain"]["args"][1]


def test_openclaw_apply_rejects_malformed_json(tmp_path, monkeypatch):
    mod = _load_module()
    mcp_json = tmp_path / ".mcp.json"
    mcp_json.write_text('{"mcpServers": ', encoding="utf-8")
    monkeypatch.setattr(mod, "OPENCLAW_MCP", mcp_json)

    with pytest.raises(RuntimeError, match="Invalid JSON"):
        mod.openclaw_apply({"gbrain": mod.canonical_servers()["gbrain"]})
