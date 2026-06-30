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
