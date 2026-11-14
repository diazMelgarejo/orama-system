#!/usr/bin/env python3
"""One W&B chat completion for Wanda.

The process environment must already contain the shell-sourced variables
DEEPSEEK_V4_FLASH_WANDB and DEEPSEEK_V4_FLASH_WANDB_PROJECT. This script
does not read the env file itself.

reasoning_effort is always sent explicitly. Qualified values are medium, then
high, then low. xhigh and max are never used and never inherited from a
provider default.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any

LOGGER = logging.getLogger("wanda_chat")

# Preference order is encoded in each tuple: first entry is the default.
QUALIFIED_EFFORTS: dict[str, tuple[str, ...]] = {
    "deepseek-ai/DeepSeek-V4.1-Flash-1017": ("high",),
    "deepseek-ai/DeepSeek-V4.1-Flash": ("high",),
    "deepseek-ai/DeepSeek-V4-Flash-0731": ("medium", "high", "low"),
}
ALLOWED_EFFORTS = frozenset({"medium", "high", "low"})
BANNED_EFFORTS = frozenset({"xhigh", "max"})


def _log_failure(kind: str, exc: BaseException) -> None:
    """Log an expected client failure without the exception text, which can echo a request."""
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.ERROR, format="%(levelname)s %(name)s: %(message)s")
    status = getattr(exc, "status_code", None)
    suffix = f" HTTP {status}" if isinstance(status, int) else ""
    LOGGER.error("%s failed: %s%s", kind, type(exc).__name__, suffix)


def _attr(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def resolve_effort(model: str, requested: str | None) -> str | None:
    """Return the effort to send, or None when the request must be refused."""
    if requested in BANNED_EFFORTS:
        return None
    qualified = QUALIFIED_EFFORTS.get(model)
    if qualified is None:
        if requested in ALLOWED_EFFORTS:
            return requested
        return None
    if requested is None:
        return qualified[0]
    if requested in qualified:
        return requested
    return None


def _refuse_effort(model: str, requested: str | None) -> int:
    print(
        f"unsupported reasoning_effort {requested!r} for model {model}",
        file=sys.stderr,
    )
    return 2


def _completion_text(response: Any) -> tuple[str | None, str | None, int | None]:
    """Return (finish_reason, content, exit_on_garbage).

    Garbage (empty choices, missing message, non-mapping payload) yields
    (None, None, 1). Callers must not traceback.
    """
    try:
        choices = _attr(response, "choices")
        if not choices:
            return None, None, 1
        choice = choices[0]
        message = _attr(choice, "message")
        if message is None:
            return None, None, 1
        finish_reason = _attr(choice, "finish_reason")
        content = _attr(message, "content")
        text = "" if content is None else str(content).strip()
        if not isinstance(finish_reason, str):
            return None, None, 1
        return finish_reason, text, None
    except Exception:
        return None, None, 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wanda W&B chat completion")
    parser.add_argument("prompt", help="User message. Do not include secrets.")
    parser.add_argument(
        "--model",
        default="deepseek-ai/DeepSeek-V4.1-Flash-1017",
        help="W&B model id that returns text on this route",
    )
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument(
        "--effort",
        default=None,
        help="Explicit reasoning_effort: medium, high, or low. Never xhigh or max.",
    )
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

    effort = resolve_effort(args.model, args.effort)
    if effort is None:
        return _refuse_effort(args.model, args.effort)

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
            reasoning_effort=effort,
        )
    except openai.APIError as exc:
        _log_failure("chat completion", exc)
        return 1

    finish_reason, text, garbage = _completion_text(response)
    if garbage is not None:
        print("Wanda returned an unusable completion", file=sys.stderr)
        return garbage
    if finish_reason == "length":
        print("INCOMPLETE: finish_reason=length")
        print(text)
        return 3
    if finish_reason != "stop" or not text:
        print("Wanda returned no text", file=sys.stderr)
        return 1
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
