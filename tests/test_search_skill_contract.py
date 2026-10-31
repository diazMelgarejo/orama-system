"""The search skills keep the 7-tier order, and each skill's manifest covers the tools it documents."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "bin/orama-system/skills"
DEEP = SKILLS / "deep-research/SKILL.md"
FIRECRAWL = SKILLS / "firecrawl/SKILL.md"
DEGRADATION = SKILLS / "oramasys-method/references/graceful-degradation.md"
TOOL_NAME = re.compile(r"\b(?:firecrawl_[a-z_]+|web_(?:search|fetch)_[a-z_]*exa|crawling_exa)\b")
GROUPED = re.compile(r"`(firecrawl_(?:monitor|research|agent))_[a-z_]+`((?:\s*/\s*`_[a-z_]+`)+)")
MARKDOWN_LINK = re.compile(r"\]\((?!https?://|#|url\))([^)#\s]+)")  # the report template's placeholder is (url)
TARGET_SKILL_LINES = 200


def allowed_tools(path: Path) -> set[str]:
    line = next(l for l in path.read_text().splitlines() if l.startswith("allowed-tools:"))
    return {name.strip() for name in line.split(":", 1)[1].split(",")}


def documented_tools(path: Path) -> set[str]:
    text = path.read_text().split("---", 2)[2]
    names = set(TOOL_NAME.findall(text))
    for prefix, rest in GROUPED.findall(text):
        names |= {prefix + suffix for suffix in re.findall(r"`(_[a-z_]+)`", rest)}
    return names


def section(text: str, heading: str) -> str:
    start = text.index(heading)
    following = re.search(r"^#{1,3} ", text[start + len(heading):], re.M)
    return text[start:start + len(heading) + following.start()] if following else text[start:]


@pytest.mark.parametrize("skill", [DEEP, FIRECRAWL])
def test_the_manifest_covers_every_tool_the_skill_documents(skill: Path) -> None:
    assert documented_tools(skill) - allowed_tools(skill) == set()


def test_firecrawl_keeps_its_existing_entries_and_authentication() -> None:
    assert {"Read", "Write", "Bash", "firecrawl_search", "firecrawl_scrape"} <= allowed_tools(FIRECRAWL)
    assert {"mcp__firecrawl__authenticate", "mcp__firecrawl__complete_authentication"} <= allowed_tools(FIRECRAWL)


def test_deep_research_needs_tiers_one_to_five_everywhere_it_says_so() -> None:
    text = DEEP.read_text()
    assert "Run tiers 1 to 5" in text
    assert "tiers 1 to 3" not in text


def test_normal_discovery_is_exa_and_firecrawl_stays_downstream() -> None:
    discover = section(DEEP.read_text(), "### Step 3:")
    assert "web_search_exa" in discover
    assert "firecrawl_search(" not in discover


def test_each_connected_server_case_is_spelled_out_and_unavailable_tools_are_never_called() -> None:
    text = DEEP.read_text()
    for case in ("EXA and Firecrawl", "EXA only", "Firecrawl only", "Neither"):
        assert f"| {case} |" in text
    assert "Never call a tool the session does not have" in text


def test_firecrawl_only_discovery_is_the_labelled_fallback() -> None:
    row = next(l for l in DEEP.read_text().splitlines() if l.startswith("| Firecrawl only |"))
    assert "firecrawl_search" in row and "degraded" in row.lower()


def test_firecrawl_preserves_the_tier_six_gate_for_exa() -> None:
    text = FIRECRAWL.read_text()
    assert "EXA when the request is broad" not in text
    assert "EXA is tier 6" in text
    assert "tiers 1 to 5" in section(text, "### EXA-first, Firecrawl-second verification pattern")


def test_the_fallback_table_walks_every_paid_tier_in_order() -> None:
    table = section(DEGRADATION.read_text(), "## Ladder A")
    rows = [line for line in table.splitlines() if line.startswith("| ")]
    steps = [row.split("|")[1].strip() for row in rows]
    assert steps.index("Perplexity") < steps.index("EXA + Firecrawl") < steps.index("Grok")
    assert "Grok" in next(row for row in rows if row.startswith("| EXA + Firecrawl")).split("|")[3]
    assert "EXA + Firecrawl" in next(row for row in rows if row.startswith("| Perplexity")).split("|")[3]


def test_cursor_reaches_exa_through_the_shared_wrapper() -> None:
    for name in (".cursor/mcp.json", ".cursor/mcp-configs/mcp-servers.json"):
        server = json.loads((ROOT / name).read_text())["mcpServers"]["exa"]
        assert server["command"] == "bash"
        assert "scripts/exa/exa-mcp-wrapper.sh" in " ".join(server["args"])
        assert "mcp-remote" not in json.dumps(server)


@pytest.mark.parametrize("harness", ["kimi", "windsurf"])
def test_every_hosted_exa_template_is_a_documented_exception(harness: str) -> None:
    config = json.loads((ROOT / f"bin/orama-system/config/{harness}-mcp.stack.json").read_text())
    assert "mcp.exa.ai" in " ".join(config["mcpServers"]["exa"]["args"])
    transports = (SKILLS / "deep-research/references/transports.md").read_text()
    assert f"{harness}-mcp.stack.json" in transports


def test_the_firecrawl_setup_and_repository_ownership_are_explained() -> None:
    transports = (SKILLS / "deep-research/references/transports.md").read_text()
    assert "## Why Firecrawl is set up this way" in transports
    assert "## Who owns what across the two repositories" in transports


def test_no_template_holds_an_exa_key() -> None:
    for name in (".cursor/mcp.json", ".cursor/mcp-configs/mcp-servers.json"):
        assert "EXA_API_KEY" not in json.dumps(json.loads((ROOT / name).read_text())["mcpServers"]["exa"])


def test_the_entry_point_is_concise_and_every_part_moved_is_reachable() -> None:
    folder = DEEP.parent
    assert len(DEEP.read_text().splitlines()) <= TARGET_SKILL_LINES
    for name in ("transports.md", "report-template.md", "evidence-and-roles.md", "depth-and-examples.md"):
        assert (folder / "references" / name).is_file()
        assert f"references/{name}" in DEEP.read_text()


@pytest.mark.parametrize("path", [DEEP, *sorted((DEEP.parent / "references").glob("*.md"))], ids=lambda p: p.name)
def test_every_relative_link_resolves(path: Path) -> None:
    for target in MARKDOWN_LINK.findall(path.read_text()):
        assert (path.parent / target).exists(), target
