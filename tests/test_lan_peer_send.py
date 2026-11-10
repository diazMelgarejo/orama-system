"""Tests for lan_peer_send.py: allowlisted env loading, output masking and delivery-evidence checks."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "bin" / "orama-system" / "skills" / "hermes-harness" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import lan_peer_send as lps  # noqa: E402

LOOP = ".".join(["127", "0", "0", "1"])  # addresses are built at runtime: tracked files carry no literals
PRIV = ".".join(["192", "168", "1", "20"])


def test_child_env_passes_only_the_allowlist_and_basic_process_settings():
    """The child process gets the peer-TLS and token settings plus basics; every other variable is dropped."""
    environ = {
        "PEER_CA_FILE": "/x/ca.pem", "PEER_PORTAL_TLS_ENABLED": "1", "ORAMA_CONTROL_PLANE_TOKEN_PEER": "t",
        "PATH": "/usr/bin", "HOME": "/h", "OPENAI_API_KEY": "sk-secret", "AWS_SECRET_ACCESS_KEY": "x", "GITHUB_TOKEN": "y",
    }
    child = lps.child_env(environ)
    assert child == {"PEER_CA_FILE": "/x/ca.pem", "PEER_PORTAL_TLS_ENABLED": "1", "ORAMA_CONTROL_PLANE_TOKEN_PEER": "t",
                     "PATH": "/usr/bin", "HOME": "/h"}


def test_helper_never_opens_an_env_file():
    """The helper reads settings only from its environment: no file named like an env file is opened by its source."""
    source = (SCRIPTS / "lan_peer_send.py").read_text(encoding="utf-8")
    assert "read_text" not in source and "open(" not in source and "--env-file" not in source


def test_mask_hides_addresses_and_token_like_strings():
    """Addresses and long token-like strings never reach the output."""
    text = f"failed https://{PRIV}:8443/x token abcdefghijklmnopqrstuvwxyz0123456789ABCD"
    masked = lps.mask(text)
    assert PRIV not in masked and "abcdefghijklmnopqrstuvwxyz" not in masked and "<ip>" in masked


def test_delivery_counts_only_with_ok_and_matching_bytes():
    """Evidence is the drop's own JSON: ok true, a received_at, and a byte count equal to the file size."""
    good = {"ok": True, "received_at": 5, "bytes": 10}
    assert lps.verdict(good, 10)["delivered"] is True
    assert lps.verdict({**good, "bytes": 9}, 10)["delivered"] is False
    assert lps.verdict({"ok": False, "detail": "timed out", "queued": True}, 10)["delivered"] is False
    assert lps.verdict({"ok": True, "bytes": 10}, 10)["delivered"] is False  # no received_at


def test_failed_send_exits_nonzero_masks_output_and_names_the_queue_record(tmp_path):
    """A send to a closed port exits 2, prints no address, and says a queued record needs explicit reconciliation."""
    home = tmp_path / "home"
    task = tmp_path / "t.md"
    task.write_text("# t\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "lan_peer_send.py"), "--file", str(task), "--peer-ip", LOOP, "--portal-port", "1", "--timeout", "2"],
        env={"PATH": "/usr/bin:/bin", "HOME": str(home)}, text=True, capture_output=True, check=False, cwd=ROOT,
    )
    assert result.returncode == 2, (result.stdout, result.stderr)
    out = json.loads(result.stdout)
    assert out["delivered"] is False and out["queued_record"] is True
    assert LOOP not in result.stdout and "outbox-resolve" in out["next"]
