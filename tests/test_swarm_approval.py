from __future__ import annotations

import os

import pytest

from orama_system import swarm_approval


def test_grandfather_legacy_approve(monkeypatch):
    monkeypatch.delenv("ORAMA_SWARM_STRICT", raising=False)
    monkeypatch.setenv("ORAMA_SWARM_LEGACY_APPROVE", "1")
    preview = {"objective": "x", "assignments": [], "task_type": "implementation"}
    swarm_approval.verify_launch(approved=True, preview_id=None, approval_token=None, preview=preview)


def test_strict_requires_token(monkeypatch):
    monkeypatch.setenv("ORAMA_SWARM_STRICT", "1")
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    preview = {"objective": "x", "assignments": [], "task_type": "implementation"}
    with pytest.raises(ValueError, match="preview_id"):
        swarm_approval.verify_launch(approved=False, preview_id=None, approval_token=None, preview=preview)


def test_issue_and_verify_token(monkeypatch):
    monkeypatch.setenv("ORAMA_SWARM_STRICT", "1")
    monkeypatch.setenv("ORAMA_SWARM_APPROVAL_SECRET", "test-secret")
    preview = {"objective": "ship", "assignments": [{"role": "a"}], "task_type": "implementation"}
    issued = swarm_approval.issue_approval(preview)
    swarm_approval.verify_launch(
        approved=False,
        preview_id=issued["preview_id"],
        approval_token=issued["approval_token"],
        preview=preview,
    )
