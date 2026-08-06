#!/usr/bin/env python3
"""Read-only Hermes health rollup (hermes-status --json)."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

APPENDIX_C_STUBS = (
    "task_api",
    "fleet_manager",
    "verifier_gate",
    "scheduler",
    "observability_transport",
    "recursive_workers",
    "hitl_approval",
)


def _canonical_result(
    *,
    status: str,
    data: dict[str, Any],
    follow_up_actions: list[str] | None = None,
    warnings: list[str] | None = None,
    error: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "skill_id": "hermes-status",
        "agent_id": "hermes",
        "executor_id": "hermes",
        "command": "hermes-status",
        "action": "rollup",
        "data": data,
        "files_modified": [],
        "follow_up_actions": follow_up_actions or [],
        "warnings": warnings or [],
        "error": error,
    }


def _run(cmd: list[str], *, timeout: int = 120, cwd: Path | None = None) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timed out"
    except OSError as exc:
        return -2, "", str(exc)


def check_pt_root(repo_root: Path) -> tuple[str, dict[str, Any]]:
    resolve_sh = Path(__file__).with_name("resolve_perp_harness.sh")
    rc, out, err = _run(
        ["bash", "-c", 'source "$1"; resolve_pt_root', "bash", str(resolve_sh)],
        timeout=30,
        cwd=repo_root,
    )
    if rc == 0 and out:
        return "ok", {"path": out.splitlines()[-1]}
    return "error", {"detail": err or out or "PT root not resolved"}


def check_spawn_session(repo_root: Path) -> tuple[str, dict[str, Any]]:
    spawn_sh = repo_root / "bin/orama-system/skills/hermes-harness/scripts/hermes_spawn.sh"
    rc, out, err = _run(["bash", str(spawn_sh), "--json", "status"], timeout=60)
    if not out:
        return "degraded", {"detail": err or "no spawn status output", "running": False}
    try:
        payload = json.loads(out)
    except json.JSONDecodeError:
        return "degraded", {"detail": "spawn status returned non-JSON", "raw": out[:200]}
    running = bool(payload.get("data", {}).get("running"))
    if payload.get("status") == "ok" and running:
        return "ok", payload.get("data", {})
    if payload.get("status") == "ok":
        return "ok", payload.get("data", {"running": False})
    return "degraded", {"detail": payload.get("error"), "running": running}


def check_partner_canaries(
    repo_root: Path,
    *,
    skip_live: bool,
    canary_timeout: int,
) -> tuple[str, dict[str, Any], list[str]]:
    warnings: list[str] = []
    if skip_live:
        warnings.append("partner canaries skipped (--skip-canaries)")
        return "degraded", {"skipped": True}, warnings

    script = repo_root / "bin/orama-system/skills/hermes-harness/scripts/verify_partner_canaries.py"
    cmd = [
        sys.executable,
        str(script),
        "--json",
        "--skip-hermes",
        "--skip-agy",
        "--skip-codex",
        "--skip-cursor-agent",
        "--timeout",
        str(canary_timeout),
    ]
    rc, out, err = _run(cmd, timeout=canary_timeout + 30)
    if not out:
        return "degraded", {"detail": err or "no canary output"}, warnings
    try:
        payload = json.loads(out)
    except json.JSONDecodeError:
        return "degraded", {"detail": "canary script returned non-JSON"}, warnings

    canaries = payload.get("canaries", [])
    required_fail = [
        c for c in canaries if c.get("required") and c.get("status") not in ("PASS", "SKIPPED")
    ]
    if required_fail:
        warnings.append(f"{len(required_fail)} required canary/canaries failed")
        return "degraded", {"canaries": canaries}, warnings
    if rc != 0:
        return "degraded", {"canaries": canaries}, warnings
    return "ok", {"canaries": canaries}, warnings


def check_profiles() -> tuple[str, dict[str, Any], list[str]]:
    warnings: list[str] = []
    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    profiles_dir = hermes_home / "profiles"
    if profiles_dir.is_dir() and any(profiles_dir.iterdir()):
        return "ok", {"profiles_dir": str(profiles_dir), "count": len(list(profiles_dir.iterdir()))}, warnings
    rc, out, err = _run(["hermes", "profile", "list"], timeout=15)
    if rc == 0 and out.strip():
        return "ok", {"source": "hermes profile list", "lines": len(out.splitlines())}, warnings
    warnings.append("profiles not materialized; run install_hermes_profiles.py --install")
    return "degraded", {"detail": err or "no profiles found"}, warnings


def build_status(
    repo_root: Path,
    *,
    skip_canaries: bool = False,
    canary_timeout: int = 30,
) -> dict[str, Any]:
    subsystems: dict[str, str] = {}
    details: dict[str, Any] = {}
    warnings: list[str] = []
    follow_up: list[str] = []

    pt_state, pt_data = check_pt_root(repo_root)
    subsystems["pt_root"] = pt_state
    details["pt_root"] = pt_data
    if pt_state != "ok":
        follow_up.append("set PERPETUA_TOOLS_ROOT or clone Perpetua-Tools")

    spawn_state, spawn_data = check_spawn_session(repo_root)
    subsystems["spawn_session"] = spawn_state
    details["spawn_session"] = spawn_data

    canary_state, canary_data, canary_warnings = check_partner_canaries(
        repo_root, skip_live=skip_canaries, canary_timeout=canary_timeout
    )
    subsystems["partner_canaries"] = canary_state
    details["partner_canaries"] = canary_data
    warnings.extend(canary_warnings)

    profile_state, profile_data, profile_warnings = check_profiles()
    subsystems["profiles"] = profile_state
    details["profiles"] = profile_data
    warnings.extend(profile_warnings)

    for stub in APPENDIX_C_STUBS:
        subsystems[stub] = "not_yet_implemented"
        details[stub] = {"deferred": "v2.1++"}

    implemented = {k: v for k, v in subsystems.items() if v != "not_yet_implemented"}
    if any(v == "error" for v in implemented.values()):
        top_status = "error"
        error = {"code": "hermes_status_subsystem_error", "message": "required subsystem check failed"}
    elif any(v == "degraded" for v in implemented.values()):
        top_status = "partial"
        error = None
        follow_up.append("inspect degraded subsystems in data.subsystems")
    elif all(v == "ok" for v in implemented.values()):
        top_status = "ok"
        error = None
    else:
        top_status = "partial"
        error = None

    return _canonical_result(
        status=top_status,
        data={"subsystems": subsystems, "details": details},
        follow_up_actions=follow_up,
        warnings=warnings,
        error=error,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", dest="json_out", action="store_true")
    parser.add_argument("--skip-canaries", action="store_true", help="Skip live canary probes")
    parser.add_argument("--canary-timeout", type=int, default=30)
    parser.add_argument("--repo-root", default="")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root or os.environ.get("REPO_ROOT", ".")).resolve()
    try:
        top = subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        repo_root = Path(top)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass

    result = build_status(
        repo_root,
        skip_canaries=args.skip_canaries,
        canary_timeout=args.canary_timeout,
    )
    if args.json_out:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result["data"]["subsystems"], indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
