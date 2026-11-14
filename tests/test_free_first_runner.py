"""The free-first profile never selects a paid model, and 1113 stops the chain."""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = (
    _ROOT
    / "bin/orama-system/scripts/cline-provider-profiles/free_first_runner.py"
)
_spec = importlib.util.spec_from_file_location("free_first_runner", _SCRIPT)
runner = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(runner)


def test_profile_starts_on_the_free_primary_and_excludes_paid() -> None:
    profile = runner.load_profile()
    assert profile["financial_mode"] == "free_only"
    assert profile["policy_id"] == "bigmodel-free-first-2026-11-13-v1"
    assert runner.next_model(profile, []) == "glm-4.7-flash"
    assert "glm-5.3-flash" not in profile["resolution"]["models"]


def test_1113_stops_before_the_next_free_model() -> None:
    profile = runner.load_profile()
    stopped = runner.next_model(
        profile,
        [{"model_id": "glm-4.7-flash", "http_status": 429, "code": "1113"}],
    )
    assert stopped is None
    throttled = runner.next_model(
        profile,
        [{"model_id": "glm-4.7-flash", "http_status": 429, "code": ""}],
    )
    assert throttled == "glm-4.5-flash"


def test_policy_pin_matches_the_sibling_blob_when_present() -> None:
    pin_line = (_ROOT / "config/bigmodel-free-first-policy.sha256").read_text().split()[0]
    assert len(pin_line) == 64
    sibling = Path(os.environ.get("PERPETUA_TOOLS_ROOT", _ROOT.parent / "Perpetua-Tools"))
    policy = sibling / "config/bigmodel-free-first-policy.json"
    if not policy.is_file():
        return
    digest = hashlib.sha256(policy.read_bytes()).hexdigest()
    assert digest == pin_line
