from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "bin/orama-system/scripts/install-mcp-stack.sh"


def _cmd(path: Path, name: str, body: str) -> None:
    target = path / name
    target.write_text("#!/usr/bin/env bash\nset -eu\n" + body, encoding="utf-8")
    target.chmod(0o755)


def _env(tmp_path: Path) -> dict[str, str]:
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


def test_core_verify_is_noninteractive_and_uses_shared_gate(tmp_path: Path) -> None:
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


def test_core_readiness_does_not_require_claude_client(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT), "--core-only", "--verify"],
        env=_env(tmp_path),
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


def test_core_only_default_arguments_are_bash32_nounset_safe(tmp_path: Path) -> None:
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
    result = subprocess.run(
        ["bash", str(SCRIPT), "--wat"],
        env=_env(tmp_path),
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 2
    assert "unknown option" in result.stderr
