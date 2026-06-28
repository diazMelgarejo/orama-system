#!/usr/bin/env python3
"""
utils/ip_resolver.py — Authoritative LAN IP resolver for orama-system.
"""
from __future__ import annotations

import functools
import json
import logging
import os
import socket
import time
import urllib.request
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

log = logging.getLogger("orama.ip_resolver")

OPENCLAW_JSON       = Path.home() / ".openclaw" / "openclaw.json"
DISCOVERY_JSON      = Path.home() / ".openclaw" / "state" / "discovery.json"
LMS_PORT            = 1234
OLLAMA_PORT         = 11434
ALPHACLAW_GATEWAY   = "http://localhost:18789"
_FALLBACK_WIN_IP    = "192.168.254.103"

# NOTE: change type behavior: PT tilting now returns full URL (scheme preserved)


def _extract_ip_from_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if host in ("localhost", "127.0.0.1", "::1"):
        return ""
    return host


def _from_pt_tilting() -> str:
    import sys as _sys
    _inserted = False
    pt_str = ""
    try:
        _orama_root = Path(__file__).resolve().parents[2]
        _pt_candidates = [
            _orama_root.parent / "perplexity-api" / "Perpetua-Tools",
            Path.home() / "Perpetua-Tools",
        ]
        pt_root = next((p for p in _pt_candidates if p.exists()), None)
        if not pt_root:
            return ""
        pt_str = str(pt_root)
        if pt_str not in _sys.path:
            _sys.path.insert(0, pt_str)
            _inserted = True
        from orchestrator.lan_discovery import detect_active_tilting_ip
        raw = detect_active_tilting_ip()  # now MAY return full URL with scheme
        if not raw:
            return ""

        # Preserve scheme if present
        parsed = urlparse(raw)
        if parsed.scheme and parsed.hostname:
            ip = parsed.hostname
            scheme = parsed.scheme
            result = f"{scheme}://{ip}"
        else:
            ip = _extract_ip_from_url(raw)
            result = ip

        if ip:
            log.debug("ip_resolver P4 (pt-tilting): %s", ip)
        return result

    except Exception:
        return ""
    finally:
        if _inserted and pt_str in _sys.path:
            _sys.path.remove(pt_str)


def get_win_lms_url(port: int = LMS_PORT) -> str:
    val = get_win_ip()
    parsed = urlparse(val)
    if parsed.scheme and parsed.hostname:
        return f"{parsed.scheme}://{parsed.hostname}:{port}"
    return f"http://{val}:{port}"


def get_win_ollama_url(port: int = OLLAMA_PORT) -> str:
    val = get_win_ip()
    parsed = urlparse(val)
    if parsed.scheme and parsed.hostname:
        return f"{parsed.scheme}://{parsed.hostname}:{port}"
    return f"http://{val}:{port}"

# NOTE: rest of file unchanged (truncated for patch safety)
