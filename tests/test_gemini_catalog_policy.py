"""Pin operator-approved namespaces and prevent automatic frontier escalation."""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_custom_google_providers_use_native_protocol_and_bare_model_ids() -> None:
    """Custom provider names remain stable while their wire identifiers stay Google-native."""
    config = json.loads((ROOT / "config/mac-orchestrator.json").read_text())
    providers = config["models"]["providers"]
    for name in ("gemini-main", "gemini-fallback"):
        assert providers[name]["api"] == "google-generative-ai"
        assert all(row["id"].startswith("gemini-") for row in providers[name]["models"])
        assert not any("argon" in row["id"] for row in providers[name]["models"])
    fallbacks = config["agents"]["list"][0]["model"]["fallbacks"]
    assert [value for value in fallbacks if "gemini" in value] == ["gemini-fallback/gemini-flash-latest"]
    assert "openrouter/google/gemini-4-argon" in config["agents"]["defaults"]["models"]


def test_orama_google_role_catalog_matches_the_approved_runtime_roles() -> None:
    """The mirrored catalog exposes capability without declaring a planning approval."""
    google = yaml.safe_load((ROOT / "config/model-governance.yml").read_text())["google"]
    assert google["default"]["launch_id"] == "gemini-3.8-flash"
    assert google["controller"]["launch_id"] == "gemini-3.5-flash-lite"
    assert google["fallback"]["launch_id"] == "gemini-flash-latest"
    assert google["gated"]["gemini-pro-latest"]["requires"] == "escalation_token"
    assert "budget_cap" in google["gated"]["gemini-4-argon"]["requires"]
