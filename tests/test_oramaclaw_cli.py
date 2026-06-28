"""Tests for oramaclaw.cli — V1 control plane CLI.

All external dependencies (ControlEngine, parse_manifest, resolve_target,
ControlStore) are patched at the oramaclaw.cli module boundary so tests
run without real disk state, a live gateway, or a real engine.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from oramaclaw.cli import main
from oramaclaw.types import ControlResult


# ── Helpers ───────────────────────────────────────────────────────────────────

def _result(
    state: str,
    applied: tuple = (),
    auto_woven: tuple = (),
    conflicts: tuple = (),
    warnings: tuple = (),
) -> ControlResult:
    return ControlResult(
        transaction_id="tx-test",
        state=state,  # type: ignore[arg-type]
        applied=applied,
        auto_woven=auto_woven,
        conflicts=conflicts,
        warnings=warnings,
    )


def _fake_target() -> MagicMock:
    target = MagicMock()
    target.workspace_root = Path("/tmp/fake-workspace")
    return target


def _fake_manifest(resources: tuple = ()) -> MagicMock:
    manifest = MagicMock()
    manifest.resources = resources
    manifest.target = None
    return manifest


# ── Fixtures & shared patches ─────────────────────────────────────────────────

@pytest.fixture()
def mock_resolve_target():
    """Patch resolve_target in the cli module to return a fake ConfigTarget."""
    with patch("oramaclaw.cli.resolve_target", return_value=_fake_target()) as m:
        yield m


@pytest.fixture()
def mock_parse_manifest():
    """Patch parse_manifest to return a fake manifest."""
    with patch("oramaclaw.cli.parse_manifest", return_value=_fake_manifest()) as m:
        yield m


# ── 1. apply → committed → exit 0 ────────────────────────────────────────────

def test_apply_committed_exits_0(
    mock_resolve_target,
    mock_parse_manifest,
    tmp_path,
    capsys,
):
    fake_manifest_file = tmp_path / "manifest.json"
    fake_manifest_file.write_text("{}")

    engine_mock = MagicMock()
    engine_mock.apply_manifest.return_value = _result("committed", applied=("res:a",))

    with patch("oramaclaw.cli.ControlEngine", return_value=engine_mock):
        code = main(["apply", str(fake_manifest_file)])

    assert code == 0
    out = capsys.readouterr().out
    assert "committed" in out


# ── 2. apply → needs_input → exit 1 ──────────────────────────────────────────

def test_apply_needs_input_exits_1(
    mock_resolve_target,
    mock_parse_manifest,
    tmp_path,
):
    fake_manifest_file = tmp_path / "manifest.json"
    fake_manifest_file.write_text("{}")

    engine_mock = MagicMock()
    engine_mock.apply_manifest.return_value = _result("needs_input")

    with patch("oramaclaw.cli.ControlEngine", return_value=engine_mock):
        code = main(["apply", str(fake_manifest_file)])

    assert code == 1


# ── 3. apply → gateway_unavailable → exit 2 ──────────────────────────────────

def test_apply_gateway_unavailable_exits_2(
    mock_resolve_target,
    mock_parse_manifest,
    tmp_path,
):
    fake_manifest_file = tmp_path / "manifest.json"
    fake_manifest_file.write_text("{}")

    engine_mock = MagicMock()
    engine_mock.apply_manifest.return_value = _result("gateway_unavailable")

    with patch("oramaclaw.cli.ControlEngine", return_value=engine_mock):
        code = main(["apply", str(fake_manifest_file)])

    assert code == 2


# ── 4. apply --dry-run skips engine ──────────────────────────────────────────

def test_apply_dry_run_flag_skips_engine(
    mock_resolve_target,
    mock_parse_manifest,
    tmp_path,
    capsys,
):
    fake_manifest_file = tmp_path / "manifest.json"
    fake_manifest_file.write_text("{}")

    engine_class_mock = MagicMock()

    with patch("oramaclaw.cli.ControlEngine", engine_class_mock):
        code = main(["apply", str(fake_manifest_file), "--dry-run"])

    # Engine must never be instantiated or called.
    engine_class_mock.assert_not_called()
    assert code == 0
    out = capsys.readouterr().out
    assert "dry-run" in out


# ── 5. status prints last transaction ────────────────────────────────────────

def test_status_prints_last_tx(mock_resolve_target, capsys):
    store_mock = MagicMock()
    store_mock.__enter__ = lambda s: s
    store_mock.__exit__ = MagicMock(return_value=False)
    store_mock.last_transaction.return_value = {
        "state": "committed",
        "transaction_id": "tx-abc",
    }
    store_mock.open_conflicts.return_value = []

    with patch("oramaclaw.cli.ControlStore") as cs_class:
        cs_class.open.return_value = store_mock
        code = main(["status"])

    assert code == 0
    out = capsys.readouterr().out
    assert "committed" in out


# ── 6. resolve → success → exit 0 ────────────────────────────────────────────

def test_resolve_success(mock_resolve_target, capsys):
    store_mock = MagicMock()
    store_mock.__enter__ = lambda s: s
    store_mock.__exit__ = MagicMock(return_value=False)
    store_mock.resolve_pending.return_value = True

    with patch("oramaclaw.cli.ControlStore") as cs_class:
        cs_class.open.return_value = store_mock
        code = main(["resolve", "res-id-001", "apply-desired"])

    assert code == 0
    out = capsys.readouterr().out
    assert "Resolved" in out
    assert "res-id-001" in out
    assert "apply-desired" in out


# ── 7. resolve → not found → exit 1 ─────────────────────────────────────────

def test_resolve_not_found_exits_1(mock_resolve_target, capsys):
    store_mock = MagicMock()
    store_mock.__enter__ = lambda s: s
    store_mock.__exit__ = MagicMock(return_value=False)
    store_mock.resolve_pending.return_value = False

    with patch("oramaclaw.cli.ControlStore") as cs_class:
        cs_class.open.return_value = store_mock
        code = main(["resolve", "missing-id", "keep-current"])

    assert code == 1


# ── 8. targets list prints names ─────────────────────────────────────────────

def test_targets_list_prints_names(capsys):
    catalog_mock = MagicMock()
    catalog_mock.names.return_value = ["dev", "prod"]

    with patch("oramaclaw.cli.TargetCatalog") as tc_class:
        tc_class.load.return_value = catalog_mock
        code = main(["targets", "list"])

    assert code == 0
    out = capsys.readouterr().out
    assert "dev" in out
    assert "prod" in out


# ── 9. $ORAMACLAW_TARGETS_PATH appears in --help output ──────────────────────

def test_oramaclaw_targets_path_in_help(capsys):
    # main() catches SystemExit and returns an int rather than raising.
    # The --target help text (mentioning $ORAMACLAW_TARGETS_PATH) is on the
    # subcommand parser, so request the apply subcommand help.
    code = main(["apply", "--help"])

    # argparse help exits with code 0; main() translates that to 0.
    assert code == 0
    out = capsys.readouterr().out
    assert "$ORAMACLAW_TARGETS_PATH" in out
