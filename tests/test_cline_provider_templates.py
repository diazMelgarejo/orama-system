"""Static checks on the checked-in Cline provider templates.

These guard the operator rules (effort medium -> high -> low, never xhigh/max;
W&B model order 1017 -> V4.1-Flash -> V4-Flash-0731) and keep dead ids out.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parent.parent
_DIR = _ROOT / "bin" / "orama-system" / "scripts" / "cline-provider-profiles"
_TEMPLATES = sorted(_DIR.glob("*.json.tmpl"))
_ALLOWED = {"medium", "high", "low"}
_DEAD_IDS = ("deepseek-ai/DeepSeek-V4-Flash\"",)
_WANDB_ORDER = [
    "deepseek-ai/DeepSeek-V4.1-Flash-1017",
    "deepseek-ai/DeepSeek-V4.1-Flash",
    "deepseek-ai/DeepSeek-V4-Flash-0731",
]


def _load(name: str) -> dict:
    return json.loads((_DIR / name).read_text())


def test_templates_exist() -> None:
    assert _TEMPLATES, "no templates found"


@pytest.mark.parametrize("path", _TEMPLATES, ids=lambda p: p.name)
def test_template_has_an_explicit_allowed_effort(path: Path) -> None:
    data = json.loads(path.read_text())
    effort = data["settings"]["reasoning"].get("effort")
    assert effort in _ALLOWED, f"{path.name}: effort {effort!r} is not one of {sorted(_ALLOWED)}"


@pytest.mark.parametrize("path", _TEMPLATES, ids=lambda p: p.name)
def test_template_resolution_efforts_follow_the_rule(path: Path) -> None:
    resolution = json.loads(path.read_text()).get("resolution", {})
    if resolution:
        assert resolution["efforts"] == ["medium", "high", "low"]
        assert resolution["models"][0] == json.loads(path.read_text())["settings"]["model"]


@pytest.mark.parametrize("path", _TEMPLATES, ids=lambda p: p.name)
def test_template_never_mentions_forbidden_efforts_or_dead_ids(path: Path) -> None:
    text = path.read_text()
    assert not re.search(r'"(xhigh|max)"', text)
    for dead in _DEAD_IDS:
        assert dead not in text


@pytest.mark.parametrize("path", _TEMPLATES, ids=lambda p: p.name)
def test_template_holds_no_literal_secret(path: Path) -> None:
    key = json.loads(path.read_text())["settings"]["apiKey"]
    assert re.fullmatch(r"\$\{[A-Z0-9_]+\}", key)


def test_wandb_and_bigmodel_enable_reasoning_explicitly() -> None:
    for name in ("wandb-deepseek-v4-flash.json.tmpl", "bigmodel-glm53-flash.json.tmpl"):
        assert _load(name)["settings"]["reasoning"]["enabled"] is True


def test_wandb_model_order_and_default() -> None:
    data = _load("wandb-deepseek-v4-flash.json.tmpl")
    assert data["resolution"]["models"] == _WANDB_ORDER
    assert data["settings"]["model"] == _WANDB_ORDER[0]
    assert data["settings"]["baseUrl"] == "https://api.inference.wandb.ai/v1"


def test_bigmodel_template_uses_the_correct_name_and_explicit_high() -> None:
    data = _load("bigmodel-glm53-flash.json.tmpl")
    assert data["settings"]["model"] == "glm-5.3-flash"
    assert data["settings"]["reasoning"]["effort"] == "high"  # default would be max


def test_old_bigmodel_name_is_no_longer_a_separate_template() -> None:
    assert not (_DIR / "bigmodel-glm52.json.tmpl").exists()


def test_wrapper_keeps_the_old_bigmodel_profile_name_as_an_alias() -> None:
    script = (_DIR / "switch-cline-provider.sh").read_text()
    assert "bigmodel-glm52" in script and "bigmodel-glm53-flash" in script


_LIVE_DIRS = ("src", "scripts", "config", "infra", "deployments", "bin/orama-system/scripts")
_DEAD_OPENROUTER = "deepseek-v4-flash:free"


def _tracked_live_files() -> list[Path]:
    import subprocess

    out = subprocess.run(["git", "ls-files", *_LIVE_DIRS], cwd=_ROOT, capture_output=True, text=True, check=True)
    return [_ROOT / n for n in out.stdout.splitlines() if n and Path(_ROOT / n).suffix in {".py", ".sh", ".json", ".jsonc", ".yml", ".yaml", ".tmpl", ".ps1"}]


def test_live_code_and_config_hold_no_dead_deepseek_ids() -> None:
    """A dead id re-entering live code/config would silently 404 at runtime (checked live 2026-11-12)."""
    offenders = []
    for path in _tracked_live_files():
        if path.name == "test_cline_provider_templates.py":
            continue
        text = path.read_text(errors="ignore")
        if _DEAD_OPENROUTER in text.replace("# 2026-11-12: deepseek/deepseek-v4-flash:free was removed", ""):
            offenders.append(str(path.relative_to(_ROOT)))
        if re.search(r"deepseek-ai/DeepSeek-V4-Flash(?!-0731)", text) and path.suffix == ".tmpl":
            offenders.append(str(path.relative_to(_ROOT)))
    assert not offenders, offenders
