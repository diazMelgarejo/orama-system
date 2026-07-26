#!/usr/bin/env python3
"""Materialize bin/agents SOUL distillates into Hermes profile trees.

Mirrors install_hermes_thin_skills.py: managed marker, non-clobber of operator files,
provenance stamp, --install --verify --dry-run.
"""
from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml


def resolve_repo_root() -> Path:
    script = Path(__file__).resolve()
    try:
        top = subprocess.check_output(
            ["git", "-C", str(script.parent), "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return Path(top)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return script.parents[5]


def install_provenance() -> str:
    try:
        branch = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--abbrev-ref", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        sha = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return f"Branch at install time: `{branch}` @ `{sha}`"
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "Read canonical SOUL from the current orama-system checkout before acting."


REPO_ROOT = resolve_repo_root()
LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
HERMES_HOME = Path(os.environ.get("HERMES_HOME", LOCALAPPDATA / "hermes"))
HERMES_PROFILES = HERMES_HOME / "profiles"
REGISTRY_PATH = REPO_ROOT / "bin" / "agents" / "REGISTRY.yml"
TEMPLATE_PROFILE = REPO_ROOT / "bin" / "agents" / "templates" / "profile"
MANAGED_MARKER = "created_by: agent"
OVERLAY_HEADER = "## Oramasys role overlay"


@dataclass(frozen=True)
class ProfileRole:
    staging_folder: str
    openclaw_id: str
    hermes_profile: str
    soul_id: str
    staged_soul: Path


def expand_home(path_str: str) -> str:
    return path_str.replace("${HOME}", str(Path.home()))


def load_roles() -> list[ProfileRole]:
    raw = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    roles: list[ProfileRole] = []
    for entry in raw.get("roles", []):
        profile = entry.get("hermes_profile")
        if not profile or profile is None:
            continue
        staged = entry.get("staged_soul")
        if not staged:
            staged = f"bin/agents/{entry['staging_folder']}/SOUL.md"
        soul_path = REPO_ROOT / staged
        roles.append(
            ProfileRole(
                staging_folder=entry["staging_folder"],
                openclaw_id=entry["openclaw_id"],
                hermes_profile=profile,
                soul_id=entry.get("soul_id", ""),
                staged_soul=soul_path,
            )
        )
    return roles


def soul_install_text(distillate: str, role: ProfileRole) -> str:
    provenance = install_provenance()
    return (
        f"{distillate.rstrip()}\n\n"
        f"---\n\n"
        f"_Canonical staging: `bin/agents/{role.staging_folder}/SOUL.md` — "
        f"{provenance}. {MANAGED_MARKER}_\n"
    )


def is_managed_soul(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    return MANAGED_MARKER in text


def install_profile_stubs(role: ProfileRole, dry_run: bool, force_memory: bool) -> list[Path]:
    written: list[Path] = []
    profile_dir = HERMES_PROFILES / role.hermes_profile
    memories = profile_dir / "memories"
    user_md = memories / "USER.md"
    memory_md = memories / "MEMORY.md"
    user_tpl = TEMPLATE_PROFILE / "USER.md"
    memory_tpl = TEMPLATE_PROFILE / "MEMORY.md"

    targets = []
    if user_tpl.is_file() and (not user_md.is_file() or force_memory):
        targets.append((user_md, user_tpl))
    if memory_tpl.is_file() and (not memory_md.is_file() or force_memory):
        targets.append((memory_md, memory_tpl))

    for target, source in targets:
        if dry_run:
            print(f"would write profile stub: {target}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        written.append(target)
    return written


def install_soul(role: ProfileRole, dry_run: bool) -> Path | None:
    if not role.staged_soul.is_file():
        raise FileNotFoundError(f"missing staged SOUL: {role.staged_soul}")
    distillate = role.staged_soul.read_text(encoding="utf-8")
    target = HERMES_PROFILES / role.hermes_profile / "SOUL.md"
    if dry_run:
        print(f"would write profile SOUL: {target}")
        return target
    if target.is_file() and not is_managed_soul(target):
        print(f"skipped unmanaged profile SOUL: {target}")
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(soul_install_text(distillate, role), encoding="utf-8")
    return target


def install(dry_run: bool = False, force_memory: bool = False) -> list[Path]:
    roles = load_roles()
    missing = [str(r.staged_soul) for r in roles if not r.staged_soul.is_file()]
    if missing:
        raise FileNotFoundError(f"missing staged SOUL files: {', '.join(missing)}")
    written: list[Path] = []
    for role in roles:
        soul = install_soul(role, dry_run)
        if soul and not dry_run:
            written.append(soul)
        stubs = install_profile_stubs(role, dry_run, force_memory)
        written.extend(stubs)
    return written


def verify() -> list[str]:
    errors: list[str] = []
    for role in load_roles():
        soul_path = HERMES_PROFILES / role.hermes_profile / "SOUL.md"
        if not soul_path.is_file():
            errors.append(f"missing profile SOUL: {soul_path}")
            continue
        text = soul_path.read_text(encoding="utf-8")
        if role.soul_id and role.soul_id not in text:
            errors.append(f"profile SOUL missing soul_id {role.soul_id!r}: {soul_path}")
        if MANAGED_MARKER not in text:
            errors.append(f"profile SOUL missing managed marker: {soul_path}")
        if not role.staged_soul.is_file():
            errors.append(f"staged SOUL missing in repo: {role.staged_soul}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Hermes profiles from bin/agents staging.")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--force-memory",
        action="store_true",
        help="Overwrite profile memories/USER.md and MEMORY.md from templates.",
    )
    args = parser.parse_args()
    if not args.install and not args.verify:
        parser.error("choose --install and/or --verify")
    if args.install:
        written = install(dry_run=args.dry_run, force_memory=args.force_memory)
        if not args.dry_run:
            print(f"wrote {len(written)} Hermes profile files under {HERMES_PROFILES}")
    if args.verify:
        errors = verify()
        if errors:
            for err in errors:
                print(err)
            return 1
        print("profile verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
