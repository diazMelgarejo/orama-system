"""The ramparts scan must run only the exactly pinned version, never a restored longer one such as 0.8.20."""

import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ci/run_agent_security_scans.sh"
PIN = "0.8.2"

FAKE_RAMPARTS = """#!/bin/sh
if [ "$1" = "--version" ]; then printf '%s\\n' "$FAKE_VERSION_OUT"; exit 0; fi
printf '%s\\n' "$*" >> "$RAMPARTS_LOG"
exit 0
"""
FAKE_CARGO = """#!/bin/sh
printf '%s\\n' "$*" >> "$CARGO_LOG"
mkdir -p "$CARGO_HOME/bin"
printf '#!/bin/sh\\nif [ "$1" = "--version" ]; then echo "ramparts %s"; exit 0; fi\\nprintf "%%s\\\\n" "$*" >> "$RAMPARTS_LOG"\\nexit 0\\n' \\
    "$PINNED" > "$CARGO_HOME/bin/ramparts"
chmod +x "$CARGO_HOME/bin/ramparts"
"""


def _executable(path: Path, body: str) -> None:
    """Write an executable helper script."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _utility_dir(tmp_path: Path) -> Path:
    """Expose only the plain utilities the scripts need, never a system cargo or ramparts."""
    utilities = tmp_path / "utilbin"
    utilities.mkdir()
    for name in ("sh", "bash", "dirname", "mkdir", "chmod", "cat", "rm", "env", "uname", "tr", "sed", "grep", "head", "date"):
        found = shutil.which(name, path="/usr/bin:/bin")
        if found:
            (utilities / name).symlink_to(found)
    return utilities


def _run(tmp_path: Path, version_out: str, *, cargo: bool, ci: bool = True) -> tuple[subprocess.CompletedProcess[str], str, str]:
    """Run only the ramparts scan in an isolated tree with fake binaries; return result, scan log, cargo log."""
    tree = tmp_path / "tree"
    script = tree / "scripts/ci/run_agent_security_scans.sh"
    script.parent.mkdir(parents=True)
    shutil.copy(SCRIPT, script)
    for scan_root in ("bin/agents", "bin/orama-system/skills"):
        (tree / scan_root).mkdir(parents=True)
    fakebin = tmp_path / "fakebin"
    _executable(fakebin / "ramparts", FAKE_RAMPARTS)
    if cargo:
        _executable(fakebin / "cargo", FAKE_CARGO)
    path = f"{fakebin}:{_utility_dir(tmp_path)}"
    found_cargo = shutil.which("cargo", path=path)
    assert (found_cargo is not None) == cargo, "only the fake cargo may ever be reachable from the test PATH"
    env = {
        "PATH": path, "HOME": str(tmp_path / "home"), "RUNNER_TEMP": str(tmp_path),
        "CARGO_HOME": str(tmp_path / "cargohome"), "FAKE_VERSION_OUT": version_out, "PINNED": PIN,
        "RAMPARTS_LOG": str(tmp_path / "ramparts.log"), "CARGO_LOG": str(tmp_path / "cargo.log"),
    }
    if ci:
        env["GITHUB_ACTIONS"] = "true"
    result = subprocess.run(["/bin/bash", str(script), "ramparts"], env=env, capture_output=True, text=True, timeout=60)
    scan = (tmp_path / "ramparts.log").read_text() if (tmp_path / "ramparts.log").exists() else ""
    installs = (tmp_path / "cargo.log").read_text() if (tmp_path / "cargo.log").exists() else ""
    return result, scan, installs


def test_exact_pinned_version_scans_without_reinstall(tmp_path: Path) -> None:
    """The pinned version is accepted as is: scanned, nothing reinstalled, CI passes."""
    result, scan, installs = _run(tmp_path, f"ramparts {PIN}", cargo=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "scan" in scan and installs == ""


@pytest.mark.parametrize("reported", [
    "ramparts 0.8.20", "ramparts 0.8.2.1", "ramparts 0.8.2-rc1", "ramparts 1.0.8.2", "ramparts 0.8.2+extra", "", "no version here",
])
def test_unpinned_or_unparseable_version_fails_closed_in_ci(tmp_path: Path, reported: str) -> None:
    """A longer, decorated or unreadable version never stands in for the pin: CI fails and nothing is scanned."""
    result, scan, installs = _run(tmp_path, reported, cargo=False)
    assert result.returncode != 0, result.stdout
    assert "FAIL ramparts" in result.stdout and scan == "" and installs == ""


def test_longer_cached_version_is_replaced_by_the_pinned_install(tmp_path: Path) -> None:
    """With cargo available, a restored 0.8.20 is reinstalled as exactly 0.8.2 (forced) before any scan."""
    result, scan, installs = _run(tmp_path, "ramparts 0.8.20", cargo=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"install ramparts@{PIN} --locked --force" in installs
    assert "scan" in scan


def test_local_run_warns_but_continues_on_a_different_version(tmp_path: Path) -> None:
    """Outside CI a developer's other ramparts version is a warning, not a failure."""
    result, scan, _ = _run(tmp_path, "ramparts 9.9.9", cargo=False, ci=False)
    assert result.returncode == 0, result.stdout
    assert "WARN ramparts version differs" in result.stdout and "scan" in scan


def test_workflow_cache_key_still_ends_at_the_pin() -> None:
    """Keep the exact-key assertion next to the runtime guard so a key edit cannot loosen the pin silently."""
    assert "key: ramparts-${{ runner.os }}-" + PIN + "\n" in (ROOT / ".github/workflows/agent-security.yml").read_text()
