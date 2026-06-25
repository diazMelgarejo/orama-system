#!/usr/bin/env python3
"""verify_partner_canaries.py — run the hermes-harness partner canary table.

Checks: LM Studio /v1/models, Hermes one-shot, AGY one-shot, Codex version.
Prints a PASS/FAIL/UNAVAILABLE summary and exits 0 only when all required
canaries pass.

Usage:
    python verify_partner_canaries.py [--lm-studio-url URL] [--timeout SECS]
    python verify_partner_canaries.py --skip-hermes --skip-agy  # CI / no-auth

Required canaries:  LM Studio, Hermes
Optional canaries:  AGY, Codex  (degrade gracefully when not installed)
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from enum import Enum


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


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timed out"
    except (FileNotFoundError, PermissionError):
        return -2, "", f"{cmd[0]!r} not found on PATH"


def check_lm_studio(base_url: str, timeout: int) -> Result:
    base = base_url.rstrip("/").removesuffix("/v1")
    models_url = base + "/v1/models"
    try:
        resp = urllib.request.urlopen(models_url, timeout=timeout)
        data = json.loads(resp.read())
        models = data.get("data", [])
        count = len(models)
        if count == 0:
            return Result("LM Studio", Status.FAIL, "no models loaded")
    except urllib.error.URLError as e:
        return Result("LM Studio", Status.FAIL, str(e))
    except Exception as e:
        return Result("LM Studio", Status.FAIL, str(e))

    # Completion probe: /v1/models only confirms LM Studio is up; this verifies
    # inference actually works. Expected round-trip: <15 s per Hermes SLA.
    model_id = models[0].get("id", "") if models else ""
    payload = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": "Reply with exactly: LM_READY"}],
        "max_tokens": 10,
        "temperature": 0,
    }).encode()
    req2 = urllib.request.Request(
        base + "/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp2 = urllib.request.urlopen(req2, timeout=timeout)
        reply = json.loads(resp2.read())
        text = reply.get("choices", [{}])[0].get("message", {}).get("content", "")
        return Result("LM Studio", Status.PASS, f"{count} model(s); completion ok ({text.strip()[:30]!r})")
    except urllib.error.URLError as e:
        return Result("LM Studio", Status.FAIL, f"{count} model(s) listed but completion failed: {e}")
    except Exception as e:
        return Result("LM Studio", Status.FAIL, f"{count} model(s) listed but completion failed: {e}")


def check_hermes(timeout: int) -> Result:
    if not shutil.which("hermes"):
        return Result("Hermes", Status.UNAVAILABLE, "hermes not on PATH", required=True)
    rc, out, err = _run(
        [
            "hermes", "chat",
            "--query", "Reply with exactly: HERMES_READY",
            "--quiet", "--safe-mode",
            "--provider", "nous",
            "--model", "nvidia/nemotron-3-ultra:free",
            "--max-turns", "1",
        ],
        timeout=timeout,
    )
    if rc == 0 and "HERMES_READY" in out:
        return Result("Hermes", Status.PASS, "HERMES_READY received")
    if rc == -2:
        return Result("Hermes", Status.UNAVAILABLE, err, required=True)
    return Result("Hermes", Status.FAIL, f"rc={rc} out={out!r:.80} err={err!r:.80}", required=True)


def check_agy(timeout: int) -> Result:
    if not shutil.which("agy"):
        return Result("AGY", Status.UNAVAILABLE, "agy not on PATH", required=False)
    rc, out, err = _run(["agy", "--print", "Reply with exactly: AGY_READY"], timeout=timeout)
    if rc == 0 and "AGY_READY" in out:
        return Result("AGY", Status.PASS, "AGY_READY received", required=False)
    if rc == 0 and not out:
        return Result("AGY", Status.UNAVAILABLE, "empty stdout — likely quota exhausted", required=False)
    if rc == -2:
        return Result("AGY", Status.UNAVAILABLE, err, required=False)
    return Result("AGY", Status.FAIL, f"rc={rc} out={out!r:.80}", required=False)


def check_codex(timeout: int) -> Result:
    if not shutil.which("codex"):
        return Result("Codex", Status.UNAVAILABLE, "codex not on PATH", required=False)
    rc, out, _ = _run(["codex", "--version"], timeout=timeout)
    if rc == 0 and out:
        return Result("Codex", Status.PASS, out.splitlines()[0], required=False)
    return Result("Codex", Status.FAIL, f"rc={rc}", required=False)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lm-studio-url", default="http://localhost:1234/v1")
    p.add_argument("--timeout", type=int, default=30, help="Per-canary timeout in seconds")
    p.add_argument("--skip-hermes", action="store_true")
    p.add_argument("--skip-agy", action="store_true")
    p.add_argument("--skip-codex", action="store_true")
    p.add_argument("--json", dest="json_out", action="store_true", help="Emit JSON summary to stdout")
    args = p.parse_args()

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
