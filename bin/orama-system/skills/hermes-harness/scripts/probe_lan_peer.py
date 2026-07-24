#!/usr/bin/env python3
"""probe_lan_peer.py — HTTP probe of the LAN peer orama install.

Reads ~/.openclaw/state/last_discovery.json for peer IP (never hardcode DHCP).
Checks peer portal /health, optional /api/status (Bearer), and LM Studio /v1/models.

Usage:
    python probe_lan_peer.py
    python probe_lan_peer.py --json
    python probe_lan_peer.py --peer-ip 192.168.x.x  # override discovery
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import quote

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parents[4]


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class Check:
    name: str
    status: Status
    detail: str = ""


def discovery_path() -> Path:
    return Path.home() / ".openclaw" / "state" / "last_discovery.json"


def probe_result_path() -> Path:
    """Local-only probe artifact (gitignored via ~/.openclaw/). Never commit."""
    return Path.home() / ".openclaw" / "state" / "last_lan_peer_probe.json"


def write_probe_result(payload: dict[str, Any]) -> Path:
    path = probe_result_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _parse_env_line(line: str) -> tuple[str, str] | None:
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None
    if raw.startswith("export "):
        raw = raw[len("export ") :].strip()
    if "=" not in raw:
        return None
    key, value = raw.split("=", 1)
    key = key.strip()
    if not key:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return key, value


def load_repo_env(root: Path = _REPO_ROOT) -> None:
    """Load repo .env files for direct CLI use without overriding shell exports."""
    values: dict[str, str] = {}
    for name in (".env", ".env.local"):
        path = root / name
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            parsed = _parse_env_line(line)
            if parsed:
                key, value = parsed
                values[key] = value
    for key, value in values.items():
        os.environ.setdefault(key, value)


load_repo_env()


def load_discovery() -> dict[str, Any]:
    path = discovery_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def local_role() -> str:
    explicit = os.environ.get("ORAMA_PLATFORM", "").strip().lower()
    if explicit in ("macos", "darwin", "mac"):
        return "mac"
    if explicit in ("windows", "win"):
        return "win"
    if platform.system().lower() == "windows":
        return "win"
    return "mac"


def peer_from_discovery(discovery: dict[str, Any], role: str) -> tuple[str, int]:
    endpoints = discovery.get("endpoints") or {}
    if role == "mac":
        peer = endpoints.get("win") or {}
        fallback_ip = os.environ.get("WIN_IP", "").strip()
    else:
        peer = endpoints.get("mac") or {}
        fallback_ip = os.environ.get("MAC_IP", "").strip()
    ip = str(peer.get("ip") or "").strip()
    port = int(peer.get("port") or 1234)
    if ip in ("", "localhost", "127.0.0.1") and fallback_ip:
        ip = fallback_ip
    return ip, port


def http_get(url: str, token: str = "", timeout: int = 8) -> tuple[int, str]:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body[:500]
    except urllib.error.HTTPError as exc:
        return exc.code, str(exc.reason)
    except Exception as exc:
        return -1, str(exc)


def http_post_json(
    url: str, payload: dict[str, Any], token: str = "", timeout: int = 8
) -> tuple[int, str]:
    """POST a JSON body; same (status, body[:2000]) contract as http_get.

    Status -1 means transport failure (connection refused, timeout, DNS),
    distinct from any HTTP status the peer actually returned.
    """
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body[:2000]
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            detail = str(exc.reason)
        return exc.code, detail
    except Exception as exc:
        return -1, str(exc)


def relay_probe(
    peer_ip: str,
    portal_port: int,
    target: str,
    default_target_port: int,
    tokens: list[str],
    timeout: int = 8,
) -> tuple[int, dict[str, Any]]:
    """Gossip relay (mother plan §4.4/§5): ask the reachable peer at peer_ip
    to probe `target` on our behalf via POST /api/peer-relay-probe.

    `target` is "IP" or "IP:PORT"; without a port, default_target_port is
    used (matching the endpoint's own default of the portal port). Tries
    each candidate token until one is accepted (same convention as the
    authenticated /api/status check). Returns (exit_code, result_payload):
      0 = relay round-trip succeeded and target reachable
      1 = relay round-trip succeeded but target NOT reachable
      2 = relay itself failed (peer unreachable, auth exhausted, bad reply)
    """
    target_ip, _, port_str = target.partition(":")
    target_ip = target_ip.strip()
    try:
        target_port = int(port_str) if port_str else default_target_port
    except ValueError:
        return 2, {"error": f"invalid --relay port in {target!r}"}
    if not target_ip:
        return 2, {"error": "empty --relay target IP"}

    url = f"http://{peer_ip}:{portal_port}/api/peer-relay-probe"
    body = {"target_ip": target_ip, "target_port": target_port}
    last: tuple[int, str] = (-1, "no token candidates")
    for token in tokens or [""]:
        status, text = http_post_json(url, body, token=token, timeout=timeout)
        last = (status, text)
        if status in (401, 403):
            continue  # try next token candidate
        break

    status, text = last
    if status != 200:
        return 2, {
            "error": "relay request failed",
            "http_status": status,
            "detail": text[:300],
            "relay_via": f"{peer_ip}:{portal_port}",
        }
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        return 2, {"error": "relay returned non-JSON", "detail": text[:300]}
    if not isinstance(result, dict):
        return 2, {"error": "relay returned unexpected JSON shape", "detail": text[:300]}
    result["relay_via"] = f"{peer_ip}:{portal_port}"
    return (0 if result.get("reachable") else 1), result


def _pt_persisted_token() -> str:
    for var in ("PERPETUA_TOOLS_ROOT", "PERPETUATOOLSROOT", "PERPETUA_TOOLS_PATH", "PT_HOME"):
        root = os.environ.get(var, "").strip()
        if not root:
            continue
        token_path = Path(root) / ".state" / "control_plane_token"
        if token_path.is_file():
            return token_path.read_text(encoding="utf-8").strip()
    return ""


def pt_lane_token_candidates() -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in (
        os.environ.get("PT_CONTROL_PLANE_TOKEN", "").strip(),
        _pt_persisted_token(),
    ):
        if raw and raw not in seen:
            seen.add(raw)
            ordered.append(raw)
    return ordered


def orama_lane_token_candidates() -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in (
        os.environ.get("ORAMA_CONTROL_PLANE_TOKEN", "").strip(),
        os.environ.get("ORAMA_CONTROL_PLANE_TOKEN_LOCAL", "").strip(),
    ):
        if raw and raw not in seen:
            seen.add(raw)
            ordered.append(raw)
    return ordered


def control_plane_auth_mode() -> str:
    pt = pt_lane_token_candidates()
    orama = orama_lane_token_candidates()
    if pt and orama:
        return "joint"
    if pt:
        return "pt_only"
    if orama:
        return "orama_only"
    return "unset"


def _merge_unique(*groups: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for raw in group:
            if raw and raw not in seen:
                seen.add(raw)
                ordered.append(raw)
    return ordered


def collect_control_plane_token_candidates() -> list[str]:
    peer = os.environ.get("ORAMA_CONTROL_PLANE_TOKEN_PEER", "").strip()
    extra = [peer] if peer else []
    mode = control_plane_auth_mode()
    if mode == "joint":
        return _merge_unique(pt_lane_token_candidates(), orama_lane_token_candidates(), extra)
    if mode == "pt_only":
        return _merge_unique(pt_lane_token_candidates(), extra)
    if mode == "orama_only":
        return _merge_unique(orama_lane_token_candidates(), extra)
    return _merge_unique(extra)


def outbound_control_plane_tokens() -> list[str]:
    peer = os.environ.get("ORAMA_CONTROL_PLANE_TOKEN_PEER", "").strip()
    ordered: list[str] = []
    seen: set[str] = set()
    if peer:
        ordered.append(peer)
        seen.add(peer)
    for raw in _merge_unique(orama_lane_token_candidates(), pt_lane_token_candidates()):
        if raw not in seen:
            seen.add(raw)
            ordered.append(raw)
    return ordered


def resolve_control_plane_token() -> str:
    """Primary outbound token (PEER if set, else first lane candidate)."""
    tokens = outbound_control_plane_tokens()
    return tokens[0] if tokens else ""


def check_ws_peer(peer_ip: str, portal_port: int, tokens: list[str], *, timeout: int = 10) -> Check:
    if not peer_ip:
        return Check("ws-peer", Status.SKIP, "no peer IP")
    if not tokens:
        return Check("ws-peer", Status.SKIP, "no control-plane token candidates")
    last_detail = ""
    for idx, token in enumerate(tokens):
        try:
            import asyncio

            async def _probe(tok: str) -> str:
                try:
                    import websockets
                except ImportError as imp_exc:
                    raise ImportError(
                        "missing websockets — pip install websockets or restart after requirements.txt update"
                    ) from imp_exc

                headers = {"Authorization": f"Bearer {tok}"} if tok else None
                qs = f"?token={quote(tok, safe='')}" if tok else ""
                # SECURITY: Bearer tokens are never sent over unencrypted ws://.
                # RFC 6750 §5.3 mandates TLS for all bearer token transmissions.
                # When a token is present, require wss:// (fail-closed).
                scheme = "wss" if tok else "ws"
                url = f"{scheme}://{peer_ip}:{portal_port}/ws/portal-peer{qs}"
                async with websockets.connect(
                    url,
                    open_timeout=timeout,
                    additional_headers=headers,
                ) as ws:
                    await ws.send(json.dumps({"type": "probe", "source": local_role()}))
                    raw = await asyncio.wait_for(ws.recv(), timeout=max(1, min(timeout, 5)))
                    return raw[:200]

            detail = asyncio.run(_probe(token))
            last_detail = detail
            if "probe-ack" in detail or '"ok"' in detail:
                label = (
                    "peer token"
                    if idx == 0 and os.environ.get("ORAMA_CONTROL_PLANE_TOKEN_PEER")
                    else f"candidate {idx + 1}"
                )
                return Check("ws-peer", Status.PASS, f"{label}: {detail[:100]}")
        except Exception as exc:
            msg = str(exc)
            last_detail = msg[:80]
            if "404" in msg or "HTTP 404" in msg:
                return Check(
                    "ws-peer",
                    Status.SKIP,
                    "peer has no /ws/portal-peer yet — pull orama >= 85ec1df and restart portal",
                )
            if "401" in msg:
                continue
            continue
    if "404" in last_detail or "HTTP 404" in last_detail:
        return Check(
            "ws-peer",
            Status.SKIP,
            "peer has no /ws/portal-peer yet — pull orama >= 85ec1df and restart portal",
        )
    return Check("ws-peer", Status.FAIL, f"tried {len(tokens)} token(s) — {last_detail}")


def run_checks(
    peer_ip: str,
    lms_port: int,
    portal_port: int,
    tokens: list[str],
    *,
    timeout: int = 8,
    status_timeout: int = 30,
    ws_timeout: int = 10,
) -> list[Check]:
    if not peer_ip:
        return [Check("peer-ip", Status.FAIL, "no peer IP in discovery or env")]

    checks: list[Check] = []
    health_url = f"http://{peer_ip}:{portal_port}/health"
    code, body = http_get(health_url, timeout=timeout)
    if code == 200 and "ok" in body.lower():
        checks.append(Check("portal-health", Status.PASS, health_url))
    else:
        hint = "set PORTAL_BIND_LAN=1 on peer and restart portal" if code == -1 else f"http {code}"
        checks.append(Check("portal-health", Status.FAIL, f"{health_url} — {hint}: {body[:80]}"))

    if tokens:
        status_url = f"http://{peer_ip}:{portal_port}/api/status"
        status_pass = False
        last_code = -1
        last_body = ""
        for idx, token in enumerate(tokens):
            last_code, last_body = http_get(status_url, token=token, timeout=status_timeout)
            if last_code == 200:
                label = (
                    "peer token"
                    if idx == 0 and os.environ.get("ORAMA_CONTROL_PLANE_TOKEN_PEER")
                    else f"candidate {idx + 1}"
                )
                checks.append(Check("portal-status", Status.PASS, f"authenticated /api/status ({label})"))
                status_pass = True
                break
        if not status_pass:
            if last_code == -1 and "timed out" in last_body.lower():
                checks.append(
                    Check(
                        "portal-status",
                        Status.FAIL,
                        f"timeout (>{status_timeout}s) — peer portal slow: {last_body[:60]}",
                    )
                )
            else:
                checks.append(
                    Check(
                        "portal-status",
                        Status.FAIL,
                        f"http {last_code} — tried {len(tokens)} token(s); set ORAMA_CONTROL_PLANE_TOKEN_PEER",
                    )
                )
    else:
        checks.append(Check("portal-status", Status.SKIP, "no control-plane token candidates (env or PT .state)"))

    models_url = f"http://{peer_ip}:{lms_port}/v1/models"
    code, body = http_get(models_url, timeout=timeout)
    if code == 200:
        try:
            count = len(json.loads(body).get("data", []))
            checks.append(Check("peer-lmstudio", Status.PASS, f"{count} models at {models_url}"))
        except json.JSONDecodeError:
            checks.append(Check("peer-lmstudio", Status.PASS, models_url))
    else:
        checks.append(Check("peer-lmstudio", Status.FAIL, f"{models_url} — http {code}"))

    checks.append(check_ws_peer(peer_ip, portal_port, tokens, timeout=ws_timeout))

    return checks


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Probe LAN peer orama install")
    p.add_argument("--peer-ip", help="Override peer IP (default: last_discovery.json)")
    p.add_argument("--portal-port", type=int, default=int(os.environ.get("PORTAL_PORT", "8002")))
    p.add_argument("--lms-port", type=int, help="LM Studio port (default: discovery win/mac port)")
    p.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("LAN_PEER_PROBE_TIMEOUT", "8")),
        help="HTTP timeout in seconds for health and model probes",
    )
    p.add_argument(
        "--status-timeout",
        type=int,
        default=int(os.environ.get("LAN_PEER_STATUS_TIMEOUT", "30")),
        help="HTTP timeout in seconds for authenticated /api/status",
    )
    p.add_argument(
        "--ws-timeout",
        type=int,
        default=int(os.environ.get("LAN_PEER_WS_TIMEOUT", "10")),
        help="WebSocket open timeout in seconds",
    )
    p.add_argument("--json", dest="json_out", action="store_true")
    p.add_argument(
        "--relay",
        metavar="TARGET_IP[:PORT]",
        help=(
            "Gossip relay: ask the (reachable) peer to probe TARGET on our "
            "behalf via POST /api/peer-relay-probe, instead of running the "
            "local check suite. Exit 0 target reachable, 1 not reachable, "
            "2 relay failed. Port defaults to --portal-port."
        ),
    )
    args = p.parse_args(argv)

    role = local_role()
    discovery = load_discovery()
    peer_ip, lms_port = peer_from_discovery(discovery, role)
    if args.peer_ip:
        peer_ip = args.peer_ip.strip()
    if args.lms_port:
        lms_port = args.lms_port

    if args.relay:
        code, result = relay_probe(
            peer_ip,
            args.portal_port,
            args.relay,
            args.portal_port,
            outbound_control_plane_tokens(),
            timeout=args.timeout,
        )
        if args.json_out:
            print(json.dumps(result, indent=2))
        elif code == 2:
            print(f"RELAY FAIL via {result.get('relay_via', peer_ip)}: "
                  f"{result.get('error', '?')} — {result.get('detail', '')}",
                  file=sys.stderr)
        else:
            verdict = "UP" if code == 0 else "DOWN"
            print(f"relay via {result.get('relay_via')}: target "
                  f"{result.get('ip')} is {verdict} "
                  f"(models: {', '.join(result.get('models', [])) or '-'}; "
                  f"path: {'→'.join(result.get('relay_path', [])) or '-'})")
        return code

    tokens = outbound_control_plane_tokens()
    checks = run_checks(
        peer_ip,
        lms_port,
        args.portal_port,
        tokens,
        timeout=args.timeout,
        status_timeout=args.status_timeout,
        ws_timeout=args.ws_timeout,
    )

    payload = {
        "status": "pending",
        "local_role": role,
        "peer_ip": peer_ip,
        "auth_mode": control_plane_auth_mode(),
        "discovery_path": str(discovery_path()),
        "checks": [asdict(c) for c in checks],
    }

    failed = [c for c in checks if c.status == Status.FAIL]
    if failed:
        payload["status"] = "fail"
        if args.json_out:
            print(json.dumps(payload, indent=2))
        else:
            for c in checks:
                print(f"  {c.name:16} {c.status.value:6} {c.detail}")
            print("FAIL — peer probe had failures", file=sys.stderr)
        return 1

    payload["status"] = "success"
    payload["probed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result_path = write_probe_result(payload)
    payload["result_path"] = str(result_path)

    if args.json_out:
        print(json.dumps(payload, indent=2))
    else:
        for c in checks:
            print(f"  {c.name:16} {c.status.value:6} {c.detail}")
        print(f"SUCCESS — peer probe passed; wrote {result_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
