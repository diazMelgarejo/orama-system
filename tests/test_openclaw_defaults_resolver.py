"""Orama reads the OpenClaw defaults from the live Perpetua-Tools file, else a stamped vendored copy, else fails closed."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESOLVER = ROOT / "scripts/lib/openclaw_defaults_resolver.py"
VENDORED = ROOT / "config/vendored/openclaw-defaults"
W_AND_B = "wandb/deepseek-ai/DeepSeek-V4.1-Flash-1017"
# `pt_root=None` means "go and find Perpetua-Tools" (environment, then sibling checkouts), so a test that needs it
# absent must name a path that does not exist.
ABSENT_PT = Path("/nonexistent/perpetua-tools")


def _load_resolver():
    spec = importlib.util.spec_from_file_location("openclaw_defaults_resolver_under_test", RESOLVER)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["openclaw_defaults_resolver_under_test"] = mod  # a dataclass needs its module registered first
    spec.loader.exec_module(mod)
    return mod


res = _load_resolver()


def _fake_pt(tmp: Path, mutate=None) -> Path:
    """A fake Perpetua-Tools tree built from the shipped vendored bundle (hermetic: no real PT checkout needed)."""
    data = json.loads((VENDORED / "openclaw-defaults.json").read_text(encoding="utf-8"))
    data.pop("_vendor", None)
    if mutate:
        mutate(data)
    (tmp / "config").mkdir(parents=True)
    (tmp / "src/perpetua_tools").mkdir(parents=True)
    (tmp / "config/openclaw-defaults.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (tmp / "src/perpetua_tools/openclaw_defaults.py").write_text(
        (VENDORED / "openclaw_defaults.py").read_text(encoding="utf-8"), encoding="utf-8"
    )
    return tmp


def _vendored_copy(tmp: Path) -> Path:
    out = tmp / "vendored"
    out.mkdir()
    for name in ("openclaw-defaults.json", "openclaw_defaults.py"):
        (out / name).write_text((VENDORED / name).read_text(encoding="utf-8"), encoding="utf-8")
    return out


def test_the_shipped_vendored_bundle_verifies_cleanly() -> None:
    r = res.resolve(pt_root=ABSENT_PT, vendored_dir=VENDORED, now=datetime.now(timezone.utc))
    assert r.source == "vendored" and r.warnings == ()
    assert r.module.chain_for(r.data)[0] == W_AND_B


def test_the_live_pt_file_wins_and_the_source_is_reported(tmp_path: Path) -> None:
    pt = _fake_pt(tmp_path / "pt")
    r = res.resolve(pt_root=pt, vendored_dir=_vendored_copy(tmp_path))
    assert r.source == "live" and r.pt_root == pt
    assert r.warnings == ()


def test_a_vendored_copy_that_differs_from_the_live_file_warns_loudly(tmp_path: Path) -> None:
    pt = _fake_pt(tmp_path / "pt", mutate=lambda d: d["chain"]["default"].reverse() or d["chain"]["default"].reverse() or d.update(updated="2026-12-01"))
    r = res.resolve(pt_root=pt, vendored_dir=_vendored_copy(tmp_path))
    assert r.source == "live"
    assert any("differs from the live" in w and "sync" in w.lower() for w in r.warnings), r.warnings


def test_without_pt_the_vendored_copy_is_used(tmp_path: Path) -> None:
    r = res.resolve(pt_root=ABSENT_PT, vendored_dir=_vendored_copy(tmp_path))
    assert r.source == "vendored"
    assert r.module.__name__ != "perpetua_tools.openclaw_defaults"


def test_discovery_finds_the_live_file_through_the_environment(tmp_path: Path) -> None:
    pt = _fake_pt(tmp_path / "pt")
    r = res.resolve(vendored_dir=_vendored_copy(tmp_path), env={"PERPETUATOOLSROOT": str(pt)})
    assert r.source == "live" and r.pt_root == pt


def test_it_fails_closed_only_when_there_is_neither_a_live_file_nor_a_vendored_copy(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(res.DefaultsUnavailable) as err:
        res.resolve(pt_root=ABSENT_PT, vendored_dir=empty)
    assert "fail closed" in str(err.value).lower()


def test_an_old_vendored_copy_warns_when_pt_is_unreachable(tmp_path: Path) -> None:
    r = res.resolve(pt_root=ABSENT_PT, vendored_dir=_vendored_copy(tmp_path), now=datetime.now(timezone.utc) + timedelta(days=90))
    assert r.source == "vendored"
    assert any("days old" in w and "cannot verify" in w.lower() for w in r.warnings), r.warnings


def test_a_hand_edited_vendored_json_is_refused_and_never_used(tmp_path: Path) -> None:
    vend = _vendored_copy(tmp_path)
    obj = json.loads((vend / "openclaw-defaults.json").read_text(encoding="utf-8"))
    obj["chain"]["default"].append("lmstudio-mac/qwen3.5-9b-mlx")
    (vend / "openclaw-defaults.json").write_text(json.dumps(obj), encoding="utf-8")
    with pytest.raises(res.DefaultsUnavailable) as err:
        res.resolve(pt_root=ABSENT_PT, vendored_dir=vend)
    assert "edited by hand" in str(err.value)


def test_a_hand_edited_vendored_module_is_never_executed(tmp_path: Path) -> None:
    vend = _vendored_copy(tmp_path)
    sentinel = tmp_path / "executed.flag"
    original = (vend / "openclaw_defaults.py").read_text(encoding="utf-8")
    (vend / "openclaw_defaults.py").write_text(f"open({str(sentinel)!r}, 'w').write('x')\n" + original, encoding="utf-8")
    with pytest.raises(res.DefaultsUnavailable):
        res.resolve(pt_root=ABSENT_PT, vendored_dir=vend)
    assert not sentinel.exists(), "an unverified module must not be imported"


def test_a_tampered_vendored_copy_only_warns_when_the_live_file_is_available(tmp_path: Path) -> None:
    pt = _fake_pt(tmp_path / "pt")
    vend = _vendored_copy(tmp_path)
    (vend / "openclaw_defaults.py").write_text("# edited\n", encoding="utf-8")
    r = res.resolve(pt_root=pt, vendored_dir=vend)
    assert r.source == "live"
    assert any("edited by hand" in w for w in r.warnings)


def test_the_pre_import_fingerprint_equals_the_modules_own_fingerprint() -> None:
    r = res.resolve(pt_root=ABSENT_PT, vendored_dir=VENDORED)
    assert res.canonical_fingerprint(r.data) == r.module.fingerprint(r.data)


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-I", str(RESOLVER), *args], capture_output=True, text=True)


def test_status_cli_is_quiet_when_fine_loud_when_stale_and_closed_when_unavailable(tmp_path: Path) -> None:
    ok = _cli("--status", "--pt-root", str(_fake_pt(tmp_path / "ok")), "--vendored-dir", str(_vendored_copy(tmp_path / "v1x") if False else VENDORED))
    assert ok.returncode == 0 and "source=live" in ok.stdout and "WARN" not in ok.stdout
    stale_pt = _fake_pt(tmp_path / "stale", mutate=lambda d: d.update(updated="2026-12-01"))
    stale = _cli("--status", "--pt-root", str(stale_pt), "--vendored-dir", str(VENDORED))
    assert stale.returncode == 1 and "WARN" in stale.stdout and "differs from the live" in stale.stdout
    empty = tmp_path / "empty"
    empty.mkdir()
    gone = _cli("--status", "--pt-root", str(tmp_path / "nowhere"), "--vendored-dir", str(empty))
    assert gone.returncode == 2 and "FAIL CLOSED" in gone.stdout


def test_render_patch_through_the_resolver_matches_the_vendored_modules_output() -> None:
    out = _cli("--render-patch", "--shape", "entries", "--pt-root", "/nonexistent", "--vendored-dir", str(VENDORED))
    assert out.returncode == 0
    patch = json.loads(out.stdout)
    assert patch["agents"]["defaults"]["model"]["primary"] == W_AND_B
    assert "lmstudio-mac" not in out.stdout


def test_start_sh_reports_the_copy_status_but_never_runs_the_sync() -> None:
    start = (ROOT / "start.sh").read_text(encoding="utf-8")
    assert "openclaw_defaults_resolver.py" in start and "--status" in start
    assert "sync-openclaw-defaults" not in start, "the sync needs a human; start-up may only report"
    assert subprocess.run(["/bin/bash", "-n", str(ROOT / "start.sh")], capture_output=True).returncode == 0
