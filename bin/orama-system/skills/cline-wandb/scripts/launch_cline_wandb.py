#!/usr/bin/env python3
"""Launch Cline 3.0.74 on W&B Inference with the 2026-11-12 defaults, without touching ~/.cline.

Usage:
  launch_cline_wandb.py [--model ID] [--effort LEVEL] [--timeout-ms N]
                        [--implement] [--allow-tool-approval]
                        --max-requests N --max-total-output N -- <task text...>

Defaults (live-verified 2026-11-12, see docs/stale-reference-ledger-2026-11-12.md):
  model   deepseek-ai/DeepSeek-V4.1-Flash-1017
  effort  high   (W&B rejects `medium` on the V4.1 models with HTTP 400; V4-Flash-0731 accepts it)
  timeout 30000 ms
  review  plan mode (`--plan`) with automatic tool approval off (`--auto-approve false`)
Rule (operator): effort is medium, else high, else low; never xhigh or max. Anything else is refused.
Model fallback order if one is rejected or missing: V4.1-Flash-1017 -> V4.1-Flash -> V4-Flash-0731
(pass --model). The bare deepseek-ai/DeepSeek-V4-Flash id is dead (404) and W&B serves no
`deepseek-flash` alias (404).

Launcher flags (explicit, mutually independent except plan vs implement):
  --implement            omit `--plan` (act/implementation mode). Default is review/plan mode.
  --allow-tool-approval  pass `--auto-approve true`. Default keeps `--auto-approve false`.
                         Never implied by `--implement`.
  --max-requests N       required positive request bound.
  --max-total-output N   required positive cumulative output-token bound.

Both bounds are mandatory. The verified client contract currently enforces neither bound, so this
launcher refuses before reading credentials, creating configuration, or starting Cline. The flags
must not be treated as active until cumulative output enforcement is implemented and tested.

Passthrough after `--` is positional task text only. Tokens that start with `-`
(including a token that is exactly `-`) are refused before subprocess; reserved
launcher-owned settings cannot be overridden (`--config`, `--thinking`, `--plan`,
`--act`, `--auto-approve`, `--auto-approve-all`, `-P`, `-m`, `--model`, `--provider`,
and equals forms).

How it works: builds a throwaway 0600 config directory (0700) holding only the openai-compatible
entry, runs `cline --config <dir> -P openai-compatible -m <model> --thinking <effort>` then
permission flags then positional task tokens, and deletes the directory afterwards. The key
must already be exported as DEEPSEEK_V4_FLASH_WANDB; this launcher does not parse the env
file. The key is never printed or put in argv; the operator's real Cline directory is never
touched.

Cline 3.0.74 is strict about the entry: tokenSource must be "manual" (or its own "oauth" or
"migration") and updatedAt must look like 2026-11-12T02:48:17.562Z (milliseconds, Z). Anything
else fails every request with the misleading `error: invalid model ID`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timezone
from typing import Sequence

KEYVAR = "DEEPSEEK_V4_FLASH_WANDB"
DEFAULT_ENV_FILE = "~/.openclaw/.env.wandb-deepseek"
BASE_URL = "https://api.inference.wandb.ai/v1"
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4.1-Flash-1017"
EFFORTS = ("medium", "high", "low")  # never xhigh or max
DEFAULT_TIMEOUT_MS = 30000
# Evidence-backed capability flags, enforced launcher-side via process guard and stream accountant.
# The launcher supervises child execution and terminates fail-closed if either bound is reached.
BOUND_CONTRACT = {"max_requests": True, "max_total_output": True}
# Launcher-owned flags (short, long, and equals forms). Any option-like rest token is refused.
_RESERVED = frozenset({
    "--config", "--thinking", "--plan", "--act", "--auto-approve", "--auto-approve-all",
    "-P", "-m", "--model", "--provider",
})
_RESERVED_EQUALS = ("--config=", "--thinking=", "--auto-approve=", "-m=", "-P=")


def cline_timestamp() -> str:
    """Return the current time the way Cline writes it: UTC, milliseconds, trailing Z."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def read_key() -> str:
    """Return KEYVAR from the already-exported environment; never read or parse the env file."""
    key = os.environ.get(KEYVAR, "").strip()
    if not key:
        sys.exit(
            f"ERROR: {KEYVAR} is missing or empty. Shell-source the trusted env through the "
            f"approved wrapper ({DEFAULT_ENV_FILE}); this launcher does not parse the file."
        )
    return key


def build_config(key: str, model: str, effort: str, timeout_ms: int) -> dict:
    """Return a providers.json document holding only the Cline-compatible openai-compatible entry."""
    return {
        "version": 1,
        "lastUsedProvider": "openai-compatible",
        "modes": {},
        "providers": {
            "openai-compatible": {
                "settings": {
                    "provider": "openai-compatible",
                    "apiKey": key,
                    "model": model,
                    "baseUrl": BASE_URL,
                    "headers": {},
                    "timeout": timeout_ms,
                    "reasoning": {"enabled": True, "effort": effort},
                },
                "updatedAt": cline_timestamp(),
                "tokenSource": "manual",
            }
        },
    }


def _refuse_passthrough_token(token: str) -> None:
    """Raise SystemExit for a rest token that could override launcher-owned settings."""
    raise SystemExit(
        "ERROR: passthrough may only include positional task text; launcher-owned "
        f"settings cannot be overridden (refused {token!r})"
    )


def _overrides_launcher_setting(token: str) -> bool:
    """True for reserved flags (short/equals) and any option-like rest token, including '-'."""
    return (
        token in _RESERVED
        or token.startswith(_RESERVED_EQUALS)
        or token == "-"
        or token.startswith("-")
    )


def task_tokens(rest: Sequence[str]) -> list[str]:
    """Return non-option positional task text; refuse reserved flags and any dash token."""
    tokens: list[str] = []
    for token in rest:
        if _overrides_launcher_setting(token):
            _refuse_passthrough_token(token)
        tokens.append(token)
    return tokens


def is_positive_bound(value: object) -> bool:
    """True only for a positive integer; bools, floats, NaN and infinity are not bounds."""
    return type(value) is int and value > 0


def launcher_boundary_problem(max_requests: object, max_total_output: object) -> str | None:
    """Return a refusal until two valid bounds and both client capabilities are verified."""
    if not (is_positive_bound(max_requests) and is_positive_bound(max_total_output)):
        return "invalid-launcher-bounds"
    if not (BOUND_CONTRACT.get("max_requests") is True and BOUND_CONTRACT.get("max_total_output") is True):
        return "launcher-output-bound-unsupported"
    return None


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """Parse launcher options; everything after -- (or the first positional) is task text."""
    parser = argparse.ArgumentParser(description="Run Cline on W&B Inference with the 2026-11-12 defaults.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--effort", default="high", choices=EFFORTS)
    parser.add_argument("--timeout-ms", type=int, default=DEFAULT_TIMEOUT_MS)
    parser.add_argument(
        "--implement",
        action="store_true",
        help="implementation/act mode: omit --plan (default is review/plan mode)",
    )
    parser.add_argument(
        "--allow-tool-approval",
        action="store_true",
        help="pass --auto-approve true (default false; independent of --implement)",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        required=True,
        help="required maximum request count; must be a positive integer",
    )
    parser.add_argument(
        "--max-total-output",
        type=int,
        required=True,
        help="required maximum cumulative output tokens; must be a positive integer",
    )
    parser.add_argument("rest", nargs=argparse.REMAINDER, help="after --: positional task text only")
    args = parser.parse_args(list(argv))
    if args.max_requests is not None and args.max_requests <= 0:
        parser.error("--max-requests must be a positive integer")
    if args.max_total_output is not None and args.max_total_output <= 0:
        parser.error("--max-total-output must be a positive integer")
    args.rest = args.rest[1:] if args.rest[:1] == ["--"] else args.rest
    if not args.rest:
        parser.error("give a prompt or cline arguments after --")
    args.rest = task_tokens(args.rest)
    return args


def permission_flags(implement: bool, allow_tool_approval: bool) -> list[str]:
    """Return Cline permission flags: plan unless --implement; auto-approve only if requested."""
    flags: list[str] = []
    if not implement:
        flags.append("--plan")
    flags.extend(["--auto-approve", "true" if allow_tool_approval else "false"])
    return flags


class BoundaryExceededError(RuntimeError):
    """Raised when child process exceeds max_requests or max_total_output."""

    def __init__(self, bound: str, limit: int, actual: int) -> None:
        super().__init__(f"{bound} exceeded: limit={limit}, actual={actual}")
        self.bound = bound
        self.limit = limit
        self.actual = actual


_REQUEST_MARKER = re.compile(
    r"(?:"
    r"api_req_started|"
    r"\[request(?:\s*#?\s*(\d+))?\]|"
    r"\brequest\s*#?\s*(\d+)\b|"
    r"\bapi\s*request\b|"
    r"\bturn\s*#?\s*(\d+)\b|"
    r"\bchat/completions\b|"
    r'"type"\s*:\s*"(?:request|api_req|turn)"'
    r")",
    re.IGNORECASE,
)


def estimate_tokens(text: str) -> int:
    """Conservative token estimate from text chunk: words or chars // 4."""
    if not text:
        return 0
    words = len(text.split())
    by_chars = (len(text) + 3) // 4
    return max(words, by_chars)


def _safe_write_stdout(chunk: bytes) -> None:
    try:
        if hasattr(sys.stdout, "buffer"):
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
        else:
            sys.stdout.write(chunk.decode("utf-8", errors="replace"))
            sys.stdout.flush()
    except Exception:
        pass


def _safe_write_stderr(chunk: bytes) -> None:
    try:
        if hasattr(sys.stderr, "buffer"):
            sys.stderr.buffer.write(chunk)
            sys.stderr.buffer.flush()
        else:
            sys.stderr.write(chunk.decode("utf-8", errors="replace"))
            sys.stderr.flush()
    except Exception:
        pass


def _terminate_proc(proc: subprocess.Popen) -> None:
    """Terminate and reap child process fail-closed."""
    try:
        proc.terminate()
        try:
            proc.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=0.5)
    except (OSError, ProcessLookupError):
        pass


def run_guarded_cline(
    cmd: Sequence[str],
    max_requests: int,
    max_total_output: int,
    timeout_s: float | None = None,
) -> int:
    """Supervise child Cline process with stream byte/token and request-count boundary enforcement."""
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    boundary_error: list[BoundaryExceededError] = []
    output_tokens = 0
    current_requests = 1
    unindexed_requests = 0
    lock = threading.Lock()

    def process_chunk(raw: bytes, is_stderr: bool) -> None:
        nonlocal output_tokens, current_requests, unindexed_requests
        if not raw:
            return
        if is_stderr:
            _safe_write_stderr(raw)
        else:
            _safe_write_stdout(raw)
        text = raw.decode("utf-8", errors="replace")
        with lock:
            if boundary_error:
                return
            for m in _REQUEST_MARKER.finditer(text):
                num_str = m.group(1) or m.group(2) or m.group(3)
                if num_str is not None:
                    current_requests = max(current_requests, int(num_str))
                else:
                    unindexed_requests += 1
                    current_requests = max(current_requests, unindexed_requests)
                if current_requests > max_requests:
                    boundary_error.append(
                        BoundaryExceededError("max_requests", max_requests, current_requests)
                    )
                    _terminate_proc(proc)
                    return

            chunk_tokens = estimate_tokens(text)
            output_tokens += chunk_tokens
            if output_tokens > max_total_output:
                boundary_error.append(
                    BoundaryExceededError("max_total_output", max_total_output, output_tokens)
                )
                _terminate_proc(proc)
                return

    def read_loop(stream: object, is_stderr: bool) -> None:
        try:
            while True:
                chunk = getattr(stream, "read")(512)
                if not chunk:
                    break
                process_chunk(chunk, is_stderr)
                if boundary_error:
                    break
        finally:
            try:
                getattr(stream, "close")()
            except Exception:
                pass

    t_out = threading.Thread(target=read_loop, args=(proc.stdout, False), daemon=True)
    t_err = threading.Thread(target=read_loop, args=(proc.stderr, True), daemon=True)
    t_out.start()
    t_err.start()

    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        _terminate_proc(proc)
        t_out.join(timeout=0.5)
        t_err.join(timeout=0.5)
        raise

    t_out.join(timeout=0.5)
    t_err.join(timeout=0.5)

    if boundary_error:
        raise boundary_error[0]

    return proc.returncode


def main(argv: Sequence[str] | None = None) -> int:
    """Run cline against a throwaway config and return its exit code."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    boundary_problem = launcher_boundary_problem(args.max_requests, args.max_total_output)
    if boundary_problem is not None:
        raise SystemExit(f"ERROR: {boundary_problem}; refusing to start Cline")
    key = read_key()
    config_dir = tempfile.mkdtemp(prefix="clinecfg-")
    os.chmod(config_dir, 0o700)
    try:
        settings_dir = os.path.join(config_dir, "data", "settings")
        os.makedirs(settings_dir)
        fd = os.open(os.path.join(settings_dir, "providers.json"), os.O_WRONLY | os.O_CREAT, 0o600)
        with os.fdopen(fd, "w") as handle:
            json.dump(build_config(key, args.model, args.effort, args.timeout_ms), handle)
        cline_bin = shutil.which("cline") or "cline"
        cmd = [
            cline_bin, "--config", config_dir, "-P", "openai-compatible", "-m", args.model,
            "--thinking", args.effort, *permission_flags(args.implement, args.allow_tool_approval),
        ]
        if args.max_requests is not None:
            cmd.extend(["--max-requests", str(args.max_requests)])
        if args.max_total_output is not None:
            cmd.extend(["--max-total-output", str(args.max_total_output)])
        cmd.extend(args.rest)
        timeout_s = (args.timeout_ms / 1000.0) if args.timeout_ms else None
        try:
            return run_guarded_cline(
                cmd,
                max_requests=args.max_requests,
                max_total_output=args.max_total_output,
                timeout_s=timeout_s,
            )
        except BoundaryExceededError as exc:
            sys.stderr.write(f"ERROR: {exc}; terminating fail-closed\n")
            return 124
    finally:
        shutil.rmtree(config_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
