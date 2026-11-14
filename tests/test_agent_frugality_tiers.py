"""Every staged agent has a frugality tier. Local seats are tier 1."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1]


def test_registry_roles_have_tiers_and_relay_cursor_is_not_last() -> None:
    data = yaml.safe_load((_ROOT / "bin/agents/REGISTRY.yml").read_text())
    roles = list(data["roles"]) + list(data["lifecycle"])
    assert all(isinstance(role.get("frugality_tier"), int) for role in roles)
    by_name = {role["staging_folder"]: role["frugality_tier"] for role in roles}
    for name, tier in by_name.items():
        if name in {"orchestrator", "lifecycle"} or "research" in name:
            assert tier == 1, name
    order = [role["staging_folder"] for role in data["roles"]]
    assert order[-2] == "relay-cursor"
    assert order[-1] == "rex"
    assert by_name["relay-cursor"] == 3
    assert by_name["rex"] == 6


def test_agent_registry_json_has_no_tierless_agent() -> None:
    data = json.loads(
        (_ROOT / "bin/orama-system/config/agent_registry.json").read_text()
    )
    for name, entry in data["openclaw_agents"].items():
        if isinstance(entry, dict) and "id" not in entry and "model" not in entry:
            continue
        if isinstance(entry, dict) and "soul" in entry:
            assert entry["frugality_tier"] == 1, name
    for entry in data["agents"]:
        assert isinstance(entry["frugality_tier"], int)
        if entry["id"] == "orchestrator":
            assert entry["frugality_tier"] == 1
    for name, entry in data["autoresearch_agents"].items():
        if not isinstance(entry, dict) or "id" not in entry:
            continue
        assert entry["frugality_tier"] == 1, name
