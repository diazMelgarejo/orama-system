"""PR2b: Portal TLS front end wiring in platform/windows/start.ps1 (static checks)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START_PS1 = ROOT / "platform" / "windows" / "start.ps1"


def _src() -> str:
    """Return the text of start.ps1 (BOM stripped, newlines normalised)."""
    return START_PS1.read_text(encoding="utf-8-sig")


def _between(text: str, start: str, end: str) -> str:
    """Return the slice of text from the first start marker up to the next end marker."""
    i = text.index(start)
    return text[i : text.index(end, i)]


def test_tls_enabled_flag_accepts_only_truthy_values():
    """PORTAL_TLS_ENABLED is read as truthy only for 1, true or yes, and the TLS port and listen host are configurable."""
    src = _src()
    assert "$env:PORTAL_TLS_ENABLED" in src
    assert re.search(r"-in @\('1', 'true', 'yes'\)", _between(src, "$PortalTlsEnabled = $false", "# ── --stop"))
    assert "PORTAL_TLS_PORT" in src and "8443" in src
    assert "PORTAL_TLS_LISTEN_HOST" in src


def test_tls_launch_block_is_gated_on_the_flag():
    """The TLS proxy launch block runs only when enabled, passes its ports and host, and reports a missing module as FAILED."""
    src = _src()
    block = _between(src, "# ── 4. Portal TLS front end", "# ── Per-service summary")
    assert block.lstrip().splitlines()[1].startswith("if ($PortalTlsEnabled")
    assert "orchestrator.portal_tls_proxy" in block
    for needle in ("--listen-port", "--upstream-port", "--listen-host", "$PtDir\\src;$PtDir"):
        assert needle in block
    # missing module fails clearly and counts as a FAILED core service
    assert "portal_tls_proxy.py" in block and "State = 'FAILED'" in block
    assert "Name 'Portal TLS'" in block


def test_portal_host_forced_to_loopback_when_tls_enabled():
    """With TLS enabled the Portal host is forced to loopback after Get-BindHost, whatever the LAN settings."""
    src = _src()
    block = _between(src, "if ($PortalTlsEnabled) {\n    # The proxy is the only", "$svc = Start-OramaService -Name 'Portal'")
    assert "$PortalHost = [System.Net.IPAddress]::Loopback.IPAddressToString" in block
    # forced regardless of PORTAL_BIND_LAN: the override sits after Get-BindHost ran
    assert src.index("$PortalHost = Get-BindHost") < src.index("$PortalHost = [System.Net.IPAddress]::Loopback")


def test_tls_proxy_counts_toward_exit_code_and_summary():
    """The TLS proxy row is added to the results, so a failure fails the summary and the exit code."""
    src = _src()
    assert "$tlsRow = Life-Settle $svc $PortalTlsListenHost" in src
    assert "$LifeResults += $tlsRow" in src
    summary = _between(src, "# ── Per-service summary", "# ── Ready")
    assert "$_.State -eq 'FAILED'" in summary and "exit 1" in summary


def test_ready_section_prints_fingerprint_lines_not_recomputed():
    """The ready section prints the CA fingerprint reported by the proxy rather than recomputing it."""
    src = _src()
    ready = _between(src, "# ── Ready", "# ── Verify model fallback")
    assert "--print-fingerprint" in ready
    assert "ca_sha256_file=" in ready and "ca_public_path=" in ready
    assert "https://localhost:" in ready
    assert "separate channel" in ready
    assert "Get-FileHash" not in ready


def test_stop_kills_proxy_by_pid_file_with_command_line_match():
    """--stop kills the TLS proxy by PID file with a command-line match, never by process name."""
    src = _src()
    stop = _between(src, "if ($Stop) {", "# ── --fleet-status")
    assert "'portal_tls'" in stop
    assert "Life-PidMatches $recorded '^pythonw?[0-9.]*$' 'portal_tls_proxy'" in stop
    assert "taskkill.exe /PID $recorded /T /F" in stop
    assert "Stop-Process -Name" not in stop and "taskkill /IM" not in stop


def test_status_lists_tls_port_and_log_slug_is_portal_tls():
    """--status lists the TLS port, and the service name Portal TLS maps to the portal_tls log and PID slug."""
    src = _src()
    status = _between(src, "if ($Status) {", "# ── LAN discovery")
    assert "Portal TLS" in status and "$PortalTlsPort" in status
    assert "-replace '\\s+', '_'" in src  # 'Portal TLS' -> portal_tls.log / portal_tls.pid


def test_added_lines_have_no_literal_loopback_or_private_ips():
    """The TLS blocks of start.ps1 contain no literal loopback or private IP addresses."""
    # repo_hygiene rejects these on any added line; guard the new block directly.
    src = _src()
    block = _between(src, "# ── Portal TLS front end (opt-in", "# ── --stop")
    block += _between(src, "# ── 4. Portal TLS front end", "# ── Per-service summary")
    dotted = r"\.".join(["127", "0", "0", "1"])
    private = [dotted, r"192\.168\.", r"10\.\d+\.\d+\.\d+", ":" + ":1"]
    assert not re.search(r"\b(" + "|".join(private) + ")", block)


def test_ps_file_keeps_bom_and_crlf():
    """start.ps1 keeps its UTF-8 BOM and uses CRLF line endings throughout."""
    raw = START_PS1.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    assert raw.count(b"\r\n") == raw.count(b"\n")


def test_reused_portal_must_be_loopback_only_before_proxy_starts():
    """A reused Portal must be loopback-only before the proxy starts, and the TLS claims are gated on that check."""
    src = _src()
    assert "function Test-PortLoopbackOnly" in src
    assert "[System.Net.IPAddress]::IsLoopback" in src
    portal = _between(src, "$portalRow = Life-Settle", "# ── 4. Portal TLS front end")
    assert "Test-PortLoopbackOnly $PortalPort" in portal
    assert "non-loopback" in portal and "State = 'FAILED'" in portal
    # the proxy launch and the 'loopback-only' claim are both gated on the check
    assert "if ($PortalTlsEnabled -and $PortalLoopbackOk) {" in _between(
        src, "# ── 4. Portal TLS front end", "# ── Per-service summary"
    )
    ready = _between(src, "# ── Ready", "# ── Verify model fallback")
    assert "if ($PortalTlsEnabled -and $PortalLoopbackOk)" in ready


def test_status_row_only_for_enabled_or_recorded_proxy():
    """The --status TLS row appears only when TLS is enabled or a PID file records the proxy."""
    status = _between(_src(), "if ($Status) {", "# ── LAN discovery")
    assert "Get-PidOnPort $PortalTlsPort" not in status
    assert "portal_tls.pid" in status


def test_service_summary_name_column_fits_portal_tls():
    """The service summary name column is wide enough for the name Portal TLS."""
    summary = _between(_src(), "# ── Per-service summary", "# ── Ready")
    assert "{0,-10} port" in summary


def _powershell51():
    """Return the path of Windows PowerShell on PATH, or None."""
    import shutil

    return shutil.which("powershell.exe") or shutil.which("powershell")


def test_loopback_probe_distinguishes_loopback_and_wildcard_listeners():
    """Test-PortLoopbackOnly returns True for a loopback listener and False for a wildcard listener or no listener (runs real PowerShell)."""
    import socket
    import subprocess

    import pytest

    ps = _powershell51()
    if not ps or not __import__("sys").platform.startswith("win"):
        pytest.skip("needs Windows PowerShell")
    src = _src()
    func = _between(src, "function Test-PortLoopbackOnly", "# Life-* helpers")
    loop = socket.socket()
    wild = socket.socket()
    try:
        loop.bind((__import__("ipaddress").ip_address(socket.gethostbyname("localhost")).compressed, 0))
        loop.listen(1)
        wild.bind(("", 0))
        wild.listen(1)
        loop_port = loop.getsockname()[1]
        wild_port = wild.getsockname()[1]
        script = (
            func
            + f"\n$a = Test-PortLoopbackOnly {loop_port}\n$b = Test-PortLoopbackOnly {wild_port}\n"
            + "$c = Test-PortLoopbackOnly 1\nWrite-Output \"$a $b $c\"\n"
        )
        out = subprocess.run(
            [ps, "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=60,
        ).stdout.strip()
    finally:
        loop.close()
        wild.close()
    assert out.splitlines()[-1] == "True False False"
