"""Tests for start.ps1 making the LAN peer link use the peer's HTTPS front end by default."""
from __future__ import annotations

import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

START_PS1 = Path(__file__).resolve().parents[1] / "platform" / "windows" / "start.ps1"
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


def _text() -> str:
    """Return start.ps1 with CRLF normalised."""
    return START_PS1.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def _function_source() -> str:
    """Return the Get-PeerTlsPortArgs function source from start.ps1."""
    text = _text()
    match = re.search(r"^function Get-PeerTlsPortArgs \{.*?^\}\n", text, re.S | re.M)
    assert match, "Get-PeerTlsPortArgs is missing from start.ps1"
    return match.group(0)


def test_probe_and_flush_pass_the_peer_tls_port_args() -> None:
    """Both the probe and the outbox flush splat the https port arguments."""
    text = _text()
    probe = re.search(r"^function Invoke-LanPeerProbe \{.*?^\}\n", text, re.S | re.M).group(0)
    flush = re.search(r"^function Invoke-LanPeerOutboxFlush \{.*?^\}\n", text, re.S | re.M).group(0)
    assert "@(Get-PeerTlsPortArgs)" in probe and "@peerPortArgs" in probe
    assert "@(Get-PeerTlsPortArgs)" in flush and "@peerPortArgs" in flush


def test_function_never_touches_trust_stores_or_the_local_portal_port() -> None:
    """The helper only sets process env for the peer CA and never changes system trust or PORTAL_PORT."""
    body = _function_source()
    assert "$env:SSL_CERT_FILE" not in body
    assert "$env:PORTAL_PORT" not in body
    assert "Import-Certificate" not in body and "certutil" not in body.lower()
    assert "PEER_PINNED_FINGERPRINTS" not in body


def _run(tmp_path: Path, env_lines: str) -> list[str]:
    """Run the extracted function under PowerShell with a stubbed _Info and return its output lines."""
    script = tmp_path / "case.ps1"
    script.write_text(
        textwrap.dedent(
            f"""
            function _Info {{ param($a, $b) }}
            $RepoRoot = '{tmp_path / "repo"}'
            {env_lines}
            {_function_source()}
            $r = @(Get-PeerTlsPortArgs)
            'ARGS=' + ($r -join '|')
            'ENABLED=' + $env:PEER_PORTAL_TLS_ENABLED
            'CA=' + $env:PEER_CA_FILE
            """
        ),
        encoding="utf-8",
    )
    done = subprocess.run(
        [POWERSHELL, "-NoProfile", "-File", str(script)],
        capture_output=True, text=True, timeout=60, check=True,
        env={"PATH": __import__("os").environ["PATH"], "SystemRoot": __import__("os").environ.get("SystemRoot", "")},
    )
    return done.stdout.splitlines()


def _ca(tmp_path: Path, name: str) -> Path:
    """Create a placeholder CA file under mac-ca-<name> in the fake repo root and return it."""
    folder = tmp_path / "repo" / f"mac-ca-{name}"
    folder.mkdir(parents=True, exist_ok=True)
    pem = folder / "orama-lan-ca.pem"
    pem.write_text("placeholder", encoding="utf-8")
    return pem


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is not available")
def test_ca_found_by_search_enables_https_on_the_default_port(tmp_path: Path) -> None:
    """A mac-ca-* folder is picked up and the peer is reached over https on 8443 with that CA."""
    _ca(tmp_path, "2026-11-03")
    newest = _ca(tmp_path, "2027-01-01")
    out = _run(tmp_path, "")
    assert "ARGS=--portal-port|8443" in out
    assert "ENABLED=1" in out
    assert f"CA={newest}" in out


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is not available")
def test_no_ca_and_no_flag_keeps_the_legacy_http_behaviour(tmp_path: Path) -> None:
    """Without a CA and without the flag nothing changes."""
    (tmp_path / "repo").mkdir()
    out = _run(tmp_path, "")
    assert "ARGS=" in out
    assert "ENABLED=" in out


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is not available")
def test_explicit_off_wins_over_a_present_ca(tmp_path: Path) -> None:
    """PEER_PORTAL_TLS_ENABLED=0 keeps http even when a CA file exists."""
    _ca(tmp_path, "2026-11-03")
    out = _run(tmp_path, "$env:PEER_PORTAL_TLS_ENABLED = '0'")
    assert "ARGS=" in out
    assert "ENABLED=0" in out


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is not available")
def test_configured_ca_file_and_port_are_honoured(tmp_path: Path) -> None:
    """An operator-set PEER_CA_FILE and PEER_PORTAL_TLS_PORT are used instead of the search."""
    _ca(tmp_path, "2026-11-03")
    own = tmp_path / "own.pem"
    own.write_text("placeholder", encoding="utf-8")
    out = _run(tmp_path, f"$env:PEER_CA_FILE = '{own}'; $env:PEER_PORTAL_TLS_PORT = '9443'")
    assert "ARGS=--portal-port|9443" in out
    assert f"CA={own}" in out
