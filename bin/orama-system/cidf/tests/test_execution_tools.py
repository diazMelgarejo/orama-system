"""
tests/test_execution_tools.py
──────────────────────────────
Boundary-validation tests for bin/agents/executor/execution_tools.py's
cidf_insert() wrapper -- specifically the timing-estimate fields forwarded
into Task, which decide()/automation_justified() compare with `>` once both
are known.

Run:
    pytest bin/orama-system/cidf/tests/test_execution_tools.py -v
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "agents", "executor"))

import pytest

from execution_tools import _validate_timing_estimate


def test_validate_timing_estimate_accepts_int():
    assert _validate_timing_estimate({"estimated_setup_seconds": 10}, "estimated_setup_seconds") == 10.0


def test_validate_timing_estimate_accepts_float():
    assert _validate_timing_estimate({"estimated_setup_seconds": 10.5}, "estimated_setup_seconds") == 10.5


def test_validate_timing_estimate_accepts_none():
    assert _validate_timing_estimate({}, "estimated_setup_seconds") is None
    assert _validate_timing_estimate({"estimated_setup_seconds": None}, "estimated_setup_seconds") is None


def test_validate_timing_estimate_rejects_string():
    with pytest.raises(TypeError, match="estimated_setup_seconds"):
        _validate_timing_estimate({"estimated_setup_seconds": "10"}, "estimated_setup_seconds")


def test_validate_timing_estimate_rejects_bool():
    # bool is a subclass of int in Python; explicitly reject it so a caller
    # passing e.g. estimated_run_seconds=True can't silently become 1.0.
    with pytest.raises(TypeError, match="estimated_run_seconds"):
        _validate_timing_estimate({"estimated_run_seconds": True}, "estimated_run_seconds")


def test_validate_timing_estimate_two_strings_would_have_compared_lexicographically():
    """Regression test for the exact scenario CodeRabbit flagged: two
    string timing values would previously compare lexicographically
    ("9" > "10" is True as strings) instead of raising. Confirm both
    fields are now rejected before ever reaching that comparison."""
    with pytest.raises(TypeError):
        _validate_timing_estimate({"estimated_setup_seconds": "9"}, "estimated_setup_seconds")
    with pytest.raises(TypeError):
        _validate_timing_estimate({"estimated_run_seconds": "10"}, "estimated_run_seconds")
