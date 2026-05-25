"""Tests for MCP path boundary (security fix 4)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from utils.mcp_path_boundary import (  # noqa: E402
    get_approved_roots,
    redact_log_text,
    resolve_allowed_path,
)


def test_allows_path_under_explicit_root(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    inside = sandbox / "inside.txt"
    inside.write_text("ok", encoding="utf-8")
    ok, resolved, err = resolve_allowed_path(
        "inside.txt", roots=[sandbox], base_for_relative=sandbox
    )
    assert ok is True
    assert err is None
    assert resolved == inside.resolve()


def test_rejects_absolute_path_outside_roots(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("nope", encoding="utf-8")
    ok, _, err = resolve_allowed_path(outside, roots=[sandbox])
    assert ok is False
    assert err is not None
    assert "outside approved MCP roots" in err


@pytest.mark.skipif(os.name == "nt", reason="symlink test unix-only")
def test_rejects_symlink_escape(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    link = sandbox / "link"
    link.symlink_to(outside)
    ok, _, err = resolve_allowed_path(link, roots=[sandbox])
    assert ok is False
    assert err is not None
    assert "symlink" in err.lower() or "escapes" in err.lower()


def test_redact_log_text_strips_secrets() -> None:
    raw = "SETUP_PASSWORD=hunter2\nuser@example.com\nAIzaSyDUMMYKEY123456789012345678901"
    redacted = redact_log_text(raw)
    assert "hunter2" not in redacted
    assert "user@example.com" not in redacted
    assert "AIzaSyDUMMY" not in redacted
    assert "[REDACTED]" in redacted


def test_get_approved_roots_parses_delimiter_list(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    prev = os.environ.get("MCP_APPROVED_ROOTS")
    os.environ["MCP_APPROVED_ROOTS"] = f"{a}{os.pathsep}{b}"
    try:
        roots = get_approved_roots()
        assert a.resolve() in roots
        assert b.resolve() in roots
    finally:
        if prev is None:
            os.environ.pop("MCP_APPROVED_ROOTS", None)
        else:
            os.environ["MCP_APPROVED_ROOTS"] = prev
