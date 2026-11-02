#!/usr/bin/env python3
"""Run Cursor and OpenClaw dispatch candidates, keeping the first success."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parents[4]
_SRC_ROOT = _REPO_ROOT / "src"
if _SRC_ROOT.is_dir() and str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from orama_system.lan_peer_files import lan_peer_state_dir  # noqa: E402
from utils.win_exec import (  # noqa: E402
    CONTAINMENT_SCOPE_NOTE,
    WinExecError,
    resolve_executable,
    safe_argv,
    launch_tree,
    terminate_tree,
)


@dataclass(frozen=True)
class Candidate:
    name: str
    command: list[str]


def dispatch_state_dir() -> Path:
    return lan_peer_state_dir() / "dispatch"


def build_prompt(agent_card: str, role: str, job_id: str) -> str:
    return (
        f"Follow {agent_card} - execute ONE {role} job ({job_id}) from "
        "mac_job_queue / inbox. PT learn+dream, push main, and drop to Win peer if needed."
    )


def openclaw_agent_for_role(role: str) -> str:
    if role == "researcher":
        return os.environ.get("OPENCLAW_MAC_RESEARCHER_AGENT", "mac-researcher")
    return os.environ.get("OPENCLAW_MAC_ORCHESTRATOR_AGENT", "orchestrator")


def _resolve_or_none(name: str) -> str | None:
    """Absolute path of ``name`` via the shared resolver (never cwd, never a bare name), else None."""
    try:
        return resolve_executable(name)
    except WinExecError:
        return None


def build_candidates(prompt: str, role: str) -> list[Candidate]:
    """Build dispatch candidates from CLIs resolved to absolute paths; unresolvable CLIs are skipped."""
    candidates: list[Candidate] = []
    cursor = _resolve_or_none(os.environ.get("CURSOR_AGENT_BIN", "cursor-agent"))
    if cursor:
        candidates.append(
            Candidate(
                "cursor-agent",
                [
                    cursor,
                    "--print",
                    "--trust",          # non-interactive workspace trust gate
                    "--model",
                    os.environ.get("CURSOR_AGENT_MODEL", "composer-2.5"),
                    prompt,
                ],
            )
        )

    # openclaw uses: openclaw agent --agent <agent-id> -m <prompt>
    # (not 'openclaw run' which does not exist in OpenClaw 2026.6.x)
    openclaw = _resolve_or_none(os.environ.get("OPENCLAW_BIN", "openclaw"))
    if openclaw:
        candidates.append(
            Candidate(
                "openclaw",
                [
                    openclaw,
                    "agent",
                    "--agent",
                    openclaw_agent_for_role(role),
                    "-m",
                    prompt,
                ],
            )
        )
    return candidates


def _terminate(process: subprocess.Popen[str]) -> str:
    """Kill the candidate's whole process tree and return its containment status."""
    return terminate_tree(process, grace=5.0)


def run_candidates(candidates: list[Candidate], log_dir: Path, timeout: int) -> dict[str, Any]:
    """Run candidates in parallel, keep the first success and tree-kill the rest, reporting containment."""
    if not candidates:
        return {"status": "error", "reason": "no dispatch candidates available", "winner": None, "attempts": []}

    log_dir.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    running: dict[str, tuple[Candidate, subprocess.Popen[str], Any, Path]] = {}
    attempts: list[dict[str, Any]] = []
    containment: dict[str, str] = {}

    for candidate in candidates:
        log_path = log_dir / f"{candidate.name}.log"
        handle = log_path.open("w", encoding="utf-8")
        handle.write(f"$ {' '.join(candidate.command[:-1])} <prompt>\n")
        handle.flush()
        # stdin=DEVNULL: candidates run detached/non-interactive in parallel;
        # an inherited-but-unfed stdin can leave a CLI (e.g. Codex) blocked
        # on "Reading additional input..." forever instead of using the
        # prompt already in candidate.command. See dispatch_codex_partner.py.
        try:
            argv = safe_argv(candidate.command[0], candidate.command[1:])
        except WinExecError as exc:
            handle.write(f"refused: {exc}" + chr(10))
            handle.close()
            attempts.append({"name": candidate.name, "returncode": "refused", "log": str(log_path), "error": str(exc)})
            continue
        proc = launch_tree(
            argv,
            stdout=handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
        )
        running[candidate.name] = (candidate, proc, handle, log_path)

    winner: dict[str, Any] | None = None
    try:
        while running and time.monotonic() < deadline:
            for name, (candidate, proc, handle, log_path) in list(running.items()):
                rc = proc.poll()
                if rc is None:
                    continue
                handle.close()
                # Root exited: kill any orphan it left in the job (bounded lifetime).
                containment[name] = _terminate(proc)
                attempts.append(
                    {
                        "name": candidate.name,
                        "returncode": rc,
                        "log": str(log_path),
                    }
                )
                del running[name]
                if rc == 0:
                    winner = attempts[-1]
                    for other_name, (_, other_proc, other_handle, _) in running.items():
                        containment[other_name] = _terminate(other_proc)
                        other_handle.close()
                    running.clear()
                    break
            if winner:
                break
            time.sleep(0.2)
    finally:
        for name, (_, proc, handle, _) in running.items():
            containment[name] = _terminate(proc)
            handle.close()

    if winner:
        return {"status": "ok", "winner": winner, "attempts": attempts, "containment": containment,
                "containment_note": CONTAINMENT_SCOPE_NOTE}

    if running:
        attempts.extend(
            {
                "name": candidate.name,
                "returncode": "timeout",
                "log": str(log_path),
                "containment": containment.get(candidate.name, "unknown"),
            }
            for candidate, _proc, _handle, log_path in running.values()
        )
        return {"status": "error", "reason": f"dispatch timed out after {timeout}s {CONTAINMENT_SCOPE_NOTE}", "winner": None, "attempts": attempts, "containment": containment}
    return {"status": "error", "reason": "all dispatch candidates failed", "winner": None, "attempts": attempts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", required=True, choices=("orchestrator", "researcher"))
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--agent-card", required=True)
    parser.add_argument("--timeout", type=int, default=int(os.environ.get("DUAL_DISPATCH_TIMEOUT", "900")))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    prompt = build_prompt(args.agent_card, args.role, args.job_id)
    candidates = build_candidates(prompt, args.role)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    log_dir = dispatch_state_dir() / f"{stamp}-{args.job_id}"

    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "dry-run",
                    "prompt": prompt,
                    "candidates": [{"name": c.name, "command": c.command[:-1] + ["<prompt>"]} for c in candidates],
                    "log_dir": str(log_dir),
                },
                indent=2,
            )
        )
        return 0

    result = run_candidates(candidates, log_dir, args.timeout)
    result.update({"job_id": args.job_id, "role": args.role, "log_dir": str(log_dir)})
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
