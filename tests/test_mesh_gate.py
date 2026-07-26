from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

MESH_GATE = Path(__file__).resolve().parents[1] / "scripts" / "mesh" / "mesh_gate.py"


@pytest.fixture
def gate_mod():
    spec = importlib.util.spec_from_file_location("mesh_gate", MESH_GATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_gossip_secret_from_env(gate_mod, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GOSSIP_SHARED_SECRET", "from-env")
    assert gate_mod.gossip_secret_configured(tmp_path)


def test_gossip_secret_from_dotenv(gate_mod, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GOSSIP_SHARED_SECRET", raising=False)
    (tmp_path / ".env.local").write_text("GOSSIP_SHARED_SECRET=from-file\n", encoding="utf-8")
    assert gate_mod.gossip_secret_configured(tmp_path)


def test_gossip_secret_missing(gate_mod, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GOSSIP_SHARED_SECRET", raising=False)
    assert not gate_mod.gossip_secret_configured(tmp_path)
