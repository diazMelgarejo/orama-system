#!/usr/bin/env python3
"""One W&B chat completion for Wanda.

The process environment must already contain the shell-sourced variables
DEEPSEEK_V4_FLASH_WANDB and DEEPSEEK_V4_FLASH_WANDB_PROJECT. This script
does not read the env file itself.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

LOGGER = logging.getLogger("wanda_chat")


def _log_failure(kind: str, exc: BaseException) -> None:
    """Log an expected client failure without the exception text, which can echo a request."""
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.ERROR, format="%(levelname)s %(name)s: %(message)s")
    status = getattr(exc, "status_code", None)
    suffix = f" HTTP {status}" if isinstance(status, int) else ""
    LOGGER.error("%s failed: %s%s", kind, type(exc).__name__, suffix)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wanda W&B chat completion")
    parser.add_argument("prompt", help="User message. Do not include secrets.")
    parser.add_argument(
        "--model",
        default="deepseek-ai/DeepSeek-V4.1-Flash-1017",
        help="W&B model id that returns text on this route",
    )
    parser.add_argument("--max-tokens", type=int, default=1024)
    args = parser.parse_args(argv)

    key = os.environ.get("DEEPSEEK_V4_FLASH_WANDB", "")
    project = os.environ.get("DEEPSEEK_V4_FLASH_WANDB_PROJECT", "")
    if not key or not project:
        print(
            "DEEPSEEK_V4_FLASH_WANDB and DEEPSEEK_V4_FLASH_WANDB_PROJECT must be "
            "shell-sourced in this process",
            file=sys.stderr,
        )
        return 2

    try:
        import openai
        import weave
    except ImportError as exc:
        _log_failure("client import", exc)
        return 1

    try:
        weave.init(project)
    except Exception as exc:
        _log_failure("tracing initialization", exc)
        return 1
    client = openai.OpenAI(
        base_url="https://api.inference.wandb.ai/v1",
        api_key=key,
        project=project,
    )
    try:
        response = client.chat.completions.create(
            model=args.model,
            messages=[{"role": "user", "content": args.prompt}],
            max_tokens=args.max_tokens,
        )
    except openai.APIError as exc:
        _log_failure("chat completion", exc)
        return 1
    text = (response.choices[0].message.content or "").strip()
    if not text:
        print("Wanda returned no text", file=sys.stderr)
        return 1
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
