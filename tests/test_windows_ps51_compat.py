"""Guards Windows PowerShell 5.1 compatibility of the Windows launcher scripts.

start.ps1 / install.ps1 must run under powershell.exe 5.1 (no PowerShell 7
operators) and keep their UTF-8 BOM (5.1 reads BOM-less files as ANSI and
mangles the box-drawing characters in them).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WIN_DIR = REPO / "platform" / "windows"
START = WIN_DIR / "start.ps1"
INSTALL = WIN_DIR / "install.ps1"
LOAD_LOCAL = REPO / "scripts" / "env" / "load-local.ps1"

SCANNED = sorted(WIN_DIR.glob("*.ps1")) + [LOAD_LOCAL]

# Pre-existing offenders in files this PR does not own. Each entry names the
# check kinds allowed to fire; remove an entry when the owning PR fixes it.
ALLOWED = {
    # backtick-e ANSI escapes; fixed by the service-lifecycle PR (F10).
    "fallback-chain-verify.ps1": {"backtick-e"},
}

# One alternation, scanned left to right so quotes inside comments (and '#'
# inside strings) are classified correctly.
_TOKEN = re.compile(
    r"""
    (?P<hs_d>@"\s*\n.*?\n"@)
  | (?P<hs_s>@'\s*\n.*?\n'@)
  | (?P<block><\#.*?\#>)
  | (?P<sq>'(?:[^']|'')*')
  | (?P<dq>"(?:`.|[^"`])*")
  | (?P<line>\#[^\n]*)
    """,
    re.DOTALL | re.VERBOSE,
)


def _strip(text: str, *, keep_strings: bool) -> str:
    def repl(m: re.Match) -> str:
        kind = m.lastgroup
        if kind in ("block", "line"):
            return " "
        return m.group(0) if keep_strings else '""'

    return _TOKEN.sub(repl, text)


def _read(path: Path) -> str:
    return path.read_bytes().decode("utf-8-sig")


def _checks(path: Path) -> set[str]:
    raw = _read(path)
    code = _strip(raw, keep_strings=False)  # comments and strings removed
    with_strings = _strip(raw, keep_strings=True)  # comments removed only
    found: set[str] = set()
    if re.search(r"\?\?", code):
        found.add("null-coalescing")
    if re.search(r"\?\.[A-Za-z_\[]", code):
        found.add("null-conditional")
    if re.search(r"\s\?\s+\S[^\n:]*\s:\s+\S", code):
        found.add("ternary")
    if "&&" in code or "||" in code:
        found.add("pipeline-chain")
    if re.search(r"-AsHashtable\b", code, re.IGNORECASE):
        found.add("as-hashtable")
    if "`e" in with_strings:
        found.add("backtick-e")
    return found


@pytest.mark.parametrize("path", [START, INSTALL])
def test_launcher_keeps_utf8_bom(path: Path) -> None:
    assert path.read_bytes()[:3] == b"\xef\xbb\xbf", f"{path.name} lost its UTF-8 BOM"


@pytest.mark.parametrize("path", SCANNED, ids=lambda p: p.name)
def test_no_powershell7_only_syntax(path: Path) -> None:
    offenders = _checks(path) - ALLOWED.get(path.name, set())
    assert not offenders, f"{path.name} uses PowerShell 7-only syntax: {sorted(offenders)}"


def test_scanner_detects_and_ignores_correctly() -> None:
    bad = _strip("$a = $b ?? 1\n$c = $x?.y\nif ($a -and $b) { } && x\n", keep_strings=False)
    assert "??" in bad and "&&" in bad
    ok = _strip("# a && b ?? c\n$s = 'x && y ?? z'\n$t = \"p || q\"\n<# &&\n#>\n", keep_strings=False)
    assert "&&" not in ok and "??" not in ok and "||" not in ok


def test_paths_ps1_written_exactly_once() -> None:
    text = _strip(_read(START), keep_strings=True)
    writes = re.findall(r"(?:Set-Content|Out-File|Add-Content)\b[^\n]*\$PathsFile", text)
    assert len(writes) == 1, f".paths.ps1 must be written once, found {len(writes)}"
    assert _read(START).count("# .paths.ps1 \u2014 auto-generated") == 1


def test_read_only_modes_gate_mutation() -> None:
    text = _read(START)
    assert "$ReadOnlyMode = [bool]($Stop -or $Status -or $FleetStatus -or $HardwarePolicy)" in text
    assert "if (-not $ReadOnlyMode -and ($LanPeer -or (Test-LanBindConfigured))) {" in text
    assert "if (-not $ReadOnlyMode) { Heal-PtVenv -PtDir $PtDir }" in text


def test_pt_venv_heal_runs_pip_in_pt_cwd() -> None:
    text = _read(START)
    assert "Push-Location $PtDir" in text
    assert "Pop-Location" in text
    assert "'-e', '.'" in text


def test_install_ps1_pip_eap_continue() -> None:
    text = _read(INSTALL)
    assert "$ErrorActionPreference = 'Continue'" in text
    assert "$coreExit = $LASTEXITCODE" in text


def test_api_server_version_fallback_reads_repo_version() -> None:
    from orama_system import api_server
    from orama_system._version import __version__ as repo_version

    # Read from pyproject.toml -> hatch version path -> _version.py, never a literal.
    assert api_server._fallback_version() == repo_version
