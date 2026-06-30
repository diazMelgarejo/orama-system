from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
START_SH = ROOT / "start.sh"
COORD_PULSE_SH = ROOT / "bin" / "orama-system" / "skills" / "hermes-harness" / "scripts" / "coord_pulse.sh"


def test_start_sh_help_exits_before_startup_and_lists_coord_pulse_flags():
    result = subprocess.run(
        ["bash", str(START_SH), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--install-coord-pulse" in result.stdout
    assert "--coord-pulse-status" in result.stdout
    assert "probing hard requirements" not in result.stdout


def test_start_sh_rejects_unknown_args_before_startup():
    result = subprocess.run(
        ["bash", str(START_SH), "--not-a-real-flag"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "unknown argument: --not-a-real-flag" in result.stdout
    assert "probing hard requirements" not in result.stdout


def test_start_sh_uses_non_positional_no_open_and_portable_timeout():
    text = START_SH.read_text(encoding="utf-8")

    assert "--no-open)             NO_OPEN=1" in text
    assert 'if [ "$NO_OPEN" != "1" ]; then' in text
    assert "_run_discover_force_with_timeout 30" in text
    assert 'timeout 30 "$US_PYTHON"' not in text
    assert "timeout 1 bash" not in text


def test_start_sh_pt_resolve_uses_src_pythonpath():
    text = START_SH.read_text(encoding="utf-8")

    assert 'PYTHONPATH="${PT_DIR}/src:${PT_DIR}"' in text
    assert 'PYTHONPATH="${PT_DIR}" \\' not in text


def test_start_sh_ollama_model_check_is_exact():
    text = START_SH.read_text(encoding="utf-8")

    assert "grep -qxF \"${model}\"" in text
    assert "MODEL_NAME=\"$model\" python3 -c" in text
    assert "model_base=" not in text


def test_start_sh_has_single_pid_on_port_definition():
    text = START_SH.read_text(encoding="utf-8")

    assert text.count("pid_on_port() {") == 1


def test_coord_pulse_uses_portable_lock_not_flock():
    text = COORD_PULSE_SH.read_text(encoding="utf-8")

    assert 'mkdir "$LOCK_DIR"' in text
    assert "flock" not in text
