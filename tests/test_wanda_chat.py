"""Wanda refuses to call W&B until the shell-sourced variables are present."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin/orama-system/skills/wanda-wandb/scripts/wanda_chat.py"


def test_wanda_chat_requires_sourced_env() -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("DEEPSEEK_V4_FLASH_WANDB")}
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "Reply with exactly PING"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "shell-sourced" in proc.stderr
    assert "DEEPSEEK_V4_FLASH_WANDB" not in proc.stdout
