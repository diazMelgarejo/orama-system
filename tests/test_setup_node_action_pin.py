"""Protect CI from mistyped immutable setup-node action references."""

from pathlib import Path

import pytest
import yaml


@pytest.mark.parametrize(
    ("filename", "job_name"),
    [("ci.yml", "test"), ("markdown-lint.yml", "lint"),
     ("markdown-lint.yml", "debt"), ("test.yml", "test")],
)
def test_setup_node_commit_matches_verified_v4_release(filename: str, job_name: str) -> None:
    """Immutable setup-node references use the commit verified upstream."""
    path = Path(__file__).resolve().parents[1] / ".github/workflows" / filename
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    refs = [
        step["uses"].split("@", 1)[1]
        for step in workflow["jobs"][job_name]["steps"]
        if str(step.get("uses", "")).startswith("actions/setup-node@")
    ]
    assert refs == ["49933ea5288caeca8642d1e84afbd3f7d6820020"]


def test_full_test_workflow_installs_markdown_before_pytest() -> None:
    """The full suite provisions the real linter before integration tests run."""
    path = Path(__file__).resolve().parents[1] / ".github/workflows/test.yml"
    workflow = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    steps = workflow["jobs"]["test"]["steps"]
    install = next(
        index for index, step in enumerate(steps)
        if "npm install" in step.get("run", "")
        and "markdownlint-cli2@0.17.2" in step["run"]
    )
    run_tests = next(index for index, step in enumerate(steps) if step.get("name") == "Run pytest")
    assert install < run_tests
    assert workflow["on"]["pull_request"]["branches"] == ["**"]
