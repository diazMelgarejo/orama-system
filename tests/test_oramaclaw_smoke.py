"""Wheel-install smoke tests for the oramaclaw package.

These tests verify that the package is importable, all public submodules
load without side-effects, and the top-level entrypoint is discoverable —
matching what a consumer would see after ``pip install orama-system``.
"""
from __future__ import annotations

import importlib
import subprocess
import sys


def test_package_importable():
    import oramaclaw  # noqa: F401 — must not raise


def test_types_submodule():
    from oramaclaw.types import (
        ConfigTarget,
        ControlManifest,
        Resource,
        ResourceKind,
        MergePolicy,
        Conflict,
        PendingResolution,
        GatewayConfig,
        GatewayApplyResult,
        StaleConfiguration,
        GatewayUnavailable,
        GatewayRejected,
        OfflineOperationNotAllowed,
    )
    assert ResourceKind.AGENT.value == "agent"
    assert MergePolicy.COOPERATIVE.value == "cooperative"


def test_schema_submodule():
    from oramaclaw.schema import parse_manifest
    assert callable(parse_manifest)


def test_target_submodule():
    from oramaclaw.target import resolve_target, TargetCatalog, TargetNotFound
    assert callable(resolve_target)
    assert callable(TargetCatalog.load)


def test_store_submodule():
    from oramaclaw.store import ControlStore, LockHeld, JOURNAL_CAP, LOCK_STALE_SECONDS
    assert JOURNAL_CAP == 200
    assert LOCK_STALE_SECONDS == 300


def test_transport_submodule():
    from oramaclaw.transport import (
        GatewayTransport,
        OfflineTransport,
        make_transport,
        SubprocessRunner,
    )
    assert callable(make_transport)


def test_merge_submodule():
    from oramaclaw.merge import plan_resource, MergePlan, FieldAction
    assert callable(plan_resource)


def test_engine_submodule():
    from oramaclaw.engine import ControlEngine
    assert callable(ControlEngine)


def test_cli_submodule():
    from oramaclaw.cli import main
    assert callable(main)


def test_cli_help_exit_zero():
    import os
    from pathlib import Path
    src = str(Path(__file__).parent.parent / "src")
    env = {**os.environ, "PYTHONPATH": src}
    result = subprocess.run(
        [sys.executable, "-m", "oramaclaw", "--help"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower() or "usage:" in result.stderr.lower()


def test_no_alphaclaw_imports():
    """oramaclaw must not import alphaclaw or perpetua_core at import time."""
    for mod_name in list(sys.modules.keys()):
        if "alphaclaw" in mod_name or "perpetua_core" in mod_name:
            assert False, f"forbidden module loaded: {mod_name}"
