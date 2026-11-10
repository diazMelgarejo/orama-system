#!/usr/bin/env python3
"""
cline_autoresearcher.py — ClinePass AutoResearcher resilience controller.

When the platform's native gateway (Hermes on Windows, OpenClaw on macOS) is
paused, not running, or rate-limited/quota-reached, the local Cline Bot takes
over as AutoResearcher — dispatching to the local coder backend (LM Studio
Win / Ollama Mac) directly when it's idle, falling back to ClinePass credits
(the `cline` CLI itself) if the local backend attempt fails.

Peer resilience (Mac<->Win co-orchestration) is delegated to the existing
lan_peer_session.py state machine: 10x consecutive peer-unreachable failures
demote to solo mode; solo mode re-checks the peer every 15 minutes
(LAN_PEER_DEGRADED_RETRY_SECONDS, default 900s).

Usage:
    python scripts/cline_autoresearcher.py --platform windows --check --json
    python scripts/cline_autoresearcher.py --platform macos --status --json
    python scripts/cline_autoresearcher.py --platform windows --dispatch --task "..."
"""
from __future__ import annotations

import argparse
import json
import os
import platform as _platform_mod
import ipaddress
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import autoresearcher_lock as _arl  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

LMS_WIN_ENDPOINT = os.getenv("LM_STUDIO_WIN_ENDPOINTS", "http://localhost:1234").split(",")[0].strip()
LMS_WIN_MODEL = os.getenv(
    "LM_STUDIO_WIN_MODEL",
    "qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2",
)
LMS_API_KEY = os.getenv("LM_STUDIO_API_TOKEN", "lm-studio")
OLLAMA_MAC_ENDPOINT = os.getenv("OLLAMA_MAC_ENDPOINT", "http://127.0.0.1:11434")
OLLAMA_MAC_MODEL = os.getenv("OLLAMA_MAC_MODEL", "qwen3.5:9b-mlx")

WIN_PULSE_LOCK = Path.home() / ".openclaw" / "state" / "lan_peer" / "win_pulse.lock"
WIN_COORD_PAUSE_FILE = Path.home() / ".openclaw" / "state" / "lan_peer" / "coord_pulse_pause.json"
MAC_PULSE_LOCK = Path.home() / ".openclaw" / "state" / "lan_peer" / "mac_pulse.lock"
MAC_GATEWAY_PAUSE_FILE = Path.home() / ".openclaw" / "state" / "lan_peer" / "openclaw_gateway_pause.json"

# Single-owner backend locks (AR-WIN-1). An OS-held lock is the authority; see scripts/autoresearcher_lock.py.
BACKEND_LOCK_WIN = Path.home() / ".openclaw" / "state" / "lan_peer" / "autoresearcher_backend_win.lock"
BACKEND_LOCK_MAC = Path.home() / ".openclaw" / "state" / "lan_peer" / "autoresearcher_backend_mac.lock"

_LAN_PEER_SESSION = (
    REPO_ROOT
    / "bin"
    / "orama-system"
    / "skills"
    / "hermes-harness"
    / "scripts"
    / "lan_peer_session.py"
)


# ── Platform detection ────────────────────────────────────────────────────────

def detect_platform() -> str:
    """Return 'windows' on a Windows host and 'macos' otherwise."""
    if os.name == "nt" or _platform_mod.system() == "Windows":
        return "windows"
    return "macos"


def _is_windows(plat: Optional[str] = None) -> bool:
    """True when *plat* (or the detected platform) is windows."""
    return (plat or detect_platform()) == "windows"


# ── Cline CLI discovery ───────────────────────────────────────────────────────

def _find_cline() -> Optional[str]:
    """Return the path of the cline CLI: a configured CLINE_BIN first, then PATH, then known install folders."""
    configured = os.getenv("CLINE_BIN", "").strip()
    if configured and Path(configured).is_file():
        return configured
    bin_name = "cline.exe" if _is_windows() else "cline"
    found = shutil.which(bin_name)
    if found:
        return found
    if _is_windows():  # the npm global install layout ships a cmd shim, not an exe (never given a prompt, see _cline_launcher)
        found = shutil.which("cline.cmd")
        if found:
            return found
    if not _is_windows():
        found = shutil.which("cline")
        if found:
            return found
    candidates = []
    local_appdata = os.getenv("LOCALAPPDATA")
    if local_appdata:
        candidates.append(Path(local_appdata) / "Programs" / "cline" / "cline.exe")
        candidates.append(Path(local_appdata) / "cline" / "bin" / "cline.exe")
    home = Path.home()
    # LM Studio bin folder: where a Windows host reported a Cline shim off PATH (reported, not verified on every host).
    candidates.append(home / ".lmstudio" / "bin" / "cline.exe")
    candidates.append(home / ".lmstudio" / "bin" / "cline.cmd")
    candidates.append(home / ".lmstudio" / "bin" / "cline.ps1")
    candidates.append(home / ".local" / "bin" / "cline")
    candidates.append(home / "bin" / "cline")
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def cline_available() -> Dict[str, Any]:
    """Return whether the cline CLI is available, with its path and a reason."""
    cline_bin = _find_cline()
    if not cline_bin:
        return {"available": False, "bin": None, "reason": "cline CLI not found on PATH or known install dirs"}
    if _cline_launcher(cline_bin) is None:
        return {"available": False, "bin": None,
                "reason": "cline is a cmd/ps1 shim whose node entry could not be resolved; refusing to pass prompts through a shell shim"}
    return {"available": True, "bin": cline_bin, "reason": "cline CLI found"}


def _cline_launcher(cline_bin: str) -> Optional[list]:
    """Return the argv prefix that launches Cline, or None when it cannot be launched safely.

    A normal executable is its own launcher. An npm ``.cmd``/``.bat``/``.ps1`` shim is never used to carry a
    prompt (cmd.exe re-parses metacharacters in arguments); the node entry script next to it is launched with node.
    """
    if Path(cline_bin).suffix.lower() not in (".cmd", ".bat", ".ps1"):
        return [cline_bin]
    base = Path(cline_bin).parent
    entry = base / "node_modules" / "cline" / "bin" / "cline"
    node = base / "node.exe"
    node_path = str(node) if node.is_file() else shutil.which("node")
    if entry.is_file() and node_path:
        return [node_path, str(entry)]
    return None


# ── Hermes CLI discovery (Windows gateway) ────────────────────────────────────

def _find_hermes() -> Optional[str]:
    """Return the path of the hermes CLI from PATH or known install folders, or None."""
    hermes_bin = shutil.which("hermes")
    if hermes_bin:
        return hermes_bin
    local_appdata = os.getenv("LOCALAPPDATA")
    if local_appdata:
        scripts_dir = Path(local_appdata) / "hermes" / "hermes-agent" / "venv" / "Scripts"
        for name in ("hermes.exe", "hermes"):
            candidate = scripts_dir / name
            if candidate.exists():
                return str(candidate)
    hermes_home = os.getenv("HERMES_HOME")
    if hermes_home:
        for rel in (
            Path("hermes-agent") / "venv" / "Scripts" / "hermes.exe",
            Path("hermes-agent") / "venv" / "bin" / "hermes",
        ):
            candidate = Path(hermes_home) / rel
            if candidate.exists():
                return str(candidate)
    return None


# ── Gateway status (per platform) ─────────────────────────────────────────────

def _read_pause_file(path: Path) -> Dict[str, Any]:
    """Read a gateway pause JSON file (BOM tolerant); a missing or unreadable file means not paused."""
    if not path.exists():
        return {"paused": False}
    try:
        # utf-8-sig: PowerShell's Set-Content -Encoding UTF8 writes a BOM;
        # plain utf-8 leaves it in the string and json.loads chokes on it,
        # silently falling to the except branch below (paused: False) --
        # exactly the class of bug documented elsewhere this session.
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {"paused": False}


def _hermes_gateway_running() -> bool:
    """True when `hermes gateway status` reports the Windows gateway as running."""
    hermes_bin = _find_hermes()
    if not hermes_bin:
        return False
    try:
        proc = subprocess.run(
            [hermes_bin, "gateway", "status"],
            capture_output=True, text=True, timeout=10,
        )
        return "Gateway is running" in (proc.stdout or "")
    except Exception:
        return False


def _openclaw_gateway_running() -> bool:
    """Best-effort process probe for the OpenClaw gateway on macOS."""
    try:
        proc = subprocess.run(
            ["pgrep", "-f", "openclaw"],
            capture_output=True, text=True, timeout=5,
        )
        return bool((proc.stdout or "").strip())
    except Exception:
        return False


def gateway_status(plat: Optional[str] = None) -> Dict[str, Any]:
    """Returns {paused, running, rate_limited, reason} for the platform's native gateway."""
    plat = plat or detect_platform()
    if _is_windows(plat):
        pause = _read_pause_file(WIN_COORD_PAUSE_FILE)
        running = _hermes_gateway_running()
        return {
            "paused": bool(pause.get("paused", False)),
            "running": running,
            "rate_limited": False,
            "reason": pause.get("reason", ""),
            "gateway": "hermes",
        }
    pause = _read_pause_file(MAC_GATEWAY_PAUSE_FILE)
    running = _openclaw_gateway_running()
    return {
        "paused": bool(pause.get("paused", False)),
        "running": running,
        "rate_limited": False,
        "reason": pause.get("reason", ""),
        "gateway": "openclaw",
    }


# ── Local backend idle probe (per platform) ───────────────────────────────────

def _probe_url(url: str) -> str:
    """Use literal IPv4 loopback for plain-HTTP localhost without DNS lookup.

    Preserve the Windows IPv6-delay repair without trusting resolver output.
    HTTPS retains its certificate hostname; explicit peer hosts stay unchanged.
    Userinfo and malformed configurations refuse instead of changing identity.
    """
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("probe requires an HTTP or HTTPS host")
    if parts.username is not None or parts.password is not None:
        raise ValueError("probe URL must not contain userinfo")
    port = parts.port
    if parts.scheme != "http" or parts.hostname != "localhost":
        return url
    loopback = str(ipaddress.IPv4Address(0x7F000001))
    netloc = loopback if port is None else f"{loopback}:{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _probe_http_ok(url: str, timeout: float = 3.0) -> bool:
    """Probe with per-I/O timeouts and at most two literal localhost attempts.

    Plain-HTTP localhost tries IPv4 first, then IPv6 loopback without DNS.
    HTTPS and explicit peer hosts retain their identity and get one attempt.
    This is not a whole-call deadline, including for DNS on unchanged hosts.
    """
    try:
        import urllib.request
        from urllib.parse import urlsplit, urlunsplit

        candidates = [_probe_url(url)]
        parts = urlsplit(url)
        if parts.scheme == "http" and parts.hostname == "localhost":
            host = f"[{ipaddress.IPv6Address(1)}]"
            netloc = host if parts.port is None else f"{host}:{parts.port}"
            candidates.append(urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment)))
        for candidate in candidates:
            try:
                req = urllib.request.Request(candidate, method="GET")
                with urllib.request.urlopen(req, timeout=timeout / len(candidates)) as resp:
                    if 200 <= resp.status < 300:
                        return True
            except Exception:
                continue
    except Exception:
        pass
    return False


# A coder lock older than this is stale even when its recorded PID was reused by an unrelated process.
LOCK_MAX_AGE_SECONDS = float(os.getenv("AUTORESEARCHER_LOCK_MAX_AGE_SECONDS", str(6 * 3600)))


def _pid_alive(pid: int) -> bool:
    """True when a process with this PID exists (Windows via OpenProcess, POSIX via signal 0)."""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.OpenProcess.restype = ctypes.c_void_p
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = kernel32.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code))
        kernel32.CloseHandle(ctypes.c_void_p(handle))
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def lock_is_held(lock: Path, now: Optional[float] = None) -> bool:
    """True when *lock* exists and is still plausibly held.

    A missing file is not held. A file whose first token is a PID is held only while that process is alive and the
    file is younger than LOCK_MAX_AGE_SECONDS (a dead owner or a very old file is stale, so a crashed job can no
    longer block the AutoResearcher forever). A file we cannot read or parse is treated as held, because
    staleness cannot be proven.
    """
    try:
        age = (time.time() if now is None else now) - lock.stat().st_mtime
    except OSError:
        return False
    try:
        pid = int(lock.read_text(encoding="utf-8", errors="replace").split()[0])
    except (OSError, ValueError, IndexError):
        return True
    return age < LOCK_MAX_AGE_SECONDS and _pid_alive(pid)


def _backend_lock_busy(path: Path) -> Optional[str]:
    """Return a reason when the backend lock at *path* is not free, or None when it is free.

    Fail closed: if the lock check itself raises (another account owns the file, a sharing violation) the backend is
    reported busy, so a broken check can never read as idle.
    """
    try:
        own = _arl.inspect(path)
    except Exception as exc:
        return f"backend lock check failed (treated as busy): {type(exc).__name__}"
    if own.state != _arl.FREE:
        return f"backend lock {own.state}: {own.reason}"
    return None


def local_backend_idle(plat: Optional[str] = None) -> Dict[str, Any]:
    """Returns {idle, reachable, reason} for the platform's local coder backend."""
    plat = plat or detect_platform()
    if _is_windows(plat):
        reachable = _probe_http_ok(f"{LMS_WIN_ENDPOINT}/v1/models")
        if not reachable:
            return {"idle": False, "reachable": False, "reason": "LM Studio Win not reachable"}
        if lock_is_held(WIN_PULSE_LOCK):
            return {"idle": False, "reachable": True, "reason": "GPU lock held (win_pulse.lock)"}
        busy = _backend_lock_busy(BACKEND_LOCK_WIN)
        if busy:
            return {"idle": False, "reachable": True, "reason": busy}
        return {"idle": True, "reachable": True, "reason": "LM Studio Win idle"}

    reachable = _probe_http_ok(f"{OLLAMA_MAC_ENDPOINT}/api/tags")
    if not reachable:
        return {"idle": False, "reachable": False, "reason": "ollama not reachable"}
    if lock_is_held(MAC_PULSE_LOCK):
        return {"idle": False, "reachable": True, "reason": "coder lock held (mac_pulse.lock)"}
    busy = _backend_lock_busy(BACKEND_LOCK_MAC)
    if busy:
        return {"idle": False, "reachable": True, "reason": busy}
    return {"idle": True, "reachable": True, "reason": "ollama idle"}


# ── Fallback decision ─────────────────────────────────────────────────────────

def _fallback_reason(
    gw: Dict[str, Any], backend: Dict[str, Any], cline: Dict[str, Any], should_fallback: bool
) -> str:
    """Explain in one line why the ClinePass fallback is or is not active."""
    if not should_fallback:
        if gw.get("running") and not gw.get("paused") and not gw.get("rate_limited"):
            return "gateway running — no fallback needed"
        if not backend.get("idle", False):
            return f"local backend not idle: {backend.get('reason', '')}"
        if not cline.get("available", False):
            return f"Cline unavailable: {cline.get('reason', '')}"
        return "fallback inactive"
    return (
        "ClinePass fallback active — "
        f"gateway paused={gw.get('paused')} running={gw.get('running')} "
        f"rate_limited={gw.get('rate_limited')}, local backend idle, Cline available"
    )


def should_fallback_to_cline(plat: Optional[str] = None) -> Dict[str, Any]:
    """Decide whether the Cline fallback should take over: gateway down, local backend idle and cline available."""
    plat = plat or detect_platform()
    gw = gateway_status(plat)
    backend = local_backend_idle(plat)
    cline = cline_available()

    gateway_down = bool(gw.get("paused")) or (not gw.get("running")) or bool(gw.get("rate_limited"))
    fallback = gateway_down and bool(backend.get("idle")) and bool(cline.get("available"))

    return {
        "should_fallback": fallback,
        "reason": _fallback_reason(gw, backend, cline, fallback),
        "gateway": gw,
        "local_backend": backend,
        "cline": cline,
        "platform": plat,
    }


# ── Dispatch ──────────────────────────────────────────────────────────────────

def _reap(proc: Any) -> None:
    """Best-effort kill and reap of a child so a failed dispatch leaves no orphan process."""
    try:
        proc.kill()
        proc.communicate(timeout=10)
    except Exception:
        pass


def _cline_argv(cline_bin: str, task: str) -> list:
    """Build the Cline command line for a one-shot prompt.

    HISTORY (kept on purpose): this controller originally called ``cline task <prompt>`` (2026-07-01). A ``task``
    subcommand existed on the Cline CLI of that period, so the call worked then (exact version unverified). It was
    verified absent on CLI 3.0.49 (2026-08-05) and 3.0.74 (2026-11-10, by the Mac peer), where it exits at once with
    "Unknown command or unquoted prompt". LIVE BEHAVIOUR (CLI 3.0.49 or later): the prompt is a bare positional
    argument to ``cline``; a one-word prompt is rejected as a mistyped subcommand, so one is padded here. Provider
    and model come from Cline's own configuration unless CLINE_PROVIDER / CLINE_MODEL pin them (``-P`` / ``-m``).
    Cline's own default is act mode with tool auto-approval ON (verified in the 3.0.74 help text), so runs are plan
    mode with auto-approve off unless CLINE_ALLOW_ACT=1 is set by the operator.
    Installed on the Windows host as 3.0.74 on 2026-11-10; the same version the Mac peer verified.
    """
    needs_prefix = len(task.split()) < 2 or task.lstrip().startswith("-")  # a leading "-" would parse as an option
    prompt = f"Task: {task}" if needs_prefix else task
    launcher = _cline_launcher(cline_bin)
    if launcher is None:  # never fall back to the shim itself: cmd.exe would re-parse metacharacters in the prompt
        raise RuntimeError("cline shim node entry could not be resolved; refusing to pass a prompt through a shell shim")
    argv = list(launcher)
    provider = os.getenv("CLINE_PROVIDER", "").strip()
    model = os.getenv("CLINE_MODEL", "").strip()
    if provider:
        argv += ["-P", provider]
    if model:
        argv += ["-m", model]
    if os.getenv("CLINE_ALLOW_ACT", "").strip() != "1":  # Cline defaults to act mode with auto-approve ON; do not
        argv += ["--plan", "--auto-approve", "false"]
    return argv + [prompt]


def _cline_workdir() -> Path:
    """Scratch working directory for Cline runs (CLINE_WORKDIR overrides), so repository hooks do not apply."""
    configured = os.getenv("CLINE_WORKDIR", "").strip()
    path = Path(configured) if configured else Path.home() / ".openclaw" / "state" / "autoresearcher_scratch"
    path.mkdir(parents=True, exist_ok=True)
    return path


def dispatch_cline(task: str, plat: Optional[str] = None) -> Dict[str, Any]:
    """Run the `cline` CLI once (ClinePass credits tier) and classify the outcome.

    ``outcome`` is ``completed``, ``not-sent`` when the CLI is missing or the process could not be started, or
    ``unknown`` for a timeout, post-start I/O error, or any nonzero exit. Output text cannot prove no request was sent.
    An unknown outcome must be held for reconciliation and never retried automatically.
    """
    cline = cline_available()
    if not cline.get("available"):
        return {"ok": False, "output": cline.get("reason", "cline unavailable"), "elapsed": 0, "outcome": "not-sent"}
    t0 = time.time()
    try:
        proc = subprocess.Popen(
            _cline_argv(cline["bin"], task),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(_cline_workdir()),
        )
    except OSError as exc:  # Popen itself failed: the process never existed, so nothing was sent
        return {"ok": False, "output": str(exc), "elapsed": time.time() - t0, "outcome": "not-sent"}
    except Exception as exc:  # could not prepare the call (for example the scratch directory): nothing was sent
        return {"ok": False, "output": str(exc), "elapsed": time.time() - t0, "outcome": "not-sent"}
    try:
        stdout, stderr = proc.communicate(timeout=300)
    except subprocess.TimeoutExpired:
        _reap(proc)
        return {"ok": False, "output": "cline task timed out (5min)", "elapsed": time.time() - t0, "outcome": "unknown"}
    except Exception as exc:  # includes OSError after the process started: the request may have left
        _reap(proc)
        return {"ok": False, "output": f"{type(exc).__name__} after start: {exc}", "elapsed": time.time() - t0, "outcome": "unknown"}
    except BaseException:  # interrupt or exit: reap the child, keep the in-flight record (reads as ambiguous), propagate
        _reap(proc)
        raise
    elapsed = time.time() - t0
    stdout, stderr = stdout or "", stderr or ""
    output = stdout + stderr
    if proc.returncode == 0:
        return {"ok": True, "output": output, "elapsed": elapsed, "outcome": "completed"}
    return {"ok": False, "output": output, "elapsed": elapsed, "outcome": "unknown"}


def _release_reporting(lock: Any, outcome: str) -> Optional[str]:
    """Release *lock*; return an error string instead of raising (the record then stays non-free, which fails closed)."""
    try:
        lock.release(outcome)
        return None
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


def _release_quietly(lock: Any, outcome: str) -> None:
    """Release *lock* with *outcome*; a failing release is swallowed (the record then stays stale, which fails closed)."""
    try:
        lock.release(outcome)
    except Exception:
        pass


def _effect_boundary_ok(plat: str) -> Tuple[bool, str]:
    """Re-read the gateway and Cline inputs right before the send (never reuse the earlier decision)."""
    gw = gateway_status(plat)
    gateway_down = bool(gw.get("paused")) or (not gw.get("running")) or bool(gw.get("rate_limited"))
    if not gateway_down:
        return False, "gateway recovered"
    cline = cline_available()
    if not cline.get("available", False):
        return False, f"Cline unavailable: {cline.get('reason', '')}"
    return True, "gateway still down and Cline available"


def dispatch_autoresearcher(plat: str, task: str) -> Dict[str, Any]:
    """Single-attempt ClinePass AutoResearcher dispatch under the backend lock.

    The fallback decision is advisory. The dispatcher takes the single-owner backend lock, re-reads the gateway
    and Cline inputs at the effect boundary, flushes an in-flight marker and sends exactly once. A failure after
    the request was written is an *unknown* outcome: it is recorded as such, the lock record stays ambiguous and
    nothing is retried or re-routed (a provably unsent request frees the lock). Operators clear an ambiguous
    record with ``autoresearcher_lock.reconcile``.
    """
    check = should_fallback_to_cline(plat)
    if not check["should_fallback"]:
        return {
            "ok": False,
            "fallback_active": False,
            "output": f"ClinePass AutoResearcher fallback is not active: {check['reason']}",
        }

    lock = _arl.BackendLock(BACKEND_LOCK_WIN if _is_windows(plat) else BACKEND_LOCK_MAC, resource="local-backend")
    try:
        lock.acquire()
    except _arl.LockRefused as exc:
        return {"ok": False, "fallback_active": True, "lock_state": exc.state,
                "output": f"backend lock {exc.state}: {exc.reason}"}
    except Exception as exc:  # the lock layer failed (permissions, sharing violation): refuse, never send
        return {"ok": False, "fallback_active": True, "lock_state": "refused",
                "output": f"backend lock could not be taken: {type(exc).__name__}: {exc}"}

    try:
        lock.recheck(lambda: _effect_boundary_ok(plat))
    except _arl.LockRefused as exc:
        release_error = _release_reporting(lock, "not-sent")
        return {"ok": False, "fallback_active": True, "lock_state": exc.state, "release_error": release_error,
                "output": f"effect-boundary recheck refused the send: {exc.reason}"}
    except Exception as exc:  # a probe raised: nothing was sent, so free the lock instead of leaving it held
        release_error = _release_reporting(lock, "not-sent")
        return {"ok": False, "fallback_active": True, "outcome": "not-sent", "lock_state": "refused",
                "release_error": release_error,
                "output": f"effect-boundary recheck failed; nothing was sent: {type(exc).__name__}: {exc}"}

    try:
        lock.mark_inflight()
    except Exception as exc:  # the marker could not be written, so nothing was sent
        release_error = _release_reporting(lock, "not-sent")
        return {"ok": False, "fallback_active": True, "outcome": "not-sent", "release_error": release_error,
                "output": f"in-flight marker could not be written; nothing was sent: {exc}"}
    try:
        attempt = dispatch_cline(task, plat)
    except Exception as exc:  # after the marker the request may have been sent: hold it, never free it
        release_error = _release_reporting(lock, "unknown")
        return {"ok": False, "fallback_active": True, "fallback_tier": "local-backend", "outcome": "unknown",
                "release_error": release_error,
                "output": f"dispatch raised after the in-flight marker: {exc}"}
    outcome = attempt.get("outcome") or ("completed" if attempt.get("ok") else "unknown")
    release_error = _release_reporting(lock, outcome if outcome in ("completed", "not-sent") else "unknown")
    return {
        "ok": bool(attempt.get("ok")),
        "fallback_active": True,
        "fallback_tier": "local-backend",
        "outcome": outcome,
        "output": attempt.get("output", ""),
        "elapsed": attempt.get("elapsed"),
        "release_error": release_error,
    }


# ── Peer session (co-orchestration resilience) ────────────────────────────────

def peer_session_status() -> Dict[str, Any]:
    """Return the LAN peer session state from lan_peer_session.py, or an unknown placeholder on any failure."""
    if not _LAN_PEER_SESSION.exists():
        return {"ok": False, "mode": "unknown", "failure_count": 0, "max_failures": 10}
    try:
        proc = subprocess.run(
            [sys.executable, str(_LAN_PEER_SESSION), "status"],
            capture_output=True, text=True, timeout=10,
        )
        return json.loads(proc.stdout)
    except Exception:
        return {"ok": False, "mode": "unknown", "failure_count": 0, "max_failures": 10}


# ── Full status ────────────────────────────────────────────────────────────────

def full_status(plat: Optional[str] = None) -> Dict[str, Any]:
    """Return the fallback decision, the peer session and solo-mode flags with a UTC timestamp."""
    plat = plat or detect_platform()
    check = should_fallback_to_cline(plat)
    peer = peer_session_status()
    now = time.time()
    solo_mode = peer.get("mode", "").endswith("-only")
    return {
        "platform": plat,
        "timestamp": now,
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "autoresearcher": check,
        "peer_session": peer,
        "solo_mode": solo_mode,
        "peer_unreachable_count": peer.get("failure_count", 0),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: Optional[list] = None) -> int:
    """Parse the command line, run the check, status or dispatch, print the result and return the exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=["windows", "macos"], default=None)
    parser.add_argument("--check", action="store_true", help="Check whether fallback should be active")
    parser.add_argument("--status", action="store_true", help="Full status incl. peer session")
    parser.add_argument("--dispatch", action="store_true", help="Dispatch a task via ClinePass fallback")
    parser.add_argument("--task", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    plat = args.platform or detect_platform()

    if args.dispatch:
        if not args.task:
            print("ERROR: --dispatch requires --task", file=sys.stderr)
            return 2
        result = dispatch_autoresearcher(plat, args.task)
    elif args.status:
        result = full_status(plat)
    else:
        result = should_fallback_to_cline(plat)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(result)
    return 0 if result.get("ok", True) or result.get("should_fallback") is not None else 1


if __name__ == "__main__":
    sys.exit(main())
