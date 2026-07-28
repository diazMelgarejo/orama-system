#!/usr/bin/env python3
"""Tests for the glm52-fallback skill hardening in this PR.

Covers:
- bin/orama-system/skills/glm52-fallback/setup-glm52.sh
    (fail-fast, non-interactive API-key requirement; profile-file guard;
     no source-line duplication; never printing the credential value)
- bin/orama-system/skills/glm52-fallback/SKILL.md
    (new frontmatter fields, canonical-folder statement, updated
     Setup/Verification/Security sections)
- docs/security/glm52-clean-replay-record.md (new file)

Run: pytest tests/test_glm52_fallback_skill.py -v
"""
from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).parent.parent
SKILL_DIR = ROOT / "bin" / "orama-system" / "skills" / "glm52-fallback"
SETUP_SCRIPT = SKILL_DIR / "setup-glm52.sh"
SKILL_MD = SKILL_DIR / "SKILL.md"
REPLAY_RECORD = ROOT / "docs" / "security" / "glm52-clean-replay-record.md"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_fake_bin(tmp_path: Path, curl_sentinel: Path) -> Path:
    """Create a fake curl/jq on PATH so tests never touch the network.

    The fake curl records its full argv (including headers) to
    *curl_sentinel* -- purely for test assertions -- then exits 1 to
    simulate an unreachable endpoint, exercising the script's graceful
    "unreachable" fallback path deterministically and without network I/O.
    """
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir(exist_ok=True)
    curl = fakebin / "curl"
    curl.write_text(
        "#!/bin/sh\n"
        f'printf \'%s\\n\' "$*" >> "{curl_sentinel}"\n'
        "exit 1\n",
        encoding="utf-8",
    )
    jq = fakebin / "jq"
    jq.write_text("#!/bin/sh\ncat >/dev/null\nexit 0\n", encoding="utf-8")
    for exe in (curl, jq):
        exe.chmod(exe.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return fakebin


def _run_setup(
    tmp_path: Path,
    env: dict,
    make_profiles: bool = False,
    home: Path | None = None,
) -> subprocess.CompletedProcess:
    """Run the real setup-glm52.sh with an isolated $HOME and a stubbed
    curl/jq on PATH so no real network call is made."""
    if home is None:
        home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    if make_profiles:
        if not (home / ".zshrc").exists():
            (home / ".zshrc").write_text("# existing zshrc\n", encoding="utf-8")
        if not (home / ".bashrc").exists():
            (home / ".bashrc").write_text("# existing bashrc\n", encoding="utf-8")

    curl_sentinel = tmp_path / "curl_calls.txt"
    fakebin = _make_fake_bin(tmp_path, curl_sentinel)

    full_env = os.environ.copy()
    full_env.pop("GLM52_API_KEY", None)
    full_env.pop("OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY", None)
    full_env.update(env)
    full_env["HOME"] = str(home)
    full_env["PATH"] = f"{fakebin}:{full_env.get('PATH', '')}"

    result = subprocess.run(
        ["bash", str(SETUP_SCRIPT)],
        capture_output=True,
        text=True,
        env=full_env,
        stdin=subprocess.DEVNULL,
        timeout=30,
    )
    result.curl_sentinel = curl_sentinel  # type: ignore[attr-defined]
    result.home = home  # type: ignore[attr-defined]
    return result


# ===========================================================================
# Shell syntax validity
# ===========================================================================

class TestSetupScriptSyntax:
    def test_script_is_valid_bash(self):
        result = subprocess.run(
            ["bash", "-n", str(SETUP_SCRIPT)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"setup-glm52.sh has bash syntax errors:\n{result.stderr}"
        )

    def test_script_uses_strict_mode(self):
        text = SETUP_SCRIPT.read_text(encoding="utf-8")
        assert "set -euo pipefail" in text


# ===========================================================================
# Fail-fast, non-interactive API-key requirement
# ===========================================================================

class TestApiKeyRequirement:
    def test_missing_api_key_exits_nonzero(self, tmp_path):
        result = _run_setup(tmp_path, env={})
        assert result.returncode == 1

    def test_missing_api_key_error_message_is_clear(self, tmp_path):
        result = _run_setup(tmp_path, env={})
        assert "GLM52_API_KEY must be set" in result.stderr

    def test_missing_api_key_shows_example_usage(self, tmp_path):
        result = _run_setup(tmp_path, env={})
        assert "export GLM52_API_KEY=" in result.stderr

    def test_missing_api_key_does_not_hang_waiting_for_input(self, tmp_path):
        """Regression: the old script used an interactive `read`. The new
        script must never block on stdin -- verified via a hard timeout and
        /dev/null stdin (see _run_setup)."""
        result = _run_setup(tmp_path, env={})
        assert result.returncode == 1  # returned promptly; no timeout raised

    def test_empty_glm52_api_key_is_treated_as_unset(self, tmp_path):
        result = _run_setup(tmp_path, env={"GLM52_API_KEY": ""})
        assert result.returncode == 1
        assert "GLM52_API_KEY must be set" in result.stderr

    def test_empty_bigmodel_apikey_fallback_does_not_satisfy_requirement(self, tmp_path):
        result = _run_setup(
            tmp_path,
            env={"OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY": ""},
        )
        assert result.returncode == 1

    def test_valid_glm52_api_key_succeeds(self, tmp_path):
        result = _run_setup(tmp_path, env={"GLM52_API_KEY": "test-key-abc123"})
        assert result.returncode == 0, result.stdout + result.stderr

    def test_no_longer_prompts_interactively(self, tmp_path):
        """Regression: the script must not contain the old interactive read."""
        text = SETUP_SCRIPT.read_text(encoding="utf-8")
        assert "read -r GLM52_KEY_INPUT" not in text
        assert "Enter your BigModel GLM-5.2 API key" not in text


# ===========================================================================
# OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY fallback and precedence
# ===========================================================================

class TestApiKeySourcePrecedence:
    def test_bigmodel_apikey_used_when_glm52_api_key_unset(self, tmp_path):
        result = _run_setup(
            tmp_path,
            env={"OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY": "fallback-key-xyz"},
        )
        assert result.returncode == 0, result.stdout + result.stderr
        secrets_file = result.home / ".openclaw" / "secrets" / "glm52-api-key"
        assert secrets_file.read_text(encoding="utf-8") == "fallback-key-xyz"

    def test_glm52_api_key_takes_precedence_over_bigmodel_apikey(self, tmp_path):
        result = _run_setup(
            tmp_path,
            env={
                "GLM52_API_KEY": "primary-key",
                "OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY": "secondary-key",
            },
        )
        assert result.returncode == 0, result.stdout + result.stderr
        secrets_file = result.home / ".openclaw" / "secrets" / "glm52-api-key"
        assert secrets_file.read_text(encoding="utf-8") == "primary-key"


# ===========================================================================
# Secure storage: secrets file and env file
# ===========================================================================

class TestSecureStorage:
    def test_secrets_dir_and_logs_dir_created(self, tmp_path):
        result = _run_setup(tmp_path, env={"GLM52_API_KEY": "k"})
        assert result.returncode == 0, result.stdout + result.stderr
        assert (result.home / ".openclaw" / "secrets").is_dir()
        assert (result.home / ".openclaw" / "logs").is_dir()

    def test_secrets_file_contains_exact_key_value(self, tmp_path):
        result = _run_setup(tmp_path, env={"GLM52_API_KEY": "my-secret-value"})
        assert result.returncode == 0, result.stdout + result.stderr
        secrets_file = result.home / ".openclaw" / "secrets" / "glm52-api-key"
        assert secrets_file.read_text(encoding="utf-8") == "my-secret-value"

    def test_secrets_file_has_mode_600(self, tmp_path):
        result = _run_setup(tmp_path, env={"GLM52_API_KEY": "k"})
        assert result.returncode == 0, result.stdout + result.stderr
        secrets_file = result.home / ".openclaw" / "secrets" / "glm52-api-key"
        mode = stat.S_IMODE(secrets_file.stat().st_mode)
        assert mode == 0o600, f"expected mode 0o600, got {oct(mode)}"

    def test_env_file_has_mode_600(self, tmp_path):
        result = _run_setup(tmp_path, env={"GLM52_API_KEY": "k"})
        assert result.returncode == 0, result.stdout + result.stderr
        env_file = result.home / ".openclaw" / ".env.glm52"
        mode = stat.S_IMODE(env_file.stat().st_mode)
        assert mode == 0o600, f"expected mode 0o600, got {oct(mode)}"

    def test_env_file_contains_expected_endpoint(self, tmp_path):
        result = _run_setup(tmp_path, env={"GLM52_API_KEY": "k"})
        assert result.returncode == 0, result.stdout + result.stderr
        env_file = result.home / ".openclaw" / ".env.glm52"
        content = env_file.read_text(encoding="utf-8")
        assert (
            'export GLM52_ENDPOINT="https://open.bigmodel.cn/api/paas/v4/chat/completions"'
            in content
        )

    def test_env_file_reads_key_from_secrets_file_not_hardcoded(self, tmp_path):
        result = _run_setup(tmp_path, env={"GLM52_API_KEY": "unique-marker-9f8e7d"})
        assert result.returncode == 0, result.stdout + result.stderr
        env_file = result.home / ".openclaw" / ".env.glm52"
        content = env_file.read_text(encoding="utf-8")
        assert "cat " in content and "secrets/glm52-api-key" in content
        assert "unique-marker-9f8e7d" not in content


# ===========================================================================
# Shell profile handling: only append to profiles that already exist
# ===========================================================================

class TestShellProfileHandling:
    def test_does_not_create_zshrc_if_absent(self, tmp_path):
        result = _run_setup(tmp_path, env={"GLM52_API_KEY": "k"}, make_profiles=False)
        assert result.returncode == 0, result.stdout + result.stderr
        assert not (result.home / ".zshrc").exists()

    def test_does_not_create_bashrc_if_absent(self, tmp_path):
        result = _run_setup(tmp_path, env={"GLM52_API_KEY": "k"}, make_profiles=False)
        assert result.returncode == 0, result.stdout + result.stderr
        assert not (result.home / ".bashrc").exists()

    def test_appends_source_line_to_existing_zshrc(self, tmp_path):
        result = _run_setup(
            tmp_path,
            env={"GLM52_API_KEY": "k", "GLM52_PERSIST_SHELL_PROFILE": "1"},
            make_profiles=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        content = (result.home / ".zshrc").read_text(encoding="utf-8")
        assert "source ~/.openclaw/.env.glm52 2>/dev/null || true" in content

    def test_appends_source_line_to_existing_bashrc(self, tmp_path):
        result = _run_setup(
            tmp_path,
            env={"GLM52_API_KEY": "k", "GLM52_PERSIST_SHELL_PROFILE": "1"},
            make_profiles=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        content = (result.home / ".bashrc").read_text(encoding="utf-8")
        assert "source ~/.openclaw/.env.glm52 2>/dev/null || true" in content

    def test_preserves_existing_profile_content(self, tmp_path):
        result = _run_setup(tmp_path, env={"GLM52_API_KEY": "k"}, make_profiles=True)
        assert result.returncode == 0, result.stdout + result.stderr
        content = (result.home / ".zshrc").read_text(encoding="utf-8")
        assert "# existing zshrc" in content

    def test_does_not_duplicate_source_line_on_rerun(self, tmp_path):
        home = tmp_path / "home"
        env = {"GLM52_API_KEY": "k", "GLM52_PERSIST_SHELL_PROFILE": "1"}
        result1 = _run_setup(tmp_path, env=env, make_profiles=True, home=home)
        assert result1.returncode == 0, result1.stdout + result1.stderr
        result2 = _run_setup(tmp_path, env=env, make_profiles=True, home=home)
        assert result2.returncode == 0, result2.stdout + result2.stderr
        content = (home / ".zshrc").read_text(encoding="utf-8")
        assert content.count("source ~/.openclaw/.env.glm52 2>/dev/null || true") == 1

    def test_added_message_printed_when_profile_exists(self, tmp_path):
        result = _run_setup(
            tmp_path,
            env={"GLM52_API_KEY": "k", "GLM52_PERSIST_SHELL_PROFILE": "1"},
            make_profiles=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "Added GLM-5.2 fallback source line to" in result.stdout
        assert ".zshrc" in result.stdout
        assert ".bashrc" in result.stdout

    def test_default_skips_persistence_and_prints_opt_in_hint(self, tmp_path):
        """Regression: shell-profile persistence is opt-in (GLM52_PERSIST_SHELL_PROFILE=1).
        Without it, the default run must not touch .zshrc/.bashrc at all.
        """
        result = _run_setup(tmp_path, env={"GLM52_API_KEY": "k"}, make_profiles=True)
        assert result.returncode == 0, result.stdout + result.stderr
        content = (result.home / ".zshrc").read_text(encoding="utf-8")
        assert "source ~/.openclaw/.env.glm52" not in content
        assert "Skipping shell profile persistence" in result.stdout
        assert "GLM52_PERSIST_SHELL_PROFILE=1" in result.stdout

    def test_no_added_message_when_profile_absent(self, tmp_path):
        result = _run_setup(tmp_path, env={"GLM52_API_KEY": "k"}, make_profiles=False)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "Added GLM-5.2 fallback source line to" not in result.stdout

    def test_no_added_message_on_second_run_already_sourced(self, tmp_path):
        home = tmp_path / "home"
        _run_setup(tmp_path, env={"GLM52_API_KEY": "k"}, make_profiles=True, home=home)
        result2 = _run_setup(tmp_path, env={"GLM52_API_KEY": "k"}, make_profiles=True, home=home)
        assert result2.returncode == 0, result2.stdout + result2.stderr
        assert "Added GLM-5.2 fallback source line to" not in result2.stdout


# ===========================================================================
# Credential secrecy: the key must never appear in the script's own output
# ===========================================================================

class TestCredentialNeverPrinted:
    SECRET = "sk-super-secret-do-not-print-987654321"

    def test_secret_not_in_stdout(self, tmp_path):
        result = _run_setup(tmp_path, env={"GLM52_API_KEY": self.SECRET})
        assert result.returncode == 0, result.stdout + result.stderr
        assert self.SECRET not in result.stdout

    def test_secret_not_in_stderr(self, tmp_path):
        result = _run_setup(tmp_path, env={"GLM52_API_KEY": self.SECRET})
        assert result.returncode == 0, result.stdout + result.stderr
        assert self.SECRET not in result.stderr

    def test_secret_not_printed_via_bigmodel_fallback_env_var(self, tmp_path):
        # The secret reaches GLM52_API_KEY via the fallback env var; it must
        # still never be echoed to stdout/stderr.
        result = _run_setup(
            tmp_path,
            env={"OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY": self.SECRET},
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert self.SECRET not in result.stdout
        assert self.SECRET not in result.stderr

    def test_curl_request_actually_carries_the_key(self, tmp_path):
        """Sanity check that the key IS sent to the API (via the Authorization
        header captured by the fake curl sentinel) even though it is never
        printed by the script itself -- i.e. secrecy is not achieved by
        accidentally failing to use the key at all."""
        result = _run_setup(tmp_path, env={"GLM52_API_KEY": self.SECRET})
        assert result.returncode == 0, result.stdout + result.stderr
        sentinel_text = result.curl_sentinel.read_text(encoding="utf-8")
        assert self.SECRET in sentinel_text
        assert "open.bigmodel.cn" in sentinel_text


# ===========================================================================
# Overall script behavior / completion messages
# ===========================================================================

class TestSetupCompletion:
    def test_prints_setup_complete_message(self, tmp_path):
        result = _run_setup(tmp_path, env={"GLM52_API_KEY": "k"})
        assert result.returncode == 0, result.stdout + result.stderr
        assert "Setup complete." in result.stdout

    def test_prints_activation_hint(self, tmp_path):
        result = _run_setup(tmp_path, env={"GLM52_API_KEY": "k"})
        assert result.returncode == 0, result.stdout + result.stderr
        assert "source ~/.openclaw/.env.glm52" in result.stdout

    def test_unreachable_endpoint_does_not_abort_script(self, tmp_path):
        """The fake curl always fails (simulating no network); the script's
        health-check chain uses && / || so this must not trigger `set -e`."""
        result = _run_setup(tmp_path, env={"GLM52_API_KEY": "k"})
        assert result.returncode == 0, result.stdout + result.stderr
        assert "unreachable" in result.stdout or "healthy" in result.stdout


# ===========================================================================
# SKILL.md content
# ===========================================================================

class TestSkillMdFrontmatter:
    @property
    def _text(self) -> str:
        return SKILL_MD.read_text(encoding="utf-8")

    def test_skill_md_exists(self):
        assert SKILL_MD.exists()

    def test_frontmatter_has_when_to_use(self):
        assert "when_to_use:" in self._text

    def test_frontmatter_disable_model_invocation_is_true(self):
        assert "disable-model-invocation: true" in self._text

    def test_frontmatter_effort_is_medium(self):
        assert "effort: medium" in self._text

    def test_frontmatter_paths_points_at_canonical_dir(self):
        assert 'paths:' in self._text
        assert '"bin/orama-system/skills/glm52-fallback/**"' in self._text

    def test_frontmatter_retains_name_and_trigger(self):
        text = self._text
        assert "name: glm52-fallback" in text
        assert 'trigger: "bash setup-glm52.sh"' in text


class TestSkillMdContent:
    @property
    def _text(self) -> str:
        return SKILL_MD.read_text(encoding="utf-8")

    def test_canonical_folder_statement_present(self):
        text = self._text
        assert "Canonical folder" in text
        assert "bin/orama-system/skills/glm52-fallback/" in text

    def test_setup_automated_exports_key_before_invocation(self):
        """Regression: docs must validate/export the key BEFORE invoking the
        script (matches the fail-fast, non-interactive contract)."""
        text = self._text
        guard_idx = text.find(': "${GLM52_API_KEY:?Set GLM52_API_KEY')
        export_idx = text.find('export GLM52_API_KEY="${GLM52_API_KEY:?}"')
        run_idx = text.find("bash bin/orama-system/skills/glm52-fallback/setup-glm52.sh")
        assert guard_idx != -1
        assert export_idx != -1
        assert run_idx != -1
        assert guard_idx < run_idx
        assert export_idx < run_idx

    def test_setup_steps_describe_fail_fast_behavior(self):
        text = self._text
        assert "fails fast" in text
        assert "unattended" in text or "CI" in text

    def test_security_note_prohibits_printing_credential(self):
        text = self._text
        assert "must not" in text
        assert "print" in text.lower()
        assert "credential value" in text

    def test_verification_section_present(self):
        text = self._text
        assert "## Verification" in text

    def test_verification_section_does_not_print_key_value(self):
        text = self._text
        v_idx = text.find("## Verification")
        next_idx = text.find("\n## Security", v_idx)
        verification_section = text[v_idx:next_idx]
        assert "Do not print the credential value" in verification_section

    def test_security_section_present(self):
        assert "## Security" in self._text

    def test_security_section_mentions_runtime_values_local_only(self):
        text = self._text
        s_idx = text.find("## Security")
        security_section = text[s_idx:]
        assert "~/.openclaw/" in security_section
        assert "never in tracked files" in security_section

    def test_referenced_setup_script_path_exists(self):
        """The doc references the script by repo-relative path; that path
        must actually exist on disk."""
        text = self._text
        assert SETUP_SCRIPT.exists()
        assert "bin/orama-system/skills/glm52-fallback/setup-glm52.sh" in text

    def test_no_real_looking_hardcoded_api_key(self):
        """Guard against accidentally hardcoding a real-looking API key
        literal in the doc (placeholders like <BigModel.API.key> are fine)."""
        text = self._text
        # Look for long base64/hex-ish runs that are not inside angle-bracket
        # placeholders or template variables.
        suspicious = re.findall(r'"[A-Za-z0-9_\-]{32,}"', text)
        assert suspicious == [], f"suspicious hardcoded-looking value(s): {suspicious}"


# ===========================================================================
# docs/security/glm52-clean-replay-record.md
# ===========================================================================

class TestReplayRecordDoc:
    @property
    def _text(self) -> str:
        return REPLAY_RECORD.read_text(encoding="utf-8")

    def test_file_exists(self):
        assert REPLAY_RECORD.exists()

    def test_has_title(self):
        assert "# GLM52 Clean Remediation Replay Record" in self._text

    def test_has_date(self):
        assert re.search(r"Date: \d{4}-\d{2}-\d{2}", self._text)

    def test_has_scope_section(self):
        assert "## Scope" in self._text

    def test_has_backup_policy_section(self):
        assert "## Backup policy" in self._text

    def test_backup_policy_prohibits_credential_backups(self):
        text = self._text
        b_idx = text.find("## Backup policy")
        next_idx = text.find("\n## ", b_idx + 1)
        backup_section = text[b_idx:next_idx]
        assert "credential-bearing backup copies" in backup_section

    def test_has_pre_replacement_inventory_table(self):
        assert "## Pre-replacement inventory" in self._text

    def test_inventory_table_lists_canonical_path_as_present(self):
        text = self._text
        assert "`bin/orama-system/skills/glm52-fallback/SKILL.md` | present" in text
        assert "`bin/orama-system/skills/glm52-fallback/setup-glm52.sh` | present" in text

    def test_inventory_table_lists_stale_paths_as_absent(self):
        text = self._text
        assert "`skills/glm52-fallback/SKILL.md` | absent" in text
        assert (
            "`bin/orama-system/skills/cline-openclaw-agent/glm52-fallback/SKILL.md` | absent"
            in text
        )

    def test_has_replay_decisions_section(self):
        assert "## Replay decisions" in self._text

    def test_replay_decisions_name_the_canonical_folder(self):
        text = self._text
        d_idx = text.find("## Replay decisions")
        next_idx = text.find("\n## ", d_idx + 1)
        decisions_section = text[d_idx:next_idx]
        assert "one consolidated canonical folder" in decisions_section
        assert "bin/orama-system/skills/glm52-fallback/" in decisions_section

    def test_replay_decisions_forbid_printing_credentials(self):
        text = self._text
        assert "Do not print, quote, or store runtime credential values" in text

    def test_replay_decisions_name_runtime_contract_env_var(self):
        text = self._text
        assert "`$GLM52_API_KEY`" in text

    def test_has_out_of_scope_section(self):
        assert "## Out of scope" in self._text

    def test_out_of_scope_excludes_history_rewrite_and_key_rotation(self):
        text = self._text
        o_idx = text.find("## Out of scope")
        out_section = text[o_idx:]
        assert "Git history rewrite" in out_section
        assert "Provider key rotation" in out_section

    def test_no_actual_secret_values_present(self):
        """This is a record ABOUT credential hygiene; it must not itself leak
        a credential-shaped value."""
        text = self._text
        # Common secret-key shapes: sk-..., long base64/hex tokens standing
        # alone (not inside backticks describing blob SHAs, which are
        # expected metadata, not credentials).
        assert "GLM52_API_KEY=" not in text  # no literal assignment, only the $VAR name
        assert not re.search(r"sk-[A-Za-z0-9]{20,}", text)

    def test_canonical_path_referenced_matches_real_skill_dir(self):
        """Cross-check the doc's canonical path claim against the actual
        repository layout introduced/kept by this PR."""
        assert SKILL_DIR.is_dir()
        assert SKILL_MD.exists()
        assert SETUP_SCRIPT.exists()