#!/usr/bin/env python3
"""Package a canonical orama-system skill into a distributable .skill file.

Stage -> trim -> validate -> zip, so `oramasys-skillify` can produce a
.skill installable via claude.ai / Claude Desktop's Settings -> Capabilities
(CLI users already get the skill via install-skills.sh's directory copy to
~/.claude/skills/ — this script is the OTHER distribution path).

Validation rules and the zip step are a from-scratch reimplementation of
the logic in Anthropic's official skill-creator plugin
(https://github.com/anthropics/claude-plugins-official/tree/main/plugins/
skill-creator, Apache 2.0) — scripts/quick_validate.py's ALLOWED_PROPERTIES/
name/description rules and scripts/package_skill.py's zip-with-excludes
behavior, fetched 2026-07-22 and cited here per Apache 2.0 attribution.
Not vendored verbatim: orama's canonical SKILL.md files use extra
frontmatter keys (version, parent_skill, triggers, when_to_use, ...) and
../../references/ links two levels up that Anthropic's schema and package
layout don't support, so staging (this script's stage_skill()) trims/
bundles those before the same validate+zip rules apply.

Usage:
    python3 package_skill.py <path/to/canonical/skill> [output-dir]

Example:
    python3 package_skill.py bin/orama-system/skills/skillify ./dist
"""
from __future__ import annotations

import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

# Anthropic's packaged-skill frontmatter schema (quick_validate.py,
# ALLOWED_PROPERTIES). Anything else found in a canonical SKILL.md's
# frontmatter is moved under `metadata:` rather than dropped.
ALLOWED_PROPERTIES = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
DESCRIPTION_MAX = 1024
NAME_MAX = 64
COMPATIBILITY_MAX = 500

EXCLUDE_DIRS = {"__pycache__", "node_modules"}
EXCLUDE_FILES = {".DS_Store"}
EXCLUDE_SUFFIXES = {".pyc"}


def _truncate(value: str, limit: int) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    cut = value[: limit - 1]
    space = cut.rfind(" ")
    return (cut[:space] if space > limit // 3 else cut).rstrip(" ,.;") + "…"


def _split_frontmatter(text: str) -> tuple[str, str] | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    body_end = text.find("\n", end + 1)
    body_end = body_end + 1 if body_end != -1 else len(text)
    return text[3:end], text[body_end:]


def _parse_frontmatter_kv(fm_text: str) -> dict[str, str]:
    """Minimal top-level `key: value` / `key: >-` block-scalar parser.

    Not a general YAML parser — this repo's canonical SKILL.md frontmatter
    is a flat top-level map with folded/literal scalars and simple lists,
    which is all skillify itself ever writes. Good enough to move unknown
    keys under metadata: without a PyYAML dependency.
    """
    lines = fm_text.splitlines()
    result: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, value = m.group(1), m.group(2).strip()
        if value in (">", ">-", ">+", "|", "|-", "|+", ""):
            collected = []
            i += 1
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or lines[i].strip() == ""):
                if lines[i].strip():
                    collected.append(lines[i].strip().lstrip("- "))
                i += 1
            value = " ".join(collected) if value.startswith((">", "")) else "\n".join(collected)
            result[key] = value.strip()
            continue
        result[key] = value.strip('"').strip("'")
        i += 1
    return result


def trim_frontmatter(fm_text: str) -> tuple[str, list[str]]:
    """Return (new frontmatter text, list of keys moved under metadata)."""
    kv = _parse_frontmatter_kv(fm_text)
    extra = {k: v for k, v in kv.items() if k not in ALLOWED_PROPERTIES}
    kept = {k: v for k, v in kv.items() if k in ALLOWED_PROPERTIES}

    if "description" in kept:
        kept["description"] = _truncate(kept["description"].replace("<", "(").replace(">", ")"), DESCRIPTION_MAX)
    if "name" in kept:
        kept["name"] = kept["name"][:NAME_MAX]
    if "compatibility" in kept:
        kept["compatibility"] = _truncate(kept["compatibility"], COMPATIBILITY_MAX)

    lines = []
    for key in ("name", "description", "license", "compatibility", "allowed-tools"):
        if key in kept:
            val = kept[key]
            if "\n" in val or len(val) > 100:
                lines.append(f'{key}: "{val}"')
            else:
                lines.append(f"{key}: {val}")
    if extra:
        lines.append("metadata:")
        for k, v in sorted(extra.items()):
            v_str = v.replace("\n", " ").strip()
            lines.append(f'  {k}: "{v_str}"')
    return "\n".join(lines), sorted(extra.keys())


# Repo-wide `bin/orama-system/references/*.md` cards get cited two
# different ways in this repo's canonical SKILL.md files: as a real
# markdown link two levels up (`[text](../../references/foo.md)`) or as a
# plain backtick-quoted path, either relative (`` `../../references/foo.md` ``)
# or repo-root-relative (`` `bin/orama-system/references/foo.md` ``). Catch
# all three — matching only the markdown-link form silently drops the
# backtick-only citations, which was found and fixed 2026-07-22 when
# oramasys-method's `../../references/contribution-standards.md` and
# `.../skill-architecture-guide.md` (both backtick-only) packaged as dead
# references while an unrelated markdown-link citation got bundled instead.
CROSS_REPO_REF_RE = re.compile(
    r"(?:\.\./\.\./references/|bin/orama-system/references/)([A-Za-z0-9_-]+\.md)"
)


def bundle_cross_repo_references(staged_dir: Path, repo_references_dir: Path) -> list[str]:
    """Rewrite every `../../references/<f>.md` or `bin/orama-system/references/
    <f>.md` citation (repo-wide refs, cited either as a real markdown link or
    a plain backtick-quoted path) to a one-level-away `references/<f>.md`
    inside the staged copy, copying the referenced file in. A packaged
    .skill is used outside this repository, so it can't resolve a path that
    assumes the repo checkout still surrounds it.
    """
    bundled: list[str] = []
    for md_file in list(staged_dir.rglob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        fnames = set(CROSS_REPO_REF_RE.findall(text))
        if not fnames:
            continue
        new_text = text
        for fname in fnames:
            src = repo_references_dir / fname
            if not src.is_file():
                continue
            dest_dir = staged_dir / "references"
            dest_dir.mkdir(exist_ok=True)
            dest = dest_dir / fname
            if not dest.exists():
                shutil.copy2(src, dest)
                bundled.append(fname)
            new_text = new_text.replace(f"../../references/{fname}", f"references/{fname}")
            new_text = new_text.replace(f"bin/orama-system/references/{fname}", f"references/{fname}")
        if new_text != text:
            md_file.write_text(new_text, encoding="utf-8")
    return bundled


def stage_skill(skill_path: Path, repo_root: Path) -> tuple[Path, list[str], list[str]]:
    """Copy a canonical skill to a temp dir, bundle cross-repo refs, trim
    frontmatter. Returns (staged_dir, bundled_files, metadata_keys)."""
    tmp_root = Path(tempfile.mkdtemp(prefix="oramasys-skillify-package-"))
    staged_dir = tmp_root / skill_path.name
    shutil.copytree(
        skill_path,
        staged_dir,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )

    repo_references_dir = repo_root / "bin" / "orama-system" / "references"
    bundled = bundle_cross_repo_references(staged_dir, repo_references_dir)

    skill_md = staged_dir / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    split = _split_frontmatter(text)
    if split is None:
        raise ValueError(f"{skill_md}: no YAML frontmatter found")
    fm_text, body = split
    new_fm, metadata_keys = trim_frontmatter(fm_text)
    skill_md.write_text(f"---\n{new_fm}\n---\n{body}", encoding="utf-8")

    return staged_dir, bundled, metadata_keys


def validate_skill(skill_path: Path) -> tuple[bool, str]:
    """Reimplements Anthropic skill-creator's quick_validate.py rules
    (name/description schema conformance) without a PyYAML dependency —
    frontmatter here has already gone through trim_frontmatter()."""
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found"
    split = _split_frontmatter(skill_md.read_text(encoding="utf-8"))
    if split is None:
        return False, "No YAML frontmatter found"
    kv = _parse_frontmatter_kv(split[0])

    unexpected = set(kv.keys()) - ALLOWED_PROPERTIES
    if unexpected:
        return False, f"Unexpected key(s) after trim: {', '.join(sorted(unexpected))}"
    if "name" not in kv:
        return False, "Missing 'name' in frontmatter"
    if "description" not in kv:
        return False, "Missing 'description' in frontmatter"

    name = kv["name"].strip()
    if not re.match(r"^[a-z0-9-]+$", name):
        return False, f"Name '{name}' should be kebab-case (lowercase letters, digits, hyphens only)"
    if name.startswith("-") or name.endswith("-") or "--" in name:
        return False, f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"
    if len(name) > NAME_MAX:
        return False, f"Name is too long ({len(name)} chars, max {NAME_MAX})"

    description = kv["description"].strip()
    if "<" in description or ">" in description:
        return False, "Description cannot contain angle brackets (< or >)"
    if len(description) > DESCRIPTION_MAX:
        return False, f"Description is too long ({len(description)} chars, max {DESCRIPTION_MAX})"

    compatibility = kv.get("compatibility", "")
    if compatibility and len(compatibility) > COMPATIBILITY_MAX:
        return False, f"Compatibility is too long ({len(compatibility)} chars, max {COMPATIBILITY_MAX})"

    return True, "Skill is valid!"


def _should_exclude(rel_path: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in rel_path.parts):
        return True
    if rel_path.name in EXCLUDE_FILES:
        return True
    return rel_path.suffix in EXCLUDE_SUFFIXES


def zip_skill(staged_dir: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    skill_filename = output_dir / f"{staged_dir.name}.skill"
    with zipfile.ZipFile(skill_filename, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in staged_dir.rglob("*"):
            if not file_path.is_file():
                continue
            arcname = file_path.relative_to(staged_dir.parent)
            if _should_exclude(arcname):
                continue
            zf.write(file_path, arcname)
    return skill_filename


def package_skill(skill_path: Path, output_dir: Path, repo_root: Path) -> Path | None:
    print(f"Staging: {skill_path}")
    staged_dir, bundled, metadata_keys = stage_skill(skill_path, repo_root)
    if bundled:
        print(f"  Bundled cross-repo references: {', '.join(bundled)}")
    if metadata_keys:
        print(f"  Moved to metadata: {', '.join(metadata_keys)}")

    ok, message = validate_skill(staged_dir)
    if not ok:
        print(f"Validation failed: {message}")
        shutil.rmtree(staged_dir.parent, ignore_errors=True)
        return None
    print(f"Validated: {message}")

    result = zip_skill(staged_dir, output_dir)
    shutil.rmtree(staged_dir.parent, ignore_errors=True)
    print(f"Packaged: {result}")
    return result


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    skill_path = Path(sys.argv[1]).resolve()
    output_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else Path.cwd() / "dist"
    repo_root = Path(__file__).resolve().parents[5]  # scripts/ -> skillify/ -> skills/ -> orama-system/ -> bin/ -> repo root

    if not skill_path.is_dir():
        print(f"Error: not a directory: {skill_path}")
        return 1
    if not (skill_path / "SKILL.md").is_file():
        print(f"Error: SKILL.md not found in {skill_path}")
        return 1

    result = package_skill(skill_path, output_dir, repo_root)
    return 0 if result else 1


if __name__ == "__main__":
    raise SystemExit(main())
