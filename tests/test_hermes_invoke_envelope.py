"""Schema validation for Hermes universal invocation envelopes (no live Hermes)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = (
    ROOT
    / "bin"
    / "orama-system"
    / "skills"
    / "hermes-harness"
    / "references"
    / "hermes-universal-invocation-protocol.md"
)


def _load_example(name: str) -> dict:
    """Extract JSON blocks from protocol doc by comment markers in tests."""
    return EXAMPLES[name]


EXAMPLES = {
    "core": {
        "skill_id": "pt-orama-council",
        "args": {},
        "agent_id": "hermes",
    },
    "dispatch": {
        "skill_id": "pt-orama-council",
        "args": {"task": "review plan"},
        "agent_id": "hermes",
        "executor_id": "codex",
        "harness": "hermes",
        "orama_system_root": "$ORAMA_SYSTEM_PATH",
        "canonical_skill_root": "bin/orama-system/skills",
        "transport": {"partner": "codex", "profile": "fanout"},
    },
    "result_ok": {
        "status": "ok",
        "files_modified": [],
        "follow_up_actions": [],
    },
    "result_blocked": {
        "status": "blocked",
        "files_modified": [],
        "follow_up_actions": ["set HERMES_GIT_BASH_PATH"],
        "warnings": ["path casing mismatch: uLtrathink vs ultrathink"],
    },
}

CORE_ENVELOPE_KEYS = frozenset({"skill_id", "args", "agent_id"})
VALID_STATUS = frozenset({"ok", "needs_input", "partial", "error", "blocked"})
PLACEHOLDER_PREFIXES = ("$", "%")


def validate_core_envelope(envelope: dict) -> list[str]:
    errors: list[str] = []
    missing = CORE_ENVELOPE_KEYS - envelope.keys()
    if missing:
        errors.append(f"missing core keys: {sorted(missing)}")
    if not isinstance(envelope.get("args"), dict):
        errors.append("args must be a JSON object")
    for key in ("orama_system_root", "openclaw_home"):
        val = envelope.get(key)
        if val is not None and not str(val).startswith(PLACEHOLDER_PREFIXES):
            if "\\" in str(val) or str(val).startswith("/Users/"):
                errors.append(f"{key} must use env placeholder in committed examples")
    transport = envelope.get("transport")
    if transport is not None:
        if not isinstance(transport, dict):
            errors.append("transport must be an object")
        elif "partner" not in transport:
            errors.append("transport.partner required for audit trail")
    return errors


def validate_core_result(result: dict) -> list[str]:
    errors: list[str] = []
    for key in ("status", "files_modified", "follow_up_actions"):
        if key not in result:
            errors.append(f"missing result key: {key}")
    status = result.get("status")
    if status not in VALID_STATUS:
        errors.append(f"invalid status: {status}")
    if not isinstance(result.get("files_modified"), list):
        errors.append("files_modified must be an array")
    if not isinstance(result.get("follow_up_actions"), list):
        errors.append("follow_up_actions must be an array")
    if status in ("needs_input", "blocked", "error") and not result.get("follow_up_actions"):
        errors.append("follow_up_actions required when status is blocked/needs_input/error")
    return errors


def test_protocol_reference_exists():
    assert PROTOCOL.is_file(), "hermes-universal-invocation-protocol.md must exist"


def test_core_envelope_valid():
    assert validate_core_envelope(EXAMPLES["core"]) == []


def test_dispatch_envelope_valid():
    assert validate_core_envelope(EXAMPLES["dispatch"]) == []


def test_dispatch_has_dual_identity():
    env = EXAMPLES["dispatch"]
    assert env["agent_id"] == "hermes"
    assert env["executor_id"] == "codex"


def test_dispatch_transport_audit_fields():
    t = EXAMPLES["dispatch"]["transport"]
    assert t["partner"] == "codex"
    assert t["profile"] == "fanout"


def test_result_ok_valid():
    assert validate_core_result(EXAMPLES["result_ok"]) == []


def test_result_blocked_requires_follow_up():
    assert validate_core_result(EXAMPLES["result_blocked"]) == []


def test_missing_core_keys_rejected():
    errors = validate_core_envelope({"skill_id": "x"})
    assert any("missing core keys" in e for e in errors)


def test_skill_md_links_protocol():
    skill = (
        ROOT
        / "bin"
        / "orama-system"
        / "skills"
        / "hermes-harness"
        / "SKILL.md"
    )
    text = skill.read_text(encoding="utf-8")
    assert "hermes-universal-invocation-protocol.md" in text
    assert "executor_id" in text
    assert "transport" in text


def test_lesson_mining_command_exists():
    cmd = (
        ROOT
        / "bin"
        / "orama-system"
        / "skills"
        / "hermes-harness"
        / "commands"
        / "pt-orama-lesson-mining"
        / "SKILL.md"
    )
    assert cmd.is_file()
    assert "learn.py" in cmd.read_text(encoding="utf-8")
