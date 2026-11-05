"""Exercise the real cross-map CLI without network or project dependencies."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECKER = Path(__file__).resolve().parents[1] / "scripts/review/check_architecture_map_parity.py"
ROWS = {
    "Execution": "State transitions and bounded execution.",
    "Coordination": "Claims, handoffs, leases, and acknowledgements.",
    "Knowledge": "Source relationships and derived knowledge.",
    "Evidence": "Support for bounded claims.",
    "Audit": "Independent review scope and unresolved limits.",
}


def document(rows: dict[str, str]) -> str:
    """Render a minimal architecture map with audience-specific prose."""
    return "\n".join([
        "# Map", "", "Different audience-specific introduction.", "",
        "| Graph | Shared meaning | Local detail |",
        "| --- | --- | --- |",
        *(f"| {name} | {meaning} | Local record |" for name, meaning in rows.items()),
        "", "## Other section", "| Graph | Unrelated |", "| --- | --- |",
        "| Not part of taxonomy | ignored |",
    ])


class ArchitectureMapParityTests(unittest.TestCase):
    """Pin strict taxonomy checks while allowing different map presentations."""

    def check_maps(self, left: str, right: str) -> subprocess.CompletedProcess[str]:
        """Run the shipped checker against two temporary local documents."""
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "v1.md"
            second = Path(directory) / "v2.md"
            first.write_text(left, encoding="utf-8")
            second.write_text(right, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(CHECKER), str(first), str(second)],
                capture_output=True, text=True, check=False,
            )

    def test_allows_audience_prose_row_order_and_whitespace(self) -> None:
        """Equivalent shared meaning passes despite presentation differences."""
        right = document(dict(reversed(list(ROWS.items())))).replace(
            "Different audience-specific introduction.", "Researcher-oriented map."
        ).replace("Support for bounded claims.", "Support  for bounded claims.")
        result = self.check_maps(document(ROWS), right)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("5 shared graph meanings match", result.stdout)

    def test_rejects_meaning_drift(self) -> None:
        """Changing shared meaning cannot pass by keeping the graph name."""
        result = self.check_maps(document(ROWS), document(ROWS).replace(
            "Support for bounded claims.", "Authority to activate serving."
        ))
        self.assertEqual(result.returncode, 1)
        self.assertIn("Evidence", result.stderr)

    def test_rejects_missing_graph_even_when_both_maps_omit_it(self) -> None:
        """Agreement on an incomplete taxonomy is still a failure."""
        incomplete = {name: meaning for name, meaning in ROWS.items() if name != "Audit"}
        result = self.check_maps(document(incomplete), document(incomplete))
        self.assertEqual(result.returncode, 1)
        self.assertIn("Audit", result.stderr)

    def test_rejects_duplicate_graph(self) -> None:
        """A repeated graph cannot silently overwrite the first meaning."""
        duplicate = document(ROWS).replace(
            "## Other section", "| Audit | Conflicting meaning | detail |\n\n## Other section"
        )
        # Keep the duplicate inside the table, not after its terminating blank line.
        duplicate = duplicate.replace("\n\n| Audit |", "\n| Audit |")
        result = self.check_maps(document(ROWS), duplicate)
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate", result.stderr)

    def test_rejects_extra_graph(self) -> None:
        """A sixth graph requires a deliberate checker contract change."""
        result = self.check_maps(document(ROWS), document({**ROWS, "Authority": "Grants."}))
        self.assertEqual(result.returncode, 1)
        self.assertIn("Authority", result.stderr)

    def test_rejects_empty_meaning(self) -> None:
        """A present but blank definition is not a valid shared meaning."""
        result = self.check_maps(document(ROWS), document({**ROWS, "Audit": " "}))
        self.assertEqual(result.returncode, 1)
        self.assertIn("empty", result.stderr)

    def test_rejects_absent_table(self) -> None:
        """Renaming or removing the shared table fails instead of skipping."""
        result = self.check_maps(document(ROWS), "# Missing taxonomy\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("table", result.stderr)

    def test_rejects_multiple_shared_tables(self) -> None:
        """Ambiguous duplicate tables cannot select a convenient passing copy."""
        result = self.check_maps(document(ROWS), document(ROWS) + "\n" + document(ROWS))
        self.assertEqual(result.returncode, 1)
        self.assertIn("table", result.stderr)

    def test_rejects_missing_file(self) -> None:
        """A missing peer is an error, not successful parity or a skip."""
        result = subprocess.run(
            [sys.executable, str(CHECKER), "/nonexistent/v1.md", "/nonexistent/v2.md"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot read", result.stderr)


if __name__ == "__main__":
    unittest.main()
