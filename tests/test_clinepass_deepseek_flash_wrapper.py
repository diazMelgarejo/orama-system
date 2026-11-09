"""Assert the ClinePass wrapper's dispatch contract without calling a provider.

The wrapper reads `cline --help` and fails closed when a required capability is
missing. These tests drive it against stub binaries, so they cover the argv it
would hand the real CLI plus every refusal path.
"""

import json
import os
from pathlib import Path
import subprocess

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "bin/orama-system/skills/clinepass-deepseek-flash/scripts/run_clinepass_deepseek_flash.sh"
)

MODERN_HELP = """Options:
  -p, --plan                    Run in plan mode
  --json                        Output messages as JSON instead of styled text
  --auto-approve <boolean>      Set tool auto-approval for all tools
  --thinking <level>            Set reasoning effort: none|low|medium|high|xhigh
  -P, --provider <id>           Provider id (default: cline)
  -t, --timeout <seconds>       Optional timeout in seconds
"""

LEGACY_HELP = """Options:
  --json                        Output messages as JSON instead of styled text
  --auto-approve-all            Enable auto-approval for all tools
  --reasoning-effort <level>    Set reasoning effort
  -P, --provider <id>           Provider id (default: cline)
"""


def _stub(tmp_path: Path, help_text: str) -> dict[str, str]:
    """Install a `cline` stub that reports argv as JSON and serves `--help`."""
    stub = tmp_path / "cline"
    stub.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "argv = sys.argv[1:]\n"
        "if '--help' in argv:\n"
        "    print(os.environ['STUB_HELP'], end='')\n"
        "    raise SystemExit(0)\n"
        "print(json.dumps(argv))\n"
    )
    stub.chmod(0o755)
    return {
        **os.environ,
        "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
        "STUB_HELP": help_text,
    }


def _run(tmp_path: Path, help_text: str, *args: str) -> subprocess.CompletedProcess:
    """Run the wrapper against a stub without contacting a provider."""
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        env=_stub(tmp_path, help_text),
        text=True,
        capture_output=True,
        timeout=20,
    )


def test_dispatch_pins_provider_model_and_medium_reasoning(tmp_path: Path) -> None:
    """A capable CLI receives the full pinned route, in that order."""
    result = _run(tmp_path, MODERN_HELP, "--cwd", "/private/tmp", "--timeout", "42", "do the thing")
    assert result.returncode == 0, result.stderr

    argv = json.loads(result.stdout)
    assert argv == ["--json", "--auto-approve", "true", "-P", "cline-pass", "-m",
                    "cline-pass/deepseek-v4.1-flash-1017", "--thinking", "medium",
                    "-c", "/private/tmp", "-t", "42", "do the thing"]
    assert "--reasoning-effort" not in argv


def test_plan_mode_maps_to_plan_flag(tmp_path: Path) -> None:
    """`--plan` reaches the CLI; `--act` adds no flag because act is the default."""
    planned = _run(tmp_path, MODERN_HELP, "--plan", "review")
    assert planned.returncode == 0, planned.stderr
    assert json.loads(planned.stdout)[:2] == ["--json", "--plan"]

    acted = _run(tmp_path, MODERN_HELP, "--act", "review")
    assert acted.returncode == 0, acted.stderr
    assert "--plan" not in json.loads(acted.stdout)


def test_legacy_cli_refuses_automatic_high_escalation(tmp_path: Path) -> None:
    """A legacy high-only CLI cannot receive a task or raise reasoning effort."""
    result = _run(tmp_path, LEGACY_HELP, "review")
    assert result.returncode == 1
    assert "lacks --thinking" in result.stderr
    assert not result.stdout


def test_older_approval_flag_with_medium_thinking(tmp_path: Path) -> None:
    """An older approval spelling remains supported when medium is advertised."""
    help_text = MODERN_HELP.replace("--auto-approve <boolean>", "--auto-approve-all")
    result = _run(tmp_path, help_text, "review")
    assert result.returncode == 0, result.stderr
    assert "--auto-approve-all" in json.loads(result.stdout)


@pytest.mark.parametrize(
    "help_text,expected",
    [
        (MODERN_HELP.replace("  -P, --provider <id>           Provider id (default: cline)\n", ""),
         "lacks --provider"),
        (MODERN_HELP.replace("  --thinking <level>            Set reasoning effort: none|low|medium|high|xhigh\n", ""),
         "lacks --thinking"),
        (MODERN_HELP.replace(
            "  --auto-approve <boolean>      Set tool auto-approval for all tools\n", ""),
         "lacks an auto-approve flag"),
    ],
)
def test_missing_capability_fails_closed(
    tmp_path: Path, help_text: str, expected: str
) -> None:
    """No required capability means no dispatch -- never a silently unpinned run."""
    result = _run(tmp_path, help_text, "review")
    assert result.returncode == 1
    assert expected in result.stderr


def test_missing_prompt_is_a_usage_error(tmp_path: Path) -> None:
    """A prompt is mandatory; the usage error exits 2 before any CLI inspection."""
    result = _run(tmp_path, MODERN_HELP)
    assert result.returncode == 2
    assert "missing prompt" in result.stderr
