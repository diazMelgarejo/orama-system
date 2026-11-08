"""ClinePass wrapper must bind provider and model before sending a prompt."""
import os
import subprocess
from pathlib import Path

WRAPPER = Path(__file__).resolve().parents[1] / "bin/orama-system/skills/clinepass-deepseek-flash/scripts/run_clinepass_deepseek_flash.sh"


def test_dispatch_binds_provider_and_pinned_model(tmp_path):
    """Dispatch explicitly selects ClinePass and the pinned model."""
    cline = tmp_path / "cline"
    cline.write_text('#!/bin/bash\nif [[ "$1" == "--help" ]]; then echo "--provider --auto-approve --thinking"; else printf "%s\\n" "$@"; fi\n')
    cline.chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}
    result = subprocess.run(["bash", str(WRAPPER), "--cwd", str(tmp_path), "--plan", "test prompt"], env=env, text=True, capture_output=True, check=True)
    args = result.stdout.splitlines()
    assert args[args.index("--provider") + 1] == "cline-pass"
    assert args[args.index("-m") + 1] == "cline-pass/deepseek-v4.1-flash-1017"
    assert args[-1] == "test prompt"


def test_dispatch_fails_closed_if_provider_flag_unavailable(tmp_path):
    """Do not send a prompt when the CLI cannot select a provider."""
    cline = tmp_path / "cline"
    cline.write_text('#!/bin/bash\nif [[ "$1" == "--help" ]]; then echo "--thinking"; else echo PROMPT_SENT; fi\n')
    cline.chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}
    result = subprocess.run(["bash", str(WRAPPER), "test prompt"], env=env, text=True, capture_output=True)
    assert result.returncode != 0
    assert "PROMPT_SENT" not in result.stdout
