"""Check ClinePass wrapper command construction without invoking a model."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_wrapper_pins_model_argument(tmp_path: Path) -> None:
    """A stub CLI records the model actually passed by the wrapper."""
    cli = tmp_path / "cline"
    args_file = tmp_path / "args"
    cli.write_text(
        '#!/bin/sh\nif [ "$1" = "--help" ]; then echo "--auto-approve-all --reasoning-effort"; '
        'else printf "%s\\n" "$@" > "$ARGS_FILE"; fi\n',
        encoding="utf-8",
    )
    cli.chmod(0o755)
    wrapper = Path(__file__).resolve().parents[1] / (
        "bin/orama-system/skills/clinepass-deepseek-flash/scripts/run_clinepass_deepseek_flash.sh"
    )
    subprocess.run(
        [str(wrapper), "--plan", "test prompt"],
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "ARGS_FILE": str(args_file)},
        check=True,
    )
    args = args_file.read_text(encoding="utf-8").splitlines()
    assert args[args.index("-m") + 1] == "cline-pass/deepseek-v4.1-flash-1017"
