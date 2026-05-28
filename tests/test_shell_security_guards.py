#!/usr/bin/env python3
"""Tests for shell security guards introduced in the PR:

- _safe_path() in bin/orama-system/scripts/install-mcp-stack.sh
- _safe_path() in bin/orama-system/scripts/first-run-install.sh
- SLUG validation in scripts/worktree-bootstrap.sh
- ALLOWED_HOSTS default in .env.example
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _bash(script: str, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run a bash snippet and return the CompletedProcess."""
    import os
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
# Bash harness builders
# ---------------------------------------------------------------------------

def _mcp_safe_path_harness(path_arg: str) -> str:
    """
    Build a bash snippet that defines the _safe_path function exactly as it
    appears in install-mcp-stack.sh, with a stub _fail that exits 1, then
    calls _safe_path with the given path argument.
    """
    # Use printf %s to safely pass arbitrary test values without shell injection
    return r"""
_fail()  { echo "[mcp-install] ✗ FATAL: $*" >&2; exit 1; }

_safe_path() {
  local p="$1"
  case "$p" in
    -*) _fail "_safe_path: path may not start with dash: $p" ;;
    *[$'\t\n\$\`\;\&\|\<\>\(\)\{\}\*\?\[\]\\\'\"']*)
      _fail "_safe_path: path contains shell metacharacters: $p" ;;
  esac
}

_safe_path "$TEST_PATH"
""".strip()


def _first_run_safe_path_harness() -> str:
    """
    Build a bash snippet that defines the _safe_path function exactly as it
    appears in first-run-install.sh (explicit exit 1 after _fail), with a
    stub _fail that just prints (does NOT exit), then calls _safe_path with
    the env var TEST_PATH.
    """
    return r"""
_fail()  { echo "[first-run] ✗ $*" >&2; }

_safe_path() {
  local p="$1"
  case "$p" in
    -*) _fail "_safe_path: path may not start with dash: $p"; exit 1 ;;
    *[$'\t\n\$\`\;\&\|\<\>\(\)\{\}\*\?\[\]\\\'\"']*)
      _fail "_safe_path: path contains shell metacharacters: $p"; exit 1 ;;
  esac
}

_safe_path "$TEST_PATH"
""".strip()


def _slug_validation_harness() -> str:
    """
    Bash snippet that replicates exactly the SLUG validation logic from
    scripts/worktree-bootstrap.sh. Reads SLUG from the env var SLUG.
    """
    return r"""
SLUG="$TEST_SLUG"

if [[ ! "$SLUG" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "ERROR: slug must match [A-Za-z0-9._-]+ (got: $SLUG)" >&2
  exit 1
fi
case "$SLUG" in
  -*|.|..) echo "ERROR: slug may not start with '-' or be '.'/'..' (got: $SLUG)" >&2; exit 1 ;;
esac

echo "OK"
""".strip()


# ---------------------------------------------------------------------------
# Helper: run safe_path with a specific path and script variant
# ---------------------------------------------------------------------------

def _run_mcp_safe_path(path: str) -> subprocess.CompletedProcess:
    return _bash(_mcp_safe_path_harness(path), env={"TEST_PATH": path})


def _run_first_run_safe_path(path: str) -> subprocess.CompletedProcess:
    return _bash(_first_run_safe_path_harness(), env={"TEST_PATH": path})


def _run_slug_validation(slug: str) -> subprocess.CompletedProcess:
    return _bash(_slug_validation_harness(), env={"TEST_SLUG": slug})


# ===========================================================================
# Tests: _safe_path() in install-mcp-stack.sh
# ===========================================================================

class TestMcpSafePath:
    """Tests for _safe_path() as defined in install-mcp-stack.sh."""

    # ── Acceptance cases ────────────────────────────────────────────────────

    def test_simple_absolute_path_accepted(self):
        result = _run_mcp_safe_path("/home/user/.claude/skills")
        assert result.returncode == 0

    def test_simple_relative_path_accepted(self):
        result = _run_mcp_safe_path("skills/orama-system")
        assert result.returncode == 0

    def test_path_with_dashes_accepted(self):
        result = _run_mcp_safe_path("/opt/orama-system/bin")
        assert result.returncode == 0

    def test_path_with_dots_accepted(self):
        result = _run_mcp_safe_path("/home/user/.claude/skills/SKILL.md")
        assert result.returncode == 0

    def test_path_with_underscores_accepted(self):
        result = _run_mcp_safe_path("/home/user/my_skills/orama")
        assert result.returncode == 0

    def test_path_with_numbers_accepted(self):
        result = _run_mcp_safe_path("/var/run/orama123/v2")
        assert result.returncode == 0

    def test_home_tilde_expanded_path_accepted(self):
        # Tilde is already expanded by the caller; we test the expanded form.
        # Use /Users/user/ — a hygiene-scanner-approved generic placeholder.
        result = _run_mcp_safe_path("/Users/user/.codex/skills/orama")
        assert result.returncode == 0

    # ── Leading-dash rejection ───────────────────────────────────────────────

    def test_leading_dash_rejected(self):
        result = _run_mcp_safe_path("-evil")
        assert result.returncode != 0

    def test_leading_dash_with_flag_like_string_rejected(self):
        result = _run_mcp_safe_path("--force")
        assert result.returncode != 0

    def test_leading_dash_in_absolute_path_is_actually_safe(self):
        # A path like /some/-dir does NOT start with dash (it starts with /).
        result = _run_mcp_safe_path("/some/-dir")
        assert result.returncode == 0

    def test_leading_dash_error_message(self):
        result = _run_mcp_safe_path("-bad-path")
        assert result.returncode != 0
        assert "dash" in result.stderr.lower() or "start" in result.stderr.lower()

    # ── Shell metacharacter rejection ────────────────────────────────────────

    @pytest.mark.parametrize("char,description", [
        ("\t", "tab"),
        ("\n", "newline"),
        (";", "semicolon"),
        ("&", "ampersand"),
        ("|", "pipe"),
        ("<", "less-than"),
        (">", "greater-than"),
        ("(", "open-paren"),
        (")", "close-paren"),
        ("{", "open-brace"),
        ("}", "close-brace"),
        ("*", "glob-star"),
        ("?", "glob-question"),
        ("[", "open-bracket"),
        ("]", "close-bracket"),
        ("\\", "backslash"),
        ("'", "single-quote"),
        ('"', "double-quote"),
        ("`", "backtick"),
    ])
    def test_metachar_in_middle_of_path_rejected(self, char, description):
        path = f"/home/user{char}evil"
        result = _run_mcp_safe_path(path)
        assert result.returncode != 0, (
            f"Expected rejection for path containing {description!r}"
        )

    def test_dollar_sign_in_path_rejected(self):
        # $ is a common injection vector (variable expansion).
        result = _run_mcp_safe_path("/home/$USER/skills")
        assert result.returncode != 0

    def test_command_substitution_pattern_rejected(self):
        # $(cmd) form
        result = _run_mcp_safe_path("/tmp/$(id)/evil")
        assert result.returncode != 0

    def test_semicolon_command_chain_rejected(self):
        result = _run_mcp_safe_path("/tmp/legit; rm -rf /")
        assert result.returncode != 0

    def test_pipe_injection_rejected(self):
        result = _run_mcp_safe_path("/tmp/legit|cat /etc/passwd")
        assert result.returncode != 0

    def test_metachar_error_message_mentions_metacharacters(self):
        result = _run_mcp_safe_path("/tmp/path;inject")
        assert result.returncode != 0
        assert "metachar" in result.stderr.lower() or "shell" in result.stderr.lower()

    # ── Boundary / regression cases ─────────────────────────────────────────

    def test_empty_path_accepted(self):
        # Empty string contains no metacharacters and does not start with dash.
        result = _run_mcp_safe_path("")
        assert result.returncode == 0

    def test_single_slash_accepted(self):
        result = _run_mcp_safe_path("/")
        assert result.returncode == 0

    def test_double_dot_path_accepted(self):
        # ".." is a valid path component and contains no metacharacters.
        result = _run_mcp_safe_path("..")
        assert result.returncode == 0

    def test_space_in_path_accepted_by_safe_path(self):
        # _safe_path's character class does NOT include space; spaces are
        # handled by quoting at the call site per the inline comment.
        result = _run_mcp_safe_path("/home/user/my skills")
        assert result.returncode == 0


# ===========================================================================
# Tests: _safe_path() in first-run-install.sh
# ===========================================================================

class TestFirstRunSafePath:
    """
    Tests for _safe_path() as defined in first-run-install.sh.
    The only implementation difference from the mcp variant is that
    first-run calls `exit 1` explicitly after `_fail` (because _fail in
    first-run-install.sh does NOT call exit itself).
    """

    def test_normal_path_accepted(self):
        result = _run_first_run_safe_path("/home/user/.orama-system/skills")
        assert result.returncode == 0

    def test_leading_dash_rejected(self):
        result = _run_first_run_safe_path("-bad")
        assert result.returncode != 0

    def test_leading_dash_exits_nonzero(self):
        result = _run_first_run_safe_path("-n")
        assert result.returncode == 1

    def test_dollar_sign_rejected(self):
        result = _run_first_run_safe_path("/tmp/$HOME")
        assert result.returncode != 0

    def test_backtick_rejected(self):
        result = _run_first_run_safe_path("/tmp/`id`")
        assert result.returncode != 0

    def test_semicolon_rejected(self):
        result = _run_first_run_safe_path("/tmp/dir;evil")
        assert result.returncode != 0

    def test_pipe_rejected(self):
        result = _run_first_run_safe_path("/tmp/dir|evil")
        assert result.returncode != 0

    def test_newline_in_path_rejected(self):
        result = _run_first_run_safe_path("/tmp/dir\nevil")
        assert result.returncode != 0

    def test_tab_in_path_rejected(self):
        result = _run_first_run_safe_path("/tmp/dir\tevil")
        assert result.returncode != 0

    def test_glob_star_rejected(self):
        result = _run_first_run_safe_path("/tmp/dir*")
        assert result.returncode != 0

    def test_glob_question_rejected(self):
        result = _run_first_run_safe_path("/tmp/dir?")
        assert result.returncode != 0

    def test_bracket_rejected(self):
        result = _run_first_run_safe_path("/tmp/dir[0]")
        assert result.returncode != 0

    def test_backslash_rejected(self):
        result = _run_first_run_safe_path("/tmp/dir\\evil")
        assert result.returncode != 0

    def test_single_quote_rejected(self):
        result = _run_first_run_safe_path("/tmp/dir'evil")
        assert result.returncode != 0

    def test_double_quote_rejected(self):
        result = _run_first_run_safe_path('/tmp/dir"evil')
        assert result.returncode != 0

    def test_path_with_dashes_and_dots_accepted(self):
        result = _run_first_run_safe_path("/home/user/.nvm/versions/node/v22.22.2/bin")
        assert result.returncode == 0

    # Regression: verify that exit 1 (not some other code) is returned.
    def test_metachar_exits_with_code_1(self):
        result = _run_first_run_safe_path("/tmp/path;inject")
        assert result.returncode == 1


# ===========================================================================
# Tests: SLUG validation in scripts/worktree-bootstrap.sh
# ===========================================================================

class TestWorktreeSlugValidation:
    """
    Tests for the SLUG validation block added to scripts/worktree-bootstrap.sh.
    Validates that:
    - Only [A-Za-z0-9._-]+ slugs are accepted
    - Slugs starting with '-' are rejected
    - The special names '.' and '..' are rejected
    """

    # ── Valid slugs ──────────────────────────────────────────────────────────

    def test_simple_kebab_slug_accepted(self):
        result = _run_slug_validation("my-feature")
        assert result.returncode == 0

    def test_date_prefixed_slug_accepted(self):
        result = _run_slug_validation("2026-05-24-my-feature")
        assert result.returncode == 0

    def test_alphanumeric_slug_accepted(self):
        result = _run_slug_validation("feature123")
        assert result.returncode == 0

    def test_slug_with_dots_accepted(self):
        result = _run_slug_validation("v2.1.0")
        assert result.returncode == 0

    def test_slug_with_underscores_accepted(self):
        # The character class ^[A-Za-z0-9._-]+$ includes underscore (_),
        # so slugs with underscores are valid.
        result = _run_slug_validation("my_feature")
        assert result.returncode == 0

    def test_single_char_slug_accepted(self):
        result = _run_slug_validation("a")
        assert result.returncode == 0

    def test_uppercase_slug_accepted(self):
        result = _run_slug_validation("MyFeature")
        assert result.returncode == 0

    def test_mixed_case_with_dashes_accepted(self):
        result = _run_slug_validation("feat-MyFeature-v2")
        assert result.returncode == 0

    # ── Invalid slugs: forbidden characters ─────────────────────────────────

    def test_slug_with_space_rejected(self):
        result = _run_slug_validation("my feature")
        assert result.returncode != 0

    def test_slug_with_slash_rejected(self):
        result = _run_slug_validation("my/feature")
        assert result.returncode != 0

    def test_slug_with_dollar_sign_rejected(self):
        result = _run_slug_validation("my$feature")
        assert result.returncode != 0

    def test_slug_with_backtick_rejected(self):
        result = _run_slug_validation("my`feature")
        assert result.returncode != 0

    def test_slug_with_semicolon_rejected(self):
        result = _run_slug_validation("my;feature")
        assert result.returncode != 0

    def test_slug_with_ampersand_rejected(self):
        result = _run_slug_validation("my&feature")
        assert result.returncode != 0

    def test_slug_with_pipe_rejected(self):
        result = _run_slug_validation("my|feature")
        assert result.returncode != 0

    def test_slug_with_newline_rejected(self):
        result = _run_slug_validation("my\nfeature")
        assert result.returncode != 0

    def test_slug_with_tab_rejected(self):
        result = _run_slug_validation("my\tfeature")
        assert result.returncode != 0

    def test_slug_with_at_sign_rejected(self):
        result = _run_slug_validation("my@feature")
        assert result.returncode != 0

    def test_slug_with_exclamation_rejected(self):
        result = _run_slug_validation("my!feature")
        assert result.returncode != 0

    def test_empty_slug_rejected(self):
        # Empty string does not match ^[A-Za-z0-9._-]+$ (needs at least 1 char).
        result = _run_slug_validation("")
        assert result.returncode != 0

    # ── Invalid slugs: leading dash ──────────────────────────────────────────

    def test_slug_starting_with_dash_rejected(self):
        result = _run_slug_validation("-my-feature")
        assert result.returncode != 0

    def test_slug_that_is_just_a_dash_rejected(self):
        result = _run_slug_validation("-")
        assert result.returncode != 0

    def test_slug_starting_with_double_dash_rejected(self):
        result = _run_slug_validation("--my-feature")
        assert result.returncode != 0

    # ── Invalid slugs: dot and double-dot ────────────────────────────────────

    def test_slug_that_is_single_dot_rejected(self):
        result = _run_slug_validation(".")
        assert result.returncode != 0

    def test_slug_that_is_double_dot_rejected(self):
        result = _run_slug_validation("..")
        assert result.returncode != 0

    # ── Error message content ─────────────────────────────────────────────────

    def test_regex_mismatch_error_message_contains_slug(self):
        result = _run_slug_validation("bad slug!")
        assert result.returncode != 0
        assert "bad slug!" in result.stderr or "slug" in result.stderr.lower()

    def test_leading_dash_error_message_contains_slug(self):
        result = _run_slug_validation("-bad")
        assert result.returncode != 0
        assert "-bad" in result.stderr or "slug" in result.stderr.lower()

    def test_dot_error_message_contains_slug(self):
        result = _run_slug_validation(".")
        assert result.returncode != 0
        assert "." in result.stderr

    # ── Regression: slug only checked once (not double-evaluated) ────────────

    def test_slug_with_dash_in_middle_accepted(self):
        # Ensure the leading-dash case statement doesn't block interior dashes.
        result = _run_slug_validation("a-b-c")
        assert result.returncode == 0

    def test_slug_ending_with_dash_accepted(self):
        # Trailing dash: matches ^[A-Za-z0-9._-]+$ and does not start with -.
        result = _run_slug_validation("feature-")
        assert result.returncode == 0

    def test_dot_prefix_slug_accepted(self):
        # A slug starting with '.' is accepted (only '-' prefix is banned).
        result = _run_slug_validation(".hidden")
        assert result.returncode == 0

    def test_triple_dot_slug_accepted(self):
        # '...' is not listed as banned (only '.' and '..').
        result = _run_slug_validation("...")
        assert result.returncode == 0


# ===========================================================================
# Tests: .env.example — ALLOWED_HOSTS default
# ===========================================================================

class TestEnvExampleAllowedHosts:
    """
    Tests for the ALLOWED_HOSTS change in .env.example:
    - Default changed from '*' (wildcard) to 'localhost,127.0.0.1'
    - Comment explains security rationale
    """

    ENV_EXAMPLE = ROOT / ".env.example"

    def test_env_example_exists(self):
        assert self.ENV_EXAMPLE.exists(), ".env.example must exist in the repo root"

    def test_allowed_hosts_default_is_localhost_only(self):
        content = self.ENV_EXAMPLE.read_text(encoding="utf-8")
        # Must contain the explicit localhost default (not commented out).
        assert "ALLOWED_HOSTS=localhost,127.0.0.1" in content

    def test_allowed_hosts_wildcard_is_not_the_default(self):
        content = self.ENV_EXAMPLE.read_text(encoding="utf-8")
        # The previous default was 'ALLOWED_HOSTS=*'; it must no longer appear
        # as an active (non-commented) assignment.
        lines = content.splitlines()
        for line in lines:
            stripped = line.strip()
            # Ignore comment lines.
            if stripped.startswith("#"):
                continue
            assert stripped != "ALLOWED_HOSTS=*", (
                "ALLOWED_HOSTS=* must not appear as an active assignment in .env.example"
            )

    def test_allowed_hosts_section_has_security_comment(self):
        content = self.ENV_EXAMPLE.read_text(encoding="utf-8")
        # The PR added a comment block explaining the security concern.
        assert "# === SECURITY ===" in content

    def test_allowed_hosts_comment_warns_against_wildcard(self):
        content = self.ENV_EXAMPLE.read_text(encoding="utf-8")
        # The comment should mention not using '*' in production.
        assert "Do NOT use '*' in production" in content or \
               "do not use '*' in production" in content.lower()

    def test_allowed_hosts_comment_mentions_loopback(self):
        content = self.ENV_EXAMPLE.read_text(encoding="utf-8")
        # The comment should mention loopback-only or similar.
        assert "localhost" in content
        assert "127.0.0.1" in content

    def test_allowed_hosts_comment_provides_lan_example(self):
        content = self.ENV_EXAMPLE.read_text(encoding="utf-8")
        # The comment should give an example of LAN configuration.
        assert "192.168." in content or "LAN" in content

    def test_allowed_hosts_value_contains_both_loopback_addresses(self):
        content = self.ENV_EXAMPLE.read_text(encoding="utf-8")
        lines = content.splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("ALLOWED_HOSTS=") and not stripped.startswith("#"):
                value = stripped.split("=", 1)[1]
                hosts = [h.strip() for h in value.split(",")]
                assert "localhost" in hosts, "localhost must be in ALLOWED_HOSTS default"
                assert "127.0.0.1" in hosts, "127.0.0.1 must be in ALLOWED_HOSTS default"
                assert "*" not in hosts, "Wildcard must not be in ALLOWED_HOSTS default"
                break
        else:
            pytest.fail("No active ALLOWED_HOSTS= line found in .env.example")


# ===========================================================================
# Tests: shell script syntax validity (sanity)
# ===========================================================================

class TestShellScriptSyntax:
    """Verify that the changed shell scripts are syntactically valid bash."""

    @pytest.mark.parametrize("script_path", [
        "bin/orama-system/scripts/install-mcp-stack.sh",
        "bin/orama-system/scripts/first-run-install.sh",
        "scripts/worktree-bootstrap.sh",
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
