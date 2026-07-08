"""Tests for lan_peer_assign.py CLI behavior."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "orama-system" / "skills" / "hermes-harness" / "scripts" / "lan_peer_assign.py"


def test_peer_drop_spools_to_local_outbox_on_delivery_failure(tmp_path):
    home = tmp_path / "home"
    task = tmp_path / "task.md"
    task.write_text("# Task\n", encoding="utf-8")

    result = subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "drop",
            "--peer",
            "--peer-ip",
            "127.0.0.1",
            "--portal-port",
            "1",
            "--file",
            str(task),
            "--filename",
            "win-task.md",
            "--assignee",
            "win",
            "--topic",
            "smoke",
        ],
        cwd=ROOT,
        env={**__import__("os").environ, "HOME": str(home)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["queued"] is True
    assert payload["scope"] == "local-outbox"
    assert payload["filename"] == "win-task.md"
    assert (home / ".openclaw" / "state" / "lan_peer" / "outbox" / "win-task.md").is_file()


def test_help_lists_flush_outbox_command():
    result = subprocess.run(
        ["python3", str(SCRIPT), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "flush-outbox" in result.stdout

    drop_help = subprocess.run(
        ["python3", str(SCRIPT), "drop", "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert drop_help.returncode == 0
    assert "--timeout" in drop_help.stdout


def test_flush_outbox_delivers_each_item_to_its_own_stored_peer(tmp_path):
    """Regression: flush-outbox used to resolve ONE peer for the whole batch
    and send every queued item there, silently misdelivering anything queued
    for a different peer. Each item must be delivered to the peer_ip it was
    originally queued with."""
    import os

    home = tmp_path / "home"
    env = {**os.environ, "HOME": str(home)}

    task_a = tmp_path / "task_a.md"
    task_a.write_text("# For peer A\n", encoding="utf-8")
    task_b = tmp_path / "task_b.md"
    task_b.write_text("# For peer B\n", encoding="utf-8")

    for task, ip, port, name in (
        (task_a, "203.0.113.10", "1", "win-peer-a.md"),
        (task_b, "203.0.113.20", "2", "win-peer-b.md"),
    ):
        drop = subprocess.run(
            [
                "python3", str(SCRIPT), "drop",
                "--peer", "--peer-ip", ip, "--portal-port", port,
                "--file", str(task), "--filename", name,
                "--assignee", "win", "--topic", "smoke",
            ],
            cwd=ROOT, env=env, text=True, capture_output=True, check=False,
        )
        assert drop.returncode == 2
        assert json.loads(drop.stdout)["queued"] is True

    flush = subprocess.run(
        ["python3", str(SCRIPT), "flush-outbox", "--peer", "--peer-ip", "203.0.113.10", "--timeout", "1"],
        cwd=ROOT, env=env, text=True, capture_output=True, check=False,
    )
    payload = json.loads(flush.stdout)
    results = {r["filename"]: r for r in payload["results"]}

    # win-peer-a.md was queued for .10 AND flush-outbox's own --peer-ip is
    # .10 here (deliberately, to prove it's not just an accidental match) —
    # win-peer-b.md must still target its own stored .20, not fall through
    # to the flush command's --peer-ip.
    assert results["win-peer-a.md"]["peer_ip"] == "203.0.113.10"
    assert results["win-peer-b.md"]["peer_ip"] == "203.0.113.20"
    assert "203.0.113.20" in results["win-peer-b.md"]["detail"]


def test_timeout_flag_controls_peer_request_duration(tmp_path):
    home = tmp_path / "home"
    task = tmp_path / "task.md"
    task.write_text("# Task\n", encoding="utf-8")

    result = subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "drop",
            "--peer",
            "--peer-ip",
            "203.0.113.1",
            "--timeout",
            "1",
            "--file",
            str(task),
            "--filename",
            "win-timeout-task.md",
            "--assignee",
            "win",
            "--topic",
            "smoke",
        ],
        cwd=ROOT,
        env={**__import__("os").environ, "HOME": str(home)},
        text=True,
        capture_output=True,
        check=False,
        timeout=8,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["queued"] is True
    assert payload["filename"] == "win-timeout-task.md"
