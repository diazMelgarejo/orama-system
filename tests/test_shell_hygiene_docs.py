"""The rule table in shell-hygiene/SKILL.md is generated from the shell-gotchas registry."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOTCHAS = ROOT / "bin/orama-system/skills/shell-hygiene/hooks/shell-gotchas.py"
SKILL = ROOT / "bin/orama-system/skills/shell-hygiene/SKILL.md"


def test_skill_rule_table_equals_the_registry() -> None:
    """The table in shell-hygiene/SKILL.md is generated: it must equal `--markdown`."""
    block = re.search(r"<!-- shell-gotchas:begin -->\n(.*?)\n<!-- shell-gotchas:end -->", SKILL.read_text(encoding="utf-8"), re.S)
    assert block is not None, "SKILL.md lost its shell-gotchas block"
    rendered = subprocess.run([sys.executable, str(GOTCHAS), "--markdown"], capture_output=True, text=True, check=True).stdout
    assert block.group(1) == rendered.rstrip("\n"), "regenerate the table with shell-gotchas.py --markdown"
