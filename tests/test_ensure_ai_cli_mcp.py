from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "scripts/ensure_ai_cli_mcp.py"
SPEC = importlib.util.spec_from_file_location("ensure_ai_cli_mcp", MODULE_PATH)
assert SPEC and SPEC.loader
mcp = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mcp
SPEC.loader.exec_module(mcp)


@pytest.mark.parametrize(
    ("raw", "supported"),
    [
        ("v20.18.9", False),
        ("v20.19.0", True),
        ("v21.7.3", False),
        ("v22.11.0", False),
        ("v22.12.0", True),
        ("v23.0.0", True),
    ],
)
def test_node_engine_matches_upstream(raw: str, supported: bool) -> None:
    parsed = mcp.parse_node_version(raw)
    assert parsed is not None
    assert mcp.node_version_supported(parsed) is supported


def test_core_ready_without_claude_does_not_infer_provider_auth(monkeypatch) -> None:
    commands: list[tuple[str, ...]] = []

    def which(name: str) -> str | None:
        if name == "claude":
            return None
        return f"/fake/{name}"

    def run(args, *, timeout=30):
        commands.append(tuple(args))
        if list(args[:4]) == ["npm", "list", "-g", "ai-cli-mcp"]:
            return subprocess.CompletedProcess(
                args, 0, '{"dependencies":{"ai-cli-mcp":{"version":"2.22.0"}}}', ""
            )
        if list(args[-1:]) == ["--version"]:
            return subprocess.CompletedProcess(args, 0, "v22.12.0\n", "")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(mcp.shutil, "which", which)
    monkeypatch.setattr(mcp, "run", run)

    result = mcp.ensure_readiness(check_only=True)

    assert result.core == "READY"
    assert result.claude_registration == "NOT_INSTALLED"
    assert not any("dangerously-skip-permissions" in " ".join(cmd) for cmd in commands)


def test_check_only_reports_wrong_pinned_version_without_install(monkeypatch) -> None:
    commands: list[tuple[str, ...]] = []
    monkeypatch.setattr(mcp.shutil, "which", lambda name: f"/fake/{name}")

    def run(args, *, timeout=30):
        commands.append(tuple(args))
        if list(args[:4]) == ["npm", "list", "-g", "ai-cli-mcp"]:
            return subprocess.CompletedProcess(
                args, 0, '{"dependencies":{"ai-cli-mcp":{"version":"2.21.0"}}}', ""
            )
        if list(args[-1:]) == ["--version"]:
            return subprocess.CompletedProcess(args, 0, "v22.12.0\n", "")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(mcp, "run", run)
    result = mcp.ensure_readiness(check_only=True)

    assert result.core == "FAILED"
    assert any("2.22.0" in item for item in result.remediation)
    assert not any(cmd[:3] == ("npm", "install", "-g") for cmd in commands)


def test_install_repairs_to_pinned_version(monkeypatch) -> None:
    versions = iter([None, "2.22.0"])
    commands: list[tuple[str, ...]] = []

    monkeypatch.setattr(mcp.shutil, "which", lambda name: f"/fake/{name}")
    monkeypatch.setattr(mcp, "installed_package_version", lambda: next(versions))

    def run(args, *, timeout=30):
        commands.append(tuple(args))
        if list(args[-1:]) == ["--version"]:
            return subprocess.CompletedProcess(args, 0, "v22.12.0\n", "")
        if list(args[:3]) == ["claude", "mcp", "list"]:
            return subprocess.CompletedProcess(
                args, 0, "ai-cli: npx -y ai-cli-mcp@2.22.0\n", ""
            )
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(mcp, "run", run)
    result = mcp.ensure_readiness()

    assert result.core == "READY"
    assert ("npm", "install", "-g", "ai-cli-mcp@2.22.0") in commands


def test_claude_registration_failure_degrades_client_not_core(monkeypatch) -> None:
    monkeypatch.setattr(mcp.shutil, "which", lambda name: f"/fake/{name}")
    monkeypatch.setattr(mcp, "installed_package_version", lambda: "2.22.0")

    def run(args, *, timeout=30):
        if list(args[-1:]) == ["--version"]:
            return subprocess.CompletedProcess(args, 0, "v22.12.0\n", "")
        if list(args[:3]) == ["claude", "mcp", "list"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if list(args[:3]) == ["claude", "mcp", "add"]:
            return subprocess.CompletedProcess(args, 1, "", "not authenticated")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(mcp, "run", run)
    result = mcp.ensure_readiness()

    assert result.core == "READY"
    assert result.claude_registration == "DEGRADED"
