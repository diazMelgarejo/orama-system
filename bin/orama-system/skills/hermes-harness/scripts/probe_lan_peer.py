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
from enum import Enum
from pathlib import Path
from typing import Any


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


def run_checks(peer_ip: str, lms_port: int, portal_port: int, token: str) -> list[Check]:
    if not peer_ip:
        return [Check("peer-ip", Status.FAIL, "no peer IP in discovery or env")]

    checks: list[Check] = []
    health_url = f"http://{peer_ip}:{portal_port}/health"
    code, body = http_get(health_url)
    if code == 200 and "ok" in body.lower():
        checks.append(Check("portal-health", Status.PASS, health_url))
    else:
        hint = "set PORTAL_BIND_LAN=1 on peer and restart portal" if code == -1 else f"http {code}"
        checks.append(Check("portal-health", Status.FAIL, f"{health_url} — {hint}: {body[:80]}"))

    if token:
        status_url = f"http://{peer_ip}:{portal_port}/api/status"
        code, body = http_get(status_url, token=token)
        if code == 200:
            checks.append(Check("portal-status", Status.PASS, "authenticated /api/status"))
        else:
            checks.append(Check("portal-status", Status.FAIL, f"http {code} — check ORAMA_CONTROL_PLANE_TOKEN"))
    else:
        checks.append(Check("portal-status", Status.SKIP, "no ORAMA_CONTROL_PLANE_TOKEN in env"))

    models_url = f"http://{peer_ip}:{lms_port}/v1/models"
    code, body = http_get(models_url)
    if code == 200:
        try:
            count = len(json.loads(body).get("data", []))
            checks.append(Check("peer-lmstudio", Status.PASS, f"{count} models at {models_url}"))
        except json.JSONDecodeError:
            checks.append(Check("peer-lmstudio", Status.PASS, models_url))
    else:
        checks.append(Check("peer-lmstudio", Status.FAIL, f"{models_url} — http {code}"))

    return checks


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Probe LAN peer orama install")
    p.add_argument("--peer-ip", help="Override peer IP (default: last_discovery.json)")
    p.add_argument("--portal-port", type=int, default=int(os.environ.get("PORTAL_PORT", "8002")))
    p.add_argument("--lms-port", type=int, help="LM Studio port (default: discovery win/mac port)")
    p.add_argument("--json", dest="json_out", action="store_true")
    args = p.parse_args(argv)

    role = local_role()
    discovery = load_discovery()
    peer_ip, lms_port = peer_from_discovery(discovery, role)
    if args.peer_ip:
        peer_ip = args.peer_ip.strip()
    if args.lms_port:
        lms_port = args.lms_port

    token = os.environ.get("ORAMA_CONTROL_PLANE_TOKEN", "").strip()
    checks = run_checks(peer_ip, lms_port, args.portal_port, token)

    payload = {
        "local_role": role,
        "peer_ip": peer_ip,
        "discovery_path": str(discovery_path()),
        "checks": [asdict(c) for c in checks],
    }

    if args.json_out:
        print(json.dumps(payload, indent=2))
    else:
        for c in checks:
            print(f"  {c.name:16} {c.status.value:6} {c.detail}")

    failed = [c for c in checks if c.status == Status.FAIL]
    if failed:
        if not args.json_out:
            print("FAIL — peer probe had failures", file=sys.stderr)
        return 1
    if not args.json_out:
        print("OK — peer probe passed (or skipped optional checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
