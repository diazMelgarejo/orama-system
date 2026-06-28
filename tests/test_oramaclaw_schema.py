from __future__ import annotations

import json
from pathlib import Path

import pytest

from oramaclaw.schema import ManifestValidationError, parse_manifest


def _manifest(target: object | None = None, spec: object | None = None) -> dict:
    data = {
        "version": 1,
        "resources": [{
            "kind": "provider",
            "id": "test-provider",
            "manager": "test",
            "policy": "strict",
            "spec": spec if spec is not None else {},
            "managed_paths": ["/models/providers/test-provider"],
        }],
    }
    if target is not None:
        data["target"] = target
    return data


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_parse_manifest_allows_cli_supplied_target(tmp_path):
    manifest = parse_manifest(_write_manifest(tmp_path, _manifest()))
    assert manifest.target is None


def test_parse_manifest_rejects_nested_raw_credential(tmp_path):
    path = _write_manifest(tmp_path, _manifest(spec={"auth": {"token": "secret"}}))

    with pytest.raises(ManifestValidationError, match=r"spec.auth.token"):
        parse_manifest(path)


@pytest.mark.parametrize("field", ("workspace_root", "config_path", "state_dir"))
def test_parse_manifest_rejects_non_string_target_field(tmp_path, field):
    target = {
        "workspace_root": "__TMP__/workspace",
        "config_path": "__TMP__/openclaw.json",
        "state_dir": "__TMP__",
    }
    target[field] = 42
    path = _write_manifest(tmp_path, _manifest(target=target))

    with pytest.raises(ManifestValidationError, match=rf"target\.{field} must be a non-empty string"):
        parse_manifest(path)
