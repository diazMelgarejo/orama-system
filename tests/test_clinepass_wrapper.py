"""Check ClinePass wrapper command construction without invoking a model."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_wrapper_pins_provider_model_and_effort(tmp_path: Path) -> None:
    """A stub CLI records the explicitly selected provider, model, and effort."""
    cli = tmp_path / "cline"
    args_file = tmp_path / "args"
    cli.write_text(
        '#!/bin/sh\nif [ "$1" = "--help" ]; then echo "--auto-approve-all --provider --thinking"; '
        'else printf "%s\\n" "$@" > "$ARGS_FILE"; fi\n',
        encoding="utf-8",
    )
    cli.chmod(0o755)
    wrapper = Path(__file__).resolve().parents[1] / (
        "bin/orama-system/skills/clinepass-deepseek-flash/scripts/run_clinepass_deepseek_flash.sh"
    )
    subprocess.run(
        [str(wrapper), "--plan", "test prompt"],
        env={**os.environ, "CLINE_BIN": str(cli), "ARGS_FILE": str(args_file)},
        check=True,
    )
    args = args_file.read_text(encoding="utf-8").splitlines()
    assert args[args.index("-P") + 1] == "cline-pass"
    assert args[args.index("-m") + 1] == "cline-pass/deepseek-v4.1-flash-1017"
    assert args[args.index("--thinking") + 1] == "medium"


def test_wrapper_refuses_cli_without_provider_support(tmp_path: Path) -> None:
    """An unsupported CLI cannot receive a task through a default provider."""
    cli = tmp_path / "cline"
    marker = tmp_path / "dispatched"
    cli.write_text(
        '#!/bin/sh\nif [ "$1" = "--help" ]; then echo "--thinking"; '
        'else touch "$MARKER"; fi\n', encoding="utf-8"
    )
    cli.chmod(0o755)
    wrapper = Path(__file__).resolve().parents[1] / (
        "bin/orama-system/skills/clinepass-deepseek-flash/scripts/run_clinepass_deepseek_flash.sh"
    )
    result = subprocess.run(
        [str(wrapper), "test prompt"],
        env={**os.environ, "CLINE_BIN": str(cli), "MARKER": str(marker)},
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert not marker.exists()
