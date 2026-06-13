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
    "orama-system/bin/orama-system/skills/shell-hygiene/SKILL.md",
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


# Renamed skills: {old_slug: new_slug}. On every run the installer (1) leaves a
# REDIRECT stub at the old slug in each target root so stale references still
# resolve to the new skill, and (2) rewrites stale `skills/<old>/` path references
# inside managed canonical docs. Add a line here whenever a skill is renamed —
# never just delete the old wrapper (that orphans every reference to it).
SKILL_RENAMES = {
    "no-sleep-chains": "shell-hygiene",
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


def redirect_stub(old_slug: str, new_spec: SkillSpec) -> str:
    """A thin redirect left at a RENAMED skill's old slug so stale references and
    muscle-memory still resolve. It points at the new skill; it is not a full card."""
    return f'''---
name: {old_slug}
description: "Renamed to `{new_spec.slug}`. Redirect stub — use {new_spec.slug}: {new_spec.description}"
---

# {old_slug} → renamed to `{new_spec.slug}`

This skill was renamed. The canonical skill now lives under the slug **`{new_spec.slug}`**.

- Use `{new_spec.slug}` going forward (same behavior, broader scope).
- Canonical: `{repo_relative(new_spec.canonical)}` (relative to the repo root).

This stub only redirects; do not add content here.
'''


def _clean_thin_dir(path: Path) -> None:
    if path.parent.is_symlink():
        path.parent.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    for child in path.parent.iterdir():
        if child.name != "SKILL.md":
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    if path.is_symlink():
        path.unlink()


def install(dry_run: bool) -> list[Path]:
    written = []
    specs = build_specs()
    by_slug = {s.slug: s for s in specs}
    for spec in specs:
        content = wrapper(spec)
        for root in TARGET_ROOTS:
            path = target_path(root, spec.slug)
            if dry_run:
                print(path)
                continue
            _clean_thin_dir(path)
            path.write_text(content, encoding="utf-8")
            written.append(path)
    # Rename redirects: leave a stub at every old slug so references keep resolving.
    for old_slug, new_slug in SKILL_RENAMES.items():
        new_spec = by_slug.get(new_slug)
        if not new_spec:
            continue  # new skill not in this manifest; nothing to redirect to
        stub = redirect_stub(old_slug, new_spec)
        for root in TARGET_ROOTS:
            path = target_path(root, old_slug)
            if dry_run:
                print(f"{path} (redirect -> {new_slug})")
                continue
            _clean_thin_dir(path)
            path.write_text(stub, encoding="utf-8")
            written.append(path)
    if not dry_run:
        rewrite_stale_references()
    return written


def rewrite_stale_references() -> list[Path]:
    """On every run, rewrite stale `skills/<old>/` path references in managed
    canonical docs to the renamed slug — so the mother skill and sibling skill
    docs keep pointing at renamed skills without manual edits."""
    changed = []
    for canonical in dict.fromkeys(CANONICAL_SKILLS):
        doc = ROOT / canonical
        if not doc.is_file():
            continue
        text = doc.read_text(encoding="utf-8")
        new = text
        for old_slug, new_slug in SKILL_RENAMES.items():
            new = new.replace(f"skills/{old_slug}/", f"skills/{new_slug}/")
        if new != text:
            doc.write_text(new, encoding="utf-8")
            changed.append(doc)
    return changed


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
    # Rename hygiene: every old slug resolves to a redirect pointing at the new
    # one, and no managed canonical doc keeps a live `skills/<old>/` reference.
    live_slugs = {s.slug for s in specs}
    for old_slug, new_slug in SKILL_RENAMES.items():
        if new_slug not in live_slugs:
            errors.append(f"rename target missing from manifest: {new_slug}")
        for root in TARGET_ROOTS:
            rp = target_path(root, old_slug)
            if not rp.is_file():
                errors.append(f"missing rename redirect: {rp}")
            elif new_slug not in rp.read_text(encoding="utf-8"):
                errors.append(f"redirect does not point to {new_slug!r}: {rp}")
    for canonical in dict.fromkeys(CANONICAL_SKILLS):
        doc = ROOT / canonical
        if doc.is_file():
            doctext = doc.read_text(encoding="utf-8")
            for old_slug, new_slug in SKILL_RENAMES.items():
                if f"skills/{old_slug}/" in doctext:
                    errors.append(f"stale skills/{old_slug}/ reference in {canonical} (rename to {new_slug})")
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
