"""OpenRouter policy ordering tests.

These tests pin the intended merge/verify behavior so Gemini cannot creep back
into the default fallback chain ahead of OpenRouter.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent.parent
POLICY_PATH = REPO_ROOT / "deployments" / "macbook-pro-head" / "openclaw" / "openclaw.model-policy.jsonc"
APPLY_SCRIPT = REPO_ROOT / "scripts" / "apply-openrouter-free-defaults.sh"
VERIFY_SCRIPT = REPO_ROOT / "scripts" / "verify-openrouter-models.sh"


def _load_jsonc(path: Path) -> dict:
    """Parse the checked-in policy subset after stripping line comments."""
    raw = path.read_text(encoding="utf-8")
    stripped = re.sub(r"(?m)^[ \t]*//.*$", "", raw)
    stripped = re.sub(r"(?<!:)//[^\n]*$", "", stripped)
    return json.loads(stripped)


def test_policy_places_openrouter_before_gemini() -> None:
    """Preserve economical routing before the only automatic Google fallback."""
    policy = _load_jsonc(POLICY_PATH)
    fallbacks = policy["agents"]["defaults"]["model"]["fallbacks_to_merge"]

    assert "openrouter/openrouter/free" in fallbacks
    assert "gemini-fallback/gemini-flash-latest" in fallbacks
    assert "google/gemini-3.8-flash" not in fallbacks
    assert fallbacks.index("openrouter/openrouter/free") < fallbacks.index("gemini-fallback/gemini-flash-latest")


def test_policy_merges_exact_provider_references_into_allowlist() -> None:
    """Register configured custom providers without inventing OpenRouter aliases."""
    policy = _load_jsonc(POLICY_PATH)
    models_to_merge = policy["agents"]["defaults"]["models_to_merge"]

    assert set(models_to_merge) == {
        "openrouter/openrouter/free", "gemini-main/gemini-3.8-flash",
        "gemini-fallback/gemini-flash-latest",
    }
    assert all(value["id"] == key for key, value in models_to_merge.items())


def test_apply_script_strips_gemini_from_existing_fallbacks() -> None:
    """Rebuild fallback ordering rather than retaining a stale Google-first chain."""
    script = APPLY_SCRIPT.read_text(encoding="utf-8")
    policy = _load_jsonc(POLICY_PATH)

    assert 'test("(^|/)gemini"; "i")' in script
    assert "fallbacks_to_merge" in script
    assert "openrouter/openrouter/free" in policy["agents"]["defaults"]["model"]["fallbacks_to_merge"]


def test_verify_script_checks_openrouter_before_gemini() -> None:
    """Keep the deployment verifier aligned with the policy ordering contract."""
    script = VERIFY_SCRIPT.read_text(encoding="utf-8")

    assert "first_nonlocal" in script
    assert "first_openrouter_index" in script
    assert "first_gemini_index" in script
    assert "Gemini relegated behind OpenRouter" in script
