# Perpetua Orama Thin Skill Wrappers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install all canonical Perpetua-Tools and orama-system skills as thin wrappers for Codex, Claude, and generic agent harness skill roots.

**Architecture:** Keep canonical skill content inside `perplexity-api/Perpetua-Tools` and `orama-system`. Generate small wrapper `SKILL.md` files in global and repo-local harness skill roots; wrappers point to canonical paths and include origin-sync and Windows UTF-8 rules.

**Tech Stack:** Python 3 standard library, Markdown skill cards, Codex `.agents/skills`, Claude `.claude/skills`, user-level `~/.codex/skills`, `~/.claude/skills`, and `~/.agents/skills`.

---

### Task 1: Add Deterministic Wrapper Installer

**Files:**
- Create: `orama-system/bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py`

- [x] **Step 1: Create the installer script**

Create `orama-system/bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py` with:

```python
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


ROOT = Path(__file__).resolve().parents[5]
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
```

- [x] **Step 2: Finish script behavior**

Add code that:

```python
def slug_for(path: str) -> str:
    if path in SLUG_OVERRIDES:
        return SLUG_OVERRIDES[path]
    parent = Path(path).parent.name
    return re.sub(r"[^a-z0-9-]+", "-", parent.lower()).strip("-")


def frontmatter_value(text: str, key: str) -> str | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    body = text[3:end]
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", body, re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip().strip('"').strip("'")
    return value if value else None


def first_heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "Canonical skill wrapper"


def compact_description(text: str, fallback: str) -> str:
    value = frontmatter_value(text, "description")
    if value:
        return value[:240]
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", "---", ">")):
            return stripped[:240]
    return fallback[:240]


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
    root_path = Path(root.replace("~", str(HOME), 1)) if root.startswith("~/") else ROOT / root
    return root_path / slug / "SKILL.md"


# NOTE (superseded): the snippet below is the ORIGINAL plan draft and embeds
# absolute paths (`{ROOT}`, `{canonical_abs}`). The SHIPPED implementation in
# bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py is
# repo-relative (resolves the repo root at runtime via `git rev-parse`) and a
# verify() guard rejects any absolute /Users/ or $HOME path. Treat the canonical
# script — not this draft — as the source of truth.
def wrapper(spec: SkillSpec) -> str:
    canonical_abs = ROOT / spec.canonical
    return f'''---
name: {spec.slug}
description: "{spec.description.replace('"', "'")}"
---

# {spec.name}

This is a thin wrapper. The canonical skill lives in the OpenClaw workspace.

- Canonical repo root: `{ROOT}`
- Canonical skill path: `{spec.canonical}`
- Absolute canonical path: `{canonical_abs}`

## Before Use

Before relying on the canonical card, check whether the canonical repository can safely sync:

```bash
cd "{canonical_abs.parent}"
git fetch origin --prune
git status --short --branch
```

If the repo is on a tracking branch and the worktree is clean:

```bash
git pull --ff-only
```

If the worktree is dirty, the branch is not tracking origin, or fast-forward is impossible, do not overwrite local work. Report the drift and read the current canonical card with that caveat.

## Load Canonical Skill

Open and follow `{spec.canonical}`. Do not copy behavior from this wrapper.

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
            path.parent.mkdir(parents=True, exist_ok=True)
            for child in path.parent.iterdir():
                if child.name != "SKILL.md":
                    if child.is_dir():
                        shutil.rmtree(child)
                    else:
                        child.unlink()
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
            for required in ("git fetch origin --prune", "git pull --ff-only", spec.canonical):
                if required not in text:
                    errors.append(f"missing {required!r}: {path}")
            for marker in bad_markers:
                if marker in text:
                    errors.append(f"bad encoding marker {marker!r}: {path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
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
```

### Task 2: Generate Wrappers Across Harness Roots

**Files:**
- Modify: `~/.codex/skills/*/SKILL.md`
- Modify: `~/.claude/skills/*/SKILL.md`
- Modify: `~/.agents/skills/*/SKILL.md`
- Modify: `.agents/skills/*/SKILL.md`
- Modify: `.claude/skills/*/SKILL.md`
- Modify: `orama-system/.agents/skills/*/SKILL.md`
- Modify: `orama-system/.claude/skills/*/SKILL.md`
- Modify: `perplexity-api/Perpetua-Tools/.agents/skills/*/SKILL.md`
- Modify: `perplexity-api/Perpetua-Tools/.claude/skills/*/SKILL.md`

- [x] **Step 1: Dry-run generated paths**

Run:

```bash
python3 orama-system/bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py --install --dry-run
```

Expected: prints one target `SKILL.md` path per canonical skill per harness root.

- [x] **Step 2: Install wrappers**

Run:

```bash
python3 orama-system/bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py --install
```

Expected: `wrote 288 wrapper files`.

### Task 3: Verify Completion

**Files:**
- Test: `orama-system/bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py`

- [x] **Step 1: Run wrapper verifier**

Run:

```bash
python3 orama-system/bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py --verify
```

Expected: `verification passed`.

- [x] **Step 2: Check encoding and wrapper thinness directly**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
roots = [
    Path.home()/'.codex/skills',
    Path.home()/'.claude/skills',
    Path.home()/'.agents/skills',
    Path('.agents/skills'),
    Path('.claude/skills'),
    Path('orama-system/.agents/skills'),
    Path('orama-system/.claude/skills'),
    Path('perplexity-api/Perpetua-Tools/.agents/skills'),
    Path('perplexity-api/Perpetua-Tools/.claude/skills'),
]
bad = []
for root in roots:
    for skill in root.glob('*/SKILL.md'):
        if not skill.is_file():
            continue
        text = skill.read_text(encoding='utf-8')
        if 'Canonical skill path:' in text:
            extras = [p.name for p in skill.parent.iterdir() if p.name != 'SKILL.md']
            if extras:
                bad.append(f'{skill.parent}: {extras}')
            if any(m in text for m in ('Ã','Â','â','�','\ufeff')):
                bad.append(f'{skill}: bad encoding marker')
if bad:
    raise SystemExit('\n'.join(bad))
print('thin wrapper scan passed')
PY
```

Expected: `thin wrapper scan passed`.
