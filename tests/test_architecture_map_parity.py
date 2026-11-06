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

    def test_allows_escaped_pipe_in_audience_detail(self) -> None:
        """An escaped pipe is content, not an additional audience column."""
        right = document(ROWS).replace("Local record", r"local foo \| bar")
        result = self.check_maps(document(ROWS), right)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_preserves_escaped_pipe_in_shared_meaning(self) -> None:
        """Shared cells containing escaped pipes still compare their full content."""
        rows = {**ROWS, "Evidence": r"Sources \| tests support bounded claims."}
        result = self.check_maps(document(rows), document(rows))
        self.assertEqual(result.returncode, 0, result.stderr)
        changed = document(rows).replace("Sources", "Unsupported")
        result = self.check_maps(document(rows), changed)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Evidence", result.stderr)

    def test_rejects_taxonomy_only_inside_a_fence(self) -> None:
        """Backtick and tilde examples do not supply the map's actual taxonomy."""
        for marker in ("```", "~~~"):
            with self.subTest(marker=marker):
                fenced = f"{marker}markdown\n{document(ROWS)}\n{marker}\n"
                result = self.check_maps(document(ROWS), fenced)
                self.assertEqual(result.returncode, 1)
                self.assertIn("table", result.stderr)

    def test_ignores_fenced_example_beside_real_taxonomy(self) -> None:
        """Examples before or after the real table do not create duplicate headers."""
        for marker in ("```", "~~~"):
            for before in (True, False):
                with self.subTest(marker=marker, before=before):
                    example = f"{marker}markdown\n{document(ROWS)}\n{marker}\n"
                    real = document(ROWS)
                    right = example + real if before else real + "\n" + example
                    result = self.check_maps(document(ROWS), right)
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_fence_requires_matching_marker_and_sufficient_length(self) -> None:
        """Shorter or different fence markers cannot expose an enclosed taxonomy."""
        for interior in ("```", "~~~~"):
            with self.subTest(interior=interior):
                right = f"````markdown\n{interior}\n{document(ROWS)}\n````\n"
                result = self.check_maps(document(ROWS), right)
                self.assertEqual(result.returncode, 1)
                self.assertIn("table", result.stderr)

    def test_unclosed_fence_keeps_taxonomy_hidden(self) -> None:
        """A missing closing fence does not turn its example into a real table."""
        result = self.check_maps(document(ROWS), "```markdown\n" + document(ROWS))
        self.assertEqual(result.returncode, 1)
        self.assertIn("table", result.stderr)

    def test_rejects_invalid_separator(self) -> None:
        """An otherwise matching table still needs a valid Markdown separator."""
        right = document(ROWS).replace("| --- | --- | --- |", "| --- | not-a-rule | --- |")
        result = self.check_maps(document(ROWS), right)
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid table separator", result.stderr)

    def test_rejects_missing_audience_column(self) -> None:
        """A taxonomy row missing its audience-specific field is malformed."""
        right = document(ROWS).replace(
            "| Evidence | Support for bounded claims. | Local record |",
            "| Evidence | Support for bounded claims. |",
        )
        result = self.check_maps(document(ROWS), right)
        self.assertEqual(result.returncode, 1)
        self.assertIn("malformed shared-meaning table row", result.stderr)

    def test_rejects_indented_example_only(self) -> None:
        """A four-space or tab-indented code example cannot supply the taxonomy."""
        for indent in ("    ", "\t"):
            with self.subTest(indent=indent):
                example = "\n".join(indent + line for line in document(ROWS).splitlines())
                result = self.check_maps(document(ROWS), example)
                self.assertEqual(result.returncode, 1)
                self.assertIn("table", result.stderr)

    def test_ignores_indented_example_beside_table(self) -> None:
        """An indented code block beside the rendered taxonomy is not a duplicate."""
        example = "\n".join("    " + line for line in document(ROWS).splitlines())
        for right in (example + "\n\n" + document(ROWS), document(ROWS) + "\n\n" + example):
            result = self.check_maps(document(ROWS), right)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_keeps_indented_table_body(self) -> None:
        """Indentation inside an already open table does not start a code block."""
        right = document(ROWS)
        for name, meaning in ROWS.items():
            right = right.replace(f"| {name} | {meaning}", f"    | {name} | {meaning}")
        result = self.check_maps(document(ROWS), right)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_excludes_code_after_setext_heading(self) -> None:
        """A Setext heading ends the paragraph before an indented code example."""
        example = "\n".join("    " + line for line in document(ROWS).splitlines()[4:])
        for underline in ("====", "-", "--"):
            with self.subTest(underline=underline):
                right = f"Example\n{underline}\n{example}\n"
                result = self.check_maps(document(ROWS), right)
                self.assertEqual(result.returncode, 1)
                self.assertIn("table", result.stderr)

    def test_setext_example_beside_real_table(self) -> None:
        """A heading's indented example does not duplicate a real taxonomy."""
        example = "\n".join("    " + line for line in document(ROWS).splitlines()[4:])
        for underline in ("====", "-", "--"):
            with self.subTest(underline=underline):
                right = f"Example\n{underline}\n{example}\n\n" + document(ROWS)
                result = self.check_maps(document(ROWS), right)
                self.assertEqual(result.returncode, 0, result.stderr)

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
