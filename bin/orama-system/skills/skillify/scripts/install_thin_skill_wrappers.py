#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import re
import shutil
import sys


@dataclass(frozen=True)
class SkillSpec:
    slug: str
    canonical: str
    name: str
    description: str


ROOT = Path(__file__).resolve().parents[6]
HOME = Path.home()


CANONICAL_SKILLS = [
    "perplexity-api/Perpetua-Tools/SKILL.md",
    "perplexity-api/Perpetua-Tools/config/SKILL.md",
    "perplexity-api/Perpetua-Tools/hardware/SKILL.md",
    "perplexity-api/Perpetua-Tools/hardware/startup-intelligence/SKILL.md",
    "orama-system/SKILL.md",
    "orama-system/bin/orama-system/SKILL.md",
    "orama-system/bin/orama-system/afrp/SKILL.md",
    "orama-system/bin/orama-system/cidf/SKILL.md",
    "orama-system/bin/orama-system/gstack/SKILL.md",
    "orama-system/bin/orama-system/skills/agent-methodology/SKILL.md",
    "orama-system/bin/orama-system/skills/code-review/SKILL.md",
    "orama-system/bin/orama-system/skills/ecc-sync/SKILL.md",
    "orama-system/bin/orama-system/skills/first-run-setup/SKILL.md",
    "orama-system/bin/orama-system/skills/git-history-surgery/SKILL.md",
    "orama-system/bin/orama-system/skills/mcp-install/SKILL.md",
    "orama-system/bin/orama-system/skills/mcp-orchestration/SKILL.md",
    "orama-system/bin/orama-system/skills/no-sleep-chains/SKILL.md",
    "orama-system/bin/orama-system/skills/openclaw-skills/SKILL.md",
    "orama-system/bin/orama-system/skills/openclaw-skills/skills/openclaw-add-channel/SKILL.md",
    "orama-system/bin/orama-system/skills/openclaw-skills/skills/openclaw-add-cron/SKILL.md",
    "orama-system/bin/orama-system/skills/openclaw-skills/skills/openclaw-add-script/SKILL.md",
    "orama-system/bin/orama-system/skills/openclaw-skills/skills/openclaw-add-secret/SKILL.md",
    "orama-system/bin/orama-system/skills/openclaw-skills/skills/openclaw-dream-setup/SKILL.md",
    "orama-system/bin/orama-system/skills/openclaw-skills/skills/openclaw-new-agent/SKILL.md",
    "orama-system/bin/orama-system/skills/openclaw-skills/skills/openclaw-restart/SKILL.md",
    "orama-system/bin/orama-system/skills/openclaw-skills/skills/openclaw-status/SKILL.md",
    "orama-system/bin/orama-system/skills/openclaw-skills/skills/openclaw-stow/SKILL.md",
    "orama-system/bin/orama-system/skills/oramasys-method/SKILL.md",
    "orama-system/bin/orama-system/skills/self-discovery/SKILL.md",
    "orama-system/bin/orama-system/skills/self-improve/SKILL.md",
    "orama-system/bin/orama-system/skills/skillify/SKILL.md",
    "orama-system/bin/orama-system/skills/using-git-worktrees/SKILL.md",
]


TARGET_ROOTS = [
    "~/.codex/skills",
    "~/.claude/skills",
    "~/.agents/skills",
    ".agents/skills",
    ".claude/skills",
    "orama-system/.agents/skills",
    "orama-system/.claude/skills",
    "perplexity-api/Perpetua-Tools/.agents/skills",
    "perplexity-api/Perpetua-Tools/.claude/skills",
]


SLUG_OVERRIDES = {
    "perplexity-api/Perpetua-Tools/SKILL.md": "perpetua-tools",
    "perplexity-api/Perpetua-Tools/config/SKILL.md": "perpetua-config",
    "perplexity-api/Perpetua-Tools/hardware/SKILL.md": "perpetua-hardware",
    "perplexity-api/Perpetua-Tools/hardware/startup-intelligence/SKILL.md": "perpetua-startup-intelligence",
    "orama-system/SKILL.md": "orama-repo-rules",
    "orama-system/bin/orama-system/SKILL.md": "orama-system",
    "orama-system/bin/orama-system/afrp/SKILL.md": "orama-afrp",
    "orama-system/bin/orama-system/cidf/SKILL.md": "orama-cidf",
    "orama-system/bin/orama-system/gstack/SKILL.md": "orama-gstack",
}


def slug_for(path: str) -> str:
    if path in SLUG_OVERRIDES:
        return SLUG_OVERRIDES[path]
    parent = Path(path).parent.name
    return re.sub(r"[^a-z0-9-]+", "-", parent.lower()).strip("-")


def _truncate(value: str, limit: int = 240) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    cut = value[:limit]
    space = cut.rfind(" ")
    # snap to a word boundary so we never cut mid-word (e.g. "...Trigger")
    return (cut[:space] if space > 80 else cut).rstrip(" ,.;") + "…"


# Metadata lines that must NOT be mistaken for a description: markdown bold
# (**Version:**), table rows (| ... |), and single-token YAML keys (name:, version:).
# A multi-word prose lead like "Use when: ..." is NOT skipped (space before colon).
_META_LINE = re.compile(r"^(\*\*|\||[A-Za-z][\w-]*:(\s|$))")


def frontmatter_value(text: str, key: str) -> str | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    body = text[3:end]
    match = re.search(rf"^{re.escape(key)}:\s*(.*)$", body, re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip()
    # YAML folded/literal block scalar (`>`, `>-`, `|`, `|-`, or empty): the real
    # value is the indented continuation block, not the indicator on this line.
    if value in {">", ">-", ">+", "|", "|-", "|+", ""}:
        collected = []
        for line in body[match.end():].splitlines():
            if line.strip() == "":
                if collected:
                    break
                continue
            if not line.startswith((" ", "\t")):
                break
            collected.append(line.strip())
        folded = " ".join(collected).strip()
        return folded or None
    return value.strip('"').strip("'") or None


def first_heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "Canonical skill wrapper"


def compact_description(text: str, fallback: str) -> str:
    value = frontmatter_value(text, "description")
    if value and not value.lower().startswith("name:"):
        return _truncate(value)
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "---", ">", "-")):
            continue
        if _META_LINE.match(stripped):
            continue
        return _truncate(stripped)
    return _truncate(fallback)


def build_specs() -> list[SkillSpec]:
    specs = []
    slugs = set()
    for canonical in CANONICAL_SKILLS:
        path = ROOT / canonical
        if not path.is_file():
            raise FileNotFoundError(path)
        text = path.read_text(encoding="utf-8-sig")
        slug = slug_for(canonical)
        if slug in slugs:
            raise ValueError(f"duplicate skill slug: {slug}")
        slugs.add(slug)
        name = frontmatter_value(text, "name") or slug
        description = compact_description(text, first_heading(text))
        specs.append(SkillSpec(slug, canonical, name, description))
    return specs


def target_path(root: str, slug: str) -> Path:
    if root.startswith("~/"):
        root_path = Path(root.replace("~", str(HOME), 1))
    else:
        root_path = ROOT / root
    return root_path / slug / "SKILL.md"


def repo_relative(canonical: str) -> str:
    """Strip the leading workspace/repo-name segment from a workspace-relative
    canonical path so the wrapper references the skill RELATIVE TO ITS OWN REPO
    ROOT — never an absolute workstation path. e.g.
    "orama-system/bin/orama-system/cidf/SKILL.md" -> "bin/orama-system/cidf/SKILL.md".
    """
    return canonical.split("/", 1)[1] if "/" in canonical else canonical


def wrapper(spec: SkillSpec) -> str:
    # PORTABILITY CONTRACT: wrappers MUST be machine-agnostic. NEVER embed an
    # absolute path (ROOT, HOME, /Users/...) — they get committed to public
    # repos and doxx the workstation. The canonical skill lives in the SAME git
    # repo as this wrapper, so reference it repo-relative and resolve the repo
    # root at runtime via `git rev-parse --show-toplevel`. verify() enforces this.
    description = spec.description.replace('"', "'")
    rel = repo_relative(spec.canonical)
    rel_dir = str(Path(rel).parent)
    return f'''---
name: {spec.slug}
description: "{description}"
---

# {spec.name}

This is a thin wrapper. The canonical skill lives in this repo at the path below
(resolve the repo root at runtime — paths are never hardcoded).

- Canonical skill path (repo-relative): `{rel}`

## Before Use

Before relying on the canonical card, check whether the canonical repository can safely sync:

```bash
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT/{rel_dir}"
git fetch origin --prune
git status --short --branch
```

If the repo is on a tracking branch and the worktree is clean:

```bash
git pull --ff-only
```

If the worktree is dirty, the branch is not tracking origin, or fast-forward is impossible, do not overwrite local work. Report the drift and read the current canonical card with that caveat.

## Load Canonical Skill

Open and follow `{rel}` (relative to the repo root). Do not copy behavior from this wrapper.

## Windows UTF-8 Note

On Windows PowerShell, set UTF-8 explicitly before reading or writing skill files:

```powershell
[Console]::InputEncoding=[System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$env:PYTHONUTF8='1'
```
'''


def install(dry_run: bool) -> list[Path]:
    written = []
    for spec in build_specs():
        content = wrapper(spec)
        for root in TARGET_ROOTS:
            path = target_path(root, spec.slug)
            if dry_run:
                print(path)
                continue
            if path.parent.is_symlink():
                path.parent.unlink()
            path.parent.mkdir(parents=True, exist_ok=True)
            for child in path.parent.iterdir():
                if child.name != "SKILL.md":
                    if child.is_dir():
                        shutil.rmtree(child)
                    else:
                        child.unlink()
            if path.is_symlink():
                path.unlink()
            path.write_text(content, encoding="utf-8")
            written.append(path)
    return written


def verify() -> list[str]:
    errors = []
    specs = build_specs()
    bad_markers = ("Ã", "Â", "â", "�", "\ufeff")
    for spec in specs:
        if not (ROOT / spec.canonical).is_file():
            errors.append(f"missing canonical: {spec.canonical}")
        for root in TARGET_ROOTS:
            path = target_path(root, spec.slug)
            if not path.is_file():
                errors.append(f"missing wrapper: {path}")
                continue
            text = path.read_text(encoding="utf-8")
            entries = [p.name for p in path.parent.iterdir()]
            if entries != ["SKILL.md"]:
                errors.append(f"non-thin wrapper dir: {path.parent} has {entries}")
            for required in ("git fetch origin --prune", "git pull --ff-only", repo_relative(spec.canonical)):
                if required not in text:
                    errors.append(f"missing {required!r}: {path}")
            for marker in bad_markers:
                if marker in text:
                    errors.append(f"bad encoding marker {marker!r}: {path}")
            # PORTABILITY GUARD: no absolute workstation paths may ever reach a
            # committed wrapper (they doxx the machine in public repos). Fail hard.
            for leak in ("/Users/", "/home/", str(HOME), str(ROOT)):
                if leak and leak in text:
                    errors.append(f"absolute path leak {leak!r}: {path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.install and not args.verify:
        parser.error("choose --install and/or --verify")
    if args.install:
        written = install(args.dry_run)
        if not args.dry_run:
            print(f"wrote {len(written)} wrapper files")
    if args.verify:
        errors = verify()
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print("verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
