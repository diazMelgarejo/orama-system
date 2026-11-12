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
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Sequence

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


# --- live model / effort resolution -------------------------------------------
# Operator rules (2026-11-12): effort order medium -> high -> low, never xhigh
# or max; the model is the first candidate the provider actually serves. A
# route with no acceptable choice is reported blocked, never guessed.
EFFORT_ORDER = ("medium", "high", "low")
FORBIDDEN_EFFORTS = frozenset({"xhigh", "max"})
_REJECTED_STATUSES = frozenset({400, 404, 422})  # the provider said "not this model/level"
_HTTP_TIMEOUT_SECONDS = 60  # hard ceiling per call; GLM on W&B answers in 23-30 s
_PROBE_PROMPT = "Reply with the number 1."


class ProbeError(RuntimeError):
    """A probe was inconclusive (auth, balance, rate limit, server or network error); it must not read as 'rejected'."""


def choose_first_available(candidates: Sequence[str], live_ids: Sequence[str]) -> str | None:
    """Return the first candidate that appears in ``live_ids`` (exact match), or None; candidate order is the preference order."""
    served = set(live_ids)
    return next((c for c in candidates if c in served), None)


def choose_effort(candidates: Sequence[str], probe: Callable[[str], bool]) -> str | None:
    """Return the first non-forbidden level that ``probe`` accepts, or None; forbidden levels are never probed and ProbeError propagates."""
    for level in candidates:
        if level in FORBIDDEN_EFFORTS:
            continue
        if probe(level):
            return level
    return None


def resolve_route(
    model_candidates: Sequence[str],
    live_ids: Sequence[str],
    effort_candidates: Sequence[str],
    probe: Callable[[str, str], bool] | None,
) -> tuple[str, str] | None:
    """Return (model, effort) for the first served model with an acceptable effort, or None when blocked.

    Without ``probe`` nothing is billed: the first served model and the first
    allowed effort are returned unverified.
    """
    served = [m for m in model_candidates if m in set(live_ids)]
    allowed = [e for e in effort_candidates if e not in FORBIDDEN_EFFORTS]
    if probe is None:
        return (served[0], allowed[0]) if served and allowed else None
    for model in served:
        effort = choose_effort(allowed, lambda level, m=model: probe(m, level))
        if effort is not None:
            return model, effort
    return None


def with_model_and_effort(settings: Mapping[str, Any], model: str, effort: str) -> dict[str, Any]:
    """Return a new settings dict with ``model`` and ``reasoning.effort`` replaced; the input is never mutated."""
    reasoning = {"enabled": True, **dict(settings.get("reasoning", {})), "effort": effort}
    return {**settings, "model": model, "reasoning": reasoning}


def read_resolution(tmpl_path: str) -> dict[str, Any]:
    """Return the template's sibling ``resolution`` block (models and efforts), or {} when absent; forbidden efforts raise ValueError."""
    with open(tmpl_path) as f:
        block = json.load(f).get("resolution", {})
    bad = FORBIDDEN_EFFORTS.intersection(block.get("efforts", []))
    if bad:
        raise ValueError(f"template resolution lists forbidden effort level(s): {sorted(bad)}")
    return block


def _request(url: str, api_key: str, body: Mapping[str, Any] | None) -> tuple[int, str]:
    """Send one bounded request with the key in an Authorization header; return (status, body text) without ever echoing the key."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method="POST" if body is not None else "GET",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_SECONDS) as resp:  # noqa: S310 - https/loopback only
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ProbeError(f"network error: {type(exc).__name__}") from exc


def list_live_models(base_url: str, api_key: str) -> list[str]:
    """Return the model ids the provider lists at ``GET {base_url}/models`` (free call); anything but 200 raises ProbeError."""
    status, text = _request(f"{base_url.rstrip('/')}/models", api_key, None)
    if status != 200:
        raise ProbeError(f"model list returned HTTP {status}")
    return [m["id"] for m in json.loads(text).get("data", []) if "id" in m]


def probe_effort(base_url: str, api_key: str, model: str, level: str) -> bool:
    """Send one tiny billed request with ``reasoning_effort=level``; True on 200, False when the provider rejects it, ProbeError otherwise."""
    if level in FORBIDDEN_EFFORTS:
        raise ValueError(f"refusing to probe forbidden effort level {level!r}")
    body = {"model": model, "messages": [{"role": "user", "content": _PROBE_PROMPT}],
            "max_tokens": 200, "reasoning_effort": level}
    status, _text = _request(f"{base_url.rstrip('/')}/chat/completions", api_key, body)
    if status == 200:
        return True
    if status in _REJECTED_STATUSES:
        return False
    raise ProbeError(f"probe returned inconclusive HTTP {status}")


def rotate_backups(backup_dir: str, max_backups: int = MAX_BACKUPS) -> None:
    """Delete the oldest backups whose stamp parses so that at most ``max_backups`` newest ones remain; unparseable names are neither counted nor deleted."""
    entries = _stamped_backups(backup_dir)
    for stale in entries[:-max_backups]:
        os.unlink(os.path.join(backup_dir, stale))


def _cline_timestamp(moment: datetime) -> str:
    """Format ``moment`` the way Cline writes timestamps: UTC, millisecond precision, trailing Z."""
    utc = moment.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


def switch_provider(
    providers_path: str,
    tmpl_path: str,
    profile: str,
    backup_dir: str,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
    resolution: tuple[str, str] | None = None,
) -> str:
    """Returns a status string: "no-op" or "activated"."""
    now = now or datetime.now(timezone.utc)

    cfg = load_json(providers_path)
    outgoing = cfg.get("providers", {}).get("openai-compatible", {}).get("settings", {})
    new_settings = resolve_template(tmpl_path, env=env)
    if resolution is not None:
        new_settings = with_model_and_effort(new_settings, *resolution)

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
        # Millisecond precision with a Z suffix, as Cline writes it; Python's isoformat() (+00:00, microseconds)
        # made Cline 3.0.74 reject the entry with "invalid model ID" (live, 2026-11-12).
        "updatedAt": _cline_timestamp(now),
        # Cline 3.0.74 accepts only its own labels (manual, oauth, migration); a custom label such as
        # "switch-cline-provider.sh:<profile>" made requests fail with "invalid model ID" (live, 2026-11-12).
        "tokenSource": "manual",
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


def _resolve_for_main(tmpl_path: str, flags: Sequence[str]) -> tuple[str, str] | None:
    """Apply ``--resolve`` (free model-list check) and ``--verify-effort`` (billed, opt-in probes); return None to keep the template as written."""
    wants_list = "--resolve" in flags or "--verify-effort" in flags
    if not wants_list:
        return None
    settings = resolve_template(tmpl_path)
    resolution = read_resolution(tmpl_path)
    models = resolution.get("models") or [settings["model"]]
    efforts = resolution.get("efforts") or list(EFFORT_ORDER)
    base_url, api_key = settings["baseUrl"], settings["apiKey"]
    live = list_live_models(base_url, api_key)
    probe = (lambda m, e: probe_effort(base_url, api_key, m, e)) if "--verify-effort" in flags else None
    chosen = resolve_route(models, live, efforts, probe)
    if chosen is None:
        raise SystemExit("ERROR: route blocked: no candidate model is served with an acceptable effort level; providers.json left unchanged")
    if probe is None:
        chosen = (chosen[0], settings.get("reasoning", {}).get("effort", chosen[1]))
    return chosen


def main(argv: Sequence[str]) -> None:
    """CLI entry: providers path, template, profile, backup dir and lock path from ``argv``, then optional ``--resolve`` / ``--verify-effort``; switch under an exclusive lock and print whether the profile was activated or already live."""
    providers_path, tmpl_path, profile, backup_dir, lock_path = argv[1:6]
    flags = argv[6:]
    try:
        chosen = _resolve_for_main(tmpl_path, flags)
    except ProbeError as exc:
        raise SystemExit(f"ERROR: could not verify the route ({exc}); providers.json left unchanged") from exc
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    _lock_exclusive(lock_fd)
    try:
        status = switch_provider(providers_path, tmpl_path, profile, backup_dir, resolution=chosen)
    finally:
        _unlock(lock_fd)
        os.close(lock_fd)

    detail = f" (model {chosen[0]}, effort {chosen[1]})" if chosen else ""
    if status == "no-op":
        print(f"Already on profile: {profile} (no changes){detail}")
    else:
        print(f"Activated profile: {profile}{detail}")


if __name__ == "__main__":
    main(sys.argv)
