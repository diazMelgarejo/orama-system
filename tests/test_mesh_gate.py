from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Protocol

import pytest

pytestmark = pytest.mark.unit

MESH_GATE = Path(__file__).resolve().parents[1] / "scripts" / "mesh" / "mesh_gate.py"


class MeshGateModule(Protocol):
    def gossip_secret_configured(self, repo_root: Path) -> bool: ...


@pytest.fixture
def gate_mod() -> MeshGateModule:
    spec = importlib.util.spec_from_file_location("mesh_gate", MESH_GATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module  # type: ignore[return-value]


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


@pytest.mark.parametrize(
    "env_value",
    ["", "   ", "\t"],
    ids=["empty", "spaces", "tab"],
)
def test_gossip_secret_blank_env_not_configured(
    gate_mod,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    env_value: str,
) -> None:
    monkeypatch.setenv("GOSSIP_SHARED_SECRET", env_value)
    assert not gate_mod.gossip_secret_configured(tmp_path)


@pytest.mark.parametrize(
    "dotenv_line",
    [
        "GOSSIP_SHARED_SECRET=\n",
        "GOSSIP_SHARED_SECRET=   \n",
        'GOSSIP_SHARED_SECRET=""\n',
        "GOSSIP_SHARED_SECRET=''\n",
    ],
    ids=["empty", "spaces", "double-quotes", "single-quotes"],
)
def test_gossip_secret_blank_dotenv_not_configured(
    gate_mod,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    dotenv_line: str,
) -> None:
    monkeypatch.delenv("GOSSIP_SHARED_SECRET", raising=False)
    (tmp_path / ".env.local").write_text(dotenv_line, encoding="utf-8")
    assert not gate_mod.gossip_secret_configured(tmp_path)
