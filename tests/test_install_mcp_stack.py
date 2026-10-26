"""Tests for bin/orama-system/scripts/install-mcp-stack.sh core readiness."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "bin/orama-system/scripts/install-mcp-stack.sh"


_NEEDS_POSIX_USERLAND = pytest.mark.skipif(
    sys.platform == "win32",
    reason="install-mcp-stack.sh needs python3 and /usr/bin:/bin on PATH, which Windows lacks",
)


def _cmd(path: Path, name: str, body: str) -> None:
    """Helper for cmd."""
    target = path / name
    target.write_text("#!/usr/bin/env bash\nset -eu\n" + body, encoding="utf-8")
    target.chmod(0o755)


def _env(tmp_path: Path) -> dict[str, str]:
    """Helper for env."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    _cmd(bindir, "node", "echo v22.12.0")
    _cmd(
        bindir,
        "npm",
        "if [ \"${1:-}\" = list ]; then "
        "printf '%s\\n' '{\"dependencies\":{\"ai-cli-mcp\":{\"version\":\"2.22.0\"}}}'; "
        "exit 0; fi\n"
        "exit 0",
    )
    _cmd(bindir, "npx", "exit 0")
    _cmd(bindir, "ai-cli", "exit 0")
    _cmd(bindir, "ai-cli-mcp", "exit 0")

    env = os.environ.copy()
    # Keep tests hermetic: the readiness helper must not call a workstation's
    # real Claude client while exercising the fake command environment.
    env["PATH"] = os.pathsep.join(
        (str(bindir), str(Path(sys.executable).parent), "/usr/bin", "/bin")
    )
    env["HOME"] = str(tmp_path)
    return env


@_NEEDS_POSIX_USERLAND
def test_core_verify_is_noninteractive_and_uses_shared_gate(tmp_path: Path) -> None:
    """Verify core verify is noninteractive and uses shared gate."""
    result = subprocess.run(
        ["bash", str(SCRIPT), "--core-only", "--non-interactive", "--verify"],
        env=_env(tmp_path),
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "Core ai-cli-mcp readiness complete" in result.stdout
    assert "dangerously-skip-permissions" not in result.stdout


@_NEEDS_POSIX_USERLAND
def test_core_readiness_does_not_require_claude_client(tmp_path: Path) -> None:
    """Verify core readiness does not require claude client."""
    result = subprocess.run(
        ["bash", str(SCRIPT), "--core-only", "--verify"],
        env=_env(tmp_path),
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.integration
@_NEEDS_POSIX_USERLAND
def test_core_only_default_arguments_are_bash32_nounset_safe(tmp_path: Path) -> None:
    """Verify core only default arguments are bash32 nounset safe."""
    result = subprocess.run(
        ["/bin/bash", "-u", str(SCRIPT), "--core-only"],
        env=_env(tmp_path),
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "Core ai-cli-mcp readiness complete" in result.stdout


def test_unknown_flag_rejected_before_any_install(tmp_path: Path) -> None:
    """Verify unknown flag rejected before any install."""
    result = subprocess.run(
        ["bash", str(SCRIPT), "--wat"],
        env=_env(tmp_path),
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 2
    assert "unknown option" in result.stderr
