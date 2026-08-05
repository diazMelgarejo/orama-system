"""Core logic for switch-cline-provider.sh, extracted for testability.

Cline stores exactly one active "openai-compatible" provider at a time in
providers.json. This module resolves a checked-in .json.tmpl profile
(placeholders filled from the environment), snapshots the outgoing state
into a rotating, deduplicated backup history, and atomically replaces the
live config -- never mutating an existing dict in place, never opening the
live file with "w" before a same-directory temp write has fully landed.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

MAX_BACKUPS = 10
# Fields that make two snapshots "the same config" for idempotency
# purposes -- updatedAt/tokenSource are metadata that always differ and
# would defeat the no-op-if-unchanged check if included.
COMPARE_KEYS = ("provider", "apiKey", "model", "baseUrl", "headers", "timeout", "reasoning")


def atomic_write_json(path: str, data: Mapping[str, Any]) -> None:
    directory = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def load_json(path: str) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def latest_backup(backup_dir: str) -> str | None:
    entries = sorted(e for e in os.listdir(backup_dir) if e.endswith(".json"))
    return os.path.join(backup_dir, entries[-1]) if entries else None


def comparable(block: Mapping[str, Any]) -> dict[str, Any]:
    return {k: block.get(k) for k in COMPARE_KEYS}


def resolve_template(tmpl_path: str, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    env = env if env is not None else os.environ
    with open(tmpl_path) as f:
        raw = f.read()

    def resolve(m: re.Match[str]) -> str:
        name = m.group(1)
        val = env.get(name)
        if val is None:
            raise SystemExit(f"ERROR: template references unset env var {name}")
        return val

    return json.loads(re.sub(r"\$\{([A-Z0-9_]+)\}", resolve, raw))["settings"]


def rotate_backups(backup_dir: str, max_backups: int = MAX_BACKUPS) -> None:
    entries = sorted(e for e in os.listdir(backup_dir) if e.endswith(".json"))
    for stale in entries[:-max_backups]:
        os.unlink(os.path.join(backup_dir, stale))


def switch_provider(
    providers_path: str,
    tmpl_path: str,
    profile: str,
    backup_dir: str,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> str:
    """Returns a status string: "no-op" or "activated"."""
    now = now or datetime.now(timezone.utc)

    cfg = load_json(providers_path)
    outgoing = cfg.get("providers", {}).get("openai-compatible", {}).get("settings", {})
    new_settings = resolve_template(tmpl_path, env=env)

    # No-op check: if the requested profile resolves to what's already
    # live, there is nothing to change and nothing to back up.
    if outgoing and comparable(outgoing) == comparable(new_settings):
        return "no-op"

    # Backup step: snapshot the state we're about to replace, but only if
    # it isn't already the most recent snapshot on file (idempotent --
    # avoids a duplicate entry for a state we already have a record of).
    prior = latest_backup(backup_dir)
    prior_settings = load_json(prior)["settings"] if prior else None

    if outgoing and comparable(outgoing) != (comparable(prior_settings) if prior_settings else None):
        # Microsecond precision: two switches inside the same wall-clock
        # second (a realistic rate for an automated agent) must not
        # collide on the same filename and silently clobber each other.
        ts = now.strftime("%Y%m%dT%H%M%S.%fZ")
        snapshot = {"settings": outgoing, "savedAt": now.isoformat()}
        atomic_write_json(os.path.join(backup_dir, f"openai-compatible-{ts}.json"), snapshot)
        rotate_backups(backup_dir)

    # Build the new config as fresh objects -- never mutate cfg/outgoing
    # in place, so unrelated provider entries (anthropic, ollama, etc.)
    # are carried over untouched by construction, not by omission.
    new_openai_compatible = {
        "settings": new_settings,
        "updatedAt": now.isoformat(),
        "tokenSource": f"switch-cline-provider.sh:{profile}",
    }
    new_providers = {**cfg.get("providers", {}), "openai-compatible": new_openai_compatible}
    new_cfg = {**cfg, "providers": new_providers, "lastUsedProvider": "openai-compatible"}

    atomic_write_json(providers_path, new_cfg)
    return "activated"


def main(argv: Sequence[str]) -> None:
    providers_path, tmpl_path, profile, backup_dir, lock_path = argv[1:6]
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    fcntl.flock(lock_fd, fcntl.LOCK_EX)
    try:
        status = switch_provider(providers_path, tmpl_path, profile, backup_dir)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)

    if status == "no-op":
        print(f"Already on profile: {profile} (no changes)")
    else:
        print(f"Activated profile: {profile}")


if __name__ == "__main__":
    main(sys.argv)
