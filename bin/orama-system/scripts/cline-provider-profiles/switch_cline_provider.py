"""Core logic for switch-cline-provider.sh, extracted for testability.

Cline stores exactly one active "openai-compatible" provider at a time in
providers.json. This module resolves a checked-in .json.tmpl profile
(placeholders filled from the environment), snapshots the outgoing state
into a rotating, deduplicated backup history, and atomically replaces the
live config -- never mutating an existing dict in place, never opening the
live file with "w" before a same-directory temp write has fully landed.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

try:  # POSIX
    import fcntl
except ImportError:  # Windows has no fcntl; msvcrt provides the same exclusive lock
    fcntl = None
    import msvcrt

MAX_BACKUPS = 10
_WIN_LOCK_TIMEOUT_ERRNO = 36  # errno.EDEADLOCK: msvcrt LK_LOCK gave up after its retries
# Metadata fields that live alongside a provider's "settings" dict (set by
# this script itself when activating a profile, see switch_provider below)
# and would always differ between snapshots even for an otherwise-identical
# config. Excluded defensively so a caller that happens to pass a block
# containing them still compares correctly -- in the current wiring these
# never actually appear inside the settings sub-dict itself (they're
# siblings of "settings", not inside it), so this denylist is a no-op today,
# but comparing the full mapping (denylist, not an allowlist) means a new
# settings key added to a future profile template is compared by default
# instead of silently ignored the way COMPARE_KEYS previously was.
_METADATA_KEYS = ("updatedAt", "tokenSource")


def atomic_write_json(path: str, data: Mapping[str, Any]) -> None:
    """Write ``data`` as JSON to ``path`` via a same-directory temp file, fsync, then ``os.replace`` so readers never see a half-written file; the temp file is removed on failure."""
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
    """Return the parsed JSON object stored at ``path``."""
    with open(path) as f:
        return json.load(f)


_BACKUP_NAME_RE = re.compile(r"^openai-compatible-(\d{8}T\d{6}\.\d{6})Z\.json$")


def _backup_stamp(path: str) -> datetime | None:
    """Return the naive timestamp encoded in a backup file name, or None when the name is not one this script wrote."""
    m = _BACKUP_NAME_RE.match(os.path.basename(path))
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y%m%dT%H%M%S.%f")
    except ValueError:
        # Pattern matched but the calendar fields are invalid (e.g. month 13).
        # Treat like an unexpected filename so switch can continue.
        return None


def _stamped_backups(backup_dir: str) -> list[str]:
    """Return the names in ``backup_dir`` whose stamp parses via ``_backup_stamp``, oldest first.

    Any other name -- an impossible date that sorts newest, or a file an operator put
    there -- is left out, so it never steers ordering, dedupe or rotation and is never
    deleted by rotation.
    """
    stamped: list[tuple[datetime, str]] = []
    for name in os.listdir(backup_dir):
        stamp = _backup_stamp(name)
        if stamp is not None:
            stamped.append((stamp, name))
    stamped.sort()
    return [name for _stamp, name in stamped]


def latest_backup(backup_dir: str) -> str | None:
    """Return the path of the newest backup in ``backup_dir`` whose stamp parses, or None when there is none; unparseable names are ignored."""
    entries = _stamped_backups(backup_dir)
    return os.path.join(backup_dir, entries[-1]) if entries else None


def comparable(block: Mapping[str, Any]) -> dict[str, Any]:
    """Return ``block`` without the metadata keys, so two settings dicts can be compared on real configuration only."""
    return {k: v for k, v in block.items() if k not in _METADATA_KEYS}


def resolve_template(tmpl_path: str, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Read the profile template, substitute ``${NAME}`` placeholders from ``env`` (default ``os.environ``) and return its ``settings`` dict; an unset variable aborts via SystemExit."""
    env = env if env is not None else os.environ
    with open(tmpl_path) as f:
        raw = f.read()

    def resolve(m: re.Match[str]) -> str:
        """Replacement callback for one ``${NAME}`` match: return the env value or exit with an error naming the unset variable."""
        name = m.group(1)
        val = env.get(name)
        if val is None:
            raise SystemExit(f"ERROR: template references unset env var {name}")
        return val

    return json.loads(re.sub(r"\$\{([A-Z0-9_]+)\}", resolve, raw))["settings"]


def rotate_backups(backup_dir: str, max_backups: int = MAX_BACKUPS) -> None:
    """Delete the oldest backups whose stamp parses so that at most ``max_backups`` newest ones remain; unparseable names are neither counted nor deleted."""
    entries = _stamped_backups(backup_dir)
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
        # Names sort chronologically and rotation/dedupe rely on that. A coarse
        # clock (Windows ticks about every 15 ms) or a clock stepped backwards can
        # hand a switch a stamp that is not newer than the latest backup, which
        # would overwrite it and break the order: jump straight to one microsecond
        # past the latest backup's stamp. latest_backup() only returns names whose
        # stamp parses, so an unparseable name never hides the real latest stamp.
        prior_stamp = _backup_stamp(prior) if prior else None
        if prior_stamp is not None:
            now_naive = now.replace(tzinfo=None)
            if now_naive <= prior_stamp:
                now = now + (prior_stamp - now_naive) + timedelta(microseconds=1)
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


def _lock_exclusive(fd: int) -> None:
    """Block until this process holds an exclusive lock on ``fd`` (flock on POSIX, a one-byte msvcrt lock on Windows)."""
    if fcntl is not None:
        fcntl.flock(fd, fcntl.LOCK_EX)
        return
    # LK_LOCK gives up with EDEADLOCK after ~10 one-second retries; flock waits
    # indefinitely, so keep waiting on contention and surface any other error.
    while True:
        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
            return
        except OSError as exc:
            if exc.errno != _WIN_LOCK_TIMEOUT_ERRNO:
                raise


def _unlock(fd: int) -> None:
    """Release the lock taken by ``_lock_exclusive``."""
    if fcntl is not None:
        fcntl.flock(fd, fcntl.LOCK_UN)
        return
    os.lseek(fd, 0, os.SEEK_SET)
    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)


def main(argv: Sequence[str]) -> None:
    """CLI entry: take providers path, template, profile name, backup dir and lock path from ``argv``, switch under an exclusive lock, then print whether the profile was activated or already live."""
    providers_path, tmpl_path, profile, backup_dir, lock_path = argv[1:6]
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    _lock_exclusive(lock_fd)
    try:
        status = switch_provider(providers_path, tmpl_path, profile, backup_dir)
    finally:
        _unlock(lock_fd)
        os.close(lock_fd)

    if status == "no-op":
        print(f"Already on profile: {profile} (no changes)")
    else:
        print(f"Activated profile: {profile}")


if __name__ == "__main__":
    main(sys.argv)
