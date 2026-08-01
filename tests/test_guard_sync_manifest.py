"""Guard sync manifest — single source of truth for attribution guard distribution."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GIT = ROOT / "scripts" / "git"
MANIFEST = GIT / "guard-sync-manifest.sh"
SYNC = GIT / "sync-attribution-guard-scripts.sh"
VERIFY = GIT / "verify-guard-parity.sh"


def _bash_array(name: str) -> list[str]:
    result = subprocess.run(
        [
            "bash",
            "-c",
            f'source "$1" && printf "%s\\n" "${{{name}[@]}}"',
            "_",
            str(MANIFEST),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


@pytest.mark.unit
def test_manifest_files_exist_on_disk() -> None:
    all_paths = _bash_array("GUARD_SYNC_EXECUTABLES") + _bash_array("GUARD_SYNC_DATA_FILES")
    missing = [rel for rel in all_paths if not (GIT / rel).is_file()]
    assert not missing, f"manifest lists missing files: {missing}"


@pytest.mark.unit
def test_parity_required_expands_in_bash() -> None:
    """GUARD_PARITY_REQUIRED is assembled at source time from the two sync arrays."""
    parity = _bash_array("GUARD_PARITY_REQUIRED")
    expected = set(_bash_array("GUARD_SYNC_EXECUTABLES")) | set(
        _bash_array("GUARD_SYNC_DATA_FILES")
    )
    assert set(parity) == expected


@pytest.mark.unit
def test_sync_and_verify_source_manifest() -> None:
    for script in (SYNC, VERIFY):
        body = script.read_text(encoding="utf-8")
        assert "guard-sync-manifest.sh" in body
        assert "source" in body


@pytest.mark.unit
def test_verify_guard_parity_passes_in_canonical_repo() -> None:
    result = subprocess.run(
        ["bash", str(VERIFY)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
