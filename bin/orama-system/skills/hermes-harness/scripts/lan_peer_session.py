#!/usr/bin/env python3
"""Persist Mac<->Windows co-orchestration retry/degrade state."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parents[4]
_SRC_ROOT = _REPO_ROOT / "src"
if _SRC_ROOT.is_dir() and str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from orama_system.lan_peer_files import lan_peer_state_dir  # noqa: E402

STATE_NAME = "co_orchestration_session.json"
LEGACY_FAIL_COUNT = "win_portal_fail_count"
LEGACY_DEGRADED = "macos_only_degraded"
DEFAULT_MAX_FAILURES = 10
DEFAULT_RETRY_SECONDS = 900


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        parsed = int(raw)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def max_failures() -> int:
    return _int_env("LAN_PEER_MAX_FAILURES", DEFAULT_MAX_FAILURES)


def retry_seconds() -> int:
    return _int_env("LAN_PEER_DEGRADED_RETRY_SECONDS", DEFAULT_RETRY_SECONDS)


def now_seconds() -> int:
    return int(time.time())


def state_path() -> Path:
    return lan_peer_state_dir() / STATE_NAME


def _iso(ts: int | None) -> str:
    if not ts:
        return ""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def _empty_state(now: int | None = None) -> dict[str, Any]:
    ts = now_seconds() if now is None else now
    return {
        "mode": "co-orchestration",
        "failure_count": 0,
        "max_failures": max_failures(),
        "retry_seconds": retry_seconds(),
        "updated_at": ts,
        "updated_at_iso": _iso(ts),
        "last_error": "",
    }


def _load_legacy(now: int) -> dict[str, Any] | None:
    root = lan_peer_state_dir()
    count = 0
    count_path = root / LEGACY_FAIL_COUNT
    degraded_path = root / LEGACY_DEGRADED
    if count_path.is_file():
        try:
            count = int(count_path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            count = 0
    if count <= 0 and not degraded_path.is_file():
        return None

    state = _empty_state(now)
    state["failure_count"] = max(count, max_failures() if degraded_path.is_file() else count)
    if degraded_path.is_file() or state["failure_count"] >= max_failures():
        state["mode"] = "macos-only"
        state["degraded_at"] = now
        state["degraded_at_iso"] = _iso(now)
        state["last_retry_at"] = now
        state["last_retry_at_iso"] = _iso(now)
        state["next_retry_after"] = now + retry_seconds()
        state["next_retry_after_iso"] = _iso(state["next_retry_after"])
    return state


def load_state(now: int | None = None) -> dict[str, Any]:
    ts = now_seconds() if now is None else now
    path = state_path()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        if isinstance(data, dict):
            state = _empty_state(ts)
            state.update(data)
            state["max_failures"] = max_failures()
            state["retry_seconds"] = retry_seconds()
            return state
    legacy = _load_legacy(ts)
    return legacy if legacy is not None else _empty_state(ts)


def save_state(state: dict[str, Any]) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _remove_legacy() -> None:
    root = lan_peer_state_dir()
    for name in (LEGACY_FAIL_COUNT, LEGACY_DEGRADED):
        try:
            (root / name).unlink()
        except FileNotFoundError:
            pass


def record_success(now: int | None = None) -> dict[str, Any]:
    ts = now_seconds() if now is None else now
    previous = load_state(ts)
    state = _empty_state(ts)
    state["last_success_at"] = ts
    state["last_success_at_iso"] = _iso(ts)
    if previous.get("mode") == "macos-only":
        state["resumed_at"] = ts
        state["resumed_at_iso"] = _iso(ts)
    save_state(state)
    _remove_legacy()
    return state


def record_failure(error: str = "", now: int | None = None) -> dict[str, Any]:
    ts = now_seconds() if now is None else now
    state = load_state(ts)
    count = int(state.get("failure_count") or 0) + 1
    state.update(
        {
            "failure_count": count,
            "max_failures": max_failures(),
            "retry_seconds": retry_seconds(),
            "updated_at": ts,
            "updated_at_iso": _iso(ts),
            "last_error": error.strip(),
        }
    )
    if count >= max_failures():
        state["mode"] = "macos-only"
        state.setdefault("degraded_at", ts)
        state["degraded_at_iso"] = _iso(int(state["degraded_at"]))
        state["last_retry_at"] = ts
        state["last_retry_at_iso"] = _iso(ts)
        state["next_retry_after"] = ts + retry_seconds()
        state["next_retry_after_iso"] = _iso(int(state["next_retry_after"]))
    else:
        state["mode"] = "co-orchestration"
    save_state(state)
    return state


def should_retry(now: int | None = None) -> tuple[bool, dict[str, Any]]:
    ts = now_seconds() if now is None else now
    state = load_state(ts)
    if state.get("mode") != "macos-only":
        return True, state

    next_retry = int(state.get("next_retry_after") or 0)
    if next_retry and ts < next_retry:
        state["updated_at"] = ts
        state["updated_at_iso"] = _iso(ts)
        save_state(state)
        return False, state

    state["last_retry_at"] = ts
    state["last_retry_at_iso"] = _iso(ts)
    state["next_retry_after"] = ts + retry_seconds()
    state["next_retry_after_iso"] = _iso(int(state["next_retry_after"]))
    state["updated_at"] = ts
    state["updated_at_iso"] = _iso(ts)
    save_state(state)
    return True, state


def _emit(state: dict[str, Any], *, ok: bool = True) -> None:
    payload = {"ok": ok, **state, "state_file": str(state_path())}
    print(json.dumps(payload, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("should-retry")
    sub.add_parser("record-success")
    failure = sub.add_parser("record-failure")
    failure.add_argument("--error", default="")
    args = parser.parse_args(argv)

    if args.cmd == "status":
        _emit(load_state())
        return 0
    if args.cmd == "should-retry":
        retry, state = should_retry()
        _emit(state, ok=retry)
        return 0 if retry else 1
    if args.cmd == "record-success":
        _emit(record_success())
        return 0
    if args.cmd == "record-failure":
        _emit(record_failure(args.error))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
