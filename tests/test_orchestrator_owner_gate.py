"""The tracked orchestrator snapshot keeps its command-owner gate without naming a person."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_REFERENCE = re.compile(r"^\$\{env:([A-Z][A-Z0-9_]*)\}$")


def test_the_command_owner_gate_is_present_and_names_only_environment_variables() -> None:
    config = json.loads((ROOT / "config/mac-orchestrator.json").read_text(encoding="utf-8"))
    owners = config.get("commands", {}).get("ownerAllowFrom", [])
    assert owners, "privileged commands need an explicit owner allow list"
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    for owner in owners:
        match = ENV_REFERENCE.match(owner)
        assert match, "an owner entry must be an environment reference, never a literal identity"
        assert re.search(rf"^#?\s*{match.group(1)}=", example, re.M), f"{match.group(1)} is not in .env.example"
