#!/usr/bin/env python3
"""Run Cursor and OpenClaw dispatch candidates, keeping the first success."""
from __future__ import annotations

import argparse
import json
import os
import shutil
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


def build_candidates(prompt: str, role: str) -> list[Candidate]:
    candidates: list[Candidate] = []
    cursor = shutil.which(os.environ.get("CURSOR_AGENT_BIN", "cursor-agent"))
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
    openclaw = shutil.which(os.environ.get("OPENCLAW_BIN", "openclaw"))
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


def _terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_candidates(candidates: list[Candidate], log_dir: Path, timeout: int) -> dict[str, Any]:
    if not candidates:
        return {"status": "error", "reason": "no dispatch candidates available", "winner": None, "attempts": []}

    log_dir.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    running: dict[str, tuple[Candidate, subprocess.Popen[str], Any, Path]] = {}
    attempts: list[dict[str, Any]] = []

    for candidate in candidates:
        log_path = log_dir / f"{candidate.name}.log"
        handle = log_path.open("w", encoding="utf-8")
        handle.write(f"$ {' '.join(candidate.command[:-1])} <prompt>\n")
        handle.flush()
        proc = subprocess.Popen(
            candidate.command,
            stdout=handle,
            stderr=subprocess.STDOUT,
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
                    for _, other_proc, other_handle, _ in running.values():
                        _terminate(other_proc)
                        other_handle.close()
                    running.clear()
                    break
            if winner:
                break
            time.sleep(0.2)
    finally:
        for _, proc, handle, _ in running.values():
            _terminate(proc)
            handle.close()

    if winner:
        return {"status": "ok", "winner": winner, "attempts": attempts}

    if running:
        attempts.extend(
            {
                "name": candidate.name,
                "returncode": "timeout",
                "log": str(log_path),
            }
            for candidate, _proc, _handle, log_path in running.values()
        )
        return {"status": "error", "reason": f"dispatch timed out after {timeout}s", "winner": None, "attempts": attempts}
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
