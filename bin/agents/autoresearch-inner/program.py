"""Inner program: propose, measure, keep or revert. The legacy entry point is dry only."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from collections.abc import Callable
from typing import Any


def _cycle() -> ModuleType:
    """Load the shared cycle implementation without selecting a provider or launching it."""
    path = Path(__file__).resolve().parents[1] / "biafra_cycle.py"
    spec = importlib.util.spec_from_file_location("biafra_cycle", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run(
    task_type: str,
    metric_before: float,
    metric_after: float,
    log_dir: Path,
    artifact: str = "train.py",
    evaluator_digest: str | None = None,
    hypothesis: str = "dry cycle",
    metric_name: str = "metric",
    attempt_id: str | None = None,
    mechanism_card: dict | None = None,
) -> dict:
    """Run this seat's dry program; armed callers must adopt the governed live interface."""
    return _cycle().run_program(
        "inner", task_type, metric_before, metric_after, log_dir, artifact, evaluator_digest, hypothesis,
        metric_name, attempt_id, mechanism_card,
    )


def run_live(
    task_type: str, prompt: str, log_dir: Path,
    evaluate: Callable[[str], dict[str, Any]], metric_before: float, **kwargs: Any,
) -> dict:
    """One live attempt for this seat. Requires the gate, arm, pin, probe evidence and spend guard; see `live_cycle`."""
    return _cycle().live_cycle("inner", task_type, prompt, log_dir, evaluate, metric_before, **kwargs)

