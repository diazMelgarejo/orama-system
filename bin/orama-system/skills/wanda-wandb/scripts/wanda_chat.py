#!/usr/bin/env python3
"""One W&B chat completion for Wanda.

The process environment must already contain the shell-sourced variables
DEEPSEEK_V4_FLASH_WANDB and DEEPSEEK_V4_FLASH_WANDB_PROJECT. This script
does not read the env file itself.
"""

from __future__ import annotations

import argparse
import os
import sys


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

    import openai
    import weave

    weave.init(project)
    client = openai.OpenAI(
        base_url="https://api.inference.wandb.ai/v1",
        api_key=key,
        project=project,
    )
    response = client.chat.completions.create(
        model=args.model,
        messages=[{"role": "user", "content": args.prompt}],
        max_tokens=args.max_tokens,
    )
    text = (response.choices[0].message.content or "").strip()
    if not text:
        print("Wanda returned no text", file=sys.stderr)
        return 1
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
