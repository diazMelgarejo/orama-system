"""Concurrent lock acquisition stress test (T3-A / S6)."""

from __future__ import annotations

import threading
import time

from oramaclaw.store import LockHeld, _acquire_lock, _release_lock


def test_concurrent_lock_acquisition_no_corruption(tmp_path):
    """No two threads should simultaneously hold the lock."""
    lock_path = tmp_path / "test.lock"
    max_concurrent = {"n": 0}
    max_seen = {"n": 0}
    counter_lock = threading.Lock()
    winners: list[int] = []

    def try_acquire():
        try:
            _acquire_lock(lock_path)
            with counter_lock:
                max_concurrent["n"] += 1
                max_seen["n"] = max(max_seen["n"], max_concurrent["n"])
                winners.append(1)
            time.sleep(0.05)
            with counter_lock:
                max_concurrent["n"] -= 1
            _release_lock(lock_path)
        except LockHeld:
            pass

    threads = [threading.Thread(target=try_acquire) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(winners) >= 1, "at least one thread must win"
    assert max_seen["n"] <= 1, f"lock held concurrently by {max_seen['n']} threads"
