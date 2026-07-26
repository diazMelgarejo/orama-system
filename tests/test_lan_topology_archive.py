from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any, Protocol

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
MESH = ROOT / "scripts" / "mesh"


class ArchiveModule(Protocol):
    def extract_env_map(self, text: str) -> dict[str, str]: ...
    def collect_from_ref(self, ref: str) -> dict[str, str]: ...
    def git_show(self, ref: str, path: str) -> str | None: ...


class DotenvModule(Protocol):
    def harmonize_dotenv_keys(
        self,
        path: Path,
        values: dict[str, str],
        *,
        managed_keys: frozenset[str] | None = None,
        header_comment: str | None = None,
        replace_keys: frozenset[str] | None = None,
        supersede_timestamp: str | None = None,
    ) -> list[str]: ...


class SecretsModule(Protocol):
    def ensure_gossip_secret(self, *, force: bool = False) -> str: ...
    ROOT: Path
    SECRETS_JSON: Path


def _load_module(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def archive_mod() -> ArchiveModule:
    return _load_module("lan_topology_archive", MESH / "lan_topology_archive.py")  # type: ignore[return-value]


@pytest.fixture
def dotenv_mod() -> DotenvModule:
    return _load_module("dotenv_merge", MESH / "dotenv_merge.py")  # type: ignore[return-value]


@pytest.fixture
def secrets_mod(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> SecretsModule:
    monkeypatch.setenv("PERPETUA_TOOLS_PATH", str(tmp_path / "perpetua"))
    return _load_module("ensure_local_mesh_secrets", MESH / "ensure_local_mesh_secrets.py")  # type: ignore[return-value]


def test_extract_env_map_classifies_5080_from_local_context_only(archive_mod: ArchiveModule) -> None:
    fixture = """
    {
      "win-researcher-5080": {"url": "http://192.168.1.50:1234/v1"},
      "win-3080": {"url": "http://192.168.1.40:1234/v1"}
    }
    """
    env = archive_mod.extract_env_map(fixture)
    assert env["LM_STUDIO_WIN_5080_ENDPOINTS"] == "http://192.168.1.50:1234"
    assert env["LM_STUDIO_WIN_ENDPOINTS"] == "http://192.168.1.40:1234"


def test_extract_env_map_does_not_globalize_5080_hostname(archive_mod: ArchiveModule) -> None:
    """Distant win-researcher-5080 slug must not reclassify unrelated IPs."""
    fixture = (
        '"slug": "win-researcher-5080",\n'
        + " " * 200
        + '"url": "http://192.168.1.40:1234/v1"'
    )
    env = archive_mod.extract_env_map(fixture)
    assert "LM_STUDIO_WIN_5080_ENDPOINTS" not in env
    assert env["LM_STUDIO_WIN_ENDPOINTS"] == "http://192.168.1.40:1234"


def test_harmonize_dotenv_preserves_comments_and_skips_nonempty(
    dotenv_mod: DotenvModule, tmp_path: Path
) -> None:
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


def test_harmonize_dotenv_updates_last_duplicate_declaration(
    dotenv_mod: DotenvModule, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "LM_STUDIO_WIN_ENDPOINTS=\n"
        "LM_STUDIO_WIN_ENDPOINTS=\n",
        encoding="utf-8",
    )
    dotenv_mod.harmonize_dotenv_keys(
        env_file,
        {"LM_STUDIO_WIN_ENDPOINTS": "http://192.168.1.40:1234"},
        managed_keys=frozenset({"LM_STUDIO_WIN_ENDPOINTS"}),
    )
    text = env_file.read_text(encoding="utf-8")
    assert "# duplicate (inactive; effective declaration follows):" in text
    assert text.strip().endswith("LM_STUDIO_WIN_ENDPOINTS=http://192.168.1.40:1234")


def test_harmonize_dotenv_rotation_supersedes_without_deleting(
    dotenv_mod: DotenvModule, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text("GOSSIP_SHARED_SECRET=old-secret\n", encoding="utf-8")
    dotenv_mod.harmonize_dotenv_keys(
        env_file,
        {"GOSSIP_SHARED_SECRET": "new-secret"},
        managed_keys=frozenset({"GOSSIP_SHARED_SECRET"}),
        replace_keys=frozenset({"GOSSIP_SHARED_SECRET"}),
        supersede_timestamp="2026-07-26T19:00:00+00:00",
    )
    text = env_file.read_text(encoding="utf-8")
    assert "# superseded 2026-07-26T19:00:00+00:00: GOSSIP_SHARED_SECRET=old-secret" in text
    assert "GOSSIP_SHARED_SECRET=new-secret" in text
    assert "old-secret" in text


def test_collect_from_ref_uses_git_show(
    archive_mod: ArchiveModule, monkeypatch: pytest.MonkeyPatch
) -> None:
    samples: dict[str, str] = {
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


def test_force_rotation_updates_env_and_archive(
    secrets_mod: SecretsModule, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo_root = tmp_path / "orama"
    repo_root.mkdir()
    (repo_root / ".local").mkdir()
    pt_root = tmp_path / "perpetua"
    pt_root.mkdir()
    monkeypatch.setenv("PERPETUA_TOOLS_PATH", str(pt_root))
    monkeypatch.setattr(secrets_mod, "ROOT", repo_root)
    monkeypatch.setattr(secrets_mod, "LOCAL_DIR", repo_root / ".local")
    monkeypatch.setattr(secrets_mod, "SECRETS_JSON", repo_root / ".local" / "mesh-secrets.json")

    orama_env = repo_root / ".env.local"
    pt_env = pt_root / ".env.local"
    orama_env.write_text("GOSSIP_SHARED_SECRET=peer-old\n", encoding="utf-8")
    pt_env.write_text("GOSSIP_SHARED_SECRET=peer-old\n", encoding="utf-8")
    secrets_mod.SECRETS_JSON.write_text(
        '{"GOSSIP_SHARED_SECRET": "peer-old"}', encoding="utf-8"
    )

    new_secret = secrets_mod.ensure_gossip_secret(force=True)
    assert new_secret != "peer-old"
    assert f"GOSSIP_SHARED_SECRET={new_secret}" in orama_env.read_text(encoding="utf-8")
    assert f"GOSSIP_SHARED_SECRET={new_secret}" in pt_env.read_text(encoding="utf-8")
    store = __import__("json").loads(secrets_mod.SECRETS_JSON.read_text(encoding="utf-8"))
    assert store["GOSSIP_SHARED_SECRET"] == new_secret
    assert "peer-old" in orama_env.read_text(encoding="utf-8")
    assert any(k.startswith("GOSSIP_SHARED_SECRET__PREVIOUS_") for k in store)
