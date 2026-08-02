"""Regression test for scripts/cursor/hooks/pr-body-guard-core.py's
_shell_segments() -- specifically the fix for a newline-separated second
command staying in the same "segment" as a legitimate append-pr-body.sh
invocation, and never being independently inspected once the
append-pr-body.sh branch short-circuited to ALLOW.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/cursor/hooks/pr-body-guard-core.py"

pytestmark = pytest.mark.unit


def _load_guard_core():
    spec = importlib.util.spec_from_file_location("pr_body_guard_core", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def guard_core(monkeypatch, tmp_path):
    # Route ACK_PATH somewhere guaranteed not to exist, so
    # _human_override_active() is deterministically False regardless of
    # whatever state this sandbox's real ~/.cursor happens to have.
    module = _load_guard_core()
    monkeypatch.setattr(module, "ACK_PATH", tmp_path / "no-such-ack-file")
    return module


def test_shell_segments_splits_on_newline(guard_core):
    cmd = "echo one\necho two"
    assert guard_core._shell_segments(cmd) == ["echo one", "echo two"]


def test_append_pr_body_alone_is_denied_without_override(guard_core):
    cmd = "bash scripts/cursor/append-pr-body.sh a/b 1 --file x.md"
    decision, _ = guard_core._shell_decision(cmd)
    assert decision == "DENY"


def test_newline_hidden_body_edit_after_append_pr_body_is_still_denied(guard_core, monkeypatch):
    """The specific bug this fixes: once a human override is genuinely
    active (so append-pr-body.sh alone would be ALLOWED), a
    newline-separated gh pr edit --body hidden after it must still be
    caught -- not silently allowed through because the whole multi-line
    block was treated as one segment and the append-pr-body.sh branch
    returned immediately without ever inspecting the rest.

    Mocking override ACTIVE is load-bearing here: with it inactive,
    append-pr-body.sh alone already denies, which would make this test
    pass for the wrong reason regardless of whether the newline-split
    fix is present."""
    monkeypatch.setattr(guard_core, "_human_override_active", lambda: True)
    cmd = "bash scripts/cursor/append-pr-body.sh a/b 1 --file x.md\ngh pr edit 1 --body evil.md"
    decision, msg = guard_core._shell_decision(cmd)
    assert decision == "DENY", f"hidden body-edit segment was not caught: {msg}"


def test_newline_hidden_manage_pr_update_is_still_denied(guard_core, monkeypatch):
    monkeypatch.setattr(guard_core, "_human_override_active", lambda: True)
    cmd = 'bash scripts/cursor/append-pr-body.sh a/b 1 --file x.md\nManagePullRequest update_pr body="evil"'
    decision, _ = guard_core._shell_decision(cmd)
    assert decision == "DENY"


def test_gh_pr_comment_alone_is_allowed(guard_core):
    decision, _ = guard_core._shell_decision("gh pr comment 1 --body 'note'")
    assert decision == "ALLOW"
