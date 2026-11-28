"""Mac LM Studio is manual use only: no tracked file may make it a default route.

Explicit routing (a requested model id, a CLI choice, discovery of its address) stays allowed; assigning it as
a primary, a fallback or an agent's provider does not.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSIGNS_ROUTE = re.compile(
    r"""["']?(?:primary|fallbacks|provider|default_provider|default_model)["']?\s*(?<![=!<>])[:=](?!=)\s*[\[(]?[^\n#]{0,160}?["']lmstudio-mac(?:/|["'])"""
)
# An older snapshot that still routes to Mac LM Studio and waits for an operator decision: generating it from
# the defaults would drop the approved Google provider names that tests/test_gemini_catalog_policy.py pins.
PENDING_DECISION = {"config/mac-orchestrator.json"}
NOT_ROUTING = ("tests/", "scripts/tests/", "docs/", "config/vendored/", "web/")


def _tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z", "--", "*.py", "*.sh", "*.ps1", "*.json", "*.yml", "*.yaml"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [name for name in out.split("\0") if name and not name.startswith(NOT_ROUTING)]


def _offenders() -> set[str]:
    found = set()
    for name in _tracked():
        path = ROOT / name
        if path.is_file() and not path.is_symlink() and ASSIGNS_ROUTE.search(path.read_text(encoding="utf-8", errors="ignore")):
            found.add(name)
    return found


def test_the_pattern_catches_each_way_of_assigning_the_route() -> None:
    for line in (
        '"primary": "lmstudio-mac/qwen"', '{"fallbacks":["ollama/q","lmstudio-mac/qwen"]}',
        '"provider": "lmstudio-mac",', "default_model: 'lmstudio-mac/qwen'",
    ):
        assert ASSIGNS_ROUTE.search(line), line
    for line in ('if provider in {"lmstudio-mac", "ollama-mac"}:', '_MAC_PROVIDER_PREFIX = "lmstudio-mac/"',
                 'choices=["codex", "lmstudio-mac"]', 'url = a if provider == "lmstudio-mac" else b',
                 'if default_provider != "lmstudio-mac":'):
        assert not ASSIGNS_ROUTE.search(line), line


def test_no_new_file_makes_mac_lm_studio_a_default_route() -> None:
    assert _offenders() - PENDING_DECISION == set()


def test_the_mac_researcher_seat_runs_on_a_local_model_from_the_default_chain() -> None:
    registry = json.loads((ROOT / "bin/orama-system/config/agent_registry.json").read_text(encoding="utf-8"))
    defaults = json.loads((ROOT / "config/vendored/openclaw-defaults/openclaw-defaults.json").read_text(
        encoding="utf-8"))
    seat = registry["openclaw_agents"]["mac-researcher"]
    assert seat["provider"] == "ollama"
    assert f"{seat['provider']}/{seat['model']}" in defaults["chain"]["default"]


def test_the_pending_list_holds_only_files_that_still_need_the_decision() -> None:
    assert PENDING_DECISION - _offenders() == set(), "remove a fixed file from PENDING_DECISION"
