"""Guards Windows PowerShell 5.1 compatibility of the Windows launcher scripts.

start.ps1 / install.ps1 must run under powershell.exe 5.1 (no PowerShell 7
operators) and keep their UTF-8 BOM (5.1 reads BOM-less files as ANSI and
mangles the box-drawing characters in them).
"""

from __future__ import annotations

import codecs
import os
import re
import shutil
import subprocess
import sys
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
    """Strip."""
    def repl(m: re.Match) -> str:
        """Repl."""
        kind = m.lastgroup
        if kind in ("block", "line"):
            return " "
        return m.group(0) if keep_strings else '""'

    return _TOKEN.sub(repl, text)


def _read(path: Path) -> str:
    """Read."""
    return path.read_bytes().decode("utf-8-sig")


def _checks(path: Path) -> set[str]:
    """Checks."""
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
    """Check that launcher keeps utf8 bom."""
    assert path.read_bytes()[:3] == b"\xef\xbb\xbf", f"{path.name} lost its UTF-8 BOM"


@pytest.mark.parametrize("path", SCANNED, ids=lambda p: p.name)
def test_no_powershell7_only_syntax(path: Path) -> None:
    """Check that no powershell7 only syntax."""
    offenders = _checks(path) - ALLOWED.get(path.name, set())
    assert not offenders, f"{path.name} uses PowerShell 7-only syntax: {sorted(offenders)}"


def test_scanner_detects_and_ignores_correctly() -> None:
    """Check that scanner detects and ignores correctly."""
    bad = _strip("$a = $b ?? 1\n$c = $x?.y\nif ($a -and $b) { } && x\n", keep_strings=False)
    assert "??" in bad and "&&" in bad
    ok = _strip("# a && b ?? c\n$s = 'x && y ?? z'\n$t = \"p || q\"\n<# &&\n#>\n", keep_strings=False)
    assert "&&" not in ok and "??" not in ok and "||" not in ok


def test_paths_ps1_written_exactly_once() -> None:
    """Check that paths ps1 written exactly once."""
    text = _strip(_read(START), keep_strings=True)
    writes = re.findall(r"(?:Set-Content|Out-File|Add-Content)\b[^\n]*\$PathsFile", text)
    assert len(writes) == 1, f".paths.ps1 must be written once, found {len(writes)}"
    assert _read(START).count("# .paths.ps1 \u2014 auto-generated") == 1


def test_read_only_modes_gate_mutation() -> None:
    """Check that read only modes gate mutation."""
    text = _read(START)
    assert "$ReadOnlyMode = [bool]($Stop -or $Status -or $FleetStatus -or $HardwarePolicy)" in text
    assert "if (-not $ReadOnlyMode -and ($LanPeer -or (Test-LanBindConfigured))) {" in text
    assert "if (-not $ReadOnlyMode) { Heal-PtVenv -PtDir $PtDir }" in text


def test_pt_venv_heal_runs_pip_in_pt_cwd() -> None:
    """Check that pt venv heal runs pip in pt cwd."""
    text = _read(START)
    assert "Push-Location $PtDir" in text
    assert "Pop-Location" in text
    assert "'-e', '.'" in text


def test_install_ps1_pip_eap_continue() -> None:
    """Check that install ps1 pip eap continue."""
    text = _read(INSTALL)
    assert "$ErrorActionPreference = 'Continue'" in text
    assert "$coreExit = $LASTEXITCODE" in text


def test_api_server_version_comes_from_version_module() -> None:
    """Check that api server version comes from version module."""
    from orama_system import api_server
    from orama_system._version import __version__ as repo_version

    assert api_server._resolve_version() == repo_version


def test_api_server_version_survives_missing_metadata_and_module() -> None:
    """Stale/absent package metadata must not change the reported version."""
    code = (
        "import importlib.metadata as m, sys\n"
        "def _boom(*a, **k): raise m.PackageNotFoundError('orama-system')\n"
        "m.version = _boom\n"
        "from orama_system import api_server\n"
        "from orama_system._version import __version__ as v\n"
        "assert api_server.__version__ == v, (api_server.__version__, v)\n"
        "sys.modules['orama_system._version'] = None\n"
        "assert api_server._resolve_version() == '0+unknown'\n"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(REPO), str(REPO / "src")])
    r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]


# --- load-local.ps1 behaviour (child powershell.exe) -------------------------

_PS = shutil.which("powershell.exe") or shutil.which("powershell")
needs_ps = pytest.mark.skipif(_PS is None, reason="powershell not available")


def _run_load_local(tmp_path: Path, env_text: str, extra_env: dict | None = None, keys=()):
    """Run load-local.ps1 against a temp repo root; return {key: value|None}."""
    (tmp_path / ".env").write_bytes(env_text.encode("utf-8"))
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    names = ",".join("'%s'" % k for k in keys)
    script = (
        "$ErrorActionPreference='Stop'; "
        "& '%s' -RepoRoot '%s'; "
        "foreach ($n in @(%s)) { $v=[Environment]::GetEnvironmentVariable($n,'Process'); "
        "if ($null -eq $v) { Write-Output ($n + '=<unset>') } else { Write-Output ($n + '=[' + $v + ']') } }"
    ) % (LOAD_LOCAL, tmp_path, names)
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("LLT_", "ORAMA_LOADLOCAL_", "PERPETUA_TOOLS_"))
    }
    env["USERPROFILE"] = env["HOME"] = str(home)
    env.update(extra_env or {})
    r = subprocess.run(
        [_PS, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr[-800:]
    out = {}
    for line in r.stdout.splitlines():
        k, _, v = line.partition("=")
        out[k] = None if v == "<unset>" else v[1:-1]
    return out


@needs_ps
def test_load_local_comment_only_values_are_empty(tmp_path: Path) -> None:
    """Check that load local comment only values are empty."""
    text = (
        "LLT_A= # comment\n"
        "LLT_B=\t#x\n"
        "LLT_C=#x\n"
        "LLT_D=val # tail\n"
        "LLT_E=a#b\n"
        'LLT_F="q # kept" ignored\n'
    )
    got = _run_load_local(tmp_path, text, keys=[f"LLT_{c}" for c in "ABCDEF"])
    assert not got["LLT_A"]  # empty or unset, never the comment text
    assert not got["LLT_B"]  # empty or unset, never the comment text
    assert not got["LLT_C"]  # empty or unset, never the comment text
    assert got["LLT_D"] == "val"
    assert got["LLT_E"] == "a#b"
    assert got["LLT_F"] == "q # kept"


@needs_ps
def test_load_local_caller_value_wins(tmp_path: Path) -> None:
    """Check that load local caller value wins."""
    got = _run_load_local(
        tmp_path,
        "PERPETUA_TOOLS_PATH=from-file\n",
        extra_env={"PERPETUA_TOOLS_PATH": "from-caller"},
        keys=["PERPETUA_TOOLS_PATH"],
    )
    assert got["PERPETUA_TOOLS_PATH"] == "from-caller"


@needs_ps
def test_load_local_stale_value_from_previous_run_is_not_caller_set(tmp_path: Path) -> None:
    # A previous run (or the launcher) left the value and its marker behind.
    """Check that load local stale value from previous run is not caller set."""
    got = _run_load_local(
        tmp_path,
        "PERPETUA_TOOLS_PATH=from-file\n",
        extra_env={
            "PERPETUA_TOOLS_PATH": "stale",
            "ORAMA_LOADLOCAL_SET_PERPETUA_TOOLS_PATH": "stale",
        },
        keys=["PERPETUA_TOOLS_PATH", "ORAMA_LOADLOCAL_SET_PERPETUA_TOOLS_PATH"],
    )
    assert got["PERPETUA_TOOLS_PATH"] == "from-file"
    assert got["ORAMA_LOADLOCAL_SET_PERPETUA_TOOLS_PATH"] == "from-file"


def test_launcher_scripts_hardening_present() -> None:
    """Check that launcher scripts hardening present."""
    start = _read(START)
    assert "'-I', '-c', $Code" in start
    assert "Set-LauncherPtEnv" in start
    assert "removed stray orama-system" in start
    assert "interpreter not found" in start
    assert "$discoverExit = $LASTEXITCODE" in _read(INSTALL)


def _tracked_powershell_scripts() -> list[Path]:
    """Every tracked .ps1 in the repository (git ls-files; empty outside a checkout)."""
    proc = subprocess.run(["git", "-C", str(REPO), "ls-files", "*.ps1"], capture_output=True, text=True)
    return sorted(REPO / line for line in proc.stdout.splitlines() if line.strip())


@pytest.mark.parametrize("path", _tracked_powershell_scripts(), ids=lambda p: str(p.relative_to(REPO)))
def test_script_with_non_ascii_text_has_a_utf8_bom(path: Path) -> None:
    """A .ps1 with non-ASCII text needs a BOM: 5.1 otherwise reads it as ANSI, and an em dash can end a string early."""
    data = path.read_bytes()
    if data.startswith(codecs.BOM_UTF8):
        return
    assert data.isascii(), f"{path.name} has non-ASCII text but no UTF-8 BOM"


@pytest.mark.skipif(sys.platform != "win32" or shutil.which("powershell.exe") is None,
                    reason="needs Windows PowerShell 5.1")
@pytest.mark.parametrize("path", _tracked_powershell_scripts(), ids=lambda p: str(p.relative_to(REPO)))
def test_script_parses_under_windows_powershell_5_1(path: Path, tmp_path: Path) -> None:
    """Parse the script with the real 5.1 parser and require zero syntax errors."""
    powershell_path = str(path).replace("'", "''")  # keep an apostrophe inside the single-quoted literal
    command = (
        "$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile("
        f"'{powershell_path}',[ref]$null,[ref]$e);if($e.Count){{$e[0].Message+' (line '+$e[0].Extent.StartLineNumber+')';exit 1}}"
    )
    proc = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                          capture_output=True, text=True, cwd=tmp_path)
    assert proc.returncode == 0, f"{path.name}: {proc.stdout.strip()}"
