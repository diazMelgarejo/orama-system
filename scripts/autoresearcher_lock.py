#!/usr/bin/env python3
"""Single-owner backend lock for AutoResearcher jobs (AR-WIN-1, W2-backend-lock design).

An OS-held lock is the only authority. The JSON record stored at the start of the file is diagnostic and
tells the next reader what happened, but age and PID absence are never proof that a lock is free. States:

* ``free``                 the OS lock is acquirable and the record is absent or cleanly released;
* ``held``                 another handle currently holds the OS lock;
* ``held-stale-unproven``  the OS lock is free but the previous owner never released cleanly;
* ``ambiguous``            a request may have been sent, or the record is torn or unreadable.

Only ``free`` admits an effect. Release never deletes the file; clearing a non-free state needs an
explicit operator action recorded in the file (``reconcile``). Standard library only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

FREE = "free"
HELD = "held"
STALE = "held-stale-unproven"
AMBIGUOUS = "ambiguous"

_SCHEMA = 1
_IS_WINDOWS = os.name == "nt"
# The lock covers one byte far beyond the record so other processes can still read the record while it is held.
_LOCK_OFFSET_HIGH = 0x7FFFFFFF


class LockRefused(Exception):
    """Raised when the lock cannot be taken or an effect-boundary recheck fails; carries the state and reason."""

    def __init__(self, state: str, reason: str) -> None:
        """Store the refusing *state* and a human-readable *reason*."""
        super().__init__(f"{state}: {reason}")
        self.state = state
        self.reason = reason


@dataclass
class Inspection:
    """Result of a non-acquiring look at a lock file: state, reason and the owner record (if readable)."""

    state: str
    reason: str
    owner: Optional[Dict[str, Any]] = None


# ── Process identity ──────────────────────────────────────────────────────────────────────────────

def process_start_id(pid: int) -> Optional[str]:
    """Return a start-identity string for *pid*, or None when the process is gone or cannot be inspected.

    The identity (creation time) distinguishes a live owner from an unrelated process that reused its PID.
    It never raises.
    """
    try:
        if not isinstance(pid, int) or pid <= 0:
            return None
        if _IS_WINDOWS:
            return _win_start_id(pid)
        if Path("/proc/self/stat").exists():
            raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace")
            return raw[raw.rindex(")") + 1:].split()[19]
        proc = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True, timeout=5)
        return proc.stdout.strip() or None
    except Exception:
        return None


def _win_start_id(pid: int) -> Optional[str]:
    """Windows creation FILETIME of *pid* as a string; None unless the process is provably still running.

    An exited process (any exit code, including 259 = STILL_ACTIVE) and a process we may not query both give
    None; identity is diagnostic only, the OS lock is the authority.
    """
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.GetProcessTimes.argtypes = [ctypes.c_void_p] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    # PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE (the wait below needs SYNCHRONIZE).
    handle = kernel32.OpenProcess(0x1000 | 0x00100000, False, pid)
    if not handle:
        return None
    try:
        if kernel32.WaitForSingleObject(handle, 0) != 258:  # only WAIT_TIMEOUT proves the process is still running
            return None
        created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
        if not kernel32.GetProcessTimes(handle, created, exited, kernel, user):
            return None
        return str((created.dwHighDateTime << 32) | created.dwLowDateTime)
    finally:
        kernel32.CloseHandle(handle)


def _identity(record: Dict[str, Any]) -> str:
    """Diagnose a record's owner: ``match`` (same process), ``mismatch`` (PID reused) or ``unverified``.

    ``unverified`` means the probe could not show a running process (it exited, or it could not be inspected);
    it is never treated as proof of death. The OS lock stays the only authority.
    """
    pid = record.get("pid")
    now = process_start_id(pid) if isinstance(pid, int) else None
    if now is None:
        return "unverified"
    return "match" if now == record.get("start_id") else "mismatch"


# ── Low-level file helpers ─────────────────────────────────────────────────────────────────────────

def _open_rw(path: Path, create: bool) -> int:
    """Open *path* read/write binary (non-inheritable); create it only when *create* is true."""
    flags = os.O_RDWR | getattr(os, "O_BINARY", 0) | (os.O_CREAT if create else 0)
    return os.open(str(path), flags, 0o600)


def _win_lock_args(fd: int) -> Tuple[Any, Any, Any, Any]:
    """Return (kernel32, handle, OVERLAPPED instance, OVERLAPPED class) prepared for the one-byte high-offset lock."""
    import ctypes
    import msvcrt

    class OVERLAPPED(ctypes.Structure):
        """Win32 OVERLAPPED carrying the lock offset."""

        _fields_ = [("Internal", ctypes.c_size_t), ("InternalHigh", ctypes.c_size_t), ("Offset", ctypes.c_uint32),
                    ("OffsetHigh", ctypes.c_uint32), ("hEvent", ctypes.c_void_p)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    for name in ("LockFileEx", "UnlockFileEx"):
        func = getattr(kernel32, name)
        func.restype = ctypes.c_int
    kernel32.LockFileEx.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
                                    ctypes.c_uint32, ctypes.POINTER(OVERLAPPED)]
    kernel32.UnlockFileEx.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
                                      ctypes.POINTER(OVERLAPPED)]
    overlapped = OVERLAPPED(0, 0, 0, _LOCK_OFFSET_HIGH, None)
    return kernel32, msvcrt.get_osfhandle(fd), overlapped, OVERLAPPED


def _try_lock(fd: int) -> bool:
    """Take the exclusive OS lock without waiting: True when acquired, False when another handle holds it."""
    if _IS_WINDOWS:
        import ctypes

        kernel32, handle, overlapped, _cls = _win_lock_args(fd)
        if kernel32.LockFileEx(handle, 0x2 | 0x1, 0, 1, 0, ctypes.byref(overlapped)):  # exclusive | fail immediately
            return True
        err = ctypes.get_last_error()
        if err in (33, 997):  # ERROR_LOCK_VIOLATION, ERROR_IO_PENDING
            return False
        raise ctypes.WinError(err)
    import fcntl

    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False
    except PermissionError as exc:  # a permission problem is not another owner: refuse with its own reason
        raise LockRefused("refused", f"permission denied taking the lock: {exc}") from exc


def _unlock(fd: int) -> None:
    """Release the OS lock taken by ``_try_lock`` (closing the descriptor also releases it)."""
    if _IS_WINDOWS:
        import ctypes

        kernel32, handle, overlapped, _cls = _win_lock_args(fd)
        if not kernel32.UnlockFileEx(handle, 0, 1, 0, ctypes.byref(overlapped)):
            raise ctypes.WinError(ctypes.get_last_error())
        return
    import fcntl

    fcntl.flock(fd, fcntl.LOCK_UN)


def _read_record(path: Path) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Read the owner record: ("none", None) when absent/empty, ("ok", record) when valid, else ("bad", None)."""
    try:
        data = Path(path).read_bytes()
    except FileNotFoundError:
        return "none", None
    except OSError:
        return "bad", None
    if not data:
        return "none", None
    text = data.decode("utf-8", errors="replace")
    if "\x00" in text:
        return "bad", None
    try:
        record = json.loads(text)
    except ValueError:
        return "bad", None
    if not isinstance(record, dict) or record.get("schema") != _SCHEMA:
        return "bad", None
    return "ok", record


def _write_record(fd: int, record: Dict[str, Any]) -> None:
    """Replace the record at the start of the file and force it to disk."""
    data = json.dumps(record, sort_keys=True).encode("utf-8")
    os.lseek(fd, 0, os.SEEK_SET)
    os.write(fd, data)
    os.ftruncate(fd, len(data))
    os.fsync(fd)


def _base_record(state: str, nonce: str, resource: str) -> Dict[str, Any]:
    """Build a record for this process with the given *state*, *nonce* and *resource*."""
    return {"schema": _SCHEMA, "state": state, "nonce": nonce, "pid": os.getpid(),
            "start_id": process_start_id(os.getpid()), "resource": resource, "ts": time.time()}


def _classify(kind: str, record: Optional[Dict[str, Any]]) -> Tuple[str, str]:
    """Map a record read while the OS lock is held by us to (state, reason)."""
    if kind == "none":
        return FREE, "no record"
    if kind == "bad" or record is None:
        return AMBIGUOUS, "record is torn or unreadable"
    state = record.get("state")
    if state == "released":
        return FREE, "cleanly released"
    if state == "acquired":
        return STALE, "previous owner never released cleanly; reconcile first"
    return AMBIGUOUS, f"previous outcome is {state!r} (a request may have been sent); reconcile first"


# ── Public API ─────────────────────────────────────────────────────────────────────────────────────

def inspect(path: Any, resource: str = "local-backend") -> Inspection:
    """Look at the lock at *path* without leaving it held and report its state.

    The look takes the OS lock briefly; a contended lock means ``held``. *resource* is only a label.
    """
    path = Path(path)
    try:
        fd = _open_rw(path, create=False)
    except FileNotFoundError:
        return Inspection(FREE, "no lock file")
    try:
        try:
            locked = _try_lock(fd)
        except LockRefused as exc:
            return Inspection(AMBIGUOUS, exc.reason)
        if not locked:
            kind, record = _read_record(path)
            owner = dict(record, identity=_identity(record)) if kind == "ok" and record else None
            pid = owner.get("pid") if owner else "unknown"
            return Inspection(HELD, f"held by a live owner (pid {pid})", owner)
        try:
            kind, record = _read_record(path)
        finally:
            _unlock(fd)
        state, reason = _classify(kind, record)
        owner = dict(record, identity=_identity(record)) if kind == "ok" and record else None
        return Inspection(state, reason, owner)
    finally:
        os.close(fd)


def reconcile(path: Any, operator: str, note: str) -> None:
    """Record an explicit operator action that clears a non-free lock record (refused while the lock is held)."""
    if not isinstance(operator, str) or not operator.strip() or not isinstance(note, str) or not note.strip():
        raise ValueError("reconcile needs a non-blank operator and note")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = _open_rw(path, create=True)
    locked = False
    try:
        if not _try_lock(fd):
            raise LockRefused(HELD, "lock is held by a live owner; cannot reconcile")
        locked = True
        record = _base_record("released", "reconciled", "local-backend")
        record.update(operator=operator.strip(), note=note.strip())
        _write_record(fd, record)
    finally:
        if locked:
            _unlock(fd)
        os.close(fd)


class BackendLock:
    """One owner at a time for a local model backend: acquire, recheck at the effect boundary, mark, release."""

    def __init__(self, path: Any, resource: str = "local-backend") -> None:
        """Remember the lock *path* and the *resource* label; nothing is opened yet."""
        self.path = Path(path)
        self.resource = resource
        self._fd: Optional[int] = None
        self._nonce: Optional[str] = None

    def acquire(self) -> "BackendLock":
        """Take the OS lock and write an ``acquired`` record, or raise LockRefused naming the state."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = _open_rw(self.path, create=True)
        if not _try_lock(fd):
            os.close(fd)
            raise LockRefused(HELD, "lock is held by another owner")
        kind, record = _read_record(self.path)
        state, reason = _classify(kind, record)
        if state != FREE:
            _unlock(fd)
            os.close(fd)
            raise LockRefused(state, reason)
        self._fd = fd
        self._nonce = uuid.uuid4().hex
        try:
            self._write("acquired")
        except BaseException:
            self._fd = None
            try:
                _unlock(fd)
            finally:
                os.close(fd)
            raise
        return self

    def _write(self, state: str) -> None:
        """Write this owner's record with *state*."""
        assert self._fd is not None and self._nonce is not None
        _write_record(self._fd, _base_record(state, self._nonce, self.resource))

    def recheck(self, extra_check: Optional[Callable[[], Tuple[bool, str]]] = None) -> None:
        """Confirm we still own the lock, then re-run *extra_check* (returns (ok, reason)); refuse on any doubt."""
        if self._fd is None:
            raise LockRefused("refused", "lock is not held")
        kind, record = _read_record(self.path)
        if kind != "ok" or record is None or record.get("nonce") != self._nonce \
                or record.get("state") not in ("acquired", "inflight"):
            raise LockRefused("refused", "owner record is not ours")
        if extra_check is not None:
            ok, reason = extra_check()
            if not ok:
                raise LockRefused("refused", f"recheck failed: {reason}")

    def mark_inflight(self) -> None:
        """Flush an in-flight marker before the request is sent; it stays until the outcome is known."""
        if self._fd is None:
            raise LockRefused("refused", "lock is not held")
        self._write("inflight")

    def release(self, outcome: str) -> None:
        """Release the lock. ``completed`` and ``not-sent`` leave it free; ``unknown`` keeps an ambiguous record."""
        if outcome not in ("completed", "not-sent", "unknown"):
            raise ValueError(f"unknown outcome {outcome!r}")
        if self._fd is None:
            return
        fd, self._fd = self._fd, None
        try:
            _write_record(fd, _base_record("unknown" if outcome == "unknown" else "released", self._nonce or "", self.resource))
        finally:
            try:
                _unlock(fd)
            finally:
                os.close(fd)


if __name__ == "__main__":  # tiny operator CLI: inspect, or reconcile with an explicit operator and note
    import argparse

    parser = argparse.ArgumentParser(description="Inspect or reconcile an AutoResearcher backend lock file")
    parser.add_argument("path")
    parser.add_argument("--reconcile", action="store_true", help="clear a non-free record (needs --operator, --note)")
    parser.add_argument("--operator", default="")
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    if args.reconcile:
        reconcile(args.path, args.operator, args.note)
    result = inspect(args.path)
    print(json.dumps({"state": result.state, "reason": result.reason, "owner": result.owner}, sort_keys=True))
    sys.exit(0 if result.state == FREE else 1)
