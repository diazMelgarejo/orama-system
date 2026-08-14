"""Tests for the non-mutating PR-body reminder."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/git/remind-pr-body-append-only.sh"


def test_reminder_defaults_cursor_agents_to_comments_and_names_grant_exception(
    tmp_path: Path,
) -> None:
    fake_gh = tmp_path / "gh"
    fake_gh.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' '123 https://github.com/example/repo/pull/123 Draft title'\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)
    env = os.environ | {"PATH": f"{tmp_path}:{os.environ['PATH']}"}

    result = subprocess.run(
        ["bash", str(SCRIPT), "feature/comment-only"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "LAYER 0 — COMMENT ONLY. Cursor agents must NOT change" in result.stdout
    assert "ManagePullRequest post_comment  OR  gh pr comment" in result.stdout
    assert "append-pr-body.sh without operator grant" in result.stdout
    assert "grant-pr-body-human-override.sh first" in result.stdout
