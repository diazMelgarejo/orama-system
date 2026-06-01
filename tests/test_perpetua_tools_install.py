#!/usr/bin/env python3
"""Tests for Perpetua-Tools MCPB integration added in the PR.

Covers:
- install.sh: PT_INSTALL candidate detection loop (PERPETUA_TOOLS_PATH,
  PERPETUA_TOOLS_ROOT, OPENCLAW_HOME fallback, $HOME/openclaw-v1 default).
- scripts/cursor/cloud-install.sh: conditional invocation of
  $OPENCLAW_HOME/Perpetua-Tools/install.sh --skip-desktop.
"""
from __future__ import annotations

import os
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


# ---------------------------------------------------------------------------
# Helpers: build isolated bash harnesses
# ---------------------------------------------------------------------------

_PT_DETECTION_HARNESS = textwrap.dedent(r"""
    warn() { echo "WARN: $1" >&2; }
    info() { echo "INFO: $1"; }

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
    echo "PT_INSTALL=$PT_INSTALL"
""").strip()

_PT_INVOCATION_HARNESS = textwrap.dedent(r"""
    warn() { echo "WARN: $1" >&2; }
    info() { echo "INFO: $1"; }

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
""").strip()

_CLOUD_INSTALL_HARNESS = textwrap.dedent(r"""
    warn() { echo "WARN: $1" >&2; }
    log()  { printf '>>> [cloud-install] %s\n' "$*"; }

    if [[ -f "$OPENCLAW_HOME/Perpetua-Tools/install.sh" ]]; then
      log "Perpetua-Tools install.sh (Claude Desktop MCPB build)"
      bash "$OPENCLAW_HOME/Perpetua-Tools/install.sh" --skip-desktop || warn "MCPB build skipped"
    fi
""").strip()


# ===========================================================================
# install.sh — PT_INSTALL candidate detection
# ===========================================================================

class TestPtInstallDetection:
    """Unit tests for the PT_INSTALL candidate detection loop in install.sh."""

    def test_no_candidates_no_install_sh_found(self, tmp_path):
        """When no env vars set and default path has no install.sh, PT_INSTALL is empty."""
        full_env = os.environ.copy()
        full_env["HOME"] = str(tmp_path)
        full_env["PERPETUA_TOOLS_PATH"] = ""
        full_env["PERPETUA_TOOLS_ROOT"] = ""
        # Unset OPENCLAW_HOME so the loop falls back to $HOME/openclaw-v1/Perpetua-Tools
        full_env.pop("OPENCLAW_HOME", None)

        result = subprocess.run(
            ["bash", "-c", _PT_DETECTION_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        # The default path $HOME/openclaw-v1/Perpetua-Tools/install.sh does not exist
        assert result.stdout.strip() == "PT_INSTALL="

    def test_perpetua_tools_path_env_var_takes_priority(self, tmp_path):
        """PERPETUA_TOOLS_PATH is checked first; if install.sh exists there it wins."""
        pt_dir = tmp_path / "pt_via_path"
        pt_dir.mkdir()
        (pt_dir / "install.sh").write_text("#!/usr/bin/env bash\necho ok\n")

        full_env = os.environ.copy()
        full_env["HOME"] = str(tmp_path)
        full_env["PERPETUA_TOOLS_PATH"] = str(pt_dir)
        full_env.pop("PERPETUA_TOOLS_ROOT", None)
        full_env.pop("OPENCLAW_HOME", None)

        result = subprocess.run(
            ["bash", "-c", _PT_DETECTION_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == f"PT_INSTALL={pt_dir}/install.sh"

    def test_perpetua_tools_root_env_var_used_when_path_missing(self, tmp_path):
        """PERPETUA_TOOLS_ROOT is used when PERPETUA_TOOLS_PATH has no install.sh."""
        pt_dir = tmp_path / "pt_via_root"
        pt_dir.mkdir()
        (pt_dir / "install.sh").write_text("#!/usr/bin/env bash\necho ok\n")

        full_env = os.environ.copy()
        full_env["HOME"] = str(tmp_path)
        full_env.pop("PERPETUA_TOOLS_PATH", None)   # not set
        full_env["PERPETUA_TOOLS_ROOT"] = str(pt_dir)
        full_env.pop("OPENCLAW_HOME", None)

        result = subprocess.run(
            ["bash", "-c", _PT_DETECTION_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == f"PT_INSTALL={pt_dir}/install.sh"

    def test_openclaw_home_fallback_path(self, tmp_path):
        """OPENCLAW_HOME/Perpetua-Tools is used when the first two candidates miss."""
        pt_dir = tmp_path / "openclaw" / "Perpetua-Tools"
        pt_dir.mkdir(parents=True)
        (pt_dir / "install.sh").write_text("#!/usr/bin/env bash\necho ok\n")

        full_env = os.environ.copy()
        full_env["HOME"] = str(tmp_path)
        full_env.pop("PERPETUA_TOOLS_PATH", None)
        full_env.pop("PERPETUA_TOOLS_ROOT", None)
        full_env["OPENCLAW_HOME"] = str(tmp_path / "openclaw")

        result = subprocess.run(
            ["bash", "-c", _PT_DETECTION_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == f"PT_INSTALL={pt_dir}/install.sh"

    def test_default_home_openclaw_v1_fallback(self, tmp_path):
        """When OPENCLAW_HOME is unset, falls back to $HOME/openclaw-v1/Perpetua-Tools."""
        pt_dir = tmp_path / "openclaw-v1" / "Perpetua-Tools"
        pt_dir.mkdir(parents=True)
        (pt_dir / "install.sh").write_text("#!/usr/bin/env bash\necho ok\n")

        full_env = os.environ.copy()
        full_env["HOME"] = str(tmp_path)
        full_env.pop("PERPETUA_TOOLS_PATH", None)
        full_env.pop("PERPETUA_TOOLS_ROOT", None)
        full_env.pop("OPENCLAW_HOME", None)

        result = subprocess.run(
            ["bash", "-c", _PT_DETECTION_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == f"PT_INSTALL={pt_dir}/install.sh"

    def test_first_valid_candidate_wins(self, tmp_path):
        """When multiple candidates are valid, the first one (PERPETUA_TOOLS_PATH) wins."""
        path_dir = tmp_path / "via_path"
        path_dir.mkdir()
        (path_dir / "install.sh").write_text("#!/usr/bin/env bash\necho from_path\n")

        root_dir = tmp_path / "via_root"
        root_dir.mkdir()
        (root_dir / "install.sh").write_text("#!/usr/bin/env bash\necho from_root\n")

        full_env = os.environ.copy()
        full_env["HOME"] = str(tmp_path)
        full_env["PERPETUA_TOOLS_PATH"] = str(path_dir)
        full_env["PERPETUA_TOOLS_ROOT"] = str(root_dir)
        full_env.pop("OPENCLAW_HOME", None)

        result = subprocess.run(
            ["bash", "-c", _PT_DETECTION_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == f"PT_INSTALL={path_dir}/install.sh"

    def test_empty_string_candidate_skipped(self, tmp_path):
        """An empty PERPETUA_TOOLS_PATH is treated as unset and skipped by -n check."""
        pt_dir = tmp_path / "via_root"
        pt_dir.mkdir()
        (pt_dir / "install.sh").write_text("#!/usr/bin/env bash\necho ok\n")

        full_env = os.environ.copy()
        full_env["HOME"] = str(tmp_path)
        full_env["PERPETUA_TOOLS_PATH"] = ""   # empty — should be skipped
        full_env["PERPETUA_TOOLS_ROOT"] = str(pt_dir)
        full_env.pop("OPENCLAW_HOME", None)

        result = subprocess.run(
            ["bash", "-c", _PT_DETECTION_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == f"PT_INSTALL={pt_dir}/install.sh"

    def test_candidate_dir_exists_but_no_install_sh(self, tmp_path):
        """A directory without install.sh is not chosen."""
        pt_dir = tmp_path / "pt_no_script"
        pt_dir.mkdir()
        # No install.sh inside pt_dir

        full_env = os.environ.copy()
        full_env["HOME"] = str(tmp_path)
        full_env["PERPETUA_TOOLS_PATH"] = str(pt_dir)
        full_env.pop("PERPETUA_TOOLS_ROOT", None)
        full_env.pop("OPENCLAW_HOME", None)

        result = subprocess.run(
            ["bash", "-c", _PT_DETECTION_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        # install.sh missing → PT_INSTALL stays empty
        assert result.stdout.strip() == "PT_INSTALL="


# ===========================================================================
# install.sh — PT_INSTALL invocation
# ===========================================================================

class TestPtInstallInvocation:
    """Tests for the invocation block that calls PT_INSTALL with --skip-desktop."""

    def test_install_sh_invoked_with_skip_desktop_flag(self, tmp_path):
        """When PT_INSTALL found, bash is called with --skip-desktop."""
        pt_dir = tmp_path / "pt"
        pt_dir.mkdir()
        install_sh = pt_dir / "install.sh"
        # Script records the args it received
        install_sh.write_text(
            "#!/usr/bin/env bash\necho \"ARGS=$*\" > "
            + str(tmp_path / "invocation.txt") + "\n"
        )
        install_sh.chmod(0o755)

        full_env = os.environ.copy()
        full_env["HOME"] = str(tmp_path)
        full_env["PERPETUA_TOOLS_PATH"] = str(pt_dir)
        full_env.pop("PERPETUA_TOOLS_ROOT", None)
        full_env.pop("OPENCLAW_HOME", None)

        result = subprocess.run(
            ["bash", "-c", _PT_INVOCATION_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        recorded = (tmp_path / "invocation.txt").read_text()
        assert "ARGS=--skip-desktop" in recorded

    def test_info_message_printed_when_invoked(self, tmp_path):
        """An info message is printed when the MCPB install is triggered."""
        pt_dir = tmp_path / "pt"
        pt_dir.mkdir()
        (pt_dir / "install.sh").write_text("#!/usr/bin/env bash\nexit 0\n")

        full_env = os.environ.copy()
        full_env["HOME"] = str(tmp_path)
        full_env["PERPETUA_TOOLS_PATH"] = str(pt_dir)
        full_env.pop("PERPETUA_TOOLS_ROOT", None)
        full_env.pop("OPENCLAW_HOME", None)

        result = subprocess.run(
            ["bash", "-c", _PT_INVOCATION_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        assert "Perpetua-Tools MCPB" in result.stdout

    def test_no_invocation_when_no_install_sh_found(self, tmp_path):
        """Nothing is invoked when no valid candidate exists."""
        full_env = os.environ.copy()
        full_env["HOME"] = str(tmp_path)
        full_env.pop("PERPETUA_TOOLS_PATH", None)
        full_env.pop("PERPETUA_TOOLS_ROOT", None)
        full_env.pop("OPENCLAW_HOME", None)

        result = subprocess.run(
            ["bash", "-c", _PT_INVOCATION_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        # No info message should appear
        assert "Perpetua-Tools MCPB" not in result.stdout

    def test_warn_on_install_sh_failure_does_not_abort(self, tmp_path):
        """A failing install.sh emits a warn message but the outer script continues (exit 0)."""
        pt_dir = tmp_path / "pt"
        pt_dir.mkdir()
        (pt_dir / "install.sh").write_text("#!/usr/bin/env bash\nexit 1\n")

        full_env = os.environ.copy()
        full_env["HOME"] = str(tmp_path)
        full_env["PERPETUA_TOOLS_PATH"] = str(pt_dir)
        full_env.pop("PERPETUA_TOOLS_ROOT", None)
        full_env.pop("OPENCLAW_HOME", None)

        result = subprocess.run(
            ["bash", "-c", _PT_INVOCATION_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        # The harness must exit 0 even when install.sh exits 1
        assert result.returncode == 0
        assert "WARN" in result.stderr

    def test_warn_message_references_perpetua_tools(self, tmp_path):
        """The warn message on failure references Perpetua-Tools/install.sh."""
        pt_dir = tmp_path / "pt"
        pt_dir.mkdir()
        (pt_dir / "install.sh").write_text("#!/usr/bin/env bash\nexit 1\n")

        full_env = os.environ.copy()
        full_env["HOME"] = str(tmp_path)
        full_env["PERPETUA_TOOLS_PATH"] = str(pt_dir)
        full_env.pop("PERPETUA_TOOLS_ROOT", None)
        full_env.pop("OPENCLAW_HOME", None)

        result = subprocess.run(
            ["bash", "-c", _PT_INVOCATION_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert "Perpetua-Tools" in result.stderr

    def test_stderr_suppressed_for_install_sh_output(self, tmp_path):
        """install.sh stderr is suppressed (2>/dev/null) — only our warn goes to stderr."""
        pt_dir = tmp_path / "pt"
        pt_dir.mkdir()
        (pt_dir / "install.sh").write_text(
            "#!/usr/bin/env bash\necho 'LEAKED_STDERR' >&2\nexit 1\n"
        )

        full_env = os.environ.copy()
        full_env["HOME"] = str(tmp_path)
        full_env["PERPETUA_TOOLS_PATH"] = str(pt_dir)
        full_env.pop("PERPETUA_TOOLS_ROOT", None)
        full_env.pop("OPENCLAW_HOME", None)

        result = subprocess.run(
            ["bash", "-c", _PT_INVOCATION_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        # Inner script's stderr must be suppressed
        assert "LEAKED_STDERR" not in result.stderr


# ===========================================================================
# scripts/cursor/cloud-install.sh — conditional MCPB invocation
# ===========================================================================

class TestCloudInstallPerpetualToolsBlock:
    """Tests for the Perpetua-Tools conditional block added to cloud-install.sh."""

    def test_install_sh_invoked_when_file_exists(self, tmp_path):
        """When $OPENCLAW_HOME/Perpetua-Tools/install.sh exists, it is invoked."""
        pt_dir = tmp_path / "openclaw" / "Perpetua-Tools"
        pt_dir.mkdir(parents=True)
        install_sh = pt_dir / "install.sh"
        install_sh.write_text(
            "#!/usr/bin/env bash\necho \"INVOKED_ARGS=$*\" > "
            + str(tmp_path / "cloud_invocation.txt") + "\n"
        )
        install_sh.chmod(0o755)

        full_env = os.environ.copy()
        full_env["OPENCLAW_HOME"] = str(tmp_path / "openclaw")

        result = subprocess.run(
            ["bash", "-c", _CLOUD_INSTALL_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        recorded = (tmp_path / "cloud_invocation.txt").read_text()
        assert "INVOKED_ARGS=--skip-desktop" in recorded

    def test_log_message_printed_before_invocation(self, tmp_path):
        """A log message is emitted when the Perpetua-Tools install.sh is found."""
        pt_dir = tmp_path / "openclaw" / "Perpetua-Tools"
        pt_dir.mkdir(parents=True)
        (pt_dir / "install.sh").write_text("#!/usr/bin/env bash\nexit 0\n")

        full_env = os.environ.copy()
        full_env["OPENCLAW_HOME"] = str(tmp_path / "openclaw")

        result = subprocess.run(
            ["bash", "-c", _CLOUD_INSTALL_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        assert "Perpetua-Tools install.sh" in result.stdout
        assert "MCPB" in result.stdout

    def test_block_skipped_when_install_sh_absent(self, tmp_path):
        """When install.sh is absent, the block is skipped entirely."""
        pt_dir = tmp_path / "openclaw" / "Perpetua-Tools"
        pt_dir.mkdir(parents=True)
        # No install.sh created

        full_env = os.environ.copy()
        full_env["OPENCLAW_HOME"] = str(tmp_path / "openclaw")

        result = subprocess.run(
            ["bash", "-c", _CLOUD_INSTALL_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        assert "Perpetua-Tools" not in result.stdout
        assert "WARN" not in result.stderr

    def test_block_skipped_when_perpetua_tools_dir_absent(self, tmp_path):
        """When the Perpetua-Tools directory itself does not exist, block is skipped."""
        full_env = os.environ.copy()
        full_env["OPENCLAW_HOME"] = str(tmp_path / "openclaw")
        # $OPENCLAW_HOME/Perpetua-Tools does not exist at all

        result = subprocess.run(
            ["bash", "-c", _CLOUD_INSTALL_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        assert "Perpetua-Tools" not in result.stdout

    def test_warn_on_failure_continues_execution(self, tmp_path):
        """A failing install.sh triggers warn but cloud-install continues (exit 0)."""
        pt_dir = tmp_path / "openclaw" / "Perpetua-Tools"
        pt_dir.mkdir(parents=True)
        (pt_dir / "install.sh").write_text("#!/usr/bin/env bash\nexit 1\n")

        full_env = os.environ.copy()
        full_env["OPENCLAW_HOME"] = str(tmp_path / "openclaw")

        result = subprocess.run(
            ["bash", "-c", _CLOUD_INSTALL_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        assert "WARN" in result.stderr

    def test_warn_message_says_mcpb_build_skipped(self, tmp_path):
        """The warn message on failure says 'MCPB build skipped'."""
        pt_dir = tmp_path / "openclaw" / "Perpetua-Tools"
        pt_dir.mkdir(parents=True)
        (pt_dir / "install.sh").write_text("#!/usr/bin/env bash\nexit 1\n")

        full_env = os.environ.copy()
        full_env["OPENCLAW_HOME"] = str(tmp_path / "openclaw")

        result = subprocess.run(
            ["bash", "-c", _CLOUD_INSTALL_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert "MCPB build skipped" in result.stderr

    def test_install_sh_passed_skip_desktop_flag(self, tmp_path):
        """The --skip-desktop flag is passed to install.sh."""
        pt_dir = tmp_path / "openclaw" / "Perpetua-Tools"
        pt_dir.mkdir(parents=True)
        flag_file = tmp_path / "flag.txt"
        install_sh = pt_dir / "install.sh"
        install_sh.write_text(
            f"#!/usr/bin/env bash\nfor a in \"$@\"; do echo \"ARG=$a\" >> {flag_file}; done\n"
        )
        install_sh.chmod(0o755)

        full_env = os.environ.copy()
        full_env["OPENCLAW_HOME"] = str(tmp_path / "openclaw")

        result = subprocess.run(
            ["bash", "-c", _CLOUD_INSTALL_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        recorded = flag_file.read_text()
        assert "ARG=--skip-desktop" in recorded

    def test_cloud_install_harness_uses_openclaw_home_exactly(self, tmp_path):
        """The install.sh path is derived directly from $OPENCLAW_HOME, not a default."""
        # Use a non-default OPENCLAW_HOME to verify no hardcoded path is used
        custom_home = tmp_path / "custom_openclaw"
        pt_dir = custom_home / "Perpetua-Tools"
        pt_dir.mkdir(parents=True)
        marker = tmp_path / "ran.txt"
        install_sh = pt_dir / "install.sh"
        install_sh.write_text(f"#!/usr/bin/env bash\ntouch {marker}\n")
        install_sh.chmod(0o755)

        full_env = os.environ.copy()
        full_env["OPENCLAW_HOME"] = str(custom_home)

        result = subprocess.run(
            ["bash", "-c", _CLOUD_INSTALL_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        assert marker.exists(), "install.sh was not invoked from custom OPENCLAW_HOME"


# ===========================================================================
# Regression / boundary tests
# ===========================================================================

class TestPerpetualToolsRegressions:
    """Extra regression and boundary tests."""

    def test_install_sh_path_with_spaces_not_used_in_detection(self, tmp_path):
        """A path with spaces is still correctly detected by -f test."""
        pt_dir = tmp_path / "my tools" / "Perpetua Tools"
        pt_dir.mkdir(parents=True)
        (pt_dir / "install.sh").write_text("#!/usr/bin/env bash\necho ok\n")

        full_env = os.environ.copy()
        full_env["HOME"] = str(tmp_path)
        full_env["PERPETUA_TOOLS_PATH"] = str(pt_dir)
        full_env.pop("PERPETUA_TOOLS_ROOT", None)
        full_env.pop("OPENCLAW_HOME", None)

        result = subprocess.run(
            ["bash", "-c", _PT_DETECTION_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        assert "install.sh" in result.stdout
        assert "PT_INSTALL=" in result.stdout
        # Should not be empty
        assert result.stdout.strip() != "PT_INSTALL="

    def test_detection_loop_does_not_set_pt_install_to_directory(self, tmp_path):
        """PT_INSTALL must point to a file, not a directory named install.sh."""
        pt_dir = tmp_path / "pt"
        pt_dir.mkdir()
        # Create a directory called install.sh instead of a file
        install_dir = pt_dir / "install.sh"
        install_dir.mkdir()

        full_env = os.environ.copy()
        full_env["HOME"] = str(tmp_path)
        full_env["PERPETUA_TOOLS_PATH"] = str(pt_dir)
        full_env.pop("PERPETUA_TOOLS_ROOT", None)
        full_env.pop("OPENCLAW_HOME", None)

        result = subprocess.run(
            ["bash", "-c", _PT_DETECTION_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        # A directory should fail the -f test → PT_INSTALL remains empty
        assert result.stdout.strip() == "PT_INSTALL="

    def test_perpetua_tools_root_fallback_when_path_dir_missing_install(self, tmp_path):
        """When PERPETUA_TOOLS_PATH dir exists but lacks install.sh, fall through to ROOT."""
        path_dir = tmp_path / "via_path"
        path_dir.mkdir()
        # No install.sh in path_dir

        root_dir = tmp_path / "via_root"
        root_dir.mkdir()
        (root_dir / "install.sh").write_text("#!/usr/bin/env bash\nexit 0\n")

        full_env = os.environ.copy()
        full_env["HOME"] = str(tmp_path)
        full_env["PERPETUA_TOOLS_PATH"] = str(path_dir)
        full_env["PERPETUA_TOOLS_ROOT"] = str(root_dir)
        full_env.pop("OPENCLAW_HOME", None)

        result = subprocess.run(
            ["bash", "-c", _PT_DETECTION_HARNESS],
            capture_output=True, text=True, env=full_env,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == f"PT_INSTALL={root_dir}/install.sh"
