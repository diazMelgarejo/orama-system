from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "scripts" / "mesh" / "lan_topology_archive.py"


@pytest.fixture
def archive_mod():
    import importlib.util

    spec = importlib.util.spec_from_file_location("lan_topology_archive", ARCHIVE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_collect_from_main_has_5080_endpoint(archive_mod):
    env = archive_mod.collect_from_ref("main")
    assert "LM_STUDIO_WIN_5080_ENDPOINTS" in env
    assert "192.168" in env["LM_STUDIO_WIN_5080_ENDPOINTS"]
