"""Tests for start.ps1 making the LAN peer link use the peer's HTTPS front end, with an authenticated CA."""
from __future__ import annotations

import base64
import hashlib
import os
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

START_PS1 = Path(__file__).resolve().parents[1] / "platform" / "windows" / "start.ps1"
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")
needs_powershell = pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is not available")


def _text() -> str:
    """Return start.ps1 with CRLF normalised."""
    return START_PS1.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def _function_source(name: str) -> str:
    """Return the source of the start.ps1 function *name*."""
    match = re.search(rf"^function {re.escape(name)} \{{.*?^\}}\n", _text(), re.S | re.M)
    assert match, f"{name} is missing from start.ps1"
    return match.group(0)


def test_probe_and_flush_pass_the_peer_tls_port_args_and_reject_bad_config() -> None:
    """Both peer calls splat the https port args, and a rejected configuration stops the call."""
    probe = _function_source("Invoke-LanPeerProbe")
    flush = _function_source("Invoke-LanPeerOutboxFlush")
    for body in (probe, flush):
        assert "@(Get-PeerTlsPortArgs)" in body and "@peerPortArgs" in body
        assert "peer TLS configuration rejected" in body
    assert "@remapArgs" in flush and "@(Get-PeerOutboxRemapArgs)" in flush


def test_function_never_touches_trust_stores_or_the_local_portal_port() -> None:
    """The helper only sets process env for the peer CA and never changes system trust or PORTAL_PORT."""
    body = _function_source("Get-PeerTlsPortArgs")
    assert "$env:SSL_CERT_FILE" not in body
    assert "$env:PORTAL_PORT" not in body
    assert "Import-Certificate" not in body and "certutil" not in body.lower()
    assert "PEER_PINNED_FINGERPRINTS" not in body


def test_lan_peer_branch_runs_the_inbox_check_after_the_probe_block() -> None:
    """--lan-peer calls Invoke-LanPeerInboxCheck once, after the pinned probe branch and before the watcher."""
    text = _text()
    assert "function Invoke-LanPeerInboxCheck {" in text
    assert "lan_peer_inbox_check.py" in text
    assert text.count("\n    Invoke-LanPeerInboxCheck\n") == 1
    assert text.index("} elseif (Invoke-LanPeerProbe) {") < text.index("\n    Invoke-LanPeerInboxCheck\n")
    assert text.index("\n    Invoke-LanPeerInboxCheck\n") < text.index("# ── LM Link watcher autostart")


class _Case:
    """A throw-away fake repository nested so every folder the launcher searches belongs to the test."""

    def __init__(self, tmp_path: Path) -> None:
        """Create tmp/l1/l2/l3/repo so the repo and its three searched parents are all test-owned."""
        self.tmp = tmp_path
        self.repo = tmp_path / "l1" / "l2" / "l3" / "repo"
        self.repo.mkdir(parents=True)

    def ca(self, folder: str, body: bytes, where: Path | None = None, count: int = 1) -> tuple[Path, str]:
        """Write a placeholder PEM with *count* certificate blocks and return (path, sha256 of the first DER)."""
        root = where or self.repo
        directory = root / folder
        directory.mkdir(parents=True, exist_ok=True)
        block = "-----BEGIN CERTIFICATE-----\n" + base64.b64encode(body).decode() + "\n-----END CERTIFICATE-----\n"
        path = directory / "orama-lan-ca.pem"
        path.write_text(block * count, encoding="utf-8")
        return path, hashlib.sha256(body).hexdigest()

    def run(self, fn: str, env_lines: str = "") -> list[str]:
        """Run function *fn* under PowerShell and return its ARGS/ENABLED/CA/THROW lines."""
        script = self.tmp / "case.ps1"
        sources = "\n".join(
            _function_source(name)
            for name in ("Get-PemCertSha256", "Get-PeerTlsPortArgs", "Get-PeerOutboxRemapArgs")
        )
        script.write_text(
            textwrap.dedent(
                f"""
                function _Info {{ param($a, $b) }}
                function _Warn {{ param($a, $b) }}
                $RepoRoot = '{self.repo}'
                {env_lines}
                {sources}
                try {{ $r = @({fn}) }} catch {{ 'THROW=' + $_.Exception.Message; $r = @() }}
                'ARGS=' + ($r -join '|')
                'ENABLED=' + $env:PEER_PORTAL_TLS_ENABLED
                'CA=' + $env:PEER_CA_FILE
                'SHA=' + $env:PEER_CA_SHA256
                """
            ),
            encoding="utf-8",
        )
        done = subprocess.run(
            [POWERSHELL, "-NoProfile", "-File", str(script)],
            capture_output=True, text=True, timeout=60, check=True,
            env={"PATH": os.environ["PATH"], "SystemRoot": os.environ.get("SystemRoot", "")},
        )
        return done.stdout.splitlines()


@pytest.fixture()
def case(tmp_path: Path) -> _Case:
    """Return a fresh nested fake repository."""
    return _Case(tmp_path)


@needs_powershell
def test_a_ca_on_disk_is_not_trusted_without_an_operator_fingerprint(case: _Case) -> None:
    """A planted mac-ca-* file is ignored unless PEER_CA_SHA256 authenticates it: no https, no env changes."""
    case.ca("mac-ca-2027-01-01", b"planted")
    out = case.run("Get-PeerTlsPortArgs")
    assert "ARGS=" in out and "ENABLED=" in out and "CA=" in out


@needs_powershell
def test_search_accepts_only_the_ca_matching_the_operator_fingerprint(case: _Case) -> None:
    """A newer planted CA never wins over the older CA whose DER hash the operator confirmed."""
    genuine, sha = case.ca("mac-ca-2026-11-03", b"genuine")
    case.ca("mac-ca-2027-01-01", b"planted")
    out = case.run("Get-PeerTlsPortArgs", f"$env:PEER_CA_SHA256 = '{sha.upper()}'")
    assert "ARGS=--portal-port|8443" in out
    assert "ENABLED=1" in out
    assert f"CA={genuine}" in out
    assert f"SHA={sha}" in out


@needs_powershell
def test_no_matching_ca_keeps_the_peer_on_http(case: _Case) -> None:
    """When no mac-ca-* file matches the fingerprint nothing is trusted."""
    case.ca("mac-ca-2026-11-03", b"other")
    out = case.run("Get-PeerTlsPortArgs", f"$env:PEER_CA_SHA256 = '{'0' * 64}'")
    assert "ARGS=" in out and "CA=" in out


@needs_powershell
def test_a_bundle_with_extra_certificates_is_not_authenticated(case: _Case) -> None:
    """A file with a matching first certificate plus an appended one is rejected, since all would be trusted."""
    _, sha = case.ca("mac-ca-2026-11-03", b"genuine", count=2)
    out = case.run("Get-PeerTlsPortArgs", f"$env:PEER_CA_SHA256 = '{sha}'")
    assert "ARGS=" in out and "ENABLED=" in out


@needs_powershell
@pytest.mark.parametrize("label", ["TRUSTED CERTIFICATE", "PRIVATE KEY"])
def test_a_file_with_any_extra_pem_block_is_not_authenticated(case: _Case, label: str) -> None:
    """The TLS library would also trust a TRUSTED CERTIFICATE block, so any extra block voids the match."""
    path, sha = case.ca("mac-ca-2026-11-03", b"genuine")
    path.write_text(
        path.read_text(encoding="utf-8")
        + f"-----BEGIN {label}-----\n{base64.b64encode(b'extra').decode()}\n-----END {label}-----\n",
        encoding="utf-8",
    )
    out = case.run("Get-PeerTlsPortArgs", f"$env:PEER_CA_SHA256 = '{sha}'")
    assert "ARGS=" in out and "ENABLED=" in out


@needs_powershell
def test_explicit_ca_file_must_match_the_fingerprint_when_one_is_set(case: _Case) -> None:
    """An explicit PEER_CA_FILE that does not match PEER_CA_SHA256 is refused loudly."""
    path, _ = case.ca("own", b"explicit")
    out = case.run("Get-PeerTlsPortArgs", f"$env:PEER_CA_FILE = '{path}'; $env:PEER_CA_SHA256 = '{'1' * 64}'")
    assert any(line.startswith("THROW=PEER_CA_FILE is not a single certificate") for line in out)
    assert "ARGS=" in out


@needs_powershell
def test_explicit_ca_file_without_a_fingerprint_is_the_operators_choice(case: _Case) -> None:
    """An explicitly configured PEER_CA_FILE is used as given, with the configured port."""
    path, _ = case.ca("own", b"explicit")
    out = case.run("Get-PeerTlsPortArgs", f"$env:PEER_CA_FILE = '{path}'; $env:PEER_PORTAL_TLS_PORT = '9443'")
    assert "ARGS=--portal-port|9443" in out
    assert f"CA={path}" in out


@needs_powershell
def test_explicit_off_wins_over_everything(case: _Case) -> None:
    """PEER_PORTAL_TLS_ENABLED=0 keeps http even with a CA and a matching fingerprint."""
    _, sha = case.ca("mac-ca-2026-11-03", b"genuine")
    out = case.run("Get-PeerTlsPortArgs", f"$env:PEER_PORTAL_TLS_ENABLED = '0'; $env:PEER_CA_SHA256 = '{sha}'")
    assert "ARGS=" in out and "ENABLED=0" in out


@needs_powershell
@pytest.mark.parametrize("bad", ["84a3", "99999", "0", "-1", "8 443"])
def test_a_malformed_peer_tls_port_is_rejected_not_defaulted(case: _Case, bad: str) -> None:
    """A typo or out-of-range port throws instead of silently probing 8443."""
    path, _ = case.ca("own", b"explicit")
    out = case.run("Get-PeerTlsPortArgs", f"$env:PEER_CA_FILE = '{path}'; $env:PEER_PORTAL_TLS_PORT = '{bad}'")
    assert any(line.startswith("THROW=PEER_PORTAL_TLS_PORT must be") for line in out)
    assert "ARGS=" in out


@needs_powershell
def test_malformed_fingerprint_is_rejected(case: _Case) -> None:
    """PEER_CA_SHA256 must be 64 hex characters."""
    out = case.run("Get-PeerTlsPortArgs", "$env:PEER_CA_SHA256 = 'abc'")
    assert any(line.startswith("THROW=PEER_CA_SHA256 must be 64 hex") for line in out)


@needs_powershell
def test_outbox_remap_args_map_the_plain_port_for_the_named_peer_only(case: _Case) -> None:
    """With https active and MAC_IP set the flush remaps the plain portal port to the https port."""
    env = (
        "$env:PEER_PORTAL_TLS_ENABLED = '1'; $env:PEER_CA_FILE = 'x.pem'; $env:MAC_IP = '203.0.113.7'; "
        "$env:PEER_PORTAL_TLS_PORT = '9443'; $env:PORTAL_PORT = '8100'"
    )
    out = case.run("Get-PeerOutboxRemapArgs", env)
    assert "ARGS=--remap-port|8100:9443|--remap-peer-ip|203.0.113.7" in out


@needs_powershell
@pytest.mark.parametrize(
    "env",
    [
        "$env:PEER_CA_FILE = 'x.pem'; $env:MAC_IP = '203.0.113.7'",
        "$env:PEER_PORTAL_TLS_ENABLED = '1'; $env:PEER_CA_FILE = 'x.pem'",
        "$env:PEER_PORTAL_TLS_ENABLED = '1'; $env:MAC_IP = '203.0.113.7'",
    ],
)
def test_outbox_remap_is_off_without_https_a_peer_ip_or_trust(case: _Case, env: str) -> None:
    """No remap unless https is on, the peer IP is known and trust is configured."""
    assert "ARGS=" in case.run("Get-PeerOutboxRemapArgs", env)
