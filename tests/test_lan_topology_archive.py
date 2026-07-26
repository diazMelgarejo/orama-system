from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MESH = ROOT / "scripts" / "mesh"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def archive_mod():
    return _load_module("lan_topology_archive", MESH / "lan_topology_archive.py")


@pytest.fixture
def dotenv_mod():
    return _load_module("dotenv_merge", MESH / "dotenv_merge.py")


def test_extract_env_map_classifies_5080_from_local_context_only(archive_mod):
    fixture = """
    {
      "win-researcher-5080": {"url": "http://192.168.1.50:1234/v1"},
      "win-3080": {"url": "http://192.168.1.40:1234/v1"}
    }
    """
    env = archive_mod.extract_env_map(fixture)
    assert env["LM_STUDIO_WIN_5080_ENDPOINTS"] == "http://192.168.1.50:1234"
    assert env["LM_STUDIO_WIN_ENDPOINTS"] == "http://192.168.1.40:1234"


def test_extract_env_map_does_not_globalize_5080_hostname(archive_mod):
    """Distant win-researcher-5080 slug must not reclassify unrelated IPs."""
    fixture = (
        '"slug": "win-researcher-5080",\n'
        + " " * 200
        + '"url": "http://192.168.1.40:1234/v1"'
    )
    env = archive_mod.extract_env_map(fixture)
    assert "LM_STUDIO_WIN_5080_ENDPOINTS" not in env
    assert env["LM_STUDIO_WIN_ENDPOINTS"] == "http://192.168.1.40:1234"


def test_harmonize_dotenv_preserves_comments_and_skips_nonempty(dotenv_mod, tmp_path):
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "# operator note — keep me\n"
        "EXA_API_KEY=existing-secret\n"
        "LM_STUDIO_WIN_ENDPOINTS=\n"
        "\n"
        "# tail comment\n",
        encoding="utf-8",
    )
    dotenv_mod.harmonize_dotenv_keys(
        env_file,
        {
            "LM_STUDIO_WIN_ENDPOINTS": "http://192.168.1.40:1234",
            "LM_STUDIO_WIN_5080_ENDPOINTS": "http://192.168.1.50:1234",
        },
        managed_keys=frozenset(
            {"LM_STUDIO_WIN_ENDPOINTS", "LM_STUDIO_WIN_5080_ENDPOINTS"}
        ),
        header_comment="# harmonized",
    )
    text = env_file.read_text(encoding="utf-8")
    assert "# operator note — keep me" in text
    assert "EXA_API_KEY=existing-secret" in text
    assert "# tail comment" in text
    assert "LM_STUDIO_WIN_ENDPOINTS=http://192.168.1.40:1234" in text
    assert "LM_STUDIO_WIN_5080_ENDPOINTS=http://192.168.1.50:1234" in text


def test_collect_from_ref_uses_git_show(archive_mod, monkeypatch):
    samples = {
        "bin/orama-system/config/agent_registry.json": (
            '{"5080": "http://192.168.1.50:1234/v1", '
            '"3080": "http://192.168.1.40:1234/v1"}'
        ),
        "config/mac-orchestrator.json": "",
    }

    def fake_git_show(ref: str, path: str) -> str | None:
        return samples.get(path)

    monkeypatch.setattr(archive_mod, "git_show", fake_git_show)
    env = archive_mod.collect_from_ref("fixture-ref")
    assert env["LM_STUDIO_WIN_5080_ENDPOINTS"] == "http://192.168.1.50:1234"
    assert env["LM_STUDIO_WIN_ENDPOINTS"] == "http://192.168.1.40:1234"
