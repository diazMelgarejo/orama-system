#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import argparse
import errno
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone


@dataclass(frozen=True)
class SkillSpec:
    slug: str
    canonical: str
    name: str
    description: str


@dataclass(frozen=True)
class SkillInventory:
    """One read-only observation of a single directory entry under a logical
    skill root (Gemini, Claude, Codex, shared-agent, or Antigravity). Used by
    the `--audit-gemini` inventory pass — see `inventory_root`,
    `inventory_all_roots`, and `render_inventory` below. Never written to
    disk; this is analysis-only data, not a mutation record."""

    slug: str
    root_id: str
    entry_kind: str  # "symlink" | "regular" | "absent"
    sha256: str
    frontmatter_keys: tuple[str, ...]


sys.path.insert(0, str(Path(__file__).parent.resolve()))
from gemini_reconciliation import (
    RootFinding,
    ReconcileLockHeldError,
    reconcile_gemini,
    verify_gemini,
    force_unlock_gemini,
    create_relative_link,
    acquire_reconcile_lock,
    release_reconcile_lock,
    load_gemini_ownership,
)

ROOT = Path(__file__).resolve().parents[6]
HOME = Path.home()


WORKSPACE_PATH_ALIASES = {
    "orama-system": ("orama-system", "ultrathink-system"),
    "perplexity-api/Perpetua-Tools": (
        "perplexity-api/Perpetua-Tools",
        "Perplexity-Tools",
    ),
}


def workspace_candidates(rel: str) -> list[Path]:
    candidates = [rel]
    for prefix, aliases in WORKSPACE_PATH_ALIASES.items():
        if rel == prefix or rel.startswith(prefix + "/"):
            suffix = rel[len(prefix):].lstrip("/")
            for alias in aliases:
                replacement = f"{alias}/{suffix}" if suffix else alias
                if replacement not in candidates:
                    candidates.append(replacement)
    return [ROOT / candidate for candidate in candidates]


def workspace_path(rel: str) -> Path:
    candidates = workspace_candidates(rel)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


CANONICAL_SKILLS = [
    "perplexity-api/Perpetua-Tools/SKILL.md",
    "perplexity-api/Perpetua-Tools/config/SKILL.md",
    "perplexity-api/Perpetua-Tools/hardware/SKILL.md",
    "perplexity-api/Perpetua-Tools/hardware/startup-intelligence/SKILL.md",
    "orama-system/SKILL.md",
    "orama-system/bin/orama-system/SKILL.md",
    "orama-system/bin/orama-system/afrp/SKILL.md",
    "orama-system/bin/orama-system/cidf/SKILL.md",
    "orama-system/bin/orama-system/gstack-gbrain/SKILL.md",
    "orama-system/bin/orama-system/skills/agent-methodology/SKILL.md",
    "orama-system/bin/orama-system/skills/code-review/SKILL.md",
    "orama-system/bin/orama-system/skills/ecc-sync/SKILL.md",
    "orama-system/bin/orama-system/skills/first-run-setup/SKILL.md",
    "orama-system/bin/orama-system/skills/git-history-surgery/SKILL.md",
    "orama-system/bin/orama-system/skills/hermes-harness/SKILL.md",
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


# NOTE: ~/.claude/skills is deliberately NOT a target here. It is a shared
# global namespace gstack also populates directly (e.g. its own bundled
# `skillify` at ~/.claude/skills/skillify/, an unrelated skill with the same
# name as this repo's). A 2026-07-22 pass added it here and it silently
# overwrote gstack's file — recovered from gstack's own source copy; see
# skillify/references/dogfood-upgrade-log.md and
# skillify/references/modular-skill-authoring.md's "External Namespace
# Collision Check". Publishing THIS repo's skills to ~/.claude/skills/ is
# scripts/install-skills.sh's job (repo root) — it publishes under
# collision-checked, disambiguated slugs (e.g. oramasys-skillify, not
# skillify). Do not re-add ~/.claude/skills to this list.
TARGET_ROOTS = [
    "~/.codex/skills",
    "~/.agents/skills",
    ".agents/skills",
    "orama-system/.agents/skills",
    "perplexity-api/Perpetua-Tools/.agents/skills",
]


# This is routing metadata, not the Task 2 ownership manifest. It names only
# the slugs Task 7 verifies in the Gemini inbound root, so ``--verify --only``
# cannot silently validate the unrelated wrapper roots instead.
GEMINI_VERIFICATION_SLUGS = frozenset(
    {
        "agent-methodology",
        "code-review",
        "git-history-surgery",
        "orama-afrp",
        "orama-gstack",
        "orama-system",
        "oramasys-method",
        "perpetua-tools",
        "perpetua-config",
        "perpetua-hardware",
        "perpetua-startup-intelligence",
    }
)


SLUG_OVERRIDES = {
    "perplexity-api/Perpetua-Tools/SKILL.md": "perpetua-tools",
    "perplexity-api/Perpetua-Tools/config/SKILL.md": "perpetua-config",
    "perplexity-api/Perpetua-Tools/hardware/SKILL.md": "perpetua-hardware",
    "perplexity-api/Perpetua-Tools/hardware/startup-intelligence/SKILL.md": "perpetua-startup-intelligence",
    "orama-system/SKILL.md": "orama-repo-rules",
    "orama-system/bin/orama-system/SKILL.md": "orama-system",
    "orama-system/bin/orama-system/afrp/SKILL.md": "orama-afrp",
    "orama-system/bin/orama-system/cidf/SKILL.md": "orama-cidf",
    "orama-system/bin/orama-system/gstack-gbrain/SKILL.md": "orama-gstack",
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


_FRONTMATTER_KEY = re.compile(r"^([A-Za-z_][\w-]*):", re.MULTILINE)


def _frontmatter_keys(text: str) -> tuple[str, ...]:
    """Return every top-level YAML frontmatter key, in document order, with
    duplicates dropped. Only unindented `key:` lines within the leading
    `---`...`---` block count — nested keys inside a list/mapping value
    (e.g. `sub_skills[].path`) are indented and therefore excluded, matching
    how the Gemini frontmatter inventory in the plan counts keys."""
    if not text.startswith("---"):
        return ()
    end = text.find("\n---", 3)
    if end == -1:
        return ()
    body = text[3:end]
    keys: list[str] = []
    for match in _FRONTMATTER_KEY.finditer(body):
        key = match.group(1)
        if key not in keys:
            keys.append(key)
    return tuple(keys)


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


def build_specs(only: set[str] | None = None) -> list[SkillSpec]:
    """Build wrapper specs for CANONICAL_SKILLS.

    `only`, when given, is a set of slugs to include. Filtering happens
    BEFORE any path is resolved so an unrelated missing sibling repo (e.g.
    Perpetua-Tools not being checked out locally) never blocks a scoped run
    for skills that don't need it.
    """
    specs = []
    slugs = set()
    for canonical in CANONICAL_SKILLS:
        slug = slug_for(canonical)
        if only is not None and slug not in only:
            continue
        path = workspace_path(canonical)
        if not path.is_file():
            raise FileNotFoundError(path)
        text = path.read_text(encoding="utf-8-sig")
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
        root_path = workspace_path(root)
    return root_path / slug / "SKILL.md"


def repo_relative(canonical: str) -> str:
    """Strip the leading workspace/repo-name segment from a workspace-relative
    canonical path so the wrapper references the skill RELATIVE TO ITS OWN REPO
    ROOT — never an absolute workstation path. e.g.
    "orama-system/bin/orama-system/cidf/SKILL.md" -> "bin/orama-system/cidf/SKILL.md".
    """
    for prefix in sorted(WORKSPACE_PATH_ALIASES, key=len, reverse=True):
        if canonical == prefix:
            return "."
        if canonical.startswith(prefix + "/"):
            return canonical[len(prefix) + 1:]
    return canonical.split("/", 1)[1] if "/" in canonical else canonical


def wrapper(spec: SkillSpec) -> str:
    # PORTABILITY CONTRACT: wrappers MUST be machine-agnostic. NEVER embed an
    # absolute path (ROOT, HOME, /Users/...) — they get committed to public
    # repos and doxx the workstation. The canonical skill lives in the SAME git
    # repo as this wrapper, so reference it repo-relative and resolve the repo
    # root at runtime via `git rev-parse --show-toplevel`. verify() enforces this.
    description = spec.description.replace('"', "'")
    rel = repo_relative(spec.canonical)
    rel_dir = PurePosixPath(rel).parent.as_posix()
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


def install(dry_run: bool, only: set[str] | None = None) -> list[Path]:
    written = []
    specs = build_specs(only=only)
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
    # Skipped under --only unless the new slug is itself in scope, to avoid
    # touching renamed-skill redirects that a scoped run has no opinion about.
    for old_slug, new_slug in SKILL_RENAMES.items():
        if only is not None and new_slug not in only:
            continue
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
        rewrite_stale_references(only=only)
    return written


def rewrite_stale_references(only: set[str] | None = None) -> list[Path]:
    """On every run, rewrite stale `skills/<old>/` path references in managed
    canonical docs to the renamed slug — so the mother skill and sibling skill
    docs keep pointing at renamed skills without manual edits."""
    changed = []
    for canonical in dict.fromkeys(CANONICAL_SKILLS):
        if only is not None and slug_for(canonical) not in only:
            continue
        doc = workspace_path(canonical)
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


def verify(only: set[str] | None = None) -> list[str]:
    errors = []
    specs = build_specs(only=only)
    bad_markers = ("Ã", "Â", "â", "�", "\ufeff")
    for spec in specs:
        if not workspace_path(spec.canonical).is_file():
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
    # Skipped for renames outside an --only scope — a scoped run has no
    # opinion about redirects for skills it wasn't asked to touch.
    live_slugs = {s.slug for s in specs}
    for old_slug, new_slug in SKILL_RENAMES.items():
        if only is not None and new_slug not in only:
            continue
        if new_slug not in live_slugs:
            errors.append(f"rename target missing from manifest: {new_slug}")
        for root in TARGET_ROOTS:
            rp = target_path(root, old_slug)
            if not rp.is_file():
                errors.append(f"missing rename redirect: {rp}")
            elif new_slug not in rp.read_text(encoding="utf-8"):
                errors.append(f"redirect does not point to {new_slug!r}: {rp}")
    for canonical in dict.fromkeys(CANONICAL_SKILLS):
        if only is not None and slug_for(canonical) not in only:
            continue
        doc = workspace_path(canonical)
        if doc.is_file():
            doctext = doc.read_text(encoding="utf-8")
            for old_slug, new_slug in SKILL_RENAMES.items():
                if f"skills/{old_slug}/" in doctext:
                    errors.append(f"stale skills/{old_slug}/ reference in {canonical} (rename to {new_slug})")
    return errors







def verify_antigravity_root(shared_agents_root: Path, antigravity_root: Path) -> RootFinding:
    if not antigravity_root.exists() and not antigravity_root.is_symlink():
        return RootFinding(
            slug="",
            status="missing",
            detail=f"missing expected root(s). shared: {shared_agents_root.exists()}, antigravity: {antigravity_root.exists()}",
            operator_next_action="Ask a human operator to approve or decline deferred Task 5a; do not create an Antigravity root in this plan."
        )
    try:
        if antigravity_root.is_symlink() and antigravity_root.resolve() == shared_agents_root.resolve():
            return RootFinding(
                slug="",
                status="shared-root",
                detail=f"Resolved roots: {shared_agents_root.resolve()}",
                operator_next_action="Record the finding; no setup action is needed."
            )
    except OSError:
        pass
    return RootFinding(
        slug=antigravity_root.name,
        status="divergent",
        detail=f"Both the shared-agent root ({shared_agents_root}) and the Antigravity root ({antigravity_root}) exist, but they are not the same directory. Antigravity must share the agent ecosystem root to avoid branching context isolation.",
        operator_next_action="Ask a human operator to inspect both root owners and approve deferred Task 5a only after resolving the intended topology.",
    )


def audit_antigravity_root(
    shared_agents_root: Path, antigravity_root: Path | None
) -> RootFinding:
    """Return a read-only topology finding for an explicitly supplied root.

    Antigravity does not have a portable, repository-owned configuration path.
    An omitted root is therefore an auditable ``missing`` outcome, not evidence
    that the shared-agent root is already configured for Antigravity.
    """
    if antigravity_root is None:
        return RootFinding(
            slug="",
            status="missing",
            detail="No Antigravity skills root was supplied for this read-only audit.",
            operator_next_action="Ask a human operator to approve or decline deferred Task 5a; do not create an Antigravity root in this plan.",
        )
    return verify_antigravity_root(shared_agents_root, antigravity_root)


# Logical roots audited by --audit-gemini. "agents" and "antigravity" resolve
# to the SAME physical directory (~/.agents/skills) — per Global Constraints,
# "Antigravity must resolve to the shared agent root; audit it rather than
# writing to it." Recording both root_ids lets the inventory show that the
# two harnesses currently share one root without implying a separate,
# writable Antigravity skills tree exists.
def _inventory_roots(home: Path) -> list[tuple[str, Path]]:
    agents_root = home / ".agents" / "skills"
    return [
        ("gemini", home / ".gemini" / "skills"),
        ("claude", home / ".claude" / "skills"),
        ("codex", home / ".codex" / "skills"),
        ("agents", agents_root),
        ("antigravity", agents_root),
    ]


def inventory_root(root_id: str, root: Path) -> list[SkillInventory]:
    """Read-only scan of one logical skill root. Never creates, archives, or
    symlinks anything — see Task 2's `reconcile_gemini` for mutation.

    Returns one row per immediate directory entry (dotfiles like `.DS_Store`
    skipped). If the root itself does not exist, returns a single sentinel
    row with entry_kind="absent" so cross-root comparisons can distinguish
    "root not present on this machine" from "root present but empty"."""
    if not root.is_dir():
        return [SkillInventory("", root_id, "absent", "", ())]

    rows: list[SkillInventory] = []
    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        if entry.name.startswith("."):
            continue
        if entry.is_symlink():
            entry_kind = "symlink"
        elif entry.is_dir():
            entry_kind = "regular"
        else:
            continue  # stray file at root level; not a skill directory

        skill_md = entry / "SKILL.md"
        sha256 = ""
        frontmatter_keys: tuple[str, ...] = ()
        if skill_md.is_file():
            data = skill_md.read_bytes()
            sha256 = hashlib.sha256(data).hexdigest()
            frontmatter_keys = _frontmatter_keys(data.decode("utf-8", errors="replace"))
        rows.append(SkillInventory(entry.name, root_id, entry_kind, sha256, frontmatter_keys))
    return rows


def inventory_all_roots() -> list[SkillInventory]:
    """Audit Gemini, Claude, Codex, shared-agent, and Antigravity roots.
    Read-only: calls no install, archive, or symlink function."""
    rows: list[SkillInventory] = []
    for root_id, root in _inventory_roots(HOME):
        rows.extend(inventory_root(root_id, root))
    return rows


def render_inventory(rows: list[SkillInventory], home: Path) -> str:
    """Render inventory rows as a portable Markdown table, sorted by slug
    then root. `home` is stripped from the rendered text defensively — rows
    should never carry an absolute path in the first place, since
    SkillInventory only stores slugs/root labels/digests/key names, but this
    guards against a future field carrying one in by accident."""
    header = ["| slug | root | kind | sha256 | frontmatter keys |", "| --- | --- | --- | --- | --- |"]
    body = []
    for row in sorted(rows, key=lambda r: (r.slug, r.root_id)):
        slug = row.slug or "—"
        sha = row.sha256 or "—"
        keys = ", ".join(row.frontmatter_keys) if row.frontmatter_keys else "—"
        body.append(f"| {slug} | {row.root_id} | {row.entry_kind} | {sha} | {keys} |")
    rendered = "\n".join(header + body)
    home_str = str(home)
    if home_str:
        rendered = rendered.replace(home_str, "<home>")
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--reconcile-gemini",
        action="store_true",
        help="Reconcile approved Gemini skills. Requires --only and --archive-root.",
    )
    parser.add_argument(
        "--gemini-root",
        help="Override the live Gemini skills root (default: ~/.gemini/skills).",
    )
    parser.add_argument(
        "--archive-root",
        help="Archive batch directory for Gemini reconciliation, or archive parent for explicit verification.",
    )
    parser.add_argument(
        "--force-unlock",
        metavar="SLUG",
        help="Explicitly clear a stale Gemini reconciliation lock for this slug.",
    )
    parser.add_argument(
        "--audit-gemini",
        action="store_true",
        help=(
            "Read-only cross-root inventory (Gemini, Claude, Codex, "
            "shared-agent, Antigravity). Prints render_inventory() and "
            "exits — never installs, archives, or symlinks anything."
        ),
    )
    parser.add_argument(
        "--audit-antigravity",
        action="store_true",
        help="Read-only Antigravity/shared-agent topology audit. Never mutates either root.",
    )
    parser.add_argument(
        "--antigravity-root",
        help="Explicit Antigravity skills root for --audit-antigravity; omit to record missing.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output audit result as JSON rather than Markdown table.",
    )
    parser.add_argument(
        "--only",
        default=None,
        help=(
            "Comma-separated slugs to scope this run to (e.g. "
            "'oramasys-method,skillify'). Skips path resolution for every "
            "other manifest entry, so a scoped run never fails on an "
            "unrelated sibling repo that isn't checked out locally. Omit "
            "for the full manifest (all registered skills)."
        ),
    )
    args = parser.parse_args()
    if args.audit_gemini:
        inventory = inventory_all_roots()
        if args.json:
            import dataclasses
            print(json.dumps([dataclasses.asdict(row) for row in inventory], indent=2))
        else:
            print(render_inventory(inventory, home=HOME))
        return 0
    if args.audit_antigravity:
        finding = audit_antigravity_root(
            HOME / ".agents" / "skills",
            Path(args.antigravity_root) if args.antigravity_root else None,
        )
        if args.json:
            import dataclasses

            print(json.dumps(dataclasses.asdict(finding), indent=2))
        else:
            print(f"{finding.status}: {finding.detail}")
            print(f"next: {finding.operator_next_action}")
        return 0
    if not args.install and not args.verify and not args.reconcile_gemini:
        parser.error("choose --install, --verify, --reconcile-gemini, --audit-gemini, and/or --audit-antigravity")
    only = {s.strip() for s in args.only.split(",")} if args.only else None
    gemini_root = Path(args.gemini_root).resolve() if args.gemini_root else HOME / ".gemini" / "skills"
    if args.reconcile_gemini:
        if only is None:
            parser.error("--reconcile-gemini requires --only")
        if not args.archive_root:
            parser.error("--reconcile-gemini requires --archive-root")
        archive_root = Path(args.archive_root)
        if args.force_unlock:
            if args.force_unlock not in only:
                parser.error("--force-unlock slug must be included in --only")
            force_unlock_gemini(archive_root, args.force_unlock)
        else:
            manifest_path = Path(__file__).resolve().parent.parent / "references" / "gemini-skill-ownership.json"
            ownership_dict = load_gemini_ownership(manifest_path)
            written = reconcile_gemini(gemini_root, archive_root, only, lambda s: ownership_dict[s])
            print(f"reconciled {len(written)} Gemini skill directories")
    if args.install:
        written = install(args.dry_run, only=only)
        if not args.dry_run:
            print(f"wrote {len(written)} wrapper files")
    if args.verify:
        if only and only & GEMINI_VERIFICATION_SLUGS:
            if not only <= GEMINI_VERIFICATION_SLUGS:
                parser.error("cannot mix Gemini reconciliation slugs with legacy wrapper slugs in one --verify")
            archive_parent = Path(args.archive_root) if args.archive_root else HOME / ".gemini" / "skills-archive"
            findings = verify_gemini(gemini_root, archive_parent, only)
            if findings:
                for finding in findings:
                    print(finding.detail, file=sys.stderr)
                return 1
        else:
            errors = verify(only=only)
            if errors:
                for error in errors:
                    print(error, file=sys.stderr)
                return 1
        if not args.reconcile_gemini:
            print("verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
