"""Outer program: read the log, rewrite the search, revert when the metric rises. Dry unless the operator arms the launcher."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _cycle():
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
    artifact: str = "search-rule",
    evaluator_digest: str | None = None,
    hypothesis: str = "dry cycle",
    metric_name: str = "metric",
    attempt_id: str | None = None,
) -> dict:
    return _cycle().run_program(
        "outer", task_type, metric_before, metric_after, log_dir, artifact, evaluator_digest, hypothesis,
        metric_name, attempt_id,
    )
