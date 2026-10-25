#!/usr/bin/env python3
"""
scripts/discover.py
LM Studio Auto-Discovery Hub — Layer A.
Always probes by default (no TTL skip). Pass --cached to reuse warm gossip.
Idempotent: writes nothing if state hash is unchanged.
"""

from __future__ import annotations
import argparse, asyncio, hashlib, ipaddress, json, logging, os, re, shutil, socket, sys, time
import urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import fcntl  # type: ignore
except ImportError:
    fcntl = None  # type: ignore[assignment]
    import msvcrt  # type: ignore
else:
    msvcrt = None  # type: ignore[assignment]

# ── Paths ─────────────────────────────────────────────────────────────────────
OPENCLAW_DIR        = Path.home() / ".openclaw"
STATE_DIR           = OPENCLAW_DIR / "state"
BACKUPS_DIR         = STATE_DIR / "backups"
ARCHIVE_DIR         = STATE_DIR / "archive"
PROFILES_DIR        = OPENCLAW_DIR / "profiles"
DISCOVERY_JSON      = STATE_DIR / "discovery.json"
LAST_DISCOVERY_JSON = STATE_DIR / "last_discovery.json"
RECOVERY_SOURCE_TXT = STATE_DIR / "recovery_source.txt"
LOCK_FILE           = STATE_DIR / ".discover.lock"
DEFAULT_LOCK_FILE   = LOCK_FILE
OPENCLAW_JSON       = OPENCLAW_DIR / "openclaw.json"

LM_STUDIO_PORT     = 1234
OLLAMA_PORT        = 11434
SUBNET             = "192.168.254"
PROBE_TIMEOUT      = 0.2
MODEL_API_TIMEOUT  = 4
MAX_BACKUPS        = 30
ARCHIVE_DAYS       = 30
GOSSIP_TTL_SECONDS = 300

# Platform role: on Windows, localhost IS the Win box and the Mac is remote.
# On Mac/Linux, localhost IS the Mac box and Windows is on the LAN.
RUNNING_ON_WINDOWS = sys.platform == "win32"

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
from mesh.discovery_trust import ack_peer, filter_endpoints_for_trust  # noqa: E402

_SRC_DIR = _SCRIPTS_DIR.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
from utils.model_endpoint_url import ModelEndpointPolicyError, validate_model_endpoint_url  # noqa: E402

# ── Repo discovery ────────────────────────────────────────────────────────────

def _resolve_perpetua_root_env() -> Path | None:
    """Resolve canonical Perpetua root env var with legacy fallback.

    Precedence:
      1) PERPETUA_TOOLS_ROOT (canonical)
      2) PERPETUA_TOOLS_PATH (legacy compatibility)
    """
    root = (
        os.getenv("PERPETUATOOLSROOT", "").strip()
        or os.getenv("PERPETUA_TOOLS_ROOT", "").strip()
    )
    legacy = os.getenv("PERPETUA_TOOLS_PATH", "").strip()
    selected = root or legacy
    return Path(selected).expanduser() if selected else None


def get_repo_paths() -> dict:
    """Get repo paths."""
    base = Path.home() / "Documents" / "Terminal xCode" / "claude" / "OpenClaw"
    candidates = {
        "alphaclaw": [Path(os.getenv("ALPHACLAW_INSTALL_DIR", "~/.alphaclaw")).expanduser()],
        "perpetua_tools": [
            base / "perplexity-api" / "Perpetua-Tools",
            Path.home() / "Perpetua-Tools",
        ],
        "orama_system": [
            base / "orama-system",
            Path.home() / "orama-system",
        ],
    }
    result = {}
    for name, paths in candidates.items():
        env_key = name.upper() + "_PATH"
        if name == "perpetua_tools":
            result[name] = _resolve_perpetua_root_env() or next((p for p in paths if p.exists()), None)
        elif env_val := os.getenv(env_key):
            result[name] = Path(env_val).expanduser()
        else:
            result[name] = next((p for p in paths if p.exists()), None)
    return result

# ── Hardware affinity policy ──────────────────────────────────────────────────

def _simple_policy_parse(text: str) -> dict[str, list[str]]:
    """Simple policy parse."""
    parsed: dict[str, list[str]] = {
        "windows_only": [],
        "mac_only": [],
        "shared": [],
        "windows_only_aliases": [],
        "mac_only_aliases": [],
        "shared_aliases": [],
    }
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.endswith(":") and not stripped.startswith("-"):
            key = stripped[:-1]
            current = key if key in parsed else None
            continue
        if current and stripped.startswith("-"):
            value = stripped[1:].strip().strip('"').strip("'")
            if value:
                parsed[current].append(value)
    return parsed


def _normalize_policy(loaded: dict[str, Any]) -> dict[str, list[str]]:
    """Merge *_aliases sections so quant-suffixed LM Studio ids enforce NEVER_MAC."""
    windows_only = list(loaded.get("windows_only", []) or [])
    windows_only.extend(loaded.get("windows_only_aliases", []) or [])
    mac_only = list(loaded.get("mac_only", []) or [])
    mac_only.extend(loaded.get("mac_only_aliases", []) or [])
    shared = list(loaded.get("shared", []) or [])
    shared.extend(loaded.get("shared_aliases", []) or [])
    return {
        "windows_only": windows_only,
        "mac_only": mac_only,
        "shared": shared,
    }


def load_policy(policy_path: Path | None = None) -> dict[str, Any]:
    """Load Perpetua-Tools' canonical hardware policy (alias-normalized)."""
    if policy_path is None:
        pt_root = _resolve_perpetua_root_env() or get_repo_paths().get("perpetua_tools")
        if not pt_root:
            return {"windows_only": [], "mac_only": [], "shared": []}
        policy_path = Path(pt_root) / "config" / "model_hardware_policy.yml"
    if not policy_path.exists():
        return {"windows_only": [], "mac_only": [], "shared": []}
    try:
        with open(str(policy_path), "r", encoding="utf-8") as _fh:
            text = _fh.read()
    except OSError as exc:
        logging.warning("load_hardware_policy: cannot read %s: %s", policy_path, exc)
        return {"windows_only": [], "mac_only": [], "shared": []}
    try:
        import yaml  # type: ignore
        loaded = yaml.safe_load(text) or {}
    except Exception:
        loaded = _simple_policy_parse(text)
    return _normalize_policy(loaded)

def _import_pt_hardware_policy():
    """Import pt hardware policy."""
    pt_root = _resolve_perpetua_root_env()
    if not pt_root:
        raise ImportError("PERPETUATOOLSROOT/PERPETUA_TOOLS_ROOT not set")
    # Load by file path under a private name. orama has its own src/utils
    # package (already first on sys.path), so `import utils.hardware_policy`
    # would resolve to orama's, not Perpetua-Tools'.
    hp_path = Path(pt_root) / "src" / "utils" / "hardware_policy.py"
    if not hp_path.is_file():
        raise ImportError(f"PT hardware_policy not found at {hp_path}")
    import importlib.util
    spec = importlib.util.spec_from_file_location("_pt_hardware_policy", str(hp_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot build import spec for {hp_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_pt_hardware_policy"] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop("_pt_hardware_policy", None)
        raise
    return module


def _filter_models_for_platform_local(models: list, platform: str, policy: dict) -> list:
    """Filter models for platform local."""
    normalized = platform.lower().strip()
    if normalized == "mac":
        forbidden = {m.lower() for m in policy.get("windows_only", [])}
    elif normalized == "win":
        forbidden = {m.lower() for m in policy.get("mac_only", [])}
    else:
        forbidden = set()
    return [m for m in models if str(m).lower() not in forbidden]


try:
    _hw_policy = _import_pt_hardware_policy()
    filter_models_for_platform = _hw_policy.filter_models_for_platform
except Exception as exc:
    # OSError [Errno 11] "Resource deadlock avoided" can occur in launchd context
    # on macOS when sys.path contains directories with spaces (known VFS quirk).
    # Fall back gracefully — discover.py runs fine without the PT policy module.
    logging.warning(
        "Cannot import PT hardware_policy (%s: %s). Falling back to local filter.",
        type(exc).__name__, exc,
    )
    filter_models_for_platform = _filter_models_for_platform_local

def filter_endpoints_for_policy(endpoints: dict, policy: dict | None = None) -> dict:
    """Return a copy of endpoint discovery data with platform-forbidden models removed."""
    policy = policy if policy is not None else load_policy()
    filtered: dict[str, dict | None] = {}
    for platform in ("mac", "win"):
        endpoint = endpoints.get(platform)
        if not endpoint:
            filtered[platform] = endpoint
            continue
        copied = dict(endpoint)
        copied["models"] = filter_models_for_platform(endpoint.get("models", []), platform, policy)
        filtered[platform] = copied
    filtered["win_peers"] = [
        {**peer, "models": filter_models_for_platform(peer.get("models", []), "win", policy)}
        for peer in endpoints.get("win_peers", [])
    ]
    return filtered

# ── Probing ───────────────────────────────────────────────────────────────────

def probe_models(base_url: str, timeout: float = MODEL_API_TIMEOUT):
    """Probe models."""
    try:
        safe_url = validate_model_endpoint_url(base_url)
    except ModelEndpointPolicyError as exc:
        logging.warning("refusing to probe endpoint rejected by policy: %s", exc)
        return None
    try:
        req = urllib.request.Request(
            f"{safe_url}/v1/models",
            headers={"Authorization": "Bearer lm-studio"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
            models = sorted(m["id"] for m in data.get("data", []))
            return models or None
    except Exception:
        return None

async def _check_port(ip: str, port: int):
    """Check port."""
    try:
        _, w = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=PROBE_TIMEOUT)
        w.close(); await w.wait_closed()
        return ip
    except Exception:
        return None

async def scan_subnet_async(subnet: str, port: int, exclude: set):
    """Scan subnet async."""
    tasks = [_check_port(f"{subnet}.{i}", port) for i in range(1, 255)
             if f"{subnet}.{i}" not in exclude]
    return [ip for ip in await asyncio.gather(*tasks) if ip]

def get_local_subnets() -> list[str]:
    """Get local subnets."""
    subnets = []
    try:
        import netifaces
        for iface in netifaces.interfaces():
            if iface.startswith(('lo', 'Loopback')):
                continue
            addrs = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr.get('addr')
                    netmask = addr.get('netmask')
                    if ip and netmask and not ip.startswith('127.'):
                        ip_parts = [int(x) for x in ip.split('.')]
                        mask_parts = [int(x) for x in netmask.split('.')]
                        net_parts = [ip_parts[i] & mask_parts[i] for i in range(4)]
                        wildcards = 256 - mask_parts[2] if mask_parts[2] < 255 else 1
                        base_octet2 = net_parts[2]
                        for j in range(wildcards):
                            subnets.append(f"{net_parts[0]}.{net_parts[1]}.{base_octet2 + j}")
    except Exception:
        pass
    return list(set(subnets))

def _lan_ip_on_subnet(subnet_prefix: str | None = None) -> str | None:
    """Return this host's LAN IP on the given subnet via UDP route probe."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            s.connect(("192.168.254.1", 80))
            ip = s.getsockname()[0]
        s.close()
        if subnet_prefix:
            return ip if ip.startswith(subnet_prefix) else None
        return ip
    except Exception:
        return None


def _mac_lan_ip():
    """Mac lan ip."""
    return _lan_ip_on_subnet()


def _win_lan_ip():
    """Win lan ip."""
    return _lan_ip_on_subnet()


def _win_lan_patch_ip(win_ip: str) -> str:
    """LAN IP for shared PT config files — never loopback on Windows host."""
    if RUNNING_ON_WINDOWS and win_ip in ("localhost", "127.0.0.1"):
        return os.getenv("WIN_IP") or _win_lan_ip() or win_ip
    return win_ip


def _endpoints_for_hash(endpoints: dict) -> dict:
    """Hash/snapshot view: resolve Windows localhost to LAN IP for stable comparisons."""
    win = endpoints.get("win") or {}
    if not win:
        return endpoints
    patch_ip = _win_lan_patch_ip(win.get("ip", ""))
    if patch_ip == win.get("ip", ""):
        return endpoints
    return {**endpoints, "win": {**win, "ip": patch_ip}}

# ── Windows-host peer identification (F12) ────────────────────────────────────

_MAC_MODEL_DEFAULTS = ("bge-m3", "qwen3.5:9b-nvfp4")
_MLX_MARKERS = ("-mlx", "mlx-community/")


def _is_loopback_host(host: str) -> bool:
    """True for localhost and any loopback IP literal."""
    host = (host or "").strip().lower()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _local_ipv4s() -> set[str]:
    """This host's non-loopback IPv4 addresses (best effort, never raises)."""
    ips: set[str] = set()
    try:
        host = socket.gethostname()
        for info in socket.getaddrinfo(host, None, socket.AF_INET):
            ips.add(info[4][0])
        ips.update(socket.gethostbyname_ex(host)[2])
    except Exception:
        pass
    try:
        import netifaces  # type: ignore
        for iface in netifaces.interfaces():
            for addr in netifaces.ifaddresses(iface).get(netifaces.AF_INET, []):
                if addr.get("addr"):
                    ips.add(addr["addr"])
    except Exception:
        pass
    try:
        lan = _win_lan_ip()
        if lan:
            ips.add(lan)
    except Exception:
        pass
    return {ip for ip in ips if ip and not _is_loopback_host(ip)}


def _env_ip_list(key: str) -> list[str]:
    """Env ip list."""
    return [p.strip() for p in os.getenv(key, "").split(",") if p.strip()]


def _known_windows_ips() -> set[str]:
    """Addresses that are Windows boxes: this host plus the configured peers."""
    known = {"localhost"} | set(_local_ipv4s())
    known.update(_env_ip_list("WIN_PEER_IPS"))
    for key in ("WIN_3080_IP", "WIN_5080_IP"):
        known.update(_env_ip_list(key))
    return known


def _policy_model_sets() -> tuple[set[str], set[str]]:
    """(mac_only, windows_only) model names; static Mac defaults always apply."""
    try:
        pol = load_policy()
    except Exception:
        pol = {}
    mac = {str(m).lower() for m in (pol.get("mac_only") or [])} | set(_MAC_MODEL_DEFAULTS)
    win = {str(m).lower() for m in (pol.get("windows_only") or [])}
    return mac, win


def _model_matches(model: str, policy_name: str) -> bool:
    """Tag-insensitive match: 'bge-m3' matches 'bge-m3:latest'."""
    m, p = model.lower(), policy_name.lower()
    if m == p:
        return True
    if ":" not in p or p.endswith(":latest"):
        return m.split(":", 1)[0] == p.split(":", 1)[0]
    return False


def _has_mac_evidence(models: list, mac_only: set[str]) -> bool:
    """Has mac evidence."""
    for raw in models or []:
        name = str(raw).lower()
        if any(mk in name for mk in _MLX_MARKERS) or re.search(r"-\d+bit", name):
            return True
        if any(_model_matches(name, p) for p in mac_only):
            return True
    return False


def _has_win_evidence(models: list, win_only: set[str]) -> bool:
    """Has win evidence."""
    for raw in models or []:
        name = str(raw).lower()
        if "gguf" in name or any(_model_matches(name, p) for p in win_only):
            return True
    return False


def _probe_mac_candidate(ip: str, mac_only: set[str], win_only: set[str]) -> dict | None:
    """Probe :1234 (LM Studio) and :11434 (Ollama) on a candidate; classify it."""
    lms = probe_models(f"http://{ip}:{LM_STUDIO_PORT}")
    ollama = probe_models(f"http://{ip}:{OLLAMA_PORT}")
    if not lms and not ollama:
        return None
    combined = list(lms or []) + list(ollama or [])
    return {
        "ip": ip,
        "models": list(lms) if lms else list(ollama),
        "ollama": list(ollama) if ollama else None,
        "mac_evidence": _has_mac_evidence(combined, mac_only),
        "win_evidence": _has_win_evidence(combined, win_only),
    }


def _mac_entry(cand: dict) -> dict:
    """Mac entry."""
    entry = {"ip": cand["ip"], "models": cand["models"]}
    if cand.get("ollama"):
        entry["ollama"] = cand["ollama"]
    return entry


def _drop_windows_mac(endpoints: dict) -> tuple[dict, bool]:
    """Drop a cached/back-filled Mac entry whose IP is a known Windows address."""
    mac = endpoints.get("mac")
    mac_ip = (mac or {}).get("ip", "")
    if mac and (mac_ip in _known_windows_ips() or _is_loopback_host(mac_ip)):
        print(f"  ⚠️  discarding mac {mac_ip}: known Windows address", file=sys.stderr)
        return {**endpoints, "mac": None}, True
    return endpoints, False


def discover_endpoints() -> dict:
    """Probe Mac and Windows LM Studio instances.

    Platform role reversal on Windows:
      When running ON Windows, localhost IS the Windows box and the Mac is remote.
      When running ON Mac/Linux, localhost IS the Mac box and Windows is on the LAN.

    Mac identification strategy (Mac/Linux host, in order):
      1. localhost:1234  — classic single-machine dev setup
      2. mac_lan_ip:1234 — LM Studio bound to all interfaces (common after
         power cycle or when LAN access is needed from other machines)
      3. Seed from last_discovery.json mac.ip — avoids full subnet scan on
         unchanged topologies

    Windows identification (Mac/Linux host):
      Any responding LM Studio on the subnet that is NOT the Mac's own IP.
      Falls back to last-known-good IP, then full subnet scan.

    Windows host (RUNNING_ON_WINDOWS=True):
      localhost:1234  → win  (the local LM Studio GGUF box)
      $MAC_IP:1234    → mac  (the remote Mac MLX box, if reachable)
    """
    result = {"mac": None, "win": None}

    if RUNNING_ON_WINDOWS:
        # ── Windows host: localhost = win, $MAC_IP = mac ────────────────────
        # Every Mac candidate is checked against the known Windows IPs (this
        # host's own addresses, $WIN_PEER_IPS, $WIN_3080_IP, $WIN_5080_IP) and
        # against model evidence, so a second Windows LM Studio on :1234 is never
        # labelled as the Mac.
        win_models = probe_models("http://localhost:1234")
        if win_models:
            result["win"] = {"ip": "localhost", "models": win_models}
        else:
            print("  ⚠️  Windows LM Studio not reachable at localhost:1234", file=sys.stderr)

        win_known = _known_windows_ips()
        policy_mac, policy_win = _policy_model_sets()
        win_extra: list[dict] = []

        def _note_win(cand: dict) -> None:
            """Note win."""
            if cand["ip"] not in {p["ip"] for p in win_extra}:
                win_extra.append({"ip": cand["ip"], "models": cand["models"]})

        mac_ip = os.getenv("MAC_IP", "").strip()
        if mac_ip and (mac_ip in win_known or _is_loopback_host(mac_ip)):
            print(f"  ⚠️  $MAC_IP={mac_ip} is a known Windows address — refusing to use it as the Mac",
                  file=sys.stderr)
            mac_ip = ""
        if mac_ip:
            cand = _probe_mac_candidate(mac_ip, policy_mac, policy_win)
            if cand and not cand["win_evidence"]:
                result["mac"] = _mac_entry(cand)
            elif cand:
                print(f"  ⚠️  $MAC_IP={mac_ip} serves Windows-only models — not labelling it as the Mac",
                      file=sys.stderr)
                _note_win(cand)
            else:
                print(f"  ⚠️  Mac LM Studio not reachable at {mac_ip}:1234 ($MAC_IP) — trying cache", file=sys.stderr)
        if not result["mac"]:
            # Last-known-good mac IP from cache (needs Mac evidence).
            last = _load_json(LAST_DISCOVERY_JSON)
            mac_last_ip = ((last or {}).get("endpoints", {}).get("mac", {}) or {}).get("ip", "")
            if (mac_last_ip and not _is_loopback_host(mac_last_ip)
                    and mac_last_ip not in win_known and mac_last_ip != mac_ip):
                cand = _probe_mac_candidate(mac_last_ip, policy_mac, policy_win)
                if cand and cand["mac_evidence"] and not cand["win_evidence"]:
                    result["mac"] = _mac_entry(cand)
                    hint = " (update $MAC_IP)" if mac_ip else " (set $MAC_IP to avoid scan)"
                    print(f"  ℹ️  Mac found at cached IP {mac_last_ip}{hint}", file=sys.stderr)
                elif cand and cand["win_evidence"]:
                    _note_win(cand)
        if not result["mac"]:
            # Fresh subnet scan — never guess .110; find a remote LM Studio with Mac evidence.
            win_lan = _win_lan_ip() or ""
            exclude = {"localhost"} | win_known
            subnets = get_local_subnets()
            if not subnets:
                subnets = [win_lan.rsplit(".", 1)[0] if win_lan else SUBNET]
            found_mac = False
            for subnet in subnets:
                for ip in asyncio.run(scan_subnet_async(subnet, LM_STUDIO_PORT, exclude)):
                    cand = _probe_mac_candidate(ip, policy_mac, policy_win)
                    if not cand:
                        continue
                    if cand["win_evidence"]:
                        _note_win(cand)
                    elif cand["mac_evidence"]:
                        result["mac"] = _mac_entry(cand)
                        print(f"  ℹ️  Mac LM Studio found at {ip} (subnet scan)", file=sys.stderr)
                        found_mac = True
                        break
                if found_mac:
                    break

        # Additional Windows peers: $WIN_PEER_IPS + $WIN_3080_IP + $WIN_5080_IP
        # minus this host and the primary win; plus scan/MAC_IP hits that
        # carried Windows evidence.
        peer_exclude = {"localhost"} | _local_ipv4s()
        if result["mac"]:
            peer_exclude.add(result["mac"]["ip"])
        peers = probe_extra_win_peers(peer_exclude, include_node_ips=True)
        seen_peer_ips = {p["ip"] for p in peers}
        for extra in win_extra:
            if extra["ip"] not in seen_peer_ips and extra["ip"] not in peer_exclude:
                peers.append(extra)
                seen_peer_ips.add(extra["ip"])
        result["win_peers"] = peers
        return result

    # ── Mac/Linux host: localhost = mac, subnet scan = win ──────────────────
    # Step 1: try localhost first (zero network traffic, instant)
    mac_models = probe_models("http://localhost:1234")
    if mac_models:
        result["mac"] = {"ip": "localhost", "models": mac_models}

    mac_lan = _mac_lan_ip()
    exclude = {"localhost", "127.0.0.1"}
    if mac_lan:
        exclude.add(mac_lan)

    # Step 2: if localhost missed, probe the Mac's own LAN IP
    # (LM Studio often binds to 0.0.0.0 and is reachable via LAN IP)
    if not result["mac"] and mac_lan:
        mac_models_lan = probe_models(f"http://{mac_lan}:1234")
        if mac_models_lan:
            result["mac"] = {"ip": mac_lan, "models": mac_models_lan}
            print(f"  ℹ️  Mac LM Studio found at LAN IP {mac_lan} (not localhost)", file=sys.stderr)

    # Step 3: seed from last discovery for Mac (avoids scan when IP unchanged)
    last = _load_json(LAST_DISCOVERY_JSON)
    if not result["mac"] and last:
        mac_last_ip = (last.get("endpoints", {}).get("mac", {}) or {}).get("ip", "")
        if mac_last_ip and mac_last_ip not in ("", "localhost", "127.0.0.1"):
            mac_models_seed = probe_models(f"http://{mac_last_ip}:1234")
            if mac_models_seed:
                result["mac"] = {"ip": mac_last_ip, "models": mac_models_seed}
                print(f"  ℹ️  Mac LM Studio rediscovered at {mac_last_ip} (seeded from cache)", file=sys.stderr)

    win_last_ip = (last or {}).get("endpoints", {}).get("win", {}).get("ip", "")
    # Mac's LAN IP (or discovered IP) must not be treated as Windows
    if result["mac"] and result["mac"]["ip"] not in ("localhost", "127.0.0.1"):
        exclude.add(result["mac"]["ip"])

    if win_last_ip and win_last_ip not in exclude:
        win_models = probe_models(f"http://{win_last_ip}:1234")
        if win_models:
            result["win"] = {"ip": win_last_ip, "models": win_models}

    if not result["win"]:
        subnets = get_local_subnets()
        if not subnets:
            subnets = [mac_lan.rsplit(".", 1)[0] if mac_lan else SUBNET]
        found_win = False
        for subnet in subnets:
            for ip in asyncio.run(scan_subnet_async(subnet, LM_STUDIO_PORT, exclude)):
                models = probe_models(f"http://{ip}:1234")
                if models:
                    result["win"] = {"ip": ip, "models": models}
                    found_win = True
                    break
            if found_win:
                break

    # Additional Windows GPU peers beyond the single primary `win` slot
    # (e.g. a second RTX box on the LAN). MVP, additive-only: never hardcode
    # — set $WIN_PEER_IPS to a comma-separated list. `win` above stays the
    # sole source of truth for every existing single-peer consumer
    # (lm_link_watch.py, lm_link_status.py); win_peers is new and optional.
    win_exclude = set(exclude)
    if result.get("win"):
        win_exclude.add(result["win"]["ip"])
    result["win_peers"] = probe_extra_win_peers(win_exclude)

    return result


def probe_extra_win_peers(exclude: set[str], include_node_ips: bool = False) -> list[dict]:
    """Probe additional Windows LM Studio peers named in $WIN_PEER_IPS.

    MVP for tracking more than one Windows GPU box (e.g. RTX 3080 + RTX
    5080) without changing the single-peer `endpoints.win` schema that
    lm_link_watch.py / lm_link_status.py already depend on. Comma-separated
    env var only — no subnet scan, no persistence beyond what
    save_discovery_state() already does for the returned list.
    """
    candidates = _env_ip_list("WIN_PEER_IPS")
    if include_node_ips:
        # Windows host: sibling GPU nodes configured by the launcher.
        for key in ("WIN_3080_IP", "WIN_5080_IP"):
            candidates.extend(_env_ip_list(key))
    if not candidates:
        return []
    peers: list[dict] = []
    seen: set[str] = set()
    for ip in candidates:
        if not ip or ip in exclude or ip in seen:
            continue
        seen.add(ip)
        models = probe_models(f"http://{ip}:1234")
        if models:
            peers.append({"ip": ip, "models": models})
        else:
            print(f"  ⚠️  Windows peer {ip} (from $WIN_PEER_IPS) not reachable", file=sys.stderr)
    return peers

# ── Hash & state ──────────────────────────────────────────────────────────────

def compute_hash(endpoints: dict) -> str:
    """Compute hash."""
    mac = endpoints.get("mac") or {}
    win = endpoints.get("win") or {}
    win_peers = sorted(
        (p.get("ip", ""), tuple(sorted(p.get("models", [])))) for p in endpoints.get("win_peers", [])
    )
    key = json.dumps({
        "mac_ip": mac.get("ip", ""),
        "mac_models": sorted(mac.get("models", [])),
        "win_ip": win.get("ip", ""),
        "win_models": sorted(win.get("models", [])),
        "win_peers": win_peers,
    }, sort_keys=True)
    return hashlib.sha1(key.encode()).hexdigest()

def _load_json(path: Path):
    """Load json."""
    try:
        with open(str(path), "r", encoding="utf-8") as fh:
            return json.loads(fh.read())
    except Exception:
        return None

def _lock_path() -> Path:
    """Lock path."""
    if LOCK_FILE != DEFAULT_LOCK_FILE:
        return LOCK_FILE
    return STATE_DIR / ".discover.lock"

def save_discovery_state(endpoints: dict, tier: int = 1):
    """Save discovery state."""
    endpoints = filter_endpoints_for_policy(endpoints)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    mac = endpoints.get("mac") or {}
    win = endpoints.get("win") or {}
    state = {
        "schema": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hash": compute_hash(endpoints),
        "recovery_tier": tier,
        "endpoints": {
            "mac": {"ip": mac.get("ip", ""), "port": LM_STUDIO_PORT, "reachable": bool(mac)},
            "win": {"ip": win.get("ip", ""), "port": LM_STUDIO_PORT, "reachable": bool(win)},
            # MVP additive field for a fleet of Windows GPU boxes beyond the
            # single `win` slot (see probe_extra_win_peers). Empty list when
            # $WIN_PEER_IPS is unset — existing single-peer readers are
            # untouched since they only ever read `endpoints.win`.
            "win_peers": [
                {"ip": p.get("ip", ""), "port": LM_STUDIO_PORT, "reachable": True}
                for p in endpoints.get("win_peers", [])
            ],
        },
        "models": {
            "mac": mac.get("models", []),
            "win": win.get("models", []),
            "win_peers": {p.get("ip", ""): p.get("models", []) for p in endpoints.get("win_peers", [])},
        },
    }
    DISCOVERY_JSON.write_text(json.dumps(state, indent=2))
    LAST_DISCOVERY_JSON.write_text(json.dumps(state, indent=2))
    RECOVERY_SOURCE_TXT.write_text(f"tier{tier}\n")

# ── Backup / archive ──────────────────────────────────────────────────────────

def backup_current_state():
    """Backup current state."""
    if not LAST_DISCOVERY_JSON.exists(): return
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    shutil.copy2(LAST_DISCOVERY_JSON, BACKUPS_DIR / f"{ts}.json")
    _enforce_backup_limits()

def _enforce_backup_limits():
    """Enforce backup limits."""
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - (ARCHIVE_DAYS * 86400)
    backups = sorted(BACKUPS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
    for f in list(backups):
        if f.stat().st_mtime < cutoff:
            shutil.move(str(f), str(ARCHIVE_DIR / f.name))
            backups.remove(f)
    backups = sorted(BACKUPS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
    while len(backups) > MAX_BACKUPS:
        backups[0].unlink()
        backups = backups[1:]

# ── Config patching ───────────────────────────────────────────────────────────

def patch_openclaw_json(endpoints: dict):
    # PERPETUATOOLSROOT is only needed for PT-specific policy operations.
    # openclaw.json IP patching works fine without it — just warn if absent.
    """Patch openclaw json."""
    if not _resolve_perpetua_root_env():
        logging.warning(
            "PERPETUATOOLSROOT/PERPETUA_TOOLS_ROOT not set — skipping PT-specific policy "
            "checks, but openclaw.json IP update will still proceed."
        )
    if not OPENCLAW_JSON.exists(): return
    cfg = _load_json(OPENCLAW_JSON)
    if not cfg: return
    endpoints = filter_endpoints_for_policy(endpoints)
    providers = cfg.setdefault("models", {}).setdefault("providers", {})
    mac = endpoints.get("mac")
    win = endpoints.get("win")
    if mac and RUNNING_ON_WINDOWS:
        # On a Windows host localhost is the Windows box: never write it (or any
        # known Windows address) as lmstudio-mac; use the discovered Mac IP only.
        mac_host = str(mac.get("ip") or "")
        if mac_host and mac_host not in _known_windows_ips() and not _is_loopback_host(mac_host):
            providers.setdefault("lmstudio-mac", {})["baseUrl"] = f"http://{mac_host}:1234/v1"
            providers["lmstudio-mac"]["models"] = [
                {"id": m, "name": f"Mac LMS — {m}", "contextWindow": 32768,
                 "maxTokens": 8192, "cost": {"input": 0, "output": 0}}
                for m in mac["models"] if "embed" not in m.lower()
            ]
    elif mac:
        # lmstudio-mac ALWAYS uses localhost — the LAN IP is discovery metadata only.
        # Native Mac processes must never route to themselves via the LAN interface.
        providers.setdefault("lmstudio-mac", {})["baseUrl"] = "http://localhost:1234/v1"
        providers["lmstudio-mac"]["models"] = [
            {"id": m, "name": f"Mac LMS — {m}", "contextWindow": 32768,
             "maxTokens": 8192, "cost": {"input": 0, "output": 0}}
            for m in mac["models"] if "embed" not in m.lower()
        ]
    if win:
        win_ip = win["ip"]
        if RUNNING_ON_WINDOWS and win_ip in ("localhost", "127.0.0.1"):
            win_ip = "localhost"
        providers.setdefault("lmstudio-win", {})["baseUrl"] = f"http://{win_ip}:1234/v1"
        providers["lmstudio-win"]["models"] = [
            {"id": m, "name": f"Win LMS — {m}", "contextWindow": 32768,
             "maxTokens": 8192, "cost": {"input": 0, "output": 0}}
            for m in win["models"] if "embed" not in m.lower()
        ]
    cfg.setdefault("meta", {})["lastTouchedAt"] = datetime.now(timezone.utc).isoformat()
    try:
        tmp = OPENCLAW_JSON.with_suffix(".json.tmp~")
        tmp.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        os.replace(tmp, OPENCLAW_JSON)
    except OSError as exc:
        logging.warning("patch_openclaw_json: cannot write %s: %s", OPENCLAW_JSON, exc)

# NOTE: discover.py previously patched live LAN IPs directly into the git-TRACKED
# config/devices.yml and config/models.yml (functions patch_devices_yml /
# patch_models_yml, removed 2026-07-08). That was a hygiene/doxxing footgun: every
# start.ps1 / start.sh run dirtied the repo with ephemeral topology, and a
# careless `git add -A` could commit live LAN IPs to the public GitHub repo.
# Verified before removal: `lan_ip` in devices.yml has ZERO Python readers
# (grep across orchestrator/, src/perpetua/) — it was write-only, dead
# metadata. models.yml's `${LM_STUDIO_WIN_ENDPOINT:-<default>}` literal is
# consulted by ModelRegistry._expand_env_default only when the env var itself
# is unset (os.getenv(var, default)) — and lan_discovery.detect_active_
# tilting_ip() / _sync_win_endpoint_env() already set that env var from the
# same authoritative, UNTRACKED ~/.openclaw/state/last_discovery.json this
# module writes below via save_discovery_state(). Tracked config now stays a
# portable placeholder; live topology lives only in last_discovery.json,
# .env.lmstudio (gitignored), and process env — never in git-tracked YAML.

def write_env_lmstudio(endpoints: dict, repo_paths: dict):
    """Write env lmstudio."""
    endpoints = filter_endpoints_for_policy(endpoints)
    mac = endpoints.get("mac") or {}
    win = endpoints.get("win") or {}
    win_ip = (win.get("ip") or "")
    mac_ip = (mac.get("ip") or "")
    # On Windows host, Mac is remote — persist LAN IP for cross-machine routing.
    if RUNNING_ON_WINDOWS and mac_ip not in ("", "localhost", "127.0.0.1"):
        mac_url = f"http://{mac_ip}:1234"
    else:
        mac_url = "http://localhost:1234"
    win_url = f"http://{win_ip}:1234" if win_ip else ""
    mac_models = mac.get("models", [])
    win_models = win.get("models", [])
    mac_primary = next((m for m in mac_models if "embed" not in m.lower()), "")
    win_primary = (next((m for m in win_models if "27b" in m.lower()), None) or
                   next((m for m in win_models if "embed" not in m.lower()), ""))
    win_fallback = next((m for m in win_models if m != win_primary and "embed" not in m.lower()), "")
    tier = (_load_json(LAST_DISCOVERY_JSON) or {}).get("recovery_tier", 1)
    content = (
        f"# Auto-generated by ~/.openclaw/scripts/discover.py — do not edit manually\n"
        f"# Last updated: {datetime.now(timezone.utc).isoformat()} | recovery_tier: {tier}\n"
        f"LM_STUDIO_MAC_ENDPOINT={mac_url}\n"
        f"LM_STUDIO_WIN_ENDPOINTS={win_url}\n"
        f"LMS_MAC_MODEL={mac_primary}\n"
        f"LMS_WIN_MODEL={win_primary}\n"
        f"LMS_WIN_FALLBACK_MODEL={win_fallback}\n"
        f"LM_STUDIO_API_TOKEN=lm-studio\n"
    )
    for repo_path in repo_paths.values():
        if repo_path and Path(repo_path).exists():
            env_path = Path(repo_path) / ".env.lmstudio"
            try:
                with open(str(env_path), "w", encoding="utf-8") as fh:
                    fh.write(content)
            except OSError as exc:
                logging.warning("write_env_lmstudio: cannot write %s: %s", env_path, exc)

# ── Recovery tiers ────────────────────────────────────────────────────────────

def _state_to_ep(state):
    """State to ep."""
    if not state or not state.get("endpoints"): return None
    return {
        "mac": {"ip": state["endpoints"]["mac"]["ip"], "models": state["models"]["mac"]}
              if state["endpoints"]["mac"]["reachable"] else None,
        "win": {"ip": state["endpoints"]["win"]["ip"], "models": state["models"]["win"]}
              if state["endpoints"]["win"]["reachable"] else None,
    }

def _load_tier2():
    """Load tier2 (last discovery state)."""
    return _state_to_ep(_load_json(LAST_DISCOVERY_JSON))
def _load_tier3():
    """Load tier3."""
    if not BACKUPS_DIR.exists(): return None
    for b in sorted(BACKUPS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        ep = _state_to_ep(_load_json(b))
        if ep: return ep
    return None
def _load_tier4(profile="lan-full"):
    """Load tier4."""
    return _state_to_ep(_load_json(PROFILES_DIR / f"{profile}.json"))

# ── File lock ─────────────────────────────────────────────────────────────────

def _try_lock_file(handle) -> None:
    """Try lock file."""
    if fcntl is not None:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return
    handle.seek(0)
    handle.write("0")
    handle.flush()
    handle.seek(0)
    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)


def _unlock_file(handle) -> None:
    """Unlock file."""
    if fcntl is not None:
        fcntl.flock(handle, fcntl.LOCK_UN)
        return
    handle.seek(0)
    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


class _Lock:
    """Helper: Lock."""
    def __init__(self, timeout=10.0):
        """Initialise the instance."""
        self._timeout = timeout; self._fd = None
    def __enter__(self):
        """Enter the context manager."""
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        lock_path = _lock_path()
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.time() + self._timeout
        while True:
            self._fd = open(lock_path, "w")
            try:
                _try_lock_file(self._fd)
                return self
            except BlockingIOError:
                if self._fd:
                    try:
                        self._fd.close()
                    except OSError:
                        pass
                    self._fd = None
                if time.time() > deadline:
                    raise TimeoutError("discovery lock timeout")
                time.sleep(0.2)
            except OSError:
                if self._fd:
                    try:
                        self._fd.close()
                    except OSError:
                        pass
                    self._fd = None
                raise
    def __exit__(self, *_):
        """Exit the context manager."""
        if self._fd:
            _unlock_file(self._fd); self._fd.close()
            try: _lock_path().unlink()
            except FileNotFoundError: pass

# ── Main discovery flow ───────────────────────────────────────────────────────

def run_discovery(force: bool = True, cached: bool = False) -> int:
    """Probe endpoints and update configs.

    Default behaviour is always-fresh (force=True).  Pass cached=True (or
    use the --cached CLI flag) to skip the probe when gossip is still warm
    (within GOSSIP_TTL_SECONDS).  The legacy --force flag is kept for
    backwards compatibility but is now a no-op (force is already the default).
    """
    with _Lock():
        if cached and not force and DISCOVERY_JSON.exists():
            state = _load_json(DISCOVERY_JSON)
            if state:
                age = (datetime.now(timezone.utc) -
                       datetime.fromisoformat(state["timestamp"])).total_seconds()
                if age < GOSSIP_TTL_SECONDS:
                    return 0

        print("🔍 Probing LM Studio endpoints...", file=sys.stderr)
        endpoints = discover_endpoints()
        tier = 1

        if not endpoints["mac"] and not endpoints["win"]:
            print("⚠️  No live endpoints — trying recovery tiers...", file=sys.stderr)
            for fn, t, name in [(_load_tier2, 2, "last known good"),
                                  (_load_tier3, 3, "newest backup"),
                                  (lambda: _load_tier4("lan-full"), 4, "lan-full profile")]:
                ep = fn()
                if ep and RUNNING_ON_WINDOWS:
                    ep, dropped = _drop_windows_mac(ep)
                    if dropped and not ep["mac"] and not ep["win"]:
                        continue
                if ep: endpoints = ep; tier = t; print(f"  → tier {t}: {name}", file=sys.stderr); break
            if not endpoints["mac"] and not endpoints["win"]:
                print("❌ All tiers failed.", file=sys.stderr)
                RECOVERY_SOURCE_TXT.write_text("tier_failed\n")
                return 1
        else:
            last = _load_json(LAST_DISCOVERY_JSON)
            if last:
                win_known = _known_windows_ips() if RUNNING_ON_WINDOWS else set()
                for role in ("mac", "win"):
                    if not endpoints[role] and last["endpoints"][role]["reachable"]:
                        role_ip = last["endpoints"][role].get("ip", "")
                        if role == "mac" and (role_ip in win_known or _is_loopback_host(role_ip)):
                            print("⚠️  mac last-good is a known Windows address — not preserving",
                                  file=sys.stderr)
                            continue
                        endpoints[role] = {"ip": last["endpoints"][role]["ip"],
                                           "models": last["models"][role]}
                        print(f"⚠️  {role} unreachable — preserving last-good", file=sys.stderr)

        endpoints = filter_endpoints_for_policy(endpoints)
        endpoints, blocked_peers = filter_endpoints_for_trust(endpoints)
        if blocked_peers and not endpoints.get("mac") and not endpoints.get("win"):
            print("❌ New peer(s) require handshake — see 🤝 lines above.", file=sys.stderr)
            return 2

        mac = endpoints.get("mac") or {}
        win = endpoints.get("win") or {}
        hash_endpoints = _endpoints_for_hash(endpoints)

        new_hash = compute_hash(hash_endpoints)
        last = _load_json(LAST_DISCOVERY_JSON)
        if last and last.get("hash") == new_hash:
            last["timestamp"] = datetime.now(timezone.utc).isoformat()
            if tier != last.get("recovery_tier", 1):
                last["recovery_tier"] = tier  # reflect actual recovery tier used this run
                RECOVERY_SOURCE_TXT.write_text(f"tier{tier}\n")
            DISCOVERY_JSON.write_text(json.dumps(last, indent=2))
            LAST_DISCOVERY_JSON.write_text(json.dumps(last, indent=2))
            print("✅ No changes. Config is current.", file=sys.stderr)
            return 0

        print("🔄 Changes detected — updating configs...", file=sys.stderr)
        backup_current_state()
        repo_paths = get_repo_paths()

        patch_openclaw_json(endpoints)
        print("  ✓ openclaw.json", file=sys.stderr)
        # Tracked config/devices.yml + config/models.yml are intentionally NOT
        # patched here — see the note above write_env_lmstudio(). Live topology
        # goes only to untracked state (below) + .env.lmstudio (gitignored).
        write_env_lmstudio(endpoints, repo_paths)
        print("  ✓ .env.lmstudio written", file=sys.stderr)
        save_discovery_state(hash_endpoints, tier)
        print(f"  ✓ state saved (tier {tier})", file=sys.stderr)
        if mac.get("ip"): print(f"  Mac: {mac['ip']} — {len(mac.get('models', []))} models", file=sys.stderr)
        if win.get("ip"): print(f"  Win: {win['ip']} — {len(win.get('models', []))} models", file=sys.stderr)
        return 0

# ── CLI ───────────────────────────────────────────────────────────────────────

def _cmd_status():
    """Cmd status."""
    state = _load_json(LAST_DISCOVERY_JSON) or _load_json(DISCOVERY_JSON)
    if not state: print("No discovery state. Run: discover.py --status (after a probe)"); return
    print(f"Tier:    {state.get('recovery_tier', '?')}")
    print(f"Updated: {state.get('timestamp', '?')}")
    for role, ep in state.get("endpoints", {}).items():
        if not isinstance(ep, dict) or "reachable" not in ep:
            # e.g. win_peers is a list of peers, not a single endpoint
            if isinstance(ep, list):
                print(f"  {role}: {len(ep)} peer(s)")
            continue
        ok = "✅" if ep["reachable"] else "❌"
        print(f"  {role}: {ok} {ep['ip']}:{ep['port']} — {len(state['models'].get(role, []))} models")
    src = RECOVERY_SOURCE_TXT.read_text().strip() if RECOVERY_SOURCE_TXT.exists() else "unknown"
    print(f"Source:  {src}")

def _cmd_restore(target: str):
    """Cmd restore."""
    if target == "latest":
        ep = _load_tier3()
    elif target.startswith("profile:"):
        ep = _load_tier4(target.split(":", 1)[1])
    else:
        matches = sorted(BACKUPS_DIR.glob(f"{target}*.json")) if BACKUPS_DIR.exists() else []
        ep = _state_to_ep(_load_json(matches[-1])) if matches else None
    if not ep: print(f"Nothing found for '{target}'."); return
    ep = filter_endpoints_for_policy(ep)
    backup_current_state()
    repo_paths = get_repo_paths()
    mac = ep.get("mac") or {}; win = ep.get("win") or {}
    with _Lock():
        patch_openclaw_json(ep)
        # Tracked config/devices.yml + config/models.yml intentionally not
        # patched — see note above write_env_lmstudio().
        write_env_lmstudio(ep, repo_paths)
        save_discovery_state(ep, tier=99)
    RECOVERY_SOURCE_TXT.write_text("manual_restore\n")
    print(f"✅ Restored: Mac={mac.get('ip', '?')} Win={win.get('ip', '?')}")

def _query_peer_topology_on_change() -> None:
    """Phase 4: Query peer fleet topology on LAN topology change.

    Called when _watch_loop detects a network change (interface up/down, DHCP renewal).
    Spawns query_peer_topology.py subprocess without blocking the watch loop.
    """
    try:
        script_path = Path(__file__).parent.parent / "bin/orama-system/skills/hermes-harness/scripts/query_peer_topology.py"
        if not script_path.exists():
            logging.debug("query_peer_topology.py not found, skipping peer topology query")
            return

        import subprocess
        import sys

        # Non-blocking subprocess call with short timeout (don't hang watch loop)
        subprocess.Popen(
            [sys.executable, str(script_path), "--timeout", "2"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # Detach from parent process
        )
        logging.info("Spawned peer topology query (non-blocking)")
    except Exception as exc:
        logging.debug("Could not spawn peer topology query: %s", exc)


def _watch_loop(interval: int = 30) -> None:
    """Poll for network changes and re-run discovery when topology shifts.

    Strategy:
      - Every `interval` seconds, probe both known IPs for liveness.
      - If liveness changes (a node appears/disappears) run full discovery.
      - On macOS, also listens for scutil network-change events via subprocess
        so recovery happens within seconds of a DHCP renewal after power cycle.
      - Phase 4: also queries peer fleet topology on topology change.

    The watch loop runs until killed (SIGINT/SIGTERM).
    """
    import subprocess, signal, threading

    _stop = threading.Event()

    def _sig(*_):
        """Signal handler: request loop stop."""
        _stop.set()
    signal.signal(signal.SIGINT,  _sig)
    signal.signal(signal.SIGTERM, _sig)

    def _quick_alive(ip: str) -> bool:
        """TCP connect probe — faster than full /v1/models round-trip."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            host = "127.0.0.1" if ip in ("localhost", "127.0.0.1") else ip
            s.connect((host, LM_STUDIO_PORT))
            s.close()
            return True
        except Exception:
            return False

    def _current_liveness() -> dict:
        """Current liveness."""
        state = _load_json(LAST_DISCOVERY_JSON) or {}
        ep = state.get("endpoints", {})
        mac_ip = (ep.get("mac") or {}).get("ip", "")
        win_ip = (ep.get("win") or {}).get("ip", "")
        return {
            "mac": _quick_alive(mac_ip) if mac_ip else False,
            "win": _quick_alive(win_ip) if win_ip else False,
            "mac_lan": _mac_lan_ip(),
        }

    def _scutil_listener():
        """macOS: wait for scutil network-change event, then set stop flag so
        the main loop immediately re-probes.  Runs in a daemon thread."""
        try:
            proc = subprocess.Popen(
                ["scutil"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            assert proc.stdin and proc.stdout
            proc.stdin.write("n.add com.apple.system.config.network_change\n")
            proc.stdin.write("n.watch\n")
            proc.stdin.flush()
            for line in proc.stdout:
                if "notification" in line.lower() or "changed" in line.lower():
                    print("🔔 Network change detected — triggering rediscovery...", file=sys.stderr)
                    _stop.set()   # wake the main loop immediately
                    _stop.clear() # re-arm for next event (set() wakes, clear() re-arms)
                    run_discovery(force=True, cached=False)
                if _stop.is_set():
                    break
            proc.kill()
        except Exception:
            pass  # scutil not available or permission denied — polling fallback handles it

    # Start macOS network-change listener in background
    t = threading.Thread(target=_scutil_listener, daemon=True)
    t.start()

    last_liveness = _current_liveness()
    print(f"👁️  Network watcher started (poll every {interval}s). Ctrl-C to stop.", file=sys.stderr)

    while not _stop.wait(timeout=interval):
        current = _current_liveness()
        topology_changed = (
            current["mac"] != last_liveness["mac"] or
            current["win"] != last_liveness["win"] or
            current["mac_lan"] != last_liveness["mac_lan"]
        )
        if topology_changed:
            print(
                f"⚡ Topology change: mac={last_liveness['mac']}→{current['mac']} "
                f"win={last_liveness['win']}→{current['win']} "
                f"mac_lan={last_liveness['mac_lan']}→{current['mac_lan']}",
                file=sys.stderr,
            )
            run_discovery(force=True, cached=False)
            # Phase 4: query peer topology on LAN interface change
            _query_peer_topology_on_change()
            last_liveness = _current_liveness()
        else:
            # Refresh timestamp so consumers know watcher is alive
            state = _load_json(LAST_DISCOVERY_JSON)
            if state:
                state["watcher_heartbeat"] = datetime.now(timezone.utc).isoformat()
                LAST_DISCOVERY_JSON.write_text(json.dumps(state, indent=2))


def main():
    """Main."""
    p = argparse.ArgumentParser(
        description="LM Studio Auto-Discovery (always probes by default; use --cached to skip when warm)",
    )
    p.add_argument("--cached",  action="store_true",
                   help="Skip probe if gossip is still fresh (within TTL). Default is always re-probe.")
    p.add_argument("--force",   action="store_true",
                   help="[legacy no-op] Re-probe is now the default; kept for backwards compat.")
    p.add_argument("--status",  action="store_true", help="Show current state (no probe)")
    p.add_argument("--restore", metavar="TARGET",    help="latest | YYYY-MM-DD | profile:name")
    p.add_argument("--prune",   action="store_true", help="Manually prune backups")
    p.add_argument("--watch",   action="store_true",
                   help="Run continuously: re-probe on network change (scutil) or topology shift")
    p.add_argument("--watch-interval", type=int, default=30, metavar="SEC",
                   help="Polling interval for --watch mode (default: 30s)")
    p.add_argument("--ack-peer", metavar="IP", help="Acknowledge new discovery peer after handshake")
    p.add_argument("--nonce", help="Handshake nonce from discover output")
    p.add_argument("--signature", help="Handshake HMAC signature")
    args = p.parse_args()
    if args.ack_peer:
        if not args.nonce or not args.signature:
            print("❌ --ack-peer requires --nonce and --signature", file=sys.stderr)
            sys.exit(1)
        if ack_peer(args.ack_peer, args.nonce, args.signature):
            print(f"✅ Peer {args.ack_peer} acknowledged")
            sys.exit(0)
        print("❌ Handshake verification failed", file=sys.stderr)
        sys.exit(1)
    if args.status:  _cmd_status(); sys.exit(0)
    if args.restore: _cmd_restore(args.restore); sys.exit(0)
    if args.prune:   _enforce_backup_limits(); print("✅ Pruned."); sys.exit(0)
    if args.watch:
        run_discovery(force=True, cached=False)  # initial probe
        _watch_loop(interval=args.watch_interval)
        sys.exit(0)
    # When --cached is given, respect TTL (skip if warm); otherwise always probe.
    if args.cached:
        sys.exit(run_discovery(force=False, cached=True))
    else:
        sys.exit(run_discovery(force=True, cached=False))

if __name__ == "__main__":
    main()
