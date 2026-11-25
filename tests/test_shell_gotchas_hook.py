"""The shell-gotchas hook: every rule's fixtures, real session incidents, the hook protocol and log."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "bin/orama-system/skills/shell-hygiene/hooks"
GOTCHAS = HOOKS / "shell-gotchas.py"

_spec = importlib.util.spec_from_file_location("shell_gotchas", GOTCHAS)
assert _spec is not None and _spec.loader is not None
sg = importlib.util.module_from_spec(_spec)
sys.modules["shell_gotchas"] = sg
_spec.loader.exec_module(sg)

CASES = [(rule.id, case, True) for rule in sg.RULES for case in rule.bad] + [
    (rule.id, case, False) for rule in sg.RULES for case in rule.good
]


@pytest.fixture
def cwd(tmp_path: Path) -> str:
    """A scratch working directory holding one file, for the glob rule."""
    (tmp_path / "exists.txt").write_text("x", encoding="utf-8")
    return str(tmp_path)


def _ids(command: str, where: str) -> set[str]:
    return {rule.id for rule in sg.evaluate(command, where)}


def _clean_env() -> dict[str, str]:
    """The inherited environment minus the hook's own controls, so a developer's exports cannot change a test."""
    return {k: v for k, v in os.environ.items() if k not in {"SHELL_GOTCHAS_MODE", "SHELL_GOTCHAS_LOG"}}


def _hook(command: str, where: str, **env: str) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": where})
    full_env = {**_clean_env(), "SHELL_GOTCHAS_LOG": os.devnull, **env}
    return subprocess.run([sys.executable, str(GOTCHAS)], input=payload, capture_output=True, text=True, env=full_env)


def test_rule_ids_are_unique_and_levels_valid() -> None:
    """Every rule has a unique id, a valid level, a hint, and fixtures on both sides."""
    ids = [rule.id for rule in sg.RULES]
    assert len(ids) == len(set(ids))
    for rule in sg.RULES:
        assert rule.level in {"deny", "warn"} and rule.hint and rule.summary
        assert rule.bad and rule.good, f"{rule.id} needs bad and good fixtures"


@pytest.mark.parametrize(("rule_id", "command", "should_fire"), CASES)
def test_rule_fixtures(rule_id: str, command: str, should_fire: bool, cwd: str) -> None:
    """Each rule fires on its bad fixtures and stays silent on its good ones."""
    assert (rule_id in _ids(command, cwd)) is should_fire, command


SESSION_INCIDENTS = [
    ('for spec in "orama-system 525" "Perpetua-Tools 521"; do set -- $spec; echo $1; done', "zsh-set-unquoted"),
    ('F="$(ls tests | grep -iE \'identity|attribution\' | sed \'s|^|tests/|\' | tr \'\\n\' \' \')"; python3 -m pytest $F -q', "zsh-unquoted-list-var"),
    ("env | grep -i supabase", "secret-env-dump"),
    ("cat -A file.txt", "bsd-cat-A"),
]


@pytest.mark.parametrize(("command", "rule_id"), SESSION_INCIDENTS)
def test_real_session_incidents_are_caught(command: str, rule_id: str, cwd: str) -> None:
    """Commands that actually failed in practice are blocked, each by the rule that names the trap."""
    assert rule_id in _ids(command, cwd)


KNOWN_GOOD = [
    "git commit -q -F - <<'E'\nfix: x\n\nMentions git commit and set -- $x as text.\nE",
    "codex exec --sandbox read-only --cd /repo -c 'model_reasoning_effort=\"medium\"' - <<'E'\nrun `git commit` carefully\nE",
    "gh api -X POST repos/o/r/pulls/1/comments/2/replies -f body='@bot fixed in abc' --jq '{id,html_url}'",
    "cd /repo && git status -sb | head -2",
    "python3 - <<'E'\nstatus = 1\npath = '/x'\nE",
    "for f in a b; do cmp \"$f\" \"$f\"; done",
    "bash -c 'set -- $x; echo ${y,,}'",
    "git add a b && git commit -m 'x'",
    "awk 'length>100{print FILENAME\": line \"FNR}' a b",
    "grep -rIn --exclude-dir=.git -E 'a|b' dir | cut -c1-190 | head -20",
    "printf '%s\\n' a b",
    "sed -n 1,60p file",
    "git push origin HEAD",
]


@pytest.mark.parametrize("command", KNOWN_GOOD)
def test_known_good_commands_are_never_flagged(command: str, cwd: str) -> None:
    """Heredoc bodies, bash bodies and ordinary commands do not trip any rule."""
    assert _ids(command, cwd) == set(), command


def test_escape_marker_skips_named_rules_only(cwd: str) -> None:
    """`# gotcha-ok: id` suppresses that rule for that command; other rules still fire."""
    command = "git commit  # gotcha-ok: git-commit-no-message"
    assert "git-commit-no-message" not in _ids(command, cwd)
    assert "git-commit-no-message" in _ids("git commit  # gotcha-ok: other-rule", cwd)
    assert _ids("env | cat  # gotcha-ok: all", cwd) == set()


def test_hook_blocks_with_exit_2_and_names_the_rule(cwd: str) -> None:
    """A deny rule exits 2 and tells the model the rule, the fix and the escape."""
    done = _hook("git commit", cwd)
    assert done.returncode == 2
    assert "[git-commit-no-message]" in done.stderr and "gotcha-ok" in done.stderr


def test_hook_allows_clean_commands_silently(cwd: str) -> None:
    done = _hook("git status -sb", cwd)
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


def test_warn_rules_add_context_without_blocking(cwd: str) -> None:
    done = _hook("pkill -f server", cwd)
    assert done.returncode == 0
    context = json.loads(done.stdout)["hookSpecificOutput"]
    assert context["hookEventName"] == "PreToolUse" and "kill-by-pattern" in context["additionalContext"]


def test_mode_warn_downgrades_blocks_and_off_disables(cwd: str) -> None:
    warned = _hook("git commit", cwd, SHELL_GOTCHAS_MODE="warn")
    assert warned.returncode == 0 and "git-commit-no-message" in warned.stdout
    off = _hook("git commit", cwd, SHELL_GOTCHAS_MODE="off")
    assert (off.returncode, off.stdout) == (0, "")


def test_malformed_input_never_blocks() -> None:
    done = subprocess.run([sys.executable, str(GOTCHAS)], input="not json", capture_output=True, text=True)
    assert done.returncode == 0


def test_log_records_rule_ids_and_a_hash_never_the_command(tmp_path: Path, cwd: str) -> None:
    """The usage log is safe to keep: it holds no command text, so no secret can land in it."""
    log = tmp_path / "gotchas.log"
    secret_command = "env | grep SUPER_SECRET_TOKEN_VALUE"
    payload = json.dumps({"tool_input": {"command": secret_command}, "cwd": cwd})
    subprocess.run([sys.executable, str(GOTCHAS)], input=payload, capture_output=True, text=True,
                   env={**_clean_env(), "SHELL_GOTCHAS_LOG": str(log)})
    entry = json.loads(log.read_text(encoding="utf-8"))
    assert entry["rules"] == ["secret-env-dump"] and len(entry["cmd"]) == 12
    assert "SUPER_SECRET" not in log.read_text(encoding="utf-8")


def test_default_log_lives_in_the_state_directory_never_in_the_claude_config(tmp_path: Path, cwd: str) -> None:
    """With no SHELL_GOTCHAS_LOG the hook logs under XDG_STATE_HOME and writes nothing inside a .claude dir."""
    home, state = tmp_path / "home", tmp_path / "state"
    (home / ".claude" / "hooks").mkdir(parents=True)
    env = _clean_env()
    env.update({"HOME": str(home), "XDG_STATE_HOME": str(state)})
    payload = json.dumps({"tool_input": {"command": "env | grep x"}, "cwd": cwd})
    subprocess.run([sys.executable, str(GOTCHAS)], input=payload, capture_output=True, text=True, env=env)
    assert json.loads((state / "shell-gotchas" / "usage.log").read_text(encoding="utf-8"))["rules"] == ["secret-env-dump"]
    assert list((home / ".claude").rglob("*")) == [home / ".claude" / "hooks"], "nothing may be written under .claude"
    report = subprocess.run([sys.executable, str(GOTCHAS), "--report"], capture_output=True, text=True, env=env)
    assert "1 firing(s) across 1 rule(s)" in report.stdout


def test_hook_is_hermetic_against_an_exported_mode(cwd: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """An operator who exports SHELL_GOTCHAS_MODE=off still gets the same test results."""
    monkeypatch.setenv("SHELL_GOTCHAS_MODE", "off")
    assert _hook("git commit", cwd).returncode == 2


def test_env_dump_safe_filter_applies_to_the_env_pipeline_only(cwd: str) -> None:
    """A later `| wc` on another statement cannot excuse the dump; counting after a filter stays allowed."""
    assert "secret-env-dump" in _ids("env | grep X; echo | wc -l", cwd)
    assert "secret-env-dump" in _ids("env | grep X && echo | wc -l", cwd)
    assert "secret-env-dump" in _ids("env | grep X & echo | wc -l", cwd)
    assert "secret-env-dump" in _ids("env & echo | wc -l", cwd)
    assert "secret-env-dump" not in _ids("env | grep PATH | wc -l", cwd)
    assert "secret-env-dump" not in _ids("env | grep -c X 2>&1 | cat", cwd)


@pytest.mark.parametrize(("selection", "fires"), [("1", False), ("1-", True), ("1,2", True)])
def test_env_dump_cut_field_selection(selection: str, fires: bool, cwd: str) -> None:
    assert ("secret-env-dump" in _ids(f"env | cut -d= -f{selection}", cwd)) is fires


@pytest.mark.parametrize(("args", "fires"), [("-c HEAD", True), ("-C HEAD", False),
                                             ("-c HEAD --no-edit", False)])
def test_commit_reuse_message_options(args: str, fires: bool, cwd: str) -> None:
    assert ("git-commit-no-message" in _ids(f"git commit {args}", cwd)) is fires


@pytest.mark.parametrize(("command", "fires"), [
    ("rg -n 'mapfile|readarray' .", False),
    ("printf '%s' '${value,,}'", False),
    ('printf "%s" "${value,,}"', True),
    ("mapfile -t items < file", True),
    ("printf x | readarray -t items", True),
    ('result="$(mapfile -t items < file)"', True),
    ('result="$(echo $(readarray -t items))"', True),
    ("printf '%s' '$(mapfile -t items)'", False),
    (r'printf "%s" "\$(mapfile -t items)"', False),
    ('result="$(printf \'%s\' mapfile)"', False),
    ('result="$((mapfile + 1))"', False),
    ('result="$(( $(mapfile -t items < file) + 1 ))"', True),
])
def test_bash4_rule_distinguishes_quoted_text(command: str, fires: bool, cwd: str) -> None:
    assert ("bash4-in-zsh" in _ids(command, cwd)) is fires


@pytest.mark.parametrize(("command", "fires"), [
    ("bash -c 'status=$?'", False),
    ("bash -c 'true'; status=$?", True),
    ("status=1; bash -c 'true'", True),
    ('bash -c "status=1" && path=example', True),
    ('bash -c "echo $(status=1)"', True),
    ('bash -c "echo \'$(status=1)\'"', True),
    ('bash -c "echo \'ordinary text\'"', False),
    ('bash -c "echo $(status=1)"suffix', True),
    ('bash -c "echo $(echo $(path=example))"', True),
    ('bash -c "status=1"', False),
    (r'bash -c "echo \$(status=1)"', False),
    ("bash -c 'echo $(status=1)'", False),
    (r"""printf '%s\n' 'example: bash -c "echo $(status=1)"'""", False),
])
def test_bash_exemption_is_limited_to_quoted_body(command: str, fires: bool, cwd: str) -> None:
    assert ("zsh-reserved-var" in _ids(command, cwd)) is fires


def test_bash_double_quoted_caller_expansions(cwd: str) -> None:
    assert "bash4-in-zsh" in _ids('bash -c "echo $(mapfile -t items)"', cwd)
    assert "bash4-in-zsh" in _ids('bash -c "echo ${value,,}"', cwd)
    assert "bash4-in-zsh" in _ids('bash -c "echo \'${value,,}\'"', cwd)
    assert "bash4-in-zsh" not in _ids('bash -c "mapfile -t items"', cwd)


def test_codex_review_accepts_fd_redirections_before_dev_null(cwd: str) -> None:
    """`2>&1 < /dev/null` is the same safe call; `2>&1` alone is still the silent hang."""
    assert "codex-review-stdin" not in _ids('codex review "x" 2>&1 < /dev/null', cwd)
    assert "codex-review-stdin" not in _ids('codex review --base main < /dev/null 2>&1 | tail -5', cwd)
    assert "codex-review-stdin" in _ids('codex review "x" 2>&1', cwd)
    assert "codex-review-stdin" in _ids('codex review "x" 2>&1 | tail -5', cwd)
    assert "codex-review-stdin" in _ids('codex review "x" > /dev/null', cwd), "an output redirect is not a stdin redirect"


def test_rendered_table_rows_never_split_on_a_pipe_inside_a_cell() -> None:
    """GFM splits cells on every unescaped pipe, code spans included; each row must keep four cells."""
    for row in sg.markdown().splitlines():
        assert len(re.split(r"(?<!\\)\|", row.strip())[1:-1]) == 4, row


def test_self_test_passes() -> None:
    done = subprocess.run([sys.executable, str(GOTCHAS), "--self-test"], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
