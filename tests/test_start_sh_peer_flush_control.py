"""Restore LAN listeners without automatically replaying queued assignments."""
from pathlib import Path
import os
import re
import subprocess

import pytest


@pytest.mark.parametrize("flag,expected", [("0", 0), ("false", 0), ("off", 0), ("invalid", 1)])
def test_outbox_hold_never_calls_peer_helpers(flag: str, expected: int) -> None:
    """Disabled or malformed controls preserve all queued files before any helper runs."""
    source = (Path(__file__).resolve().parents[1] / "start.sh").read_text()
    function = re.search(r"^_flush_lan_peer_outbox\(\) \{\n.*?^\}\n", source, re.M | re.S)
    assert function
    script = (
        "set -euo pipefail\n"
        "_info() { :; }\n_warn() { :; }\n"
        "_sync_control_plane_token() { exit 91; }\n"
        + function.group() + "\n_flush_lan_peer_outbox\n"
    )
    result = subprocess.run(
        ["/bin/bash", "-c", script],
        env={**os.environ, "LAN_PEER_OUTBOX_AUTO_FLUSH": flag},
        capture_output=True, text=True, timeout=10, check=False,
    )
    assert result.returncode == expected, result.stderr


@pytest.mark.parametrize("flag,expected", [("0", 0), ("false", 0), ("off", 0), ("invalid", 1)])
def test_service_restoration_can_disable_research_dispatch(flag: str, expected: int) -> None:
    """The dispatch gate exits before any researcher or remote watcher is spawned."""
    source = (Path(__file__).resolve().parents[1] / "start.sh").read_text()
    guard = re.search(
        r'^# BEGIN ORCHESTRATOR DISPATCH GATE\n(.*?)^# END ORCHESTRATOR DISPATCH GATE$',
        source, re.M | re.S,
    )
    assert guard
    script = "set -euo pipefail\n_info() { :; }\n_warn() { :; }\n" + guard.group(1) + "\nexit 91\n"
    result = subprocess.run(
        ["/bin/bash", "-c", script],
        env={**os.environ, "ORAMA_ORCHESTRATOR_AUTO_DISPATCH": flag},
        capture_output=True, text=True, timeout=10, check=False,
    )
    assert result.returncode == expected, result.stderr
