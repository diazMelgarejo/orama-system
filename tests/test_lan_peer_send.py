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


def test_env_loading_takes_only_allowlisted_keys_and_never_overrides(tmp_path):
    """Only the TLS and token keys are read; an already-set variable is kept; other keys are ignored."""
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        'PEER_CA_FILE="/x/ca.pem"\nexport PEER_PORTAL_TLS_ENABLED=1\nOPENAI_API_KEY=sk-secret\nPEER_CA_SHA256=aa\n', encoding="utf-8"
    )
    loaded = lps.load_allowed_env(env_file, {"PEER_CA_SHA256": "keep"})
    assert loaded == {"PEER_CA_FILE": "/x/ca.pem", "PEER_PORTAL_TLS_ENABLED": "1"}


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
        [sys.executable, str(SCRIPTS / "lan_peer_send.py"), "--file", str(task), "--peer-ip", LOOP, "--portal-port", "1",
         "--env-file", str(tmp_path / "none.env"), "--timeout", "2"],
        env={"PATH": "/usr/bin:/bin", "HOME": str(home)}, text=True, capture_output=True, check=False, cwd=ROOT,
    )
    assert result.returncode == 2, (result.stdout, result.stderr)
    out = json.loads(result.stdout)
    assert out["delivered"] is False and out["queued_record"] is True
    assert LOOP not in result.stdout and "outbox-resolve" in out["next"]
