from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).parent.parent
VALIDATOR_PATH = ROOT / "scripts" / "review" / "check_orama_skills.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("check_orama_skills", VALIDATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_skill(tmp_path: Path, name: str, body: str) -> Path:
    skill_dir = tmp_path / "bin" / "orama-system" / "skills" / name
    skill_dir.mkdir(parents=True)
    path = skill_dir / "SKILL.md"
    path.write_text(body, encoding="utf-8")
    return path


def rules(findings) -> set[str]:
    return {finding.rule for finding in findings}


def test_parse_frontmatter_reads_folded_and_list_fields():
    validator = load_validator()
    text = """---
name: sample-skill
description: >-
  Use when the user asks for sample work.
paths:
  - "bin/orama-system/skills/**"
---
# Body
"""

    frontmatter = validator.parse_frontmatter(text)

    assert frontmatter["name"] == "sample-skill"
    assert frontmatter["description"] == "Use when the user asks for sample work."
    assert frontmatter["paths"] == ["bin/orama-system/skills/**"]


def test_closing_fence_is_not_reported_as_missing_language(tmp_path):
    validator = load_validator()
    skill = write_skill(
        tmp_path,
        "sample-skill",
        """---
name: sample-skill
description: Use when the user asks for sample work.
when_to_use: Activates for sample checks.
effort: low
---
# Sample

```python
print("ok")
```

## When Not To Use
Do not use for unrelated work.

## Glossary
Jargon is defined once.

Use imperative runbook voice.
""",
    )

    findings = validator.validate_skill(skill, tmp_path, strict=False)

    assert "markdown.code-fence" not in rules(findings)


def test_opening_fence_without_language_is_reported(tmp_path):
    validator = load_validator()
    skill = write_skill(
        tmp_path,
        "sample-skill",
        """---
name: sample-skill
description: Use when the user asks for sample work.
---
```
missing language
```
""",
    )

    findings = validator.validate_skill(skill, tmp_path, strict=False)

    assert "markdown.code-fence" in rules(findings)


def test_reference_link_depth_only_warns_beyond_one_parent(tmp_path):
    validator = load_validator()
    cases = [
        ("one-level", "[ok](../references/foo.md)", False),
        ("too-deep", "[bad](../../references/foo.md)", True),
    ]
    for name, link, should_warn in cases:
        skill = write_skill(
            tmp_path,
            name,
            f"""---
name: {name}
description: Use when the user asks for link checks.
---
{link}
""",
        )
        has_warning = "references.one-level" in rules(
            validator.validate_skill(skill, tmp_path, strict=False)
        )
        assert has_warning is should_warn


def test_personal_path_detection(tmp_path):
    validator = load_validator()
    skill = write_skill(
        tmp_path,
        "sample-skill",
        """---
name: sample-skill
description: Use when the user asks for path checks.
---
See /Users/janedoe/repo/secret-layout for old notes.
""",
    )

    findings = validator.validate_skill(skill, tmp_path, strict=False)

    assert "opsec.personal-path" in rules(findings)


def test_strict_mode_fails_on_unallowed_warnings_and_passes_allowed_warning(tmp_path):
    validator = load_validator()
    write_skill(
        tmp_path,
        "sample-skill",
        """---
name: sample-skill
description: Use when the user asks for sample work.
---
# Sample
""",
    )

    strict_result = validator.main([str(tmp_path), "--mode", "strict", "--scan-root", "bin/orama-system/skills"])
    allowed_result = validator.main([
        str(tmp_path),
        "--mode",
        "strict",
        "--scan-root",
        "bin/orama-system/skills",
        "--allow-warning",
        "usability.when-not-to-use",
        "--allow-warning",
        "distillation.jargon",
        "--allow-warning",
        "distillation.voice",
    ])

    assert strict_result == 1
    assert allowed_result == 0
