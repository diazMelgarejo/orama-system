from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_environment_templates_publish_canonical_and_v1_compatibility_names() -> None:
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    cloud = json.loads(
        (ROOT / ".cursor" / "environment.json").read_text(encoding="utf-8")
    )["environment"]

    assert "ORAMASYS_ENDPOINT=http://localhost:8001/oramasys" in example
    assert "ULTRATHINK_ENDPOINT=http://localhost:8001" in example
    assert cloud["ORAMASYS_ENDPOINT"] == "http://localhost:8001/oramasys"
    assert cloud["ULTRATHINK_ENDPOINT"] == "http://localhost:8001"
    assert cloud["ORAMASYS_PORT"] == "8001"
    assert cloud["ULTRATHINK_PORT"] == "8001"
