from __future__ import annotations

import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "bin/orama-system/scripts/install-mcp-stack.sh"


def _cmd(path: Path, name: str, body: str) -> None:
    target = path / name
    target.write_text("#!/usr/bin/env bash\nset -eu\n" + body)
    target.chmod(0o755)


def _env(tmp_path: Path, *, doctor_ok: bool = True, registered: bool = True) -> dict[str, str]:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    # The installer's Node compatibility probe uses `node -e`; this stub models
    # a supported runtime without needing a real npm/network operation in CI.
    _cmd(bindir, "node", "if [ \"${1:-}\" = -e ]; then exit 0; fi\necho v22.12.0")
    _cmd(bindir, "npm", "echo npm \"$@\"")
    _cmd(bindir, "npx", "exit 0")
    doctor = "exit 0" if doctor_ok else "exit 7"
    _cmd(
        bindir,
        "ai-cli",
        f"if [ \"${{1:-}}\" = doctor ]; then {doctor}; fi\n"
        "if [ \"${1:-}\" = models ]; then exit 0; fi\nexit 0",
    )
    _cmd(bindir, "ai-cli-mcp", "exit 0")
    listing = "ai-cli: npx -y ai-cli-mcp@2.22.0" if registered else ""
    _cmd(
        bindir,
        "claude",
        f"if [ \"${{1:-}} ${{2:-}}\" = 'mcp list' ]; then echo '{listing}'; exit 0; fi\n"
        "echo claude \"$@\"",
    )
    env = os.environ.copy()
    env["PATH"] = f"{bindir}:{env['PATH']}"
    env["HOME"] = str(tmp_path)
    return env


def test_verify_ready_is_noninteractive(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT), "--core-only", "--non-interactive", "--verify"],
        env=_env(tmp_path), text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert '"core":"READY"' in result.stdout
    assert "dangerously-skip-permissions" not in result.stdout


def test_doctor_failure_is_core_failure(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT), "--core-only", "--non-interactive", "--verify"],
        env=_env(tmp_path, doctor_ok=False), text=True, capture_output=True,
    )
    assert result.returncode != 0
    assert "ai-cli doctor failed" in result.stderr


def test_missing_registration_verify_fails_without_mutation(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT), "--core-only", "--non-interactive", "--verify"],
        env=_env(tmp_path, registered=False), text=True, capture_output=True,
    )
    assert result.returncode != 0
    assert "registration 'ai-cli' missing" in result.stderr


def test_unknown_flag_rejected(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT), "--wat"], env=_env(tmp_path), text=True, capture_output=True,
    )
    assert result.returncode == 2
