#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "scripts" / "review" / "verify_trusted_install.py"


@pytest.fixture
def trusted_mod(monkeypatch):
    spec = importlib.util.spec_from_file_location("verify_trusted_install", VERIFY)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


def test_trusted_install_allows_override(trusted_mod, monkeypatch):
    monkeypatch.setenv("ORAMA_TRUST_HERMES_SYNC", "1")
    ok, reason = trusted_mod.trusted_install_allowed(trusted_mod.resolve_repo_root())
    assert ok is True
    assert "override" in reason


def test_trusted_install_blocks_skip(trusted_mod, monkeypatch):
    monkeypatch.setenv("ORAMA_SKIP_HERMES_SYNC", "1")
    ok, reason = trusted_mod.trusted_install_allowed(trusted_mod.resolve_repo_root())
    assert ok is False
    assert "SKIP" in reason
