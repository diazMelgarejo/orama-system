"""Cover launcher path precedence and npm-prefix discovery without services."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.unit
def test_explicit_pt_source_overrides_cached_paths(tmp_path: Path) -> None:
    """An operator-selected source wins over a valid but obsolete cached path."""
    script = (ROOT / "start.sh").read_text()
    resolution = script.split("_discover_pt_dir()", 1)[1]
    resolution = "_discover_pt_dir()" + resolution.split("PT_PORT=${", 1)[0]
    live = tmp_path / "live"
    (live / "orchestrator").mkdir(parents=True)
    (live / "orchestrator/fastapi_app.py").touch()
    (live / "orchestrator/alphaclaw_manager.py").touch()
    cached = tmp_path / ".paths"
    cached.write_text('PT_DIR="/old/source"\nPT_PYTHON="/old/python"\n')
    env = dict(os.environ, PERPETUA_TOOLS_ROOT=str(live))
    result = subprocess.run(
        ["/bin/bash", "-c", 'set -eu; SCRIPT_DIR="$1"; PATHS_FILE="$2"; '
         '_debug() { :; }; _warn() { :; }; _info() { :; }; '
         + resolution + '\nprintf "%s\\n" "$PT_DIR" "$PT_PYTHON"',
         "test", str(tmp_path), str(cached)],
        env=env, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[0] == str(live)
    assert "/old/python" not in result.stdout


@pytest.mark.unit
def test_node_path_uses_npm_prefix_with_spaces(tmp_path: Path) -> None:
    """The sourced helper updates its caller, not just a Python subprocess."""
    bins = tmp_path / "bin"
    bins.mkdir()
    prefix = tmp_path / "npm prefix"
    (prefix / "bin").mkdir(parents=True)
    npm = bins / "npm"
    npm.write_text(f'#!/bin/sh\nprintf "%s\\n" "{prefix}"\n')
    npm.chmod(0o755)
    executable = prefix / "bin/ai-cli"
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    result = subprocess.run(
        ["/bin/bash", "-c", 'source "$1"; command -v ai-cli', "test",
         str(ROOT / "scripts/lib/node-global-path.sh")],
        env=dict(os.environ, PATH=str(bins) + ":/usr/bin:/bin"),
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(executable)


@pytest.mark.unit
def test_macos_banner_probe_sets_connection_timeout(tmp_path: Path) -> None:
    """Darwin nc needs -G; -w alone does not bound the connection phase."""
    script = (ROOT / "start.sh").read_text()
    function = "_nc_probe()" + script.split("_nc_probe()", 1)[1].split(
        "  ( _nc_probe localhost", 1
    )[0]
    nc = tmp_path / "nc"
    nc.write_text('#!/bin/sh\ncase " $* " in *" -G 1 "*) exit 0;; *) exit 1;; esac\n')
    nc.chmod(0o755)
    result = subprocess.run(
        ["/bin/bash", "-c", '_OS_NAME=Darwin; ' + function + '\n_nc_probe host 1234'],
        env=dict(os.environ, PATH=str(tmp_path) + ":/usr/bin:/bin"),
        capture_output=True, text=True, timeout=3,
    )
    assert result.returncode == 0, result.stderr
