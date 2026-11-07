"""Tests for start.sh --lan-peer: Mac mirror of the Windows peer TLS, outbox remap, inbox check and front end."""
from __future__ import annotations

import base64
import hashlib
import os
import re
import socket
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
START_SH = ROOT / "start.sh"
BASH = "/bin/bash"  # macOS ships bash 3.2: the functions must work there under set -euo pipefail
FUNCS = (
    "_peer_tls_frontend_dir", "_peer_tls_frontend_configured", "_peer_cert_sha256", "_peer_tls_port_args",
    "_peer_ip_from_discovery", "_peer_outbox_remap_args", "_port_listening", "_ensure_peer_tls_frontend",
    "_run_lan_peer_probe", "_flush_lan_peer_outbox", "_run_lan_peer_inbox_check",
)
pytestmark = pytest.mark.skipif(not os.path.exists(BASH), reason="/bin/bash is not available")


def _text() -> str:
    """Return start.sh text."""
    return START_SH.read_text(encoding="utf-8")


def _function_source(name: str) -> str:
    """Return the source of the start.sh function *name* (a top-level ``name() {`` ... ``}`` block)."""
    match = re.search(rf"^{re.escape(name)}\(\) \{{\n.*?^\}}\n", _text(), re.S | re.M)
    assert match, f"{name} is missing from start.sh"
    return match.group(0)


def _pem(der: bytes) -> tuple[str, str]:
    """Return a one-certificate PEM wrapper around *der* and its SHA-256 (the launcher hashes the DER bytes only)."""
    body = base64.encodebytes(der).decode()
    return f"-----BEGIN CERTIFICATE-----\n{body}-----END CERTIFICATE-----\n", hashlib.sha256(der).hexdigest()


def _bash(tmp: Path, body: str, env: dict[str, str] | None = None, python: str | None = None, path: str | None = None):
    """Run *body* under bash with the start.sh functions defined and a stubbed logger; return the CompletedProcess."""
    funcs = "\n".join(_function_source(name) for name in FUNCS)
    script = textwrap.dedent(
        f"""
        set -euo pipefail
        SCRIPT_DIR="{ROOT}"; PT_DIR=""; US_PYTHON="{python or sys.executable}"
        _info() {{ echo "INFO $*"; }}
        _warn() {{ echo "WARN $*" >&2; }}
        _sync_control_plane_token() {{ :; }}
        """
    ) + funcs + "\n" + textwrap.dedent(body)
    full_env = {"PATH": path or "/usr/bin:/bin", "HOME": str(tmp), "LC_ALL": "C"}
    full_env.update(env or {})
    return subprocess.run([BASH, "-c", script], env=full_env, capture_output=True, text=True, check=False, timeout=60)


def _recorder(tmp: Path, name: str = "recorder") -> tuple[Path, Path]:
    """Create an executable that appends its argv to a log; return (script, log)."""
    log = tmp / f"{name}.log"
    script = tmp / name
    # US_PYTHON is also used for stdin helpers (fingerprint, discovery): those pass through to real Python
    # and are not recorded, so the log holds only the genuine peer calls.
    script.write_text(
        f'#!/bin/bash\nif [ "${{1:-}}" = "-" ]; then exec "{sys.executable}" "$@"; fi\n'
        f'echo "$@" >> "{log}"\nexit "${{RECORDER_RC:-0}}"\n',
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script, log


# ── peer TLS port args (mirror of Get-PeerTlsPortArgs) ───────────────────────────
def test_tls_disabled_flag_keeps_legacy_http(tmp_path) -> None:
    """PEER_PORTAL_TLS_ENABLED=off yields no port arguments and never reads a CA."""
    result = _bash(tmp_path, '_peer_tls_port_args; echo "args=${#_PEER_PORT_ARGS[@]}"', {"PEER_PORTAL_TLS_ENABLED": "OFF"})
    assert result.returncode == 0 and "args=0" in result.stdout


def test_explicit_ca_with_matching_fingerprint_selects_https_port(tmp_path) -> None:
    """An operator CA whose single certificate matches PEER_CA_SHA256 turns on https on 8443 for this process."""
    pem, digest = _pem(b"orama-test-cert-one")
    ca = tmp_path / "ca.pem"
    ca.write_text(pem, encoding="utf-8")
    result = _bash(
        tmp_path,
        f"PEER_CA_SHA256={digest.upper()}; "
        '_peer_tls_port_args; echo "args=${_PEER_PORT_ARGS[*]} en=${PEER_PORTAL_TLS_ENABLED} ca=${PEER_CA_FILE##*/} sha=${PEER_CA_SHA256:-unset}"; '
        """ "$US_PYTHON" -c 'import os; print("child_sha=" + os.environ.get("PEER_CA_SHA256", "unset"))'""",
        {"PEER_CA_FILE": str(ca)},
    )
    assert result.returncode == 0, result.stderr
    assert f"args=--portal-port 8443 en=1 ca=ca.pem sha={digest.lower()}" in result.stdout
    assert f"child_sha={digest.lower()}" in result.stdout


def test_tls_enabled_without_ca_exports_enablement_to_child(tmp_path) -> None:
    """Unexported PEER_PORTAL_TLS_ENABLED=1 selects https 8443 and exports enablement to child processes."""
    result = _bash(
        tmp_path,
        'PEER_PORTAL_TLS_ENABLED=1; '
        '_peer_tls_port_args; echo "args=${_PEER_PORT_ARGS[*]} en=${PEER_PORTAL_TLS_ENABLED}"; '
        """ "$US_PYTHON" -c 'import os; print("child_en=" + os.environ.get("PEER_PORTAL_TLS_ENABLED", "unset"))'""",
    )
    assert result.returncode == 0, result.stderr
    assert "args=--portal-port 8443 en=1" in result.stdout
    assert "child_en=1" in result.stdout


def test_fingerprint_mismatch_or_malformed_is_refused(tmp_path) -> None:
    """A CA that does not match the pinned fingerprint, or a malformed fingerprint, stops the peer call."""
    pem, _ = _pem(b"orama-test-cert-two")
    ca = tmp_path / "ca.pem"
    ca.write_text(pem, encoding="utf-8")
    wrong = _bash(tmp_path, "_peer_tls_port_args", {"PEER_CA_FILE": str(ca), "PEER_CA_SHA256": "0" * 64})
    assert wrong.returncode != 0 and "matching PEER_CA_SHA256" in wrong.stderr
    bad = _bash(tmp_path, "_peer_tls_port_args", {"PEER_CA_SHA256": "not-hex"})
    assert bad.returncode != 0 and "64 hex characters" in bad.stderr


def test_ca_with_extra_or_non_certificate_blocks_never_matches(tmp_path) -> None:
    """A PEM with a second block or a private key has no fingerprint, so it cannot be trusted."""
    pem, digest = _pem(b"orama-test-cert-three")
    ca = tmp_path / "ca.pem"
    ca.write_text(pem + "-----BEGIN " + "PRIVATE KEY-----\nAAAA\n-----END " + "PRIVATE KEY-----\n", encoding="utf-8")
    result = _bash(tmp_path, "_peer_tls_port_args", {"PEER_CA_FILE": str(ca), "PEER_CA_SHA256": digest})
    assert result.returncode != 0


def test_ca_found_on_disk_without_fingerprint_is_never_trusted(tmp_path) -> None:
    """A win-ca-*/orama-lan-ca.pem next to the repo is ignored unless the operator supplied its fingerprint."""
    repo = tmp_path / "repo"
    (repo / "win-ca-planted").mkdir(parents=True)
    pem, digest = _pem(b"orama-test-planted")
    (repo / "win-ca-planted" / "orama-lan-ca.pem").write_text(pem, encoding="utf-8")
    body = f'SCRIPT_DIR="{repo}"; _peer_tls_port_args; echo "args=${{#_PEER_PORT_ARGS[@]}} ca=${{PEER_CA_FILE:-none}}"'
    assert "args=0 ca=none" in _bash(tmp_path, body).stdout
    found = _bash(tmp_path, body, {"PEER_CA_SHA256": digest})
    assert found.returncode == 0 and "args=2" in found.stdout and "win-ca-planted" in found.stdout


def test_port_override_and_validation(tmp_path) -> None:
    """PEER_PORTAL_TLS_PORT is honoured when valid and rejects non-numeric or out-of-range values."""
    pem, digest = _pem(b"orama-test-cert-port")
    ca = tmp_path / "ca.pem"
    ca.write_text(pem, encoding="utf-8")
    base = {"PEER_CA_FILE": str(ca), "PEER_CA_SHA256": digest}
    ok = _bash(tmp_path, '_peer_tls_port_args; echo "${_PEER_PORT_ARGS[*]}"', {**base, "PEER_PORTAL_TLS_PORT": "9443"})
    assert ok.returncode == 0 and "--portal-port 9443" in ok.stdout
    for bad in ("0", "65536", "84x3", "-1"):
        assert _bash(tmp_path, "_peer_tls_port_args", {**base, "PEER_PORTAL_TLS_PORT": bad}).returncode != 0, bad


def test_helper_never_touches_trust_stores_or_the_local_portal_port() -> None:
    """The helper only sets process env for the peer CA; it never edits system trust, SSL_CERT_FILE or PORTAL_PORT."""
    body = _function_source("_peer_tls_port_args")
    for forbidden in ("SSL_CERT_FILE", "PORTAL_PORT=", "security add-trusted-cert", "update-ca", "keychain"):
        assert forbidden not in body, forbidden
    assert "curl -k" not in _text() and "--insecure" not in _text()


# ── queued-item remap (mirror of Get-PeerOutboxRemapArgs) ────────────────────────
def _discovery(tmp: Path, ip: str = "198.51.100.7") -> None:
    """Write a minimal last_discovery.json whose win endpoint is *ip* (a documentation address)."""
    path = tmp / ".openclaw" / "state"
    path.mkdir(parents=True, exist_ok=True)
    (path / "last_discovery.json").write_text(f'{{"endpoints": {{"win": {{"ip": "{ip}"}}}}}}', encoding="utf-8")


def test_remap_args_only_when_https_active_and_peer_known(tmp_path) -> None:
    """The remap maps the plain portal port to the https port for the discovered Windows peer only."""
    _discovery(tmp_path)
    env = {"PEER_PORTAL_TLS_ENABLED": "1", "PEER_CA_FILE": "/x/ca.pem"}
    ok = _bash(tmp_path, '_peer_outbox_remap_args; echo "${_PEER_REMAP_ARGS[*]}"', env)
    assert ok.returncode == 0 and "--remap-port 8002:8443 --remap-peer-ip 198.51.100.7" in ok.stdout
    custom = _bash(tmp_path, '_peer_outbox_remap_args; echo "${_PEER_REMAP_ARGS[*]}"', {**env, "PORTAL_PORT": "9001", "PEER_PORTAL_TLS_PORT": "9443"})
    assert "--remap-port 9001:9443" in custom.stdout
    for off in ({}, {"PEER_PORTAL_TLS_ENABLED": "0", "PEER_CA_FILE": "/x/ca.pem"}, {"PEER_PORTAL_TLS_ENABLED": "1"},
                {**env, "PORTAL_PORT": "8443"}):
        none = _bash(tmp_path, '_peer_outbox_remap_args; echo "n=${#_PEER_REMAP_ARGS[@]}"', off)
        assert "n=0" in none.stdout, off


def test_remap_args_empty_without_discovery_or_with_bad_address(tmp_path) -> None:
    """A missing discovery file or a non-IPv4 value never produces a remap (and the IP is never hardcoded)."""
    env = {"PEER_PORTAL_TLS_ENABLED": "1", "PEER_CA_FILE": "/x/ca.pem"}
    assert "n=0" in _bash(tmp_path, '_peer_outbox_remap_args; echo "n=${#_PEER_REMAP_ARGS[@]}"', env).stdout
    _discovery(tmp_path, ip="evil; rm -rf /")
    assert "n=0" in _bash(tmp_path, '_peer_outbox_remap_args; echo "n=${#_PEER_REMAP_ARGS[@]}"', env).stdout


# ── probe, flush and inbox wiring ───────────────────────────────────────────────
def test_probe_and_flush_pass_tls_args_and_reject_bad_config(tmp_path) -> None:
    """Both peer calls use the https port and remap, and a rejected configuration stops them before any call."""
    _discovery(tmp_path)
    pem, digest = _pem(b"orama-test-cert-flush")
    ca = tmp_path / "ca.pem"
    ca.write_text(pem, encoding="utf-8")
    stub, log = _recorder(tmp_path)
    env = {"PEER_CA_FILE": str(ca), "PEER_CA_SHA256": digest}
    flushed = _bash(tmp_path, "_flush_lan_peer_outbox", env, python=str(stub))
    assert flushed.returncode == 0, flushed.stderr
    line = log.read_text(encoding="utf-8")
    assert "flush-outbox --peer --portal-port 8443 --remap-port 8002:8443 --remap-peer-ip 198.51.100.7" in line
    log.unlink()
    probed = _bash(tmp_path, "_run_lan_peer_probe", env, python=str(stub))
    assert probed.returncode == 0, probed.stderr
    assert "--json --portal-port 8443" in log.read_text(encoding="utf-8")
    log.unlink()
    for call in ("_flush_lan_peer_outbox", "_run_lan_peer_probe"):
        rejected = _bash(tmp_path, call, {"PEER_CA_SHA256": "zz"}, python=str(stub))
        assert rejected.returncode != 0 and "peer TLS configuration rejected" in rejected.stderr
        assert not log.exists(), "a rejected configuration must not reach the peer"


def test_legacy_http_when_tls_is_off(tmp_path) -> None:
    """With TLS off the flush keeps the old arguments exactly (no port, no remap)."""
    stub, log = _recorder(tmp_path)
    result = _bash(tmp_path, "_flush_lan_peer_outbox", {"PEER_PORTAL_TLS_ENABLED": "0"}, python=str(stub))
    assert result.returncode == 0
    assert log.read_text(encoding="utf-8").strip().endswith("flush-outbox --peer --timeout 2")


def test_inbox_check_runs_for_windows_and_never_fails_the_launch(tmp_path) -> None:
    """The Mac check asks for Windows drops; an integrity failure warns but the function still returns 0."""
    stub, log = _recorder(tmp_path)
    ok = _bash(tmp_path, "_run_lan_peer_inbox_check", python=str(stub))
    assert ok.returncode == 0 and log.read_text(encoding="utf-8").strip().endswith("lan_peer_inbox_check.py --peer win")
    bad = _bash(tmp_path, "_run_lan_peer_inbox_check", {"RECORDER_RC": "2"}, python=str(stub))
    assert bad.returncode == 0 and "failed its integrity check" in bad.stderr


def test_lan_peer_branch_wiring() -> None:
    """--lan-peer starts the front end before the probe and runs the inbox check once, before the watcher block."""
    text = _text()
    block = text[text.index('if ! _lan_peer_session should-retry'):]
    assert text.count("\n  _run_lan_peer_inbox_check") + text.count("\n    _run_lan_peer_inbox_check") == 1
    assert text.index("_ensure_peer_tls_frontend ||") < text.index("if ! _lan_peer_session should-retry")
    assert block.index("_run_lan_peer_probe") < text.index("_run_lan_peer_inbox_check", text.index("if ! _lan_peer_session should-retry"))
    assert text.index("_run_lan_peer_inbox_check", text.index("if ! _lan_peer_session should-retry")) < text.index("# ── network watcher install")


# ── front end provisioning ──────────────────────────────────────────────────────
def _free_port() -> int:
    """Return a currently free loopback TCP port."""
    with socket.socket() as sock:
        sock.bind(("localhost", 0))
        return int(sock.getsockname()[1])


def _fake_caddy(tmp: Path) -> tuple[Path, Path]:
    """Create a fake ``caddy`` that logs calls, can fail validation and can open a listener on start."""
    bindir = tmp / "bin"
    bindir.mkdir(exist_ok=True)
    log = tmp / "caddy.log"
    listener = "import socket,sys,time\ns=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)\ns.bind(('localhost',int(sys.argv[1])));s.listen(5);time.sleep(6)"
    script = bindir / "caddy"
    script.write_text(
        '#!/bin/bash\necho "$@" >> "' + str(log) + '"\ncase "$1" in\n validate) exit "${FAKE_CADDY_VALIDATE_RC:-0}";;\n'
        ' start) if [ -n "${FAKE_CADDY_LISTEN_PORT:-}" ]; then "' + sys.executable + '" -c "' + listener.replace('"', '\\"') + '" "$FAKE_CADDY_LISTEN_PORT" >/dev/null 2>&1 & fi; exit 0;;\nesac\n',
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return bindir, log


def _config_dir(tmp: Path, proxy: str = "localhost:8002", admin: int | None = None) -> Path:
    """Create a front end config directory with a Caddyfile that proxies to *proxy* (and sets *admin* when given)."""
    directory = tmp / "cp"
    directory.mkdir(exist_ok=True)
    head = f"{{\n\tadmin localhost:{admin}\n}}\n\n" if admin else ""
    (directory / "Caddyfile").write_text(f"{head}https://:8443 {{\n\treverse_proxy {proxy}\n}}\n", encoding="utf-8")
    return directory


def test_port_listening_detects_a_loopback_listener() -> None:
    """_port_listening is true for an open loopback port and false for a closed one, with no external tool."""
    with socket.socket() as sock:
        sock.bind(("localhost", 0))
        sock.listen(1)
        port = sock.getsockname()[1]
        up = subprocess.run([BASH, "-c", _function_source("_port_listening") + f"\n_port_listening {port}"], capture_output=True, check=False)
        assert up.returncode == 0
    down = subprocess.run([BASH, "-c", _function_source("_port_listening") + f"\n_port_listening {_free_port()}"], capture_output=True, check=False)
    assert down.returncode != 0


def test_frontend_skipped_when_disabled_and_honest_when_prerequisites_missing(tmp_path) -> None:
    """Disabled is a no-op; missing caddy, missing Caddyfile or failed validation each warn and return non-zero."""
    bindir, log = _fake_caddy(tmp_path)
    cfg = _config_dir(tmp_path)
    off = _bash(tmp_path, "_ensure_peer_tls_frontend", {"ORAMA_PEER_TLS_FRONTEND": "0", "ORAMA_LAN_CONTROL_PLANE_DIR": str(cfg)}, path=f"{bindir}:/usr/bin:/bin")
    assert off.returncode == 0 and not log.exists()
    nocaddy = _bash(tmp_path, "_ensure_peer_tls_frontend", {"ORAMA_LAN_CONTROL_PLANE_DIR": str(cfg)}, path="/usr/bin:/bin")
    assert nocaddy.returncode != 0 and "caddy" in nocaddy.stderr
    empty = tmp_path / "empty"
    empty.mkdir()
    nofile = _bash(tmp_path, "_ensure_peer_tls_frontend", {"ORAMA_LAN_CONTROL_PLANE_DIR": str(empty)}, path=f"{bindir}:/usr/bin:/bin")
    assert nofile.returncode != 0 and "Caddyfile" in nofile.stderr and not log.exists()
    invalid = _bash(tmp_path, "_ensure_peer_tls_frontend", {"ORAMA_LAN_CONTROL_PLANE_DIR": str(cfg), "FAKE_CADDY_VALIDATE_RC": "1"}, path=f"{bindir}:/usr/bin:/bin")
    assert invalid.returncode != 0 and "validation" in invalid.stderr
    assert "start" not in log.read_text(encoding="utf-8"), "an invalid config must never be started"


def test_frontend_starts_validated_config_and_reports_listening(tmp_path) -> None:
    """A valid config is validated, started with the Caddyfile adapter, and success needs a real listener."""
    bindir, log = _fake_caddy(tmp_path)
    cfg = _config_dir(tmp_path)
    port = _free_port()
    env = {"ORAMA_LAN_CONTROL_PLANE_DIR": str(cfg), "PEER_PORTAL_TLS_PORT": str(port), "FAKE_CADDY_LISTEN_PORT": str(port)}
    started = _bash(tmp_path, "_ensure_peer_tls_frontend", env, path=f"{bindir}:/usr/bin:/bin")
    assert started.returncode == 0, started.stderr
    calls = log.read_text(encoding="utf-8").splitlines()
    assert calls[0].startswith("validate --config") and "--adapter caddyfile" in calls[0]
    assert calls[1].startswith("start --config") and "--adapter caddyfile" in calls[1]
    assert f"listening on port {port}" in started.stdout


def test_frontend_not_listening_after_start_is_reported_as_failure(tmp_path) -> None:
    """If caddy 'starts' but nothing listens, the function fails instead of claiming success."""
    bindir, _ = _fake_caddy(tmp_path)
    cfg = _config_dir(tmp_path)
    result = _bash(tmp_path, "_ensure_peer_tls_frontend", {"ORAMA_LAN_CONTROL_PLANE_DIR": str(cfg), "PEER_PORTAL_TLS_PORT": str(_free_port())}, path=f"{bindir}:/usr/bin:/bin")
    assert result.returncode != 0 and "did not come up" in result.stderr


def test_frontend_already_listening_is_not_restarted(tmp_path) -> None:
    """An existing listener is left alone: no validate-and-start churn and no second caddy."""
    bindir, log = _fake_caddy(tmp_path)
    cfg = _config_dir(tmp_path)
    with socket.socket() as sock:
        sock.bind(("localhost", 0))
        sock.listen(1)
        port = sock.getsockname()[1]
        result = _bash(tmp_path, "_ensure_peer_tls_frontend", {"ORAMA_LAN_CONTROL_PLANE_DIR": str(cfg), "PEER_PORTAL_TLS_PORT": str(port)}, path=f"{bindir}:/usr/bin:/bin")
    assert result.returncode == 0 and "already listening" in result.stdout
    assert not log.exists() or "start" not in log.read_text(encoding="utf-8")


def test_frontend_warns_when_the_proxy_target_does_not_match_the_portal_port(tmp_path) -> None:
    """A Caddyfile that proxies to another port than PORTAL_PORT is flagged before anything starts."""
    bindir, _ = _fake_caddy(tmp_path)
    cfg = _config_dir(tmp_path, proxy="localhost:9999")
    result = _bash(tmp_path, "_ensure_peer_tls_frontend", {"ORAMA_LAN_CONTROL_PLANE_DIR": str(cfg), "PORTAL_PORT": "8002", "PEER_PORTAL_TLS_PORT": str(_free_port())}, path=f"{bindir}:/usr/bin:/bin")
    assert "proxies to port 9999" in result.stderr and "PORTAL_PORT is 8002" in result.stderr


def test_portal_stays_on_loopback_only_when_the_front_end_is_configured(tmp_path) -> None:
    """With a usable front end the plain-HTTP portal is not LAN-bound by default; the operator can still override."""
    bindir, _ = _fake_caddy(tmp_path)
    cfg = _config_dir(tmp_path)
    configured = _bash(tmp_path, "_peer_tls_frontend_configured && echo yes || echo no", {"ORAMA_LAN_CONTROL_PLANE_DIR": str(cfg)}, path=f"{bindir}:/usr/bin:/bin")
    assert "yes" in configured.stdout
    off = _bash(tmp_path, "_peer_tls_frontend_configured && echo yes || echo no", {"ORAMA_LAN_CONTROL_PLANE_DIR": str(cfg), "ORAMA_PEER_TLS_FRONTEND": "0"}, path=f"{bindir}:/usr/bin:/bin")
    assert "no" in off.stdout
    text = _text()
    early = text[text.index('if [ "$_LAN_PEER_MODE" = "1" ]; then\n  export PT_BIND_LAN'):][:1400]
    assert "_peer_tls_frontend_configured" in early and 'PORTAL_BIND_LAN="${PORTAL_BIND_LAN:-0}"' in early
    assert 'PORTAL_BIND_LAN="${PORTAL_BIND_LAN:-1}"' in early, "without a front end the legacy default must remain, with a warning"


# ── idempotence: never start over something running, never stop or restart implicitly ──────────
def test_existing_admin_endpoint_blocks_a_second_instance_and_names_the_explicit_stop(tmp_path) -> None:
    """With a caddy admin endpoint up and the peer port closed, nothing starts and the operator gets the stop command."""
    bindir, log = _fake_caddy(tmp_path)
    with socket.socket() as sock:
        sock.bind(("localhost", 0))
        sock.listen(1)
        admin = sock.getsockname()[1]
        cfg = _config_dir(tmp_path, admin=admin)
        result = _bash(tmp_path, "_ensure_peer_tls_frontend", {"ORAMA_LAN_CONTROL_PLANE_DIR": str(cfg), "PEER_PORTAL_TLS_PORT": str(_free_port())}, path=f"{bindir}:/usr/bin:/bin")
    assert result.returncode != 0
    assert f"caddy stop --address localhost:{admin}" in result.stderr and "not starting a second instance" in result.stderr
    assert not log.exists(), "nothing may be validated or started while another instance is running"


def test_calling_twice_starts_exactly_once(tmp_path) -> None:
    """A second call finds the listener the first one created and does not start again."""
    bindir, log = _fake_caddy(tmp_path)
    cfg = _config_dir(tmp_path)
    port = _free_port()
    env = {"ORAMA_LAN_CONTROL_PLANE_DIR": str(cfg), "PEER_PORTAL_TLS_PORT": str(port), "FAKE_CADDY_LISTEN_PORT": str(port)}
    result = _bash(tmp_path, "_ensure_peer_tls_frontend\n_ensure_peer_tls_frontend", env, path=f"{bindir}:/usr/bin:/bin")
    assert result.returncode == 0, result.stderr
    starts = [line for line in log.read_text(encoding="utf-8").splitlines() if line.startswith("start ")]
    assert len(starts) == 1
    assert result.stdout.count("already listening") == 1


def test_nothing_ever_stops_restarts_or_reloads(tmp_path) -> None:
    """Across every scenario the fake caddy never sees stop, reload or restart, and the source never kills or relaunches."""
    bindir, log = _fake_caddy(tmp_path)
    cfg = _config_dir(tmp_path)
    port = _free_port()
    env = {"ORAMA_LAN_CONTROL_PLANE_DIR": str(cfg), "PEER_PORTAL_TLS_PORT": str(port), "FAKE_CADDY_LISTEN_PORT": str(port)}
    _bash(tmp_path, "_ensure_peer_tls_frontend\n_ensure_peer_tls_frontend", env, path=f"{bindir}:/usr/bin:/bin")
    _bash(tmp_path, "_ensure_peer_tls_frontend", {**env, "FAKE_CADDY_VALIDATE_RC": "1"}, path=f"{bindir}:/usr/bin:/bin")
    verbs = {line.split()[0] for line in log.read_text(encoding="utf-8").splitlines() if line.strip()}
    assert verbs <= {"validate", "start"}, verbs
    body = _function_source("_ensure_peer_tls_frontend")
    for line in body.splitlines():
        code = line.strip()
        assert not re.match(r"^(caddy (stop|reload|run)|kill|pkill|killall|launchctl)\b", code), code
