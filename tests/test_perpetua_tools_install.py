#!/usr/bin/env python3
"""Tests for the Perpetua-Tools MCPB integration added in this PR.

Covers two changed files:
- install.sh  (lines 157-173): PT_INSTALL discovery loop + conditional invocation
- scripts/cursor/cloud-install.sh (lines 86-89): conditional Perpetua-Tools invocation
"""
from __future__ import annotations

import os
import stat
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _bash(script: str, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run a bash snippet and return the CompletedProcess."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=full_env,
    )


def _make_fake_install_sh(directory: Path, exit_code: int = 0) -> Path:
    """Create a fake install.sh under *directory* that records its invocation.

    The script writes its arguments to a sentinel file (called.txt) and
    exits with *exit_code*.
    """
    directory.mkdir(parents=True, exist_ok=True)
    script = directory / "install.sh"
    sentinel = directory / "called.txt"
    script.write_text(
        textwrap.dedent(f"""\
            #!/usr/bin/env bash
            echo "$@" >> "{sentinel}"
            exit {exit_code}
        """)
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return script


# ---------------------------------------------------------------------------
# Bash harness: install.sh PT_INSTALL discovery + invocation block
# ---------------------------------------------------------------------------

# This harness replicates ONLY the new code added to install.sh (lines 157-173).
# It is self-contained so it can be run with arbitrary env vars via the `env`
# parameter of _bash().

_PT_DISCOVERY_HARNESS = r"""
warn() { echo "WARN: $*" >&2; }
info() { echo "INFO: $*"; }

PT_INSTALL=""
for PT_CANDIDATE in \
  "${PERPETUA_TOOLS_PATH:-}" \
  "${PERPETUA_TOOLS_ROOT:-}" \
  "${OPENCLAW_HOME:-$HOME/openclaw-v1}/Perpetua-Tools" \
; do
  if [[ -n "$PT_CANDIDATE" && -f "$PT_CANDIDATE/install.sh" ]]; then
    PT_INSTALL="$PT_CANDIDATE/install.sh"
    break
  fi
done
if [[ -n "$PT_INSTALL" ]]; then
  info "Installing Claude Desktop LLM extensions (Perpetua-Tools MCPB)..."
  bash "$PT_INSTALL" --skip-desktop 2>/dev/null || warn "Perpetua-Tools MCPB install skipped (see Perpetua-Tools/install.sh)"
fi
echo ""

# Report what was found (for assertions)
echo "PT_INSTALL=$PT_INSTALL"
"""


def _run_discovery(env: dict) -> subprocess.CompletedProcess:
    return _bash(_PT_DISCOVERY_HARNESS, env=env)


# ---------------------------------------------------------------------------
# Bash harness: cloud-install.sh Perpetua-Tools conditional block (lines 86-89)
# ---------------------------------------------------------------------------

_CLOUD_INSTALL_HARNESS = r"""
warn() { echo "WARN: $*" >&2; }
log()  { printf '>>> [cloud-install] %s\n' "$*"; }

if [[ -f "$OPENCLAW_HOME/Perpetua-Tools/install.sh" ]]; then
  log "Perpetua-Tools install.sh (Claude Desktop MCPB build)"
  bash "$OPENCLAW_HOME/Perpetua-Tools/install.sh" --skip-desktop || warn "MCPB build skipped"
fi

echo "BLOCK_DONE"
"""


def _run_cloud_block(env: dict) -> subprocess.CompletedProcess:
    return _bash(_CLOUD_INSTALL_HARNESS, env=env)


# ===========================================================================
# Tests: install.sh — Perpetua-Tools PT_INSTALL discovery loop
# ===========================================================================

class TestInstallShPtDiscovery:
    """Tests for the PT_INSTALL discovery loop added to install.sh."""

    # ── PERPETUA_TOOLS_PATH takes priority ──────────────────────────────────

    def test_perpetua_tools_path_used_when_set_and_install_sh_exists(self, tmp_path):
        pt_dir = tmp_path / "pt-path"
        _make_fake_install_sh(pt_dir)
        result = _run_discovery({"PERPETUA_TOOLS_PATH": str(pt_dir)})
        assert result.returncode == 0
        assert f"PT_INSTALL={pt_dir}/install.sh" in result.stdout

    def test_perpetua_tools_path_skipped_when_install_sh_absent(self, tmp_path):
        pt_dir = tmp_path / "pt-path-no-install"
        pt_dir.mkdir()
        # No install.sh created
        result = _run_discovery({
            "PERPETUA_TOOLS_PATH": str(pt_dir),
            "HOME": str(tmp_path),
        })
        assert result.returncode == 0
        # PT_INSTALL should be empty (no candidate found)
        assert "PT_INSTALL=" in result.stdout
        # Value after = should be empty (no path)
        line = next(l for l in result.stdout.splitlines() if l.startswith("PT_INSTALL="))
        assert line == "PT_INSTALL="

    # ── PERPETUA_TOOLS_ROOT is the fallback ─────────────────────────────────

    def test_perpetua_tools_root_used_when_path_absent(self, tmp_path):
        pt_root = tmp_path / "pt-root"
        _make_fake_install_sh(pt_root)
        result = _run_discovery({
            "PERPETUA_TOOLS_PATH": "",        # empty → skipped
            "PERPETUA_TOOLS_ROOT": str(pt_root),
        })
        assert result.returncode == 0
        assert f"PT_INSTALL={pt_root}/install.sh" in result.stdout

    def test_perpetua_tools_root_used_when_path_env_not_set(self, tmp_path):
        pt_root = tmp_path / "pt-root-only"
        _make_fake_install_sh(pt_root)
        env = {"PERPETUA_TOOLS_ROOT": str(pt_root)}
        # Explicitly unset PERPETUA_TOOLS_PATH
        env_copy = os.environ.copy()
        env_copy.pop("PERPETUA_TOOLS_PATH", None)
        env_copy.update(env)
        result = _bash(_PT_DISCOVERY_HARNESS, env=env_copy)
        assert result.returncode == 0
        assert f"PT_INSTALL={pt_root}/install.sh" in result.stdout

    # ── OPENCLAW_HOME fallback ───────────────────────────────────────────────

    def test_openclaw_home_perpetua_tools_used_as_last_resort(self, tmp_path):
        openclaw = tmp_path / "openclaw-v1"
        pt_dir = openclaw / "Perpetua-Tools"
        _make_fake_install_sh(pt_dir)
        result = _run_discovery({
            "PERPETUA_TOOLS_PATH": "",
            "PERPETUA_TOOLS_ROOT": "",
            "OPENCLAW_HOME": str(openclaw),
        })
        assert result.returncode == 0
        assert f"PT_INSTALL={pt_dir}/install.sh" in result.stdout

    def test_openclaw_home_defaults_to_home_openclaw_v1(self, tmp_path):
        """When OPENCLAW_HOME is unset, falls back to $HOME/openclaw-v1."""
        openclaw = tmp_path / "openclaw-v1"
        pt_dir = openclaw / "Perpetua-Tools"
        _make_fake_install_sh(pt_dir)
        env_copy = os.environ.copy()
        env_copy.pop("OPENCLAW_HOME", None)
        env_copy.pop("PERPETUA_TOOLS_PATH", None)
        env_copy.pop("PERPETUA_TOOLS_ROOT", None)
        env_copy["HOME"] = str(tmp_path)
        result = _bash(_PT_DISCOVERY_HARNESS, env=env_copy)
        assert result.returncode == 0
        assert f"PT_INSTALL={pt_dir}/install.sh" in result.stdout

    # ── Priority: PATH > ROOT > OPENCLAW_HOME ───────────────────────────────

    def test_perpetua_tools_path_wins_over_root(self, tmp_path):
        pt_path_dir = tmp_path / "from-path"
        pt_root_dir = tmp_path / "from-root"
        _make_fake_install_sh(pt_path_dir)
        _make_fake_install_sh(pt_root_dir)
        result = _run_discovery({
            "PERPETUA_TOOLS_PATH": str(pt_path_dir),
            "PERPETUA_TOOLS_ROOT": str(pt_root_dir),
        })
        assert result.returncode == 0
        assert f"PT_INSTALL={pt_path_dir}/install.sh" in result.stdout
        assert str(pt_root_dir) not in result.stdout.split("PT_INSTALL=", 1)[1]

    def test_perpetua_tools_path_wins_over_openclaw_home(self, tmp_path):
        pt_path_dir = tmp_path / "from-path"
        openclaw = tmp_path / "openclaw-v1"
        pt_oc_dir = openclaw / "Perpetua-Tools"
        _make_fake_install_sh(pt_path_dir)
        _make_fake_install_sh(pt_oc_dir)
        result = _run_discovery({
            "PERPETUA_TOOLS_PATH": str(pt_path_dir),
            "PERPETUA_TOOLS_ROOT": "",
            "OPENCLAW_HOME": str(openclaw),
        })
        assert result.returncode == 0
        assert f"PT_INSTALL={pt_path_dir}/install.sh" in result.stdout

    def test_perpetua_tools_root_wins_over_openclaw_home(self, tmp_path):
        pt_root_dir = tmp_path / "from-root"
        openclaw = tmp_path / "openclaw-v1"
        pt_oc_dir = openclaw / "Perpetua-Tools"
        _make_fake_install_sh(pt_root_dir)
        _make_fake_install_sh(pt_oc_dir)
        result = _run_discovery({
            "PERPETUA_TOOLS_PATH": "",
            "PERPETUA_TOOLS_ROOT": str(pt_root_dir),
            "OPENCLAW_HOME": str(openclaw),
        })
        assert result.returncode == 0
        assert f"PT_INSTALL={pt_root_dir}/install.sh" in result.stdout

    # ── No candidate found ───────────────────────────────────────────────────

    def test_no_candidate_found_pt_install_stays_empty(self, tmp_path):
        """When no candidate has install.sh, PT_INSTALL is empty and nothing runs."""
        env_copy = os.environ.copy()
        env_copy.pop("PERPETUA_TOOLS_PATH", None)
        env_copy.pop("PERPETUA_TOOLS_ROOT", None)
        env_copy.pop("OPENCLAW_HOME", None)
        env_copy["HOME"] = str(tmp_path)   # no openclaw-v1 directory created
        result = _bash(_PT_DISCOVERY_HARNESS, env=env_copy)
        assert result.returncode == 0
        line = next(l for l in result.stdout.splitlines() if l.startswith("PT_INSTALL="))
        assert line == "PT_INSTALL="
        # INFO line must NOT appear (no invocation)
        assert "INFO:" not in result.stdout

    def test_all_candidates_set_but_none_have_install_sh(self, tmp_path):
        """Directories exist but lack install.sh — PT_INSTALL stays empty."""
        pt_path = tmp_path / "pt-path-no-file"
        pt_root = tmp_path / "pt-root-no-file"
        openclaw = tmp_path / "openclaw-v1"
        pt_oc = openclaw / "Perpetua-Tools"
        for d in (pt_path, pt_root, pt_oc):
            d.mkdir(parents=True)
        result = _run_discovery({
            "PERPETUA_TOOLS_PATH": str(pt_path),
            "PERPETUA_TOOLS_ROOT": str(pt_root),
            "OPENCLAW_HOME": str(openclaw),
        })
        assert result.returncode == 0
        line = next(l for l in result.stdout.splitlines() if l.startswith("PT_INSTALL="))
        assert line == "PT_INSTALL="

    # ── Invocation behaviour ─────────────────────────────────────────────────

    def test_install_sh_invoked_with_skip_desktop_flag(self, tmp_path):
        """The discovered install.sh must be called with --skip-desktop."""
        pt_dir = tmp_path / "pt"
        _make_fake_install_sh(pt_dir, exit_code=0)
        _run_discovery({"PERPETUA_TOOLS_PATH": str(pt_dir)})
        sentinel = pt_dir / "called.txt"
        assert sentinel.exists(), "install.sh was not invoked"
        args = sentinel.read_text().strip()
        assert "--skip-desktop" in args

    def test_info_message_printed_on_invocation(self, tmp_path):
        """An info message is printed when PT_INSTALL is found."""
        pt_dir = tmp_path / "pt"
        _make_fake_install_sh(pt_dir)
        result = _run_discovery({"PERPETUA_TOOLS_PATH": str(pt_dir)})
        assert result.returncode == 0
        assert "INFO:" in result.stdout or "Perpetua-Tools MCPB" in result.stdout

    # ── Failure handling ─────────────────────────────────────────────────────

    def test_failed_install_sh_does_not_abort_caller(self, tmp_path):
        """If PT_INSTALL exits nonzero, the discovery block does NOT exit 1."""
        pt_dir = tmp_path / "pt-fail"
        _make_fake_install_sh(pt_dir, exit_code=1)
        result = _run_discovery({"PERPETUA_TOOLS_PATH": str(pt_dir)})
        # The harness itself should still exit 0 (failure is warn-only)
        assert result.returncode == 0

    def test_failed_install_sh_emits_warning(self, tmp_path):
        """A warning is emitted to stderr when PT_INSTALL fails."""
        pt_dir = tmp_path / "pt-fail"
        # The harness redirects PT_INSTALL stderr to /dev/null but our warn()
        # writes to stderr directly.  Use exit_code=1 to trigger the warn path.
        _make_fake_install_sh(pt_dir, exit_code=1)
        result = _run_discovery({"PERPETUA_TOOLS_PATH": str(pt_dir)})
        # warn() writes to stderr in the harness
        assert "WARN:" in result.stderr or "skipped" in result.stderr.lower()

    # ── Empty-string candidate guard ─────────────────────────────────────────

    def test_empty_perpetua_tools_path_is_skipped(self, tmp_path):
        """An empty PERPETUA_TOOLS_PATH must not produce a false positive."""
        # If the empty string were accepted as a candidate, [[ -f "/install.sh" ]]
        # might spuriously match on some systems.  Verify it is always skipped.
        openclaw = tmp_path / "openclaw-v1"
        # Ensure no fallback install.sh exists either
        result = _run_discovery({
            "PERPETUA_TOOLS_PATH": "",
            "PERPETUA_TOOLS_ROOT": "",
            "HOME": str(tmp_path),
        })
        assert result.returncode == 0
        line = next(l for l in result.stdout.splitlines() if l.startswith("PT_INSTALL="))
        assert line == "PT_INSTALL="

    # ── Regression: only first matching candidate is used ───────────────────

    def test_loop_breaks_after_first_match(self, tmp_path):
        """The loop must break after the first match; subsequent candidates ignored."""
        pt_path_dir = tmp_path / "first"
        pt_root_dir = tmp_path / "second"
        _make_fake_install_sh(pt_path_dir)
        _make_fake_install_sh(pt_root_dir)
        _run_discovery({
            "PERPETUA_TOOLS_PATH": str(pt_path_dir),
            "PERPETUA_TOOLS_ROOT": str(pt_root_dir),
        })
        # Only first sentinel should be written
        first_sentinel = pt_path_dir / "called.txt"
        second_sentinel = pt_root_dir / "called.txt"
        assert first_sentinel.exists()
        assert not second_sentinel.exists()


# ===========================================================================
# Tests: scripts/cursor/cloud-install.sh — Perpetua-Tools conditional block
# ===========================================================================

class TestCloudInstallPerpetuaToolsBlock:
    """Tests for the Perpetua-Tools conditional block added to cloud-install.sh."""

    # ── File-present branch ──────────────────────────────────────────────────

    def test_install_sh_invoked_when_file_exists(self, tmp_path):
        openclaw = tmp_path / "openclaw-v1"
        pt_dir = openclaw / "Perpetua-Tools"
        _make_fake_install_sh(pt_dir, exit_code=0)
        result = _run_cloud_block({"OPENCLAW_HOME": str(openclaw)})
        assert result.returncode == 0
        sentinel = pt_dir / "called.txt"
        assert sentinel.exists(), "Perpetua-Tools/install.sh was not invoked"

    def test_install_sh_invoked_with_skip_desktop_flag(self, tmp_path):
        openclaw = tmp_path / "openclaw-v1"
        pt_dir = openclaw / "Perpetua-Tools"
        _make_fake_install_sh(pt_dir, exit_code=0)
        _run_cloud_block({"OPENCLAW_HOME": str(openclaw)})
        sentinel = pt_dir / "called.txt"
        assert sentinel.exists()
        args = sentinel.read_text().strip()
        assert "--skip-desktop" in args

    def test_log_message_printed_on_invocation(self, tmp_path):
        openclaw = tmp_path / "openclaw-v1"
        pt_dir = openclaw / "Perpetua-Tools"
        _make_fake_install_sh(pt_dir)
        result = _run_cloud_block({"OPENCLAW_HOME": str(openclaw)})
        assert result.returncode == 0
        assert "Perpetua-Tools install.sh" in result.stdout or \
               "MCPB build" in result.stdout

    # ── File-absent branch ───────────────────────────────────────────────────

    def test_block_skipped_when_install_sh_absent(self, tmp_path):
        openclaw = tmp_path / "openclaw-v1"
        pt_dir = openclaw / "Perpetua-Tools"
        pt_dir.mkdir(parents=True)   # directory exists but no install.sh
        result = _run_cloud_block({"OPENCLAW_HOME": str(openclaw)})
        assert result.returncode == 0
        sentinel = pt_dir / "called.txt"
        assert not sentinel.exists(), "install.sh should not have been invoked"
        assert "BLOCK_DONE" in result.stdout

    def test_block_skipped_when_perpetua_tools_dir_absent(self, tmp_path):
        openclaw = tmp_path / "openclaw-v1"
        openclaw.mkdir(parents=True)  # no Perpetua-Tools subdir at all
        result = _run_cloud_block({"OPENCLAW_HOME": str(openclaw)})
        assert result.returncode == 0
        assert "BLOCK_DONE" in result.stdout

    def test_block_skipped_when_openclaw_home_dir_absent(self, tmp_path):
        missing = tmp_path / "does-not-exist"
        result = _run_cloud_block({"OPENCLAW_HOME": str(missing)})
        assert result.returncode == 0
        assert "BLOCK_DONE" in result.stdout

    # ── Failure handling ─────────────────────────────────────────────────────

    def test_failed_install_sh_does_not_abort_block(self, tmp_path):
        """A nonzero exit from install.sh must not propagate to the block."""
        openclaw = tmp_path / "openclaw-v1"
        pt_dir = openclaw / "Perpetua-Tools"
        _make_fake_install_sh(pt_dir, exit_code=1)
        result = _run_cloud_block({"OPENCLAW_HOME": str(openclaw)})
        assert result.returncode == 0
        assert "BLOCK_DONE" in result.stdout

    def test_failed_install_sh_emits_warning(self, tmp_path):
        openclaw = tmp_path / "openclaw-v1"
        pt_dir = openclaw / "Perpetua-Tools"
        _make_fake_install_sh(pt_dir, exit_code=1)
        result = _run_cloud_block({"OPENCLAW_HOME": str(openclaw)})
        assert "WARN:" in result.stderr or "skipped" in result.stderr.lower()

    # ── Regression: install.sh path must come from OPENCLAW_HOME ────────────

    def test_correct_path_used_for_install_sh_check(self, tmp_path):
        """Block checks the path derived from OPENCLAW_HOME, not a hardcoded path."""
        openclaw_a = tmp_path / "openclaw-a"
        openclaw_b = tmp_path / "openclaw-b"
        pt_a = openclaw_a / "Perpetua-Tools"
        pt_b = openclaw_b / "Perpetua-Tools"
        # Only B has an install.sh
        pt_a.mkdir(parents=True)
        _make_fake_install_sh(pt_b)

        result_a = _run_cloud_block({"OPENCLAW_HOME": str(openclaw_a)})
        result_b = _run_cloud_block({"OPENCLAW_HOME": str(openclaw_b)})

        assert not (pt_a / "called.txt").exists(), \
            "install.sh in openclaw_a should not be invoked"
        assert (pt_b / "called.txt").exists(), \
            "install.sh in openclaw_b should be invoked"
        assert result_a.returncode == 0
        assert result_b.returncode == 0


# ===========================================================================
# Tests: bash syntax validity for both changed scripts
# ===========================================================================

class TestChangedScriptSyntax:
    """Verify that the two changed shell scripts remain syntactically valid bash."""

    @pytest.mark.parametrize("script_path", [
        "install.sh",
        "scripts/cursor/cloud-install.sh",
    ])
    def test_script_is_valid_bash(self, script_path):
        result = subprocess.run(
            ["bash", "-n", script_path],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"{script_path} has bash syntax errors:\n{result.stderr}"
        )
