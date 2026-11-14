#!/usr/bin/env python3
"""Launch Cline 3.0.74 on W&B Inference with the 2026-11-12 defaults, without touching ~/.cline.

Usage:
  launch_cline_wandb.py [--model ID] [--effort LEVEL] [--timeout-ms N] [--env-file PATH] -- <prompt or cline args...>

Defaults (live-verified 2026-11-12, see docs/stale-reference-ledger-2026-11-12.md):
  model   deepseek-ai/DeepSeek-V4.1-Flash-1017
  effort  high   (W&B rejects `medium` on the V4.1 models with HTTP 400; V4-Flash-0731 accepts it)
  timeout 30000 ms
Rule (operator): effort is medium, else high, else low; never xhigh or max. Anything else is refused.
Model fallback order if one is rejected or missing: V4.1-Flash-1017 -> V4.1-Flash -> V4-Flash-0731
(pass --model). The bare deepseek-ai/DeepSeek-V4-Flash id is dead (404) and W&B serves no
`deepseek-flash` alias (404).

How it works: builds a throwaway 0600 config directory (0700) holding only the openai-compatible
entry, runs `cline --config <dir> -P openai-compatible -m <model> --thinking <effort> ...` and
deletes the directory afterwards. The key is read from DEEPSEEK_V4_FLASH_WANDB (or the local env
file) and is never printed or put in argv; the operator's real Cline directory is never touched.

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
from datetime import datetime, timezone
from typing import Sequence

KEYVAR = "DEEPSEEK_V4_FLASH_WANDB"
DEFAULT_ENV_FILE = "~/.openclaw/.env.wandb-deepseek"
BASE_URL = "https://api.inference.wandb.ai/v1"
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4.1-Flash-1017"
EFFORTS = ("medium", "high", "low")  # never xhigh or max
DEFAULT_TIMEOUT_MS = 30000


def cline_timestamp() -> str:
    """Return the current time the way Cline writes it: UTC, milliseconds, trailing Z."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def read_key(env_file: str = DEFAULT_ENV_FILE) -> str:
    """Return the W&B key from the environment or the local env file; exit without echoing it."""
    key = os.environ.get(KEYVAR, "")
    path = os.path.expanduser(env_file)
    if not key and os.path.exists(path):
        with open(path) as handle:
            for line in handle:
                match = re.match(rf"\s*(?:export\s+)?{KEYVAR}=(.*)", line)
                if match:
                    key = match.group(1).strip().strip("'\"")
    if not key:
        sys.exit(f"ERROR: {KEYVAR} is not set (environment or {env_file})")
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


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """Parse launcher options; everything after -- (or the first positional) goes to cline."""
    parser = argparse.ArgumentParser(description="Run Cline on W&B Inference with the 2026-11-12 defaults.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--effort", default="high", choices=EFFORTS)
    parser.add_argument("--timeout-ms", type=int, default=DEFAULT_TIMEOUT_MS)
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE)
    parser.add_argument("rest", nargs=argparse.REMAINDER, help="after --: the prompt or cline arguments")
    args = parser.parse_args(list(argv))
    args.rest = args.rest[1:] if args.rest[:1] == ["--"] else args.rest
    if not args.rest:
        parser.error("give a prompt or cline arguments after --")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    """Run cline against a throwaway config and return its exit code."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    key = read_key(args.env_file)
    config_dir = tempfile.mkdtemp(prefix="clinecfg-")
    os.chmod(config_dir, 0o700)
    try:
        settings_dir = os.path.join(config_dir, "data", "settings")
        os.makedirs(settings_dir)
        fd = os.open(os.path.join(settings_dir, "providers.json"), os.O_WRONLY | os.O_CREAT, 0o600)
        with os.fdopen(fd, "w") as handle:
            json.dump(build_config(key, args.model, args.effort, args.timeout_ms), handle)
        cmd = ["cline", "--config", config_dir, "-P", "openai-compatible", "-m", args.model,
               "--thinking", args.effort, *args.rest]
        return subprocess.run(cmd, stdin=subprocess.DEVNULL).returncode
    finally:
        shutil.rmtree(config_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
