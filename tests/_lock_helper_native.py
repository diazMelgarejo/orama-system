"""Child-process helper for native Windows AutoResearcher lock evidence tests."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import autoresearcher_lock as arl  # noqa: E402


def _emit(path: Path, payload: dict[str, object]) -> None:
    """Publish one small result atomically so the parent never reads partial JSON."""
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _identity_payload(outcome: str) -> dict[str, object]:
    pid = os.getpid()
    return {
        "outcome": outcome,
        "pid": pid,
        "start_id": arl.process_start_id(pid),
    }


def hold(lock_path: Path, event_path: Path, release_path: Path) -> int:
    """Acquire through the public API, report the result, and hold until released."""
    try:
        lock = arl.BackendLock(lock_path).acquire()
    except arl.LockRefused as exc:
        payload = _identity_payload("refused")
        payload.update(state=exc.state, reason=exc.reason)
        _emit(event_path, payload)
        return 0

    _emit(event_path, _identity_payload("acquired"))
    deadline = time.monotonic() + 60
    while not release_path.exists():
        if time.monotonic() >= deadline:
            raise TimeoutError("timed out waiting for the test's release event")
        time.sleep(0.02)
    lock.release("not-sent")
    return 0


def identity(event_path: Path) -> int:
    """Capture a real child PID and its start identity, then exit without cleanup."""
    _emit(event_path, _identity_payload("identity"))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) == 5 and argv[1] == "hold":
        return hold(Path(argv[2]), Path(argv[3]), Path(argv[4]))
    if len(argv) == 3 and argv[1] == "identity":
        return identity(Path(argv[2]))
    raise SystemExit(f"usage: {argv[0]} hold LOCK EVENT RELEASE | identity EVENT")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
