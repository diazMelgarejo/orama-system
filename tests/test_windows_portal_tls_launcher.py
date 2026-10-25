"""PR2b: Portal TLS front end wiring in platform/windows/start.ps1 (static checks)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START_PS1 = ROOT / "platform" / "windows" / "start.ps1"


def _src() -> str:
    return START_PS1.read_text(encoding="utf-8-sig")


def _between(text: str, start: str, end: str) -> str:
    i = text.index(start)
    return text[i : text.index(end, i)]


def test_tls_enabled_flag_accepts_only_truthy_values():
    src = _src()
    assert "$env:PORTAL_TLS_ENABLED" in src
    assert re.search(r"-in @\('1', 'true', 'yes'\)", _between(src, "$PortalTlsEnabled = $false", "# ── --stop"))
    assert "PORTAL_TLS_PORT" in src and "8443" in src
    assert "PORTAL_TLS_LISTEN_HOST" in src


def test_tls_launch_block_is_gated_on_the_flag():
    src = _src()
    block = _between(src, "# ── 4. Portal TLS front end", "# ── Per-service summary")
    assert block.lstrip().splitlines()[1].startswith("if ($PortalTlsEnabled)")
    assert "orchestrator.portal_tls_proxy" in block
    for needle in ("--listen-port", "--upstream-port", "--listen-host", "$PtDir\\src;$PtDir"):
        assert needle in block
    # missing module fails clearly and counts as a FAILED core service
    assert "portal_tls_proxy.py" in block and "State = 'FAILED'" in block
    assert "Name 'Portal TLS'" in block


def test_portal_host_forced_to_loopback_when_tls_enabled():
    src = _src()
    block = _between(src, "if ($PortalTlsEnabled) {\n    # The proxy is the only", "$svc = Start-OramaService -Name 'Portal'")
    assert "$PortalHost = [System.Net.IPAddress]::Loopback.IPAddressToString" in block
    # forced regardless of PORTAL_BIND_LAN: the override sits after Get-BindHost ran
    assert src.index("$PortalHost = Get-BindHost") < src.index("$PortalHost = [System.Net.IPAddress]::Loopback")


def test_tls_proxy_counts_toward_exit_code_and_summary():
    src = _src()
    assert "$LifeResults += Life-Settle $svc $PortalTlsListenHost" in src
    summary = _between(src, "# ── Per-service summary", "# ── Ready")
    assert "$_.State -eq 'FAILED'" in summary and "exit 1" in summary


def test_ready_section_prints_fingerprint_lines_not_recomputed():
    src = _src()
    ready = _between(src, "# ── Ready", "# ── Verify model fallback")
    assert "--print-fingerprint" in ready
    assert "ca_sha256_file=" in ready and "ca_public_path=" in ready
    assert "https://localhost:" in ready
    assert "separate channel" in ready
    assert "Get-FileHash" not in ready


def test_stop_kills_proxy_by_pid_file_with_command_line_match():
    src = _src()
    stop = _between(src, "if ($Stop) {", "# ── --fleet-status")
    assert "'portal_tls'" in stop
    assert "Life-PidMatches $recorded '^pythonw?[0-9.]*$' 'portal_tls_proxy'" in stop
    assert "taskkill.exe /PID $recorded /T /F" in stop
    assert "Stop-Process -Name" not in stop and "taskkill /IM" not in stop


def test_status_lists_tls_port_and_log_slug_is_portal_tls():
    src = _src()
    status = _between(src, "if ($Status) {", "# ── LAN discovery")
    assert "Portal TLS" in status and "$PortalTlsPort" in status
    assert "-replace '\\s+', '_'" in src  # 'Portal TLS' -> portal_tls.log / portal_tls.pid


def test_added_lines_have_no_literal_loopback_or_private_ips():
    # repo_hygiene rejects these on any added line; guard the new block directly.
    src = _src()
    block = _between(src, "# ── Portal TLS front end (opt-in", "# ── --stop")
    block += _between(src, "# ── 4. Portal TLS front end", "# ── Per-service summary")
    dotted = r"\.".join(["127", "0", "0", "1"])
    private = [dotted, r"192\.168\.", r"10\.\d+\.\d+\.\d+", ":" + ":1"]
    assert not re.search(r"\b(" + "|".join(private) + ")", block)


def test_ps_file_keeps_bom_and_crlf():
    raw = START_PS1.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    assert raw.count(b"\r\n") == raw.count(b"\n")
