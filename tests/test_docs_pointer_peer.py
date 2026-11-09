"""Check immutable cross-repository pointer partner selection and refusals."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "docs_pointer_peer", Path(__file__).resolve().parents[1]
    / "scripts/review/docs_pointer_peer.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PointerPeerTests(unittest.TestCase):
    """Ensure explicit partners cannot silently select branches or arbitrary refs."""

    def resolve(self, content: object, number: str = "477") -> str:
        """Resolve a synthetic registry without touching live repository metadata."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "peers.json"
            path.write_text(json.dumps(content), encoding="utf-8")
            return MODULE.paired_ref(path, number)

    def test_exact_pin(self) -> None:
        """Different branch names can pair using an immutable PT commit."""
        self.assertEqual(self.resolve({"477": "a" * 40}), "a" * 40)

    def test_unpaired_pull_uses_legacy_lookup(self) -> None:
        """An unrelated PR or main run does not inherit another PR's pin."""
        self.assertEqual(self.resolve({"477": "a" * 40}, "478"), "")
        self.assertEqual(self.resolve({"477": "a" * 40}, ""), "")

    def test_invalid_registry_refuses(self) -> None:
        """Mutable refs, output injection and malformed registries fail closed."""
        for content in [[], {"477": "main"}, {"477": 123},
                        {"0": "a" * 40}, {"477": "a" * 40 + "\nref=main"}]:
            with self.subTest(content=content), self.assertRaises(ValueError):
                self.resolve(content)

    def test_pinned_checkout_is_not_allowed_to_fallback(self) -> None:
        """A failed explicit checkout must fail the job, not test unrelated main."""
        workflow = (Path(__file__).resolve().parents[1]
                    / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        step = workflow.split("- name: Checkout explicit Perpetua-Tools partner", 1)[1]
        step = step.split("- name:", 1)[0]
        self.assertNotIn("continue-on-error", step)
        self.assertIn("steps.pt-pointer-partner.outputs.ref", step)

    def test_review_stack_has_explicit_published_partners(self) -> None:
        """Every review-stack layer uses its matching immutable PT producer."""
        path = Path(__file__).resolve().parents[1] / "config/docs-pointer-peers.json"
        expected = {
            "481": "e6cb79e7f3b0220b2e1e50c263aca85bcd31d233",
            "482": "f5815e03a4ba9de6df3991b8e1e569fd701194b4",
            "483": "f5815e03a4ba9de6df3991b8e1e569fd701194b4",
        }
        for number, sha in expected.items():
            with self.subTest(pull=number):
                self.assertEqual(MODULE.paired_ref(path, number), sha)


if __name__ == "__main__":
    unittest.main()
