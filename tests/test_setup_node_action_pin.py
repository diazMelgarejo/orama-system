"""Protect CI from mistyped immutable setup-node action references."""

from pathlib import Path

import pytest
import yaml


@pytest.mark.parametrize("filename", ["ci.yml", "markdown-lint.yml"])
def test_setup_node_commit_matches_verified_v4_release(filename: str) -> None:
    """Immutable setup-node references use the commit verified upstream."""
    path = Path(__file__).resolve().parents[1] / ".github/workflows" / filename
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    refs = [
        step["uses"].split("@", 1)[1]
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if str(step.get("uses", "")).startswith("actions/setup-node@")
    ]
    assert refs, "The workflow must exercise Node provisioning"
    immutable = [ref for ref in refs if not ref.startswith("v")]
    assert immutable, "Reviewed immutable action references must remain pinned"
    assert set(immutable) == {"49933ea5288caeca8642d1e84afbd3f7d6820020"}
