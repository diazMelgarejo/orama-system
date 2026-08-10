from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE = Path(__file__).parents[1] / "scripts/verify_mastery_convergence.py"
SPEC = importlib.util.spec_from_file_location("verify_mastery_convergence", MODULE)
assert SPEC and SPEC.loader
verify_mastery = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verify_mastery
SPEC.loader.exec_module(verify_mastery)


def test_mastery_convergence_gate_passes_current_v1() -> None:
    verify_mastery.verify()


def test_p3_sentinels_are_explicitly_out_of_scope() -> None:
    rendered = {str(path.relative_to(verify_mastery.ROOT)) for path in verify_mastery.P3_SENTINELS}
    assert "skills/prompt-engineering/SKILL.md" in rendered
    assert "skills/spec-contract/SKILL.md" in rendered
    assert "core/frugality_router.py" in rendered
    assert ".github/workflows/mastery-eval.yml" in rendered
