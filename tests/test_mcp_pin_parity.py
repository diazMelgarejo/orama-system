from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
HELPER = ROOT / "scripts/ensure_ai_cli_mcp.py"
STACK = ROOT / "bin/orama-system/config/cursor-mcp.stack.json"


def _load_helper():
    spec = importlib.util.spec_from_file_location("ensure_ai_cli_mcp_pin", HELPER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_cursor_ai_cli_mcp_pin_matches_readiness_source_of_truth() -> None:
    helper = _load_helper()
    config = json.loads(STACK.read_text(encoding="utf-8"))
    args = config["mcpServers"]["ai-cli-mcp"]["args"]
    assert args == ["-y", f"ai-cli-mcp@{helper.AI_CLI_MCP_VERSION}"]
