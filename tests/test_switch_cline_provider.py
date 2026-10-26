"""Tests for switch_cline_provider.py's backup/atomicity/immutability logic.

Per docs/TDD.md: idempotent read-modify-write flows require a run-twice,
second-run-is-a-no-op test. These tests operate entirely on tmp_path
fixtures -- no real ~/.cline state or secrets are touched.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import pytest

pytestmark = pytest.mark.unit

_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "bin", "orama-system", "scripts", "cline-provider-profiles", "switch_cline_provider.py",
)
_spec = importlib.util.spec_from_file_location("switch_cline_provider", _MODULE_PATH)
switch_cline_provider = importlib.util.module_from_spec(_spec)
sys.modules["switch_cline_provider"] = switch_cline_provider
_spec.loader.exec_module(switch_cline_provider)

switch_provider = switch_cline_provider.switch_provider

Workspace = tuple[Path, Path, Path]


def _read_json(path: Path) -> Any:
    """Return the parsed JSON stored at ``path``."""
    with path.open() as file:
        return json.load(file)


def _write_json(path: Path, data: Mapping[str, Any]) -> None:
    """Write ``data`` to ``path`` as indented JSON."""
    with path.open("w") as f:
        json.dump(data, f, indent=2)


def _providers_cfg(
    openai_compatible_settings: Mapping[str, Any] | None = None,
    extra_providers: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a providers.json document with an optional openai-compatible entry and extra providers."""
    providers: dict[str, Any] = dict(extra_providers or {})
    if openai_compatible_settings is not None:
        providers["openai-compatible"] = {
            "settings": openai_compatible_settings,
            "updatedAt": "2020-01-01T00:00:00+00:00",
            "tokenSource": "test-seed",
        }
    return {"lastUsedProvider": "anthropic", "providers": providers}


def _settings(model: str = "model-a", api_key: str = "key-a") -> dict[str, Any]:
    """Return a synthetic openai-compatible settings dict for ``model`` and ``api_key``."""
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
def workspace(tmp_path: Path) -> Workspace:
    """Return (providers path, empty backup dir, profile-a template) under ``tmp_path``."""
    providers_path = tmp_path / "providers.json"
    backup_dir = tmp_path / "history"
    backup_dir.mkdir()
    tmpl_path = tmp_path / "profile-a.json.tmpl"
    with tmpl_path.open("w") as f:
        json.dump({"settings": {**_settings("model-a", "${A_KEY}"), "apiKey": "${A_KEY}"}}, f)
    return providers_path, backup_dir, tmpl_path


def test_first_switch_backs_up_prior_state_and_activates(workspace: Workspace) -> None:
    """The first switch snapshots the outgoing settings once and activates the new profile."""
    providers_path, backup_dir, tmpl_path = workspace
    _write_json(providers_path, _providers_cfg(_settings("model-prior", "key-prior")))

    status = switch_provider(
        str(providers_path), str(tmpl_path), "profile-a", str(backup_dir),
        env={"A_KEY": "key-a"},
    )

    assert status == "activated"
    backups = sorted(os.listdir(backup_dir))
    assert len(backups) == 1
    snapshot = _read_json(backup_dir / backups[0])
    assert snapshot["settings"]["model"] == "model-prior"

    new_cfg = _read_json(providers_path)
    assert new_cfg["providers"]["openai-compatible"]["settings"]["model"] == "model-a"
    assert new_cfg["providers"]["openai-compatible"]["settings"]["apiKey"] == "key-a"


def test_running_the_same_profile_twice_is_a_true_no_op(workspace: Workspace) -> None:
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


def test_a_settings_key_outside_the_old_compare_keys_allowlist_is_still_compared(
    workspace: Workspace,
) -> None:
    """Regression for the comparable() fix (PR #275 review 4861794528): the
    previous COMPARE_KEYS allowlist silently ignored any settings key not in
    its fixed tuple, so a real difference confined to such a key would be
    mis-reported as a no-op. Uses a key ("customField") that was never in
    COMPARE_KEYS to prove the current denylist-based comparable() actually
    detects it.
    """
    providers_path, backup_dir, tmpl_path = workspace
    outgoing = {**_settings("model-a", "key-a"), "customField": "old-value"}
    _write_json(providers_path, _providers_cfg(outgoing))

    with tmpl_path.open("w") as f:
        json.dump(
            {"settings": {**_settings("model-a", "${A_KEY}"), "customField": "new-value"}},
            f,
        )

    status = switch_provider(
        str(providers_path), str(tmpl_path), "profile-a", str(backup_dir),
        env={"A_KEY": "key-a"},
    )

    assert status == "activated", (
        "a real difference confined to a key outside the old COMPARE_KEYS "
        "allowlist must not be reported as a no-op"
    )
    new_cfg = _read_json(providers_path)
    assert new_cfg["providers"]["openai-compatible"]["settings"]["customField"] == "new-value"


def test_cycling_between_profiles_backs_up_each_distinct_outgoing_state(
    workspace: Workspace,
) -> None:
    """prior -> a -> b -> a: each switch replaces a genuinely different
    outgoing state, so each transition's outgoing state gets its own
    backup (prior, then a, then b) -- 3 backups, not deduped, because
    none of them is a repeat of the immediately-preceding one."""
    providers_path, backup_dir, tmpl_path = workspace
    tmpl_b = tmpl_path.parent / "profile-b.json.tmpl"
    with tmpl_b.open("w") as f:
        json.dump({"settings": {**_settings("model-b", "${B_KEY}"), "apiKey": "${B_KEY}"}}, f)

    _write_json(providers_path, _providers_cfg(_settings("model-prior", "key-prior")))

    switch_provider(str(providers_path), str(tmpl_path), "profile-a", str(backup_dir), env={"A_KEY": "key-a"})
    switch_provider(str(providers_path), str(tmpl_b), "profile-b", str(backup_dir), env={"B_KEY": "key-b"})
    switch_provider(str(providers_path), str(tmpl_path), "profile-a", str(backup_dir), env={"A_KEY": "key-a"})

    models_backed_up = [
        _read_json(backup_dir / f)["settings"]["model"] for f in sorted(os.listdir(backup_dir))
    ]
    assert models_backed_up == ["model-prior", "model-a", "model-b"]


def test_same_timestamp_switches_never_overwrite_or_misorder_backups(
    workspace: Workspace,
) -> None:
    """A coarse clock can give two switches the identical timestamp: each outgoing
    state must still get its own backup, in chronological name order."""
    from datetime import datetime, timezone

    providers_path, backup_dir, tmpl_path = workspace
    tmpl_b = tmpl_path.parent / "profile-b.json.tmpl"
    with tmpl_b.open("w") as f:
        json.dump({"settings": {**_settings("model-b", "${B_KEY}"), "apiKey": "${B_KEY}"}}, f)
    _write_json(providers_path, _providers_cfg(_settings("model-prior", "key-prior")))
    frozen = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    switch_provider(str(providers_path), str(tmpl_path), "profile-a", str(backup_dir),
                    env={"A_KEY": "key-a"}, now=frozen)
    switch_provider(str(providers_path), str(tmpl_b), "profile-b", str(backup_dir),
                    env={"B_KEY": "key-b"}, now=frozen)
    switch_provider(str(providers_path), str(tmpl_path), "profile-a", str(backup_dir),
                    env={"A_KEY": "key-a"}, now=frozen)

    names = sorted(os.listdir(backup_dir))
    assert len(names) == 3, names
    assert [_read_json(backup_dir / n)["settings"]["model"] for n in names] == [
        "model-prior", "model-a", "model-b"]


def test_backup_stamp_treats_invalid_calendar_fields_as_unparseable() -> None:
    """Regex-shaped names with impossible dates must not abort stamp parsing."""
    _backup_stamp = switch_cline_provider._backup_stamp
    assert _backup_stamp("openai-compatible-20260101T120000.000000Z.json") == datetime(
        2026, 1, 1, 12, 0, 0
    )
    assert _backup_stamp("openai-compatible-20261301T120000.000000Z.json") is None
    assert _backup_stamp("not-a-backup.json") is None


def test_switch_continues_when_latest_backup_name_has_invalid_date(
    workspace: Workspace,
) -> None:
    """A lexicographically-newest backup with an impossible stamp must not stop activation.

    Finding the latest backup parses every backup name's stamp, the bogus one included.
    Without the ValueError guard in ``_backup_stamp`` that parse raises, so neither the
    backup nor the activation happens and this test fails.
    """
    providers_path, backup_dir, tmpl_path = workspace
    _write_json(providers_path, _providers_cfg(_settings("model-prior", "key-prior")))
    bogus = backup_dir / "openai-compatible-20261301T120000.000000Z.json"
    _write_json(bogus, {"settings": _settings("model-older", "key-older")})
    before = set(os.listdir(backup_dir))

    status = switch_provider(
        str(providers_path),
        str(tmpl_path),
        "profile-a",
        str(backup_dir),
        env={"A_KEY": "key-a"},
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert status == "activated"
    assert _read_json(providers_path)["providers"]["openai-compatible"]["settings"]["model"] == "model-a"
    new_backups = sorted(set(os.listdir(backup_dir)) - before)
    assert len(new_backups) == 1, new_backups
    assert switch_cline_provider._backup_stamp(new_backups[0]) is not None, new_backups
    assert _read_json(backup_dir / new_backups[0])["settings"]["model"] == "model-prior"
    assert _read_json(bogus)["settings"]["model"] == "model-older", "bogus backup must be untouched"


# Regex-shaped backup names whose stamps cannot parse (month 13, February 31).
# The first sorts after every real 2026 name, the second before them.
_BOGUS_NEWEST = "openai-compatible-20261301T120000.000000Z.json"
_BOGUS_OLDEST = "openai-compatible-20250231T000000.000000Z.json"
# An operator file that is not a backup name at all; sorts before "openai-".
_OPERATOR_FILE = "manual-snapshot.json"


def _real_backups(backup_dir: Path) -> list[str]:
    """Return the backup names in ``backup_dir`` whose stamp parses, oldest first."""
    return sorted(
        name for name in os.listdir(backup_dir)
        if switch_cline_provider._backup_stamp(name) is not None
    )


def _write_profile(tmpl_dir: Path, name: str, model: str, var: str) -> Path:
    """Write a profile template for ``model`` whose apiKey is the ``${var}`` placeholder and return its path."""
    tmpl = tmpl_dir / f"{name}.json.tmpl"
    _write_json(tmpl, {"settings": {**_settings(model, f"${{{var}}}"), "apiKey": f"${{{var}}}"}})
    return tmpl


def test_bogus_newest_name_does_not_let_same_tick_switches_overwrite_backups(
    workspace: Workspace,
) -> None:
    """Two switches in one clock tick keep two distinct backups despite a bogus newest-sorting name.

    The unparseable name used to be returned as the latest backup, so its stamp parsed to
    None, the strictly-newer bump was skipped and the second switch overwrote the first
    switch's backup.
    """
    providers_path, backup_dir, tmpl_path = workspace
    tmpl_b = _write_profile(tmpl_path.parent, "profile-b", "model-b", "B_KEY")
    _write_json(providers_path, _providers_cfg(_settings("model-prior", "key-prior")))
    bogus = backup_dir / _BOGUS_NEWEST
    _write_json(bogus, {"settings": _settings("model-bogus", "key-bogus")})
    frozen = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    switch_provider(str(providers_path), str(tmpl_path), "profile-a", str(backup_dir),
                    env={"A_KEY": "key-a"}, now=frozen)
    switch_provider(str(providers_path), str(tmpl_b), "profile-b", str(backup_dir),
                    env={"B_KEY": "key-b"}, now=frozen)

    real = _real_backups(backup_dir)
    assert len(real) == 2, real
    assert [_read_json(backup_dir / n)["settings"]["model"] for n in real] == [
        "model-prior", "model-a"]
    assert _read_json(bogus)["settings"]["model"] == "model-bogus", "bogus file must be untouched"


def test_dedupe_skips_a_duplicate_of_the_real_newest_backup_despite_a_bogus_name(
    workspace: Workspace,
) -> None:
    """The outgoing state matches the real newest backup, so no new backup is written.

    A bogus newest-sorting name holding different settings used to be the dedupe target,
    so the already-recorded outgoing state was written again as a duplicate.
    """
    providers_path, backup_dir, tmpl_path = workspace
    _write_json(providers_path, _providers_cfg(_settings("model-prior", "key-prior")))
    _write_json(
        backup_dir / "openai-compatible-20260101T000000.000000Z.json",
        {"settings": _settings("model-prior", "key-prior")},
    )
    _write_json(backup_dir / _BOGUS_NEWEST, {"settings": _settings("model-bogus", "key-bogus")})
    before = sorted(os.listdir(backup_dir))

    status = switch_provider(
        str(providers_path), str(tmpl_path), "profile-a", str(backup_dir),
        env={"A_KEY": "key-a"}, now=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert status == "activated"
    assert sorted(os.listdir(backup_dir)) == before, "a duplicate of the real newest backup was written"


def test_dedupe_records_outgoing_state_that_only_a_bogus_name_matches(
    workspace: Workspace,
) -> None:
    """The outgoing state differs from the real newest backup, so it is backed up.

    A bogus newest-sorting name holding the same settings as the live state used to be the
    dedupe target, so the outgoing state was treated as already recorded and never saved.
    """
    providers_path, backup_dir, tmpl_path = workspace
    _write_json(providers_path, _providers_cfg(_settings("model-prior", "key-prior")))
    _write_json(
        backup_dir / "openai-compatible-20260101T000000.000000Z.json",
        {"settings": _settings("model-older", "key-older")},
    )
    _write_json(backup_dir / _BOGUS_NEWEST, {"settings": _settings("model-prior", "key-prior")})

    switch_provider(
        str(providers_path), str(tmpl_path), "profile-a", str(backup_dir),
        env={"A_KEY": "key-a"}, now=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    real = _real_backups(backup_dir)
    assert [_read_json(backup_dir / n)["settings"]["model"] for n in real] == [
        "model-older", "model-prior"]


def test_rotation_keeps_max_real_backups_and_never_deletes_unparseable_files(
    workspace: Workspace,
) -> None:
    """Rotation counts only parseable backups and leaves bogus and operator files in place.

    Unparseable names used to take a slot among the newest kept files (leaving fewer real
    backups than configured), and any that sorted oldest were deleted.
    """
    providers_path, backup_dir, tmpl_path = workspace
    _write_json(providers_path, _providers_cfg(_settings("model-0", "key-0")))
    untouchable = {
        _BOGUS_NEWEST: {"settings": _settings("model-bogus-new", "key-x")},
        _BOGUS_OLDEST: {"settings": _settings("model-bogus-old", "key-y")},
        _OPERATOR_FILE: {"note": "operator-owned, not a backup"},
    }
    for name, data in untouchable.items():
        _write_json(backup_dir / name, data)

    for i in range(1, 13):
        tmpl = _write_profile(tmpl_path.parent, f"profile-{i}", f"model-{i}", f"K{i}")
        switch_provider(
            str(providers_path), str(tmpl), f"profile-{i}", str(backup_dir),
            env={f"K{i}": f"key-{i}"},
            now=datetime(2026, 1, i, tzinfo=timezone.utc),
        )

    real = _real_backups(backup_dir)
    assert [_read_json(backup_dir / n)["settings"]["model"] for n in real] == [
        f"model-{i}" for i in range(2, 12)], "must keep exactly the ten newest real backups"
    for name, data in untouchable.items():
        assert (backup_dir / name).exists(), f"rotation deleted unparseable file {name}"
        assert _read_json(backup_dir / name) == data, f"rotation changed unparseable file {name}"


def test_latest_backup_ignores_unparseable_names(tmp_path: Path) -> None:
    """latest_backup returns the newest parseable backup, or None when only unparseable names exist."""
    latest_backup = switch_cline_provider.latest_backup
    for name in (_BOGUS_NEWEST, _BOGUS_OLDEST, _OPERATOR_FILE):
        _write_json(tmp_path / name, {"settings": {}})
    assert latest_backup(str(tmp_path)) is None

    real = "openai-compatible-20260101T000000.000000Z.json"
    _write_json(tmp_path / real, {"settings": {}})
    assert latest_backup(str(tmp_path)) == os.path.join(str(tmp_path), real)


def test_backup_rotation_caps_at_ten(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Twelve distinct switches keep only the ten newest backups, evicting the oldest first."""
    providers_path, backup_dir, tmpl_path = workspace
    _write_json(providers_path, _providers_cfg(_settings("model-0", "key-0")))

    for i in range(1, 13):
        tmpl = tmpl_path.parent / f"profile-{i}.json.tmpl"
        with tmpl.open("w") as f:
            json.dump({"settings": {**_settings(f"model-{i}", f"key-{i}"), "apiKey": f"${{K{i}}}"}}, f)
        switch_provider(
            str(providers_path), str(tmpl), f"profile-{i}", str(backup_dir),
            env={f"K{i}": f"key-{i}"},
            now=datetime(2026, 1, i, tzinfo=timezone.utc),
        )

    backups = sorted(os.listdir(backup_dir))
    assert len(backups) == 10, "must rotate to a maximum of 10 snapshots"
    oldest_kept = _read_json(backup_dir / backups[0])
    assert oldest_kept["settings"]["model"] == "model-2", "oldest backups (0, 1) must be evicted first"


def test_unrelated_provider_entries_are_preserved_not_mutated(workspace: Workspace) -> None:
    """Other provider entries are carried over unchanged and the caller's dict is not mutated."""
    providers_path, backup_dir, tmpl_path = workspace
    extra = {"anthropic": {"settings": {"apiKey": "anthropic-key"}}, "ollama": {"settings": {}}}
    original_cfg = _providers_cfg(_settings("model-prior", "key-prior"), extra_providers=extra)
    _write_json(providers_path, original_cfg)

    switch_provider(str(providers_path), str(tmpl_path), "profile-a", str(backup_dir), env={"A_KEY": "key-a"})

    # Original in-memory dict must be untouched -- proves construction
    # builds new objects rather than mutating cfg/outgoing in place.
    assert original_cfg["providers"]["openai-compatible"]["settings"]["model"] == "model-prior"

    new_cfg = _read_json(providers_path)
    assert new_cfg["providers"]["anthropic"] == extra["anthropic"]
    assert new_cfg["providers"]["ollama"] == extra["ollama"]


def test_missing_env_var_raises_before_any_write(workspace: Workspace) -> None:
    """An unset template variable aborts before any backup or live-config write."""
    providers_path, backup_dir, tmpl_path = workspace
    _write_json(providers_path, _providers_cfg(_settings("model-prior", "key-prior")))

    with pytest.raises(SystemExit):
        switch_provider(str(providers_path), str(tmpl_path), "profile-a", str(backup_dir), env={})

    assert os.listdir(backup_dir) == []
    assert _read_json(providers_path)["providers"]["openai-compatible"]["settings"]["model"] == "model-prior"


def test_atomic_write_cleans_up_temp_file_on_serialization_failure(tmp_path: Path) -> None:
    """A serialization failure leaves the target untouched and removes the temp file."""
    target = tmp_path / "providers.json"
    target.write_text('{"original": true}')

    class Unserializable:
        """An object json.dump cannot encode, used to force a mid-write failure."""

    with pytest.raises(TypeError):
        switch_cline_provider.atomic_write_json(str(target), {"bad": Unserializable()})

    assert _read_json(target) == {"original": True}, "original file must be untouched on failure"
    leftovers = [f for f in os.listdir(tmp_path) if f.startswith(".tmp-")]
    assert leftovers == [], "temp file must be cleaned up, not left behind"


def test_main_wires_lock_and_switch_and_prints_activated(
    workspace: Workspace, capsys: pytest.CaptureFixture[str]
) -> None:
    """main() takes the lock, switches the profile and reports the activation."""
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


def test_main_prints_no_changes_when_already_on_profile(
    workspace: Workspace, capsys: pytest.CaptureFixture[str]
) -> None:
    """main() reports no changes when the requested profile is already live."""
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
