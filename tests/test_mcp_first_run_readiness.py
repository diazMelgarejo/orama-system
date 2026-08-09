from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "bin" / "orama-system" / "scripts" / "install-mcp-stack.sh"
ENSURE = ROOT / "scripts" / "ensure_requirements.sh"
PLATFORM_ENSURE = ROOT / "scripts" / "ensure_platform_requirements.sh"


def _write_exe(path: Path, body: str) -> None:
    path.write_text("#!/bin/sh\nset -eu\n" + body, encoding="utf-8")
    path.chmod(0o755)


def _fake_core(tmp_path: Path, *, version: str = "2.22.0", claude_ready: bool = False):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "commands.log"

    _write_exe(
        bin_dir / "node",
        'if [ "${1:-}" = "-e" ]; then exit 0; fi\nprintf "v22.12.0\\n"\n',
    )
    _write_exe(
        bin_dir / "npm",
        f'''printf '%s\\n' "$*" >> "{log}"
if [ "${{1:-}}" = "list" ]; then
  printf '%s\\n' '{{"dependencies":{{"ai-cli-mcp":{{"version":"{version}"}}}}}}'
fi
''',
    )
    _write_exe(bin_dir / "npx", f'printf "%s\\n" "$*" >> "{log}"\n')
    _write_exe(
        bin_dir / "ai-cli",
        f'printf "ai-cli %s\\n" "$*" >> "{log}"\ncase "${{1:-}}" in doctor|models) exit 0;; esac\n',
    )
    _write_exe(bin_dir / "ai-cli-mcp", 'exit 0\n')
    auth_rc = 0 if claude_ready else 1
    _write_exe(
        bin_dir / "claude",
        f'''printf 'claude %s\\n' "$*" >> "{log}"
if [ "${{1:-}} ${{2:-}} ${{3:-}}" = "mcp get ai-cli" ]; then
  printf '%s\\n' 'args: -y ai-cli-mcp@2.22.0'
  exit 0
fi
if [ "${{1:-}} ${{2:-}}" = "auth status" ]; then exit {auth_rc}; fi
exit 0
''',
    )
    env = os.environ.copy()
    env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]
    return env, log


def test_noninteractive_verify_separates_core_from_provider_auth(tmp_path: Path):
    env, log = _fake_core(tmp_path, claude_ready=False)
    result = subprocess.run(
        ["bash", str(INSTALLER), "--core-only", "--non-interactive", "--verify"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["core"] == "READY"
    assert payload["package"]["version"] == "2.22.0"
    assert payload["provider"]["claude"] == "DEGRADED"

    commands = log.read_text(encoding="utf-8")
    assert "--dangerously-skip-permissions" not in commands
    assert "auth login" not in commands
    assert "npm install" not in commands


def test_verify_rejects_unreviewed_installed_version(tmp_path: Path):
    env, _ = _fake_core(tmp_path, version="2.21.0")
    result = subprocess.run(
        ["bash", str(INSTALLER), "--core-only", "--non-interactive", "--verify"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "2.22.0 is not installed exactly" in result.stderr


def test_startup_requirements_compose_platform_and_mcp_contracts():
    wrapper = ENSURE.read_text(encoding="utf-8")
    assert PLATFORM_ENSURE.exists()
    assert "ensure_platform_requirements.sh" in wrapper
    assert "install-mcp-stack.sh" in wrapper
    assert "--core-only" in wrapper
    assert "--non-interactive" in wrapper
    assert "ORAMA_SKIP_MCP_BOOTSTRAP" in wrapper
    assert "--check) mcp_args+=(--verify)" in wrapper


def test_installer_has_no_false_acceptance_marker_or_floating_latest():
    text = INSTALLER.read_text(encoding="utf-8")
    assert ".dangerously-skip-accepted" not in text
    assert "touch " not in text
    assert "ai-cli-mcp@latest" not in text
    assert 'AI_CLI_MCP_VERSION="${AI_CLI_MCP_VERSION:-2.22.0}"' in text
