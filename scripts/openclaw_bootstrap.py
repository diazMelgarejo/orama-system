#!/usr/bin/env python3
from __future__ import annotations

"""
openclaw_bootstrap.py — orama-system delegation shim
----------------------------------------------------------
Bootstrap logic has moved to Perpetua-Tools/alphaclaw_bootstrap.py.

This shim delegates to the canonical PT script via PT_HOME env var,
falling back to the inline logic below only when PT is not found.

Set PT_HOME to the root of your Perpetua-Tools checkout:
    export PT_HOME=/path/to/Perpetua-Tools

Usage:
    python openclaw_bootstrap.py --bootstrap              # never changes openclaw.json; prints the proposal
    python openclaw_bootstrap.py --bootstrap --write      # creates it when absent
    python openclaw_bootstrap.py --bootstrap --force --write   # replaces it, keeping a backup

The inline fallback builds openclaw.json from the OpenClaw defaults (live Perpetua-Tools file, else the stamped
vendored copy, else it fails closed). Secrets are referenced by environment variable name, never copied.
"""
import argparse
import asyncio
import importlib.util
import json
import os
import secrets
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# ── delegation ────────────────────────────────────────────────────────────────

_PT_HOME    = Path(os.getenv("PT_HOME", str(Path.home() / "Perpetua-Tools")))
_PT_SCRIPT  = _PT_HOME / "alphaclaw_bootstrap.py"


async def bootstrap_openclaw(force: bool = False, write: bool = False) -> bool:
    """Delegate to PT's alphaclaw_bootstrap.py, fallback to inline logic."""
    if _PT_SCRIPT.exists():
        print(f"[openclaw] → Delegating to PT bootstrap: {_PT_SCRIPT}")
        extra = (["--force"] if force else []) + (["--write"] if write else [])
        result = subprocess.run(
            [sys.executable, str(_PT_SCRIPT), "--bootstrap"] + extra,
            env={**os.environ, "UTS_HOME": str(SCRIPT_DIR)},
        )
        return result.returncode == 0

    print("[openclaw] ⚠  PT_HOME not found "
          f"({_PT_HOME}) — running inline fallback")
    return await _bootstrap_inline(force=force, write=write)


# ── inline fallback (kept for UTS standalone use without PT) ──────────────────

def _parse_port_list(raw: str) -> list[int]:
    """Parse comma-separated port env vars; skip invalid tokens instead of crashing."""
    ports: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            port = int(token)
        except ValueError:
            print(f"[openclaw] ⚠  Ignoring invalid port in OPENCLAW_EXTRA_PORTS: {token!r}")
            continue
        if 1 <= port <= 65535:
            ports.append(port)
        else:
            print(f"[openclaw] ⚠  Ignoring out-of-range port: {port}")
    return ports


def _parse_single_port(raw: str, *, default: int, env_name: str) -> int:
    try:
        port = int(raw)
    except ValueError:
        print(f"[openclaw] ⚠  Invalid {env_name}: {raw!r}; using {default}")
        return default
    if not 1 <= port <= 65535:
        print(f"[openclaw] ⚠  Out-of-range {env_name}: {port}; using {default}")
        return default
    return port


OPENCLAW_GATEWAY_PORT: int = _parse_single_port(
    os.getenv("OPENCLAW_GATEWAY_PORT", "18789"),
    default=18789,
    env_name="OPENCLAW_GATEWAY_PORT",
)
_extra_ports = _parse_port_list(os.getenv("OPENCLAW_EXTRA_PORTS", ""))
OPENCLAW_CANDIDATE_PORTS: list[int] = list(dict.fromkeys(
    [OPENCLAW_GATEWAY_PORT, 11435, 8080, 3000, 4000, 9000] + _extra_ports
))

# Autoresearch — env-var configurable (mirrors PT's alphaclaw_bootstrap.py)
AUTORESEARCH_REMOTE = os.getenv(
    "AUTORESEARCH_REMOTE", "https://github.com/uditgoenka/autoresearch"
)


async def _probe_url(url: str, client) -> bool:
    for path in ("/health", "/v1/models"):
        try:
            r = await client.get(f"{url.rstrip('/')}{path}")
            if r.status_code < 400:
                return True
        except Exception:
            pass
    return False


async def _find_any_gateway() -> str | None:
    try:
        import httpx
    except ImportError:
        return None
    async with httpx.AsyncClient(timeout=1.5) as client:
        for port in OPENCLAW_CANDIDATE_PORTS:
            url = f"http://localhost:{port}"
            if await _probe_url(url, client):
                return url
    return None


class DefaultsUnavailable(RuntimeError):
    """The OpenClaw defaults cannot be read from Perpetua-Tools or the vendored copy."""


def _resolve_defaults():
    """The resolved OpenClaw defaults: live Perpetua-Tools file, else the stamped vendored copy."""
    name = "openclaw_defaults_resolver_bootstrap"
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / "lib" / "openclaw_defaults_resolver.py")
    resolver = importlib.util.module_from_spec(spec)
    sys.modules[name] = resolver
    spec.loader.exec_module(resolver)
    try:
        return resolver.resolve()
    except resolver.DefaultsUnavailable as exc:
        raise DefaultsUnavailable(str(exc)) from exc


def _proposed_config(resolution, shape: str) -> dict:
    """A complete config: the rendered defaults patch plus the local gateway section."""
    config = resolution.module.render_patch(resolution.data, shape=shape)
    gateway = resolution.data["baseline"]["gateway"]
    config["gateway"] = {"mode": "local", "port": OPENCLAW_GATEWAY_PORT, "bind": gateway["bind"]}
    if os.getenv("XAI_API_KEY", "").strip():
        config["models"]["providers"]["xai"] = {
            "baseUrl": "https://api.x.ai/v1",
            "apiKey": {"source": "env", "provider": "default", "id": "XAI_API_KEY"},
            "api": "openai-completions",
            "models": [
                {"id": "grok-4.1-fast", "name": "Grok 4.1 Fast"},
                {"id": "grok-code-fast", "name": "Grok Code Fast"},
            ],
        }
    return config


def _write_openclaw_config(config_dir: Path, config_file: Path, write: bool = False, shape: str = "entries") -> bool:
    """Propose openclaw.json from the defaults; write it only when `write` is set. True if a file was written."""
    try:
        resolution = _resolve_defaults()
    except DefaultsUnavailable as exc:
        print(f"[openclaw] ✗ {exc}; openclaw.json not touched")
        return False
    for warning in resolution.warnings:
        print(f"[openclaw] ⚠ OpenClaw defaults: {warning}")
    text = json.dumps(_proposed_config(resolution, shape), indent=2) + "\n"
    if not write:
        print(f"[openclaw] proposed openclaw.json from the {resolution.source} defaults (nothing written):")
        print(text, end="")
        print(f"[openclaw] review it, then re-run with --write to write {config_file}")
        return False
    config_dir.mkdir(parents=True, exist_ok=True)
    if config_file.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = config_file.with_name(f"{config_file.name}.before-bootstrap-{stamp}")
        shutil.copy2(config_file, backup)
        backup.chmod(0o600)
        print(f"[openclaw] ✓ previous config kept → {backup}")
    staged = config_file.with_name(f".{config_file.name}.new-{os.getpid()}")
    fd = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(staged, config_file)
    print(f"[openclaw] ✓ openclaw.json written → {config_file}")
    return True


def _ensure_agent_workspaces(config_dir: Path) -> None:
    soul_src   = SCRIPT_DIR / "bin" / "agents"
    agents_dir = config_dir / "agents"
    roles = ["mac-researcher", "win-researcher", "orchestrator",
             "coder", "autoresearcher"]
    for role in roles:
        role_dir = agents_dir / role
        role_dir.mkdir(parents=True, exist_ok=True)
        soul_file = role_dir / "SOUL.md"
        if soul_file.exists():
            continue
        src = soul_src / role / "SOUL.md"
        if src.exists():
            shutil.copy(src, soul_file)
            print(f"[openclaw] ✓ agent workspace: {role}")
        else:
            print(f"[openclaw] ⚠ missing SOUL.md for {role}")


def _ensure_autoresearch() -> None:
    """Idempotent clone + uv sync --dev of ~/autoresearch (uditgoenka/autoresearch)."""
    repo = Path.home() / "autoresearch"
    if repo.exists():
        print("[openclaw] ✓ ~/autoresearch already exists")
        return
    print(f"[openclaw] → Cloning {AUTORESEARCH_REMOTE}…")
    try:
        subprocess.run(["git", "clone", AUTORESEARCH_REMOTE, str(repo)],
                       check=True)
        import datetime
        branch = f"autoresearch/{datetime.date.today().isoformat()}"
        subprocess.run(["git", "checkout", "-b", branch], cwd=repo, check=True)
        result = subprocess.run(["pip", "install", "uv"], check=False, capture_output=False)
        if result.returncode != 0:
            logger.error("pip install uv failed with exit code %d", result.returncode)
        subprocess.run(["uv", "sync", "--dev"], cwd=repo, check=True)
        print("[openclaw] ✓ autoresearch ready")
    except subprocess.CalledProcessError as e:
        print(f"[openclaw] ✗ autoresearch setup failed (non-fatal): {e}")


async def _bootstrap_inline(force: bool = False, write: bool = False) -> bool:
    """Inline fallback when PT is unavailable."""
    try:
        import httpx  # noqa: F401
    except ImportError:
        print("[openclaw] ✗ httpx not installed — run: pip install httpx")
        return False

    config_dir  = Path.home() / ".openclaw"
    config_file = config_dir / "openclaw.json"

    print(f"[openclaw] → Probing {len(OPENCLAW_CANDIDATE_PORTS)} candidate ports…")
    existing_url = await _find_any_gateway()
    if existing_url:
        print(f"[openclaw] ✓ Found gateway at {existing_url} — commandeering")
        os.environ["OPENCLAW_GATEWAY_URL"] = existing_url
        if not config_file.exists() or force:
            _write_openclaw_config(config_dir, config_file, write=write)
        _ensure_agent_workspaces(config_dir)
        _ensure_autoresearch()
        return True

    if not shutil.which("npm"):
        print("[openclaw] ✗ npm not found — install Node.js from https://nodejs.org/")
        return False

    _aclaw_installed = shutil.which("alphaclaw") is not None
    if not _aclaw_installed:
        install_dir = Path.home() / ".alphaclaw"
        install_dir.mkdir(parents=True, exist_ok=True)
        print("[openclaw] → Installing @chrysb/alphaclaw…")
        try:
            subprocess.run(["npm", "install", "@chrysb/alphaclaw"],
                           check=True, cwd=str(install_dir))
        except subprocess.CalledProcessError as e:
            print(f"[openclaw] ✗ install failed: {e}")
            return False

    if not config_file.exists() or force:
        _write_openclaw_config(config_dir, config_file, write=write)
    if not config_file.exists():
        print("[openclaw] ✗ there is no openclaw.json, so the gateway is not started")
        return False
    _ensure_agent_workspaces(config_dir)

    print("[openclaw] → Starting AlphaClaw gateway…")
    try:
        install_dir = Path.home() / ".alphaclaw"
        setup_password = os.getenv("SETUP_PASSWORD", "").strip()
        insecure_dev = os.getenv("ORAMA_INSECURE_DEV", "").strip().lower() in ("1", "true", "yes")
        if not setup_password:
            if insecure_dev:
                setup_password = secrets.token_urlsafe(16)
                once_path = install_dir / ".setup-password-once"
                once_path.write_text(f"{setup_password}\n", encoding="utf-8")
                once_path.chmod(0o600)
                print(
                    "[openclaw] ORAMA_INSECURE_DEV=1 — generated one-time SETUP_PASSWORD; "
                    f"read once from {once_path} (not logged)."
                )
            else:
                print(
                    "[openclaw] Refusing fallback bootstrap without SETUP_PASSWORD. "
                    "Set SETUP_PASSWORD or ORAMA_INSECURE_DEV=1 for local-only dev."
                )
                return False
        env = {**os.environ, "SETUP_PASSWORD": setup_password}
        subprocess.Popen(["npx", "alphaclaw", "start"], cwd=str(install_dir), env=env)
        gateway_url = f"http://localhost:{OPENCLAW_GATEWAY_PORT}"
        os.environ["OPENCLAW_GATEWAY_URL"] = gateway_url
    except Exception as e:
        print(f"[openclaw] ✗ gateway start failed: {e}")
        return False

    _ensure_autoresearch()
    return True


# ── PT payload applier ───────────────────────────────────────────────────────

def apply_runtime_payload(payload: dict, force: bool = False, write: bool = False) -> dict:
    """Write the PT-resolved openclaw_config to ~/.openclaw/openclaw.json.

    This is the programmatic entry point when a PT runtime payload dict is
    already available in memory (e.g. from an orchestrator call or test).
    The delegation path in bootstrap_openclaw() is for CLI/subprocess use.

    Args:
        payload: PT runtime payload dict containing gateway.openclaw_config.
        force: If True, overwrite even if the file already matches.
        write: Required to change the file; without it the difference is only reported.

    Returns:
        Status dict with gateway_ready, topology, applied, config_path, gateway_url.
    """
    openclaw_config = payload.get("gateway", {}).get("openclaw_config")
    if not openclaw_config:
        raise ValueError("PT runtime payload does not contain gateway.openclaw_config")

    config_dir = Path.home() / ".openclaw"
    config_file = config_dir / "openclaw.json"

    existing: dict = {}
    if config_file.exists():
        try:
            existing = json.loads(config_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    if not write:
        state = "differs from" if existing != openclaw_config else "matches"
        print(f"[openclaw] PT payload {state} {config_file}; nothing written (write=True applies it)")
        return {
            "applied": False,
            "config_path": str(config_file),
            "gateway_ready": bool(payload.get("gateway", {}).get("gateway_ready")),
            "gateway_url": payload.get("gateway", {}).get("gateway_url"),
            "topology": payload.get("role_routing", {}).get("topology"),
        }
    config_dir.mkdir(parents=True, exist_ok=True)
    if force or existing != openclaw_config:
        config_file.write_text(json.dumps(openclaw_config, indent=2), encoding="utf-8")
        print(f"[openclaw] applied PT-resolved config -> {config_file}")
    else:
        print(f"[openclaw] config already matches PT payload -> {config_file}")

    _ensure_agent_workspaces(config_dir)
    return {
        "applied": True,
        "config_path": str(config_file),
        "gateway_ready": bool(payload.get("gateway", {}).get("gateway_ready")),
        "gateway_url": payload.get("gateway", {}).get("gateway_url"),
        "topology": payload.get("role_routing", {}).get("topology"),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="orama-system OpenClaw/AlphaClaw bootstrap shim",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Delegates to Perpetua-Tools/alphaclaw_bootstrap.py when PT_HOME is set.\n"
            "Falls back to inline logic if PT is unavailable.\n\n"
            "Set PT_HOME to your Perpetua-Tools checkout root:\n"
            "  export PT_HOME=/path/to/Perpetua-Tools\n"
        ),
    )
    parser.add_argument("--bootstrap", action="store_true",
                        help="Idempotent AlphaClaw install + configure + start")
    parser.add_argument("--force", action="store_true",
                        help="Propose a new openclaw.json even if one exists")
    parser.add_argument("--write", action="store_true",
                        help="Write the proposed openclaw.json (a backup of the old one is kept)")
    return parser


if __name__ == "__main__":
    parser = build_parser()
    _args = parser.parse_args()

    if _args.bootstrap:
        ok = asyncio.run(bootstrap_openclaw(force=_args.force, write=_args.write))
        sys.exit(0 if ok else 1)
    else:
        parser.print_help()
        sys.exit(1)
