"""Tests for switch_cline_provider.py's backup/atomicity/immutability logic.

Per docs/TDD.md: idempotent read-modify-write flows require a run-twice,
second-run-is-a-no-op test. These tests operate entirely on tmp_path
fixtures -- no real ~/.cline state or secrets are touched.
"""
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone

import pytest

_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "bin", "orama-system", "scripts", "cline-provider-profiles", "switch_cline_provider.py",
)
_spec = importlib.util.spec_from_file_location("switch_cline_provider", _MODULE_PATH)
switch_cline_provider = importlib.util.module_from_spec(_spec)
sys.modules["switch_cline_provider"] = switch_cline_provider
_spec.loader.exec_module(switch_cline_provider)

switch_provider = switch_cline_provider.switch_provider


def _write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


def _providers_cfg(openai_compatible_settings=None, extra_providers=None):
    providers = dict(extra_providers or {})
    if openai_compatible_settings is not None:
        providers["openai-compatible"] = {
            "settings": openai_compatible_settings,
            "updatedAt": "2020-01-01T00:00:00+00:00",
            "tokenSource": "test-seed",
        }
    return {"lastUsedProvider": "anthropic", "providers": providers}


def _settings(model="model-a", api_key="key-a"):
    return {
        "provider": "openai-compatible",
        "apiKey": api_key,
        "model": model,
        "baseUrl": "https://example.test/v1",
        "headers": {},
        "timeout": 30000,
        "reasoning": {"effort": "high"},
    }


@pytest.fixture
def workspace(tmp_path):
    providers_path = tmp_path / "providers.json"
    backup_dir = tmp_path / "history"
    backup_dir.mkdir()
    tmpl_path = tmp_path / "profile-a.json.tmpl"
    with open(tmpl_path, "w") as f:
        json.dump({"settings": {**_settings("model-a", "${A_KEY}"), "apiKey": "${A_KEY}"}}, f)
    return providers_path, backup_dir, tmpl_path


def test_first_switch_backs_up_prior_state_and_activates(workspace):
    providers_path, backup_dir, tmpl_path = workspace
    _write_json(providers_path, _providers_cfg(_settings("model-prior", "key-prior")))

    status = switch_provider(
        str(providers_path), str(tmpl_path), "profile-a", str(backup_dir),
        env={"A_KEY": "key-a"},
    )

    assert status == "activated"
    backups = sorted(os.listdir(backup_dir))
    assert len(backups) == 1
    snapshot = json.load(open(backup_dir / backups[0]))
    assert snapshot["settings"]["model"] == "model-prior"

    new_cfg = json.load(open(providers_path))
    assert new_cfg["providers"]["openai-compatible"]["settings"]["model"] == "model-a"
    assert new_cfg["providers"]["openai-compatible"]["settings"]["apiKey"] == "key-a"


def test_running_the_same_profile_twice_is_a_true_no_op(workspace):
    """docs/TDD.md idempotency requirement: run twice, second run is a no-op."""
    providers_path, backup_dir, tmpl_path = workspace
    _write_json(providers_path, _providers_cfg(_settings("model-prior", "key-prior")))

    first = switch_provider(
        str(providers_path), str(tmpl_path), "profile-a", str(backup_dir),
        env={"A_KEY": "key-a"},
    )
    assert first == "activated"
    backups_after_first = sorted(os.listdir(backup_dir))

    second = switch_provider(
        str(providers_path), str(tmpl_path), "profile-a", str(backup_dir),
        env={"A_KEY": "key-a"},
    )

    assert second == "no-op"
    assert sorted(os.listdir(backup_dir)) == backups_after_first, (
        "re-running the same profile must not create a second backup"
    )


def test_cycling_between_profiles_backs_up_each_distinct_outgoing_state(workspace):
    """prior -> a -> b -> a: each switch replaces a genuinely different
    outgoing state, so each transition's outgoing state gets its own
    backup (prior, then a, then b) -- 3 backups, not deduped, because
    none of them is a repeat of the immediately-preceding one."""
    providers_path, backup_dir, tmpl_path = workspace
    tmpl_b = tmpl_path.parent / "profile-b.json.tmpl"
    with open(tmpl_b, "w") as f:
        json.dump({"settings": {**_settings("model-b", "${B_KEY}"), "apiKey": "${B_KEY}"}}, f)

    _write_json(providers_path, _providers_cfg(_settings("model-prior", "key-prior")))

    switch_provider(str(providers_path), str(tmpl_path), "profile-a", str(backup_dir), env={"A_KEY": "key-a"})
    switch_provider(str(providers_path), str(tmpl_b), "profile-b", str(backup_dir), env={"B_KEY": "key-b"})
    switch_provider(str(providers_path), str(tmpl_path), "profile-a", str(backup_dir), env={"A_KEY": "key-a"})

    models_backed_up = [json.load(open(backup_dir / f))["settings"]["model"] for f in sorted(os.listdir(backup_dir))]
    assert models_backed_up == ["model-prior", "model-a", "model-b"]


def test_backup_rotation_caps_at_ten(workspace, monkeypatch):
    providers_path, backup_dir, tmpl_path = workspace
    _write_json(providers_path, _providers_cfg(_settings("model-0", "key-0")))

    for i in range(1, 13):
        tmpl = tmpl_path.parent / f"profile-{i}.json.tmpl"
        with open(tmpl, "w") as f:
            json.dump({"settings": {**_settings(f"model-{i}", f"key-{i}"), "apiKey": f"${{K{i}}}"}}, f)
        switch_provider(
            str(providers_path), str(tmpl), f"profile-{i}", str(backup_dir),
            env={f"K{i}": f"key-{i}"},
            now=datetime(2026, 1, i, tzinfo=timezone.utc),
        )

    backups = sorted(os.listdir(backup_dir))
    assert len(backups) == 10, "must rotate to a maximum of 10 snapshots"
    oldest_kept = json.load(open(backup_dir / backups[0]))
    assert oldest_kept["settings"]["model"] == "model-2", "oldest backups (0, 1) must be evicted first"


def test_unrelated_provider_entries_are_preserved_not_mutated(workspace):
    providers_path, backup_dir, tmpl_path = workspace
    extra = {"anthropic": {"settings": {"apiKey": "anthropic-key"}}, "ollama": {"settings": {}}}
    original_cfg = _providers_cfg(_settings("model-prior", "key-prior"), extra_providers=extra)
    _write_json(providers_path, original_cfg)

    switch_provider(str(providers_path), str(tmpl_path), "profile-a", str(backup_dir), env={"A_KEY": "key-a"})

    # Original in-memory dict must be untouched -- proves construction
    # builds new objects rather than mutating cfg/outgoing in place.
    assert original_cfg["providers"]["openai-compatible"]["settings"]["model"] == "model-prior"

    new_cfg = json.load(open(providers_path))
    assert new_cfg["providers"]["anthropic"] == extra["anthropic"]
    assert new_cfg["providers"]["ollama"] == extra["ollama"]


def test_missing_env_var_raises_before_any_write(workspace):
    providers_path, backup_dir, tmpl_path = workspace
    _write_json(providers_path, _providers_cfg(_settings("model-prior", "key-prior")))

    with pytest.raises(SystemExit):
        switch_provider(str(providers_path), str(tmpl_path), "profile-a", str(backup_dir), env={})

    assert os.listdir(backup_dir) == []
    assert json.load(open(providers_path))["providers"]["openai-compatible"]["settings"]["model"] == "model-prior"


def test_atomic_write_cleans_up_temp_file_on_serialization_failure(tmp_path):
    target = tmp_path / "providers.json"
    target.write_text('{"original": true}')

    class Unserializable:
        pass

    with pytest.raises(TypeError):
        switch_cline_provider.atomic_write_json(str(target), {"bad": Unserializable()})

    assert json.load(open(target)) == {"original": True}, "original file must be untouched on failure"
    leftovers = [f for f in os.listdir(tmp_path) if f.startswith(".tmp-")]
    assert leftovers == [], "temp file must be cleaned up, not left behind"


def test_main_wires_lock_and_switch_and_prints_activated(workspace, capsys):
    providers_path, backup_dir, tmpl_path = workspace
    _write_json(providers_path, _providers_cfg(_settings("model-prior", "key-prior")))
    lock_path = tmpl_path.parent / "switch.lock"
    os.environ["A_KEY"] = "key-a"
    try:
        switch_cline_provider.main([
            "switch_cline_provider.py", str(providers_path), str(tmpl_path),
            "profile-a", str(backup_dir), str(lock_path),
        ])
    finally:
        del os.environ["A_KEY"]

    assert "Activated profile: profile-a" in capsys.readouterr().out
    assert lock_path.exists(), "lock file must be created"


def test_main_prints_no_changes_when_already_on_profile(workspace, capsys):
    providers_path, backup_dir, tmpl_path = workspace
    _write_json(providers_path, _providers_cfg(_settings("model-a", "key-a")))
    lock_path = tmpl_path.parent / "switch.lock"
    os.environ["A_KEY"] = "key-a"
    try:
        switch_cline_provider.main([
            "switch_cline_provider.py", str(providers_path), str(tmpl_path),
            "profile-a", str(backup_dir), str(lock_path),
        ])
    finally:
        del os.environ["A_KEY"]

    assert "Already on profile: profile-a (no changes)" in capsys.readouterr().out
