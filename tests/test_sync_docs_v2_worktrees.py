"""Ensure canonical decision pointers are generated in linked worktrees."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/git/sync-docs-v2-pointers.sh"
WRAPPER = Path(__file__).resolve().parents[1] / "scripts/check_docs_v2_pointer_sync.sh"


class PointerWorktreeTests(unittest.TestCase):
    """Exercise generation and drift refusal through the real shell entrypoint."""

    def test_linked_worktree_is_not_silently_skipped(self) -> None:
        """A .git file is a valid repository marker, not a successful no-op."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, linked = root / "repo", root / "linked"
            env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
            subprocess.run(["git", "init", "-q", str(repo)], env=env, check=True)
            subprocess.run(
                ["git", "-C", str(repo), "-c", "user.name=fixture", "-c",
                 "user.email=fixture@example.invalid", "commit", "--allow-empty", "-qm", "fixture"],
                env=env, check=True,
            )
            subprocess.run(
                ["git", "-C", str(repo), "worktree", "add", "--detach", "-q", str(linked)],
                env=env, check=True,
            )
            self.assertTrue((linked / ".git").is_file())
            generated = subprocess.run(
                ["bash", str(SCRIPT), str(linked)], env=env, capture_output=True, text=True,
            )
            self.assertEqual(generated.returncode, 0, generated.stderr)
            pointer = linked / "docs/adr/ADR-002-multi-llm-router-caching-batching-decorator.md"
            self.assertTrue(pointer.is_file(), generated.stderr)
            checked = subprocess.run(
                ["bash", str(SCRIPT), "--check", str(linked)], env=env, capture_output=True, text=True,
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)
            wrapper_env = {**env, "PERPETUA_TOOLS_ROOT": str(linked),
                           "GIT_DIR": str(root / "missing-git-dir"),
                           "GIT_WORK_TREE": str(root / "missing-worktree")}
            wrapper_check = subprocess.run(
                ["bash", str(WRAPPER)], env=wrapper_env, capture_output=True, text=True,
            )
            self.assertEqual(wrapper_check.returncode, 0, wrapper_check.stderr)
            self.assertIn("in sync", wrapper_check.stdout)
            pointer.write_text("stale pointer\n", encoding="utf-8")
            drift = subprocess.run(
                ["bash", str(SCRIPT), "--check", str(linked)], env=env, capture_output=True, text=True,
            )
            self.assertNotEqual(drift.returncode, 0)
            wrapper_drift = subprocess.run(
                ["bash", str(WRAPPER)], env=wrapper_env, capture_output=True, text=True,
            )
            self.assertNotEqual(wrapper_drift.returncode, 0, wrapper_drift.stderr)
            self.assertIn("DRIFT:", wrapper_drift.stderr)


if __name__ == "__main__":
    unittest.main()
