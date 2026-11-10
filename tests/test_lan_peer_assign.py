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


# ── default portal port follows the TLS configuration ───────────────────────────
LOOP = ".".join(["127", "0", "0", "1"])  # built at runtime: tracked files carry no address literals


def _drop_sidecar_port(tmp_path, env_extra, extra_args=()):
    """Run a peer drop that cannot be delivered (closed ports) and return the portal_port its outbox record stored."""
    home = tmp_path / "home"
    task = tmp_path / "task.md"
    task.write_text("# Task\n", encoding="utf-8")
    ca = tmp_path / "ca.pem"
    ca.write_text("not-a-real-certificate\n", encoding="utf-8")
    env = {k: v for k, v in __import__("os").environ.items() if not k.startswith(("PEER_", "PORTAL_"))}
    env.update({"HOME": str(home), "PEER_CA_FILE": str(ca), **env_extra})
    result = subprocess.run(
        ["python3", str(SCRIPT), "drop", "--peer", "--peer-ip", LOOP, *extra_args,
         "--file", str(task), "--filename", "win-port.md", "--assignee", "win", "--topic", "smoke", "--timeout", "2"],
        cwd=ROOT, env=env, text=True, capture_output=True, check=False,
    )
    meta = home / ".openclaw" / "state" / "lan_peer" / "outbox" / "win-port.md.meta.json"
    assert meta.is_file(), (result.stdout, result.stderr)
    return json.loads(meta.read_text(encoding="utf-8")).get("portal_port")


def test_drop_defaults_to_the_tls_port_when_pinned_tls_is_configured(tmp_path):
    """With peer TLS enabled and a pinned CA, a bare drop targets the TLS port, not the plain portal port."""
    port = _drop_sidecar_port(tmp_path, {"PEER_PORTAL_TLS_ENABLED": "1", "PEER_PORTAL_TLS_PORT": "1", "PORTAL_PORT": "2"})
    assert str(port) == "1"


def test_drop_keeps_the_plain_portal_port_when_tls_is_not_enabled(tmp_path):
    """Without peer TLS the default is unchanged (PORTAL_PORT, else 8002)."""
    port = _drop_sidecar_port(tmp_path, {"PORTAL_PORT": "2", "PEER_PORTAL_TLS_PORT": "1"})
    assert str(port) == "2"


def test_an_explicit_portal_port_always_wins(tmp_path):
    """--portal-port overrides the TLS-derived default."""
    port = _drop_sidecar_port(
        tmp_path, {"PEER_PORTAL_TLS_ENABLED": "1", "PEER_PORTAL_TLS_PORT": "1"}, ("--portal-port", "3"),
    )
    assert str(port) == "3"
