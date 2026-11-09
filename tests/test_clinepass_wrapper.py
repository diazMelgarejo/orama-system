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
        '#!/bin/sh\nif [ "$1" = "--help" ]; then echo "--auto-approve-all --provider --thinking medium"; '
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


def test_wrapper_refuses_missing_medium_or_approval(tmp_path: Path) -> None:
    """Incomplete capabilities must not fall through to a task invocation."""
    cli = tmp_path / "cline"
    marker = tmp_path / "dispatched"
    wrapper = Path(__file__).resolve().parents[1] / (
        "bin/orama-system/skills/clinepass-deepseek-flash/scripts/run_clinepass_deepseek_flash.sh"
    )
    for help_text in ("--provider --thinking low high --auto-approve-all", "--provider --thinking medium"):
        cli.write_text(
            '#!/bin/sh\nif [ "$1" = "--help" ]; then printf "%s\\n" "$HELP_TEXT"; '
            'else touch "$MARKER"; fi\n', encoding="utf-8"
        )
        cli.chmod(0o755)
        result = subprocess.run(
            [str(wrapper), "test prompt"],
            env={**os.environ, "CLINE_BIN": str(cli), "MARKER": str(marker), "HELP_TEXT": help_text},
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert not marker.exists()

WRAPPER = Path(__file__).resolve().parents[1] / "bin/orama-system/skills/clinepass-deepseek-flash/scripts/run_clinepass_deepseek_flash.sh"


def test_dispatch_binds_provider_and_pinned_model(tmp_path: Path) -> None:
    """Dispatch explicitly selects ClinePass and the pinned model."""
    cline = tmp_path / "cline"
    cline.write_text('#!/bin/bash\nif [[ "$1" == "--help" ]]; then echo "--provider --auto-approve true --thinking medium"; else printf "%s\\n" "$@"; fi\n')
    cline.chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}
    result = subprocess.run(["bash", str(WRAPPER), "--cwd", str(tmp_path), "--plan", "test prompt"], env=env, text=True, capture_output=True, check=True)
    args = result.stdout.splitlines()
    assert args[args.index("-P") + 1] == "cline-pass"
    assert args[args.index("-m") + 1] == "cline-pass/deepseek-v4.1-flash-1017"
    assert args[-1] == "test prompt"


def test_dispatch_fails_closed_if_provider_flag_unavailable(tmp_path: Path) -> None:
    """Do not send a prompt when the CLI cannot select a provider."""
    cline = tmp_path / "cline"
    cline.write_text('#!/bin/bash\nif [[ "$1" == "--help" ]]; then echo "--thinking"; else echo PROMPT_SENT; fi\n')
    cline.chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}
    result = subprocess.run(["bash", str(WRAPPER), "test prompt"], env=env, text=True, capture_output=True)
    assert result.returncode != 0
    assert "PROMPT_SENT" not in result.stdout
