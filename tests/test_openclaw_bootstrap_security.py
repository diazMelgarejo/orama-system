#!/usr/bin/env python3
"""Security tests for openclaw_bootstrap fallback path."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

os.environ["OPENCLAW_EXTRA_PORTS"] = ""
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import openclaw_bootstrap as bootstrap


def test_parse_port_list_ignores_invalid_tokens(capsys):
    ports = bootstrap._parse_port_list("8081,not-a-port,9090")
    assert ports == [8081, 9090]
    assert "Ignoring invalid port" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_inline_bootstrap_refuses_without_setup_password(monkeypatch, tmp_path):
    monkeypatch.setattr(bootstrap, "_PT_SCRIPT", tmp_path / "missing-pt-bootstrap.py")

    async def _no_gateway():
        return None

    monkeypatch.setattr(bootstrap, "_find_any_gateway", _no_gateway)
    monkeypatch.setattr(
        bootstrap.shutil,
        "which",
        lambda name: "/usr/bin/true" if name in ("npm", "alphaclaw") else None,
    )
    monkeypatch.setattr(
        bootstrap.subprocess,
        "run",
        lambda *args, **kwargs: MagicMock(returncode=0),
    )
    monkeypatch.setattr(bootstrap.Path, "home", lambda: tmp_path)
    monkeypatch.delenv("SETUP_PASSWORD", raising=False)
    monkeypatch.delenv("ORAMA_INSECURE_DEV", raising=False)

    ok = await bootstrap._bootstrap_inline(force=True)

    assert ok is False
