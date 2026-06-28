#!/usr/bin/env python3
"""verify_partner_canaries.py — run the hermes-harness partner canary table.

Checks: LM Studio /v1/models, Hermes one-shot, AGY one-shot, Codex version.
Prints a PASS/FAIL/UNAVAILABLE summary and exits 0 only when all required
canaries pass.

Usage:
    python verify_partner_canaries.py [--lm-studio-url URL] [--timeout SECS]
    python verify_partner_canaries.py --skip-hermes --skip-agy  # CI / no-auth
    python verify_partner_canaries.py --tail-lmstudio-logs  # last ~30 lines of newest server log

Required canaries:  LM Studio, Hermes
Optional canaries:  AGY, Codex  (degrade gracefully when not installed)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from enum import Enum

HERMES_CANARY_MODEL = "stepfun/step-3.7-flash:free"
LM_STUDIO_LOG_HINT = os.path.expanduser("~/.lmstudio/server-logs")
from pathlib import Path


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNAVAILABLE = "UNAVAILABLE"
    SKIPPED = "SKIPPED"


@dataclass
class Result:
    name: str
    status: Status
    detail: str = ""
    required: bool = True


def lmstudio_server_logs_dir() -> Path:
    """Cross-platform LM Studio server log root (~/.lmstudio/server-logs)."""
    return Path.home() / ".lmstudio" / "server-logs"


def newest_lmstudio_log_file(logs_dir: Path | None = None) -> Path | None:
    base = logs_dir if logs_dir is not None else lmstudio_server_logs_dir()
    if not base.is_dir():
        return None
    candidates = [p for p in base.rglob("*.log") if p.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def tail_lmstudio_logs(lines: int = 30, logs_dir: Path | None = None) -> tuple[str, str]:
    """Return (tail_text, error). error is empty on success."""
    base = logs_dir if logs_dir is not None else lmstudio_server_logs_dir()
    log_file = newest_lmstudio_log_file(base)
    if log_file is None:
        return "", f"no log files under {base}"
    try:
        content = log_file.read_text(encoding="utf-8", errors="replace")
        tail = content.splitlines()[-lines:]
        header = f"--- {log_file} (last {len(tail)} lines) ---"
        return header + "\n" + "\n".join(tail), ""
    except OSError as exc:
        return "", str(exc)


def _lmstudio_fail_detail(detail: str) -> str:
    logs = lmstudio_server_logs_dir()
    return (
        f"{detail} — check LM Studio server logs at {logs} "
        f"(or: verify_partner_canaries.py --tail-lmstudio-logs)"
    )


def _trunc(text: str, limit: int = 80) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timed out"
    except (FileNotFoundError, PermissionError):
        return -2, "", f"{cmd[0]!r} not found on PATH"


def _run_partner(name: str, args: list[str], timeout: int = 30) -> tuple[int, str, str]:
    exe = _resolve_partner_cli(name)
    if not exe:
        return -2, "", f"{name!r} not found on PATH"
    return _run([exe, *args], timeout=timeout)


def _loaded_lmstudio_chat_model(base: str, timeout: int) -> tuple[str, int]:
    """Return (model_id, catalog_count) for the one loaded chat model, if any."""
    root = base.rstrip("/").removesuffix("/v1")
    v0_url = root + "/api/v0/models"
    try:
        resp = urllib.request.urlopen(v0_url, timeout=timeout)
        data = json.loads(resp.read())
        rows = data.get("data", data if isinstance(data, list) else [])
        catalog = len(rows)
        for row in rows:
            if not isinstance(row, dict):
                continue
            if row.get("state") != "loaded":
                continue
            if row.get("type") in ("embeddings", "embedding"):
                continue
            mid = row.get("id", "")
            if mid:
                return mid, catalog
    except Exception:
        pass

    # Fallback: OpenAI-compatible list (may include not-loaded catalog entries).
    try:
        resp = urllib.request.urlopen(root + "/v1/models", timeout=timeout)
        models = json.loads(resp.read()).get("data", [])
        catalog = len(models)
        for row in models:
            mid = row.get("id", "")
            low = mid.lower()
            if mid and "embed" not in low:
                return mid, catalog
    except Exception:
        pass
    return "", 0


def _lm_completion_timeout(model_id: str, base_timeout: int) -> int:
    """Reasoning / large models need more time for LM_READY."""
    low = model_id.lower()
    if any(k in low for k in ("reasoning", "distilled", "27b", "26b")):
        return max(base_timeout, 180)
    return max(base_timeout, 60)


def check_lm_studio(base_url: str, timeout: int) -> Result:
    base = base_url.rstrip("/").removesuffix("/v1")
    model_id, count = _loaded_lmstudio_chat_model(base, timeout)
    if not model_id:
        return Result("LM Studio", Status.FAIL, _lmstudio_fail_detail("no loaded chat model (one model at a time)"))

    completion_timeout = _lm_completion_timeout(model_id, timeout)
    max_tokens = 512 if "reasoning" in model_id.lower() or "distilled" in model_id.lower() else 64

    payload = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": "Reply with exactly: LM_READY"}],
        "max_tokens": max_tokens,
        "temperature": 0,
    }).encode()
    req2 = urllib.request.Request(
        base + "/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp2 = urllib.request.urlopen(req2, timeout=completion_timeout)
        reply = json.loads(resp2.read())
        msg = reply.get("choices", [{}])[0].get("message", {})
        text = msg.get("content") or msg.get("reasoning_content") or ""
        if "LM_READY" not in text:
            return Result(
                "LM Studio",
                Status.FAIL,
                _lmstudio_fail_detail(
                    f"loaded={model_id!r} readiness marker missing ({text.strip()[:40]!r})"
                ),
            )
        return Result(
            "LM Studio",
            Status.PASS,
            f"loaded={model_id}; completion ok ({text.strip()[:40]!r})",
        )
    except urllib.error.URLError as e:
        return Result(
            "LM Studio",
            Status.FAIL,
            _lmstudio_fail_detail(f"loaded={model_id!r} completion failed: {e}"),
        )
    except Exception as e:
        return Result(
            "LM Studio",
            Status.FAIL,
            _lmstudio_fail_detail(f"loaded={model_id!r} completion failed: {e}"),
        )


def check_hermes(timeout: int) -> Result:
    if not _resolve_partner_cli("hermes"):
        return Result("Hermes", Status.UNAVAILABLE, "hermes not on PATH", required=True)
    rc, out, err = _run_partner(
        "hermes",
        [
            "chat",
            "--query", "Reply with exactly: HERMES_READY",
            "--quiet", "--safe-mode",
            "--provider", "nous",
            "--model", HERMES_CANARY_MODEL,
            "--max-turns", "1",
        ],
        timeout=timeout,
    )
    if "HERMES_READY" in out or "HERMES_READY" in err:
        return Result("Hermes", Status.PASS, "HERMES_READY received")
    if rc == -2:
        return Result("Hermes", Status.UNAVAILABLE, err, required=True)
    return Result(
        "Hermes",
        Status.FAIL,
        f"rc={rc} out={_trunc(out)!r} err={_trunc(err)!r}",
        required=True,
    )


def check_agy(timeout: int) -> Result:
    if not _resolve_partner_cli("agy"):
        return Result("AGY", Status.UNAVAILABLE, "agy not on PATH", required=False)
    rc, out, err = _run_partner("agy", ["--print", "Reply with exactly: AGY_READY"], timeout=max(timeout, 120))
    if rc == 0 and "AGY_READY" in out:
        return Result("AGY", Status.PASS, "AGY_READY received", required=False)
    if rc == 0 and not out:
        return Result("AGY", Status.UNAVAILABLE, "empty stdout — likely quota exhausted", required=False)
    if rc in (-1, -2):
        return Result("AGY", Status.UNAVAILABLE, err or "timed out", required=False)
    return Result("AGY", Status.UNAVAILABLE, f"rc={rc} out={_trunc(out)!r}", required=False)


def check_codex(timeout: int) -> Result:
    if not _resolve_partner_cli("codex"):
        return Result("Codex", Status.UNAVAILABLE, "codex not on PATH", required=False)
    rc, out, err = _run_partner("codex", ["--version"], timeout=timeout)
    if rc == 0 and (out or err):
        line = (out or err).splitlines()[0]
        return Result("Codex", Status.PASS, line, required=False)
    if rc in (-1, -2):
        return Result("Codex", Status.UNAVAILABLE, err or "timed out", required=False)
    return Result("Codex", Status.UNAVAILABLE, f"rc={rc}", required=False)


def check_cursor_agent(timeout: int) -> Result:
    if not _resolve_partner_cli("cursor-agent"):
        return Result("cursor-agent", Status.UNAVAILABLE, "cursor-agent not on PATH", required=False)
    rc, out, err = _run_partner("cursor-agent", ["--version"], timeout=timeout)
    if rc == 0 and (out or err):
        line = (out or err).splitlines()[0]
        return Result("cursor-agent", Status.PASS, line, required=False)
    if rc in (-1, -2):
        return Result("cursor-agent", Status.UNAVAILABLE, err or "timed out", required=False)
    return Result("cursor-agent", Status.UNAVAILABLE, f"rc={rc}", required=False)


def _windows_partner_dirs() -> list[Path]:
    local = os.environ.get("LOCALAPPDATA", "")
    home = Path.home()
    return [
        # WinGet / native OpenAI Codex before LM Studio npm shim (same binary family; native updates cleanly).
        Path(local) / "Programs" / "OpenAI" / "Codex" / "bin",
        home / ".lmstudio" / "bin",
        Path(local) / "cursor-agent",
        Path(local) / "agy" / "bin",
        Path(local) / "hermes" / "hermes-agent" / "venv" / "Scripts",
        Path(local) / "hermes" / "bin",
    ]


def _partner_cli_in_dir(base: Path, name: str) -> str | None:
    for ext in (".exe", ".cmd", ".ps1", ".bat"):
        candidate = base / f"{name}{ext}"
        if candidate.is_file():
            return str(candidate)
    nested = list(base.glob(f"**/versions/*/{name}.cmd"))
    if nested:
        return str(nested[0])
    nested = list(base.glob(f"**/versions/*/{name}.ps1"))
    if nested:
        return str(nested[0])
    return None


def _resolve_partner_cli(name: str) -> str | None:
    """Resolve partner CLI on PATH; on Windows also find .cmd/.ps1 shims."""
    if sys.platform == "win32":
        for base in _windows_partner_dirs():
            if not base.is_dir():
                continue
            hit = _partner_cli_in_dir(base, name)
            if hit:
                return hit
    found = shutil.which(name)
    if found:
        return found
    return None


def _ensure_windows_partner_path() -> None:
    """Prepend known partner CLI dirs so subprocess canaries work in fresh sessions."""
    if sys.platform != "win32":
        return
    prepend = os.pathsep.join(str(p) for p in _windows_partner_dirs() if p.is_dir())
    if prepend:
        os.environ["PATH"] = prepend + os.pathsep + os.environ.get("PATH", "")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lm-studio-url", default="http://localhost:1234/v1")
    p.add_argument("--timeout", type=int, default=90, help="Per-canary timeout in seconds (Hermes/AGY/Codex)")
    p.add_argument("--skip-hermes", action="store_true")
    p.add_argument("--skip-agy", action="store_true")
    p.add_argument("--skip-codex", action="store_true")
    p.add_argument("--skip-cursor-agent", action="store_true")
    p.add_argument("--json", dest="json_out", action="store_true", help="Emit JSON summary to stdout")
    p.add_argument(
        "--prepare",
        action="store_true",
        help="Offline prep: print Win localhost runtime checklist; skip live probes",
    )
    p.add_argument(
        "--tail-lmstudio-logs",
        action="store_true",
        help="Print last ~30 lines from newest file under ~/.lmstudio/server-logs",
    )
    args = p.parse_args()

    if not args.prepare and not args.tail_lmstudio_logs:
        _ensure_windows_partner_path()

    if args.tail_lmstudio_logs:
        text, err = tail_lmstudio_logs()
        if err:
            print(f"LM Studio server logs: {err}", file=sys.stderr)
            return 1
        print(text)
        return 0

    if args.prepare:
        checklist = [
            "1. PowerShell UTF-8 bootstrap — run first:",
            "   bin\\orama-system\\skills\\git-history-surgery\\references\\windows-powershell-runtime-bootstrap.md",
            "2. Verify env vars resolve: $env:PERPETUA_TOOLS_PATH  $env:ORAMA_SYSTEM_PATH",
            "3. LM Studio listening on http://localhost:1234 (own-machine locality — NOT LAN IP when on Win)",
            "4. Hermes on PATH; HERMES_GIT_BASH_PATH set for Git Bash lane",
            "5. Run canary probe (repo-relative, any cwd):",
            "   cd $env:ORAMA_SYSTEM_PATH",
            "   python bin\\orama-system\\skills\\hermes-harness\\scripts\\verify_partner_canaries.py --lm-studio-url http://localhost:1234/v1",
            "   Optional: add --skip-hermes --skip-agy when those lanes are intentionally absent",
            "6. Install + verify + test thin wrappers (Phase 9):",
            "   python bin\\orama-system\\skills\\hermes-harness\\scripts\\install_hermes_thin_skills.py --install",
            "   python bin\\orama-system\\skills\\hermes-harness\\scripts\\install_hermes_thin_skills.py --verify",
            "   python bin\\orama-system\\skills\\hermes-harness\\scripts\\install_hermes_thin_skills.py --test",
            "Full reference: bin\\orama-system\\skills\\hermes-harness\\references\\win-localhost-runtime-checklist.md",
        ]
        if args.json_out:
            print(json.dumps({"prepare": True, "checklist": checklist}, indent=2))
        else:
            print("Hermes harness — offline prepare (no live probes)")
            for i, line in enumerate(checklist, 1):
                print(f"  {i}. {line}")
        return 0

    results: list[Result] = []
    results.append(check_lm_studio(args.lm_studio_url, args.timeout))
    if not args.skip_hermes:
        results.append(check_hermes(args.timeout))
    else:
        results.append(Result("Hermes", Status.SKIPPED, "--skip-hermes"))
    if not args.skip_agy:
        results.append(check_agy(args.timeout))
    else:
        results.append(Result("AGY", Status.SKIPPED, "--skip-agy", required=False))
    if not args.skip_codex:
        results.append(check_codex(args.timeout))
    else:
        results.append(Result("Codex", Status.SKIPPED, "--skip-codex", required=False))
    if not args.skip_cursor_agent:
        results.append(check_cursor_agent(args.timeout))
    else:
        results.append(Result("cursor-agent", Status.SKIPPED, "--skip-cursor-agent", required=False))

    if args.json_out:
        summary = [{"name": r.name, "status": r.status.value, "detail": r.detail, "required": r.required} for r in results]
        print(json.dumps({"canaries": summary}, indent=2))
    else:
        width = max(len(r.name) for r in results) + 2
        for r in results:
            flag = " (required)" if r.required else ""
            print(f"  {r.name:<{width}} {r.status.value:<14} {r.detail}{flag}")

    required_failures = [r for r in results if r.required and r.status not in (Status.PASS, Status.SKIPPED)]
    if required_failures:
        if not args.json_out:
            print(f"\nFAIL — {len(required_failures)} required canary/canaries did not pass")
        return 1
    if not args.json_out:
        passed = sum(1 for r in results if r.status == Status.PASS)
        print(f"\nOK — {passed}/{len(results)} canaries passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
