"""Pytest defaults for orama-system — keep legacy tests unauthenticated in CI."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

import pytest


@pytest.fixture(autouse=True)
def _orama_insecure_dev_for_tests(monkeypatch):
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "1")
    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN", raising=False)


# ── oramaclaw engine test helpers ────────────────────────────────────────────
# Used by tests/test_oramaclaw_engine.py (Task 5). Importing oramaclaw here
# is conditional so legacy tests keep working even before the package exists.

def _try_import_oramaclaw():
    try:
        from oramaclaw.types import (  # noqa: PLC0415
            ConfigTarget, ControlManifest, MergePolicy, Resource, ResourceKind,
        )
        return ConfigTarget, ControlManifest, MergePolicy, Resource, ResourceKind
    except ImportError:
        return None


def provider_manifest_with_medium_effort(tmp_path: Path | None = None) -> Any:
    """Return a ControlManifest for the codex-app-server provider with effort=medium.

    Used in Task 5 engine tests to exercise the cooperative-drift auto-weave path.
    The manifest's target points to tmp_path so it never touches live config.
    """
    imported = _try_import_oramaclaw()
    if imported is None:
        pytest.skip("oramaclaw package not yet installed")
    ConfigTarget, ControlManifest, MergePolicy, Resource, ResourceKind = imported
    import hashlib, json  # noqa: E401

    target_dir = tmp_path or Path("/tmp/oramaclaw-test-fixture")
    spec: Mapping[str, Any] = {
        "api": "openai-completions",
        "baseUrl": "http://127.0.0.1:61234/v1",
        "authReference": "~/.codex/config.toml",
        "models": [{"id": "gpt-5.5", "name": "Codex — GPT-5.5", "contextWindow": 200000}],
        "effort": "medium",
    }
    resource = Resource(
        kind=ResourceKind.PROVIDER,
        identifier="codex-app-server",
        manager="codex-binder",
        spec=spec,
        managed_paths=("/models/providers/codex-app-server", "/models/providers/codex-app-server/effort"),
        policy=MergePolicy.COOPERATIVE,
    )
    raw = json.dumps({"version": 1, "resources": [{"kind": "provider", "id": "codex-app-server"}]}).encode()
    return ControlManifest(
        version=1,
        target=ConfigTarget(
            workspace_root=target_dir / "workspace",
            config_path=target_dir / "openclaw.json",
            state_dir=target_dir,
        ),
        resources=(resource,),
        source_path=Path("tests/fixtures/oramaclaw-cooperative-drift.json"),
        source_fingerprint=hashlib.sha256(raw).hexdigest(),
    )


class NoResponseInteraction:
    """Interaction stub that never provides a user response — simulates the 90-second timeout.

    Used in Task 5 engine tests to exercise the auto-weave path without
    starting a real TTY or portal session.
    """

    def choose(
        self,
        prompt: str,
        choices: tuple[str, ...],
        timeout_seconds: int,
        resolution_id: str,
    ) -> str | None:
        return None
