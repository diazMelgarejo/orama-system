#!/usr/bin/env python3
"""Materialize bin/agents SOUL distillates into Hermes profile trees.

Mirrors install_hermes_thin_skills.py: managed marker, non-clobber of operator files,
provenance stamp, --install --verify --sync --dry-run.

Idempotent: skips profile SOUL writes when distillate body already matches staging.
Memory stubs: harmonize (integrative merge + backup), never blind overwrite.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROFILE_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
HARMONIZE_SECTION = "## Orama profile template (managed harmonize)"
MEMORY_BACKUP_SUFFIX = ".orama-profile-backup"


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
PROVENANCE_MARKER = "\n\n---\n\n_Canonical staging:"
VERIFY_TRUST_SCRIPT = REPO_ROOT / "scripts" / "review" / "verify_trusted_install.py"


@dataclass(frozen=True)
class ProfileRole:
    staging_folder: str
    openclaw_id: str
    hermes_profile: str
    soul_id: str
    staged_soul: Path


@dataclass
class InstallStats:
    written: list[Path]
    skipped_synced: list[str]
    skipped_unmanaged: list[str]
    harmonized: list[Path]


def assert_trusted_install() -> None:
    if not VERIFY_TRUST_SCRIPT.is_file():
        return
    if os.environ.get("ORAMA_TRUST_HERMES_SYNC", "").strip() in ("1", "true", "yes"):
        return
    result = subprocess.run(
        [sys.executable, str(VERIFY_TRUST_SCRIPT), "--quiet"],
        cwd=str(REPO_ROOT),
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Hermes profile install blocked: checkout not trusted. "
            "git pull --ff-only on main, review bin/agents changes, then "
            "ORAMA_TRUST_HERMES_SYNC=1 for explicit operator override."
        )


def validate_profile_slug(slug: str) -> None:
    if not PROFILE_SLUG_RE.fullmatch(slug):
        raise ValueError(f"invalid hermes_profile slug {slug!r} — use [a-z0-9-] only")


def profile_paths_for_slug(slug: str) -> Path:
    validate_profile_slug(slug)
    profiles_root = HERMES_PROFILES.resolve()
    profile_dir = (HERMES_PROFILES / slug).resolve()
    if profiles_root not in profile_dir.parents and profile_dir != profiles_root:
        raise ValueError(f"hermes_profile path escapes profiles root: {slug!r}")
    return profile_dir


def load_roles() -> list[ProfileRole]:
    raw = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    roles: list[ProfileRole] = []
    for entry in raw.get("roles", []):
        profile = entry.get("hermes_profile")
        if not profile or profile is None:
            continue
        validate_profile_slug(str(profile))
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


def staged_distillate(role: ProfileRole) -> str:
    return role.staged_soul.read_text(encoding="utf-8").rstrip()


def installed_soul_body(text: str) -> str:
    if PROVENANCE_MARKER in text:
        return text.split(PROVENANCE_MARKER, 1)[0].rstrip()
    return text.rstrip()


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


def soul_needs_update(role: ProfileRole) -> bool:
    target = profile_paths_for_slug(role.hermes_profile) / "SOUL.md"
    if not target.is_file():
        return True
    if not is_managed_soul(target):
        return False
    expected = staged_distillate(role)
    actual = installed_soul_body(target.read_text(encoding="utf-8"))
    return actual != expected


def backup_before_harmonize(target: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = target.with_name(f"{target.name}{MEMORY_BACKUP_SUFFIX}-{stamp}")
    shutil.copy2(target, backup)
    return backup


def harmonize_memory_stub(target: Path, template_text: str, *, harmonize: bool) -> tuple[str | None, str]:
    """Integrative merge: preserve operator content; append template when harmonizing."""
    if not target.is_file():
        return template_text, "create"
    existing = target.read_text(encoding="utf-8")
    if existing.strip() == template_text.strip():
        return None, "unchanged"
    if HARMONIZE_SECTION in existing and template_text.strip() in existing:
        return None, "unchanged"
    if "created_by: user" in existing and not harmonize:
        return None, "skip-user-owned"
    if not harmonize:
        return None, "skip-existing"
    backup_before_harmonize(target)
    merged = (
        f"{existing.rstrip()}\n\n---\n\n{HARMONIZE_SECTION}\n\n{template_text.rstrip()}\n"
    )
    return merged, "harmonized"


def install_profile_stubs(
    role: ProfileRole,
    dry_run: bool,
    harmonize_memory: bool,
    stats: InstallStats,
) -> None:
    profile_dir = profile_paths_for_slug(role.hermes_profile)
    memories = profile_dir / "memories"
    user_md = memories / "USER.md"
    memory_md = memories / "MEMORY.md"
    user_tpl = TEMPLATE_PROFILE / "USER.md"
    memory_tpl = TEMPLATE_PROFILE / "MEMORY.md"

    for target, source in ((user_md, user_tpl), (memory_md, memory_tpl)):
        if not source.is_file():
            continue
        template_text = source.read_text(encoding="utf-8")
        content, action = harmonize_memory_stub(target, template_text, harmonize=harmonize_memory)
        if content is None:
            continue
        if dry_run:
            print(f"would {action} profile stub: {target}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        stats.written.append(target)
        if action == "harmonized":
            stats.harmonized.append(target)


def install_soul(role: ProfileRole, dry_run: bool, stats: InstallStats) -> None:
    if not role.staged_soul.is_file():
        raise FileNotFoundError(f"missing staged SOUL: {role.staged_soul}")
    target = profile_paths_for_slug(role.hermes_profile) / "SOUL.md"
    if target.is_file() and not is_managed_soul(target):
        print(f"skipped unmanaged profile SOUL: {target}")
        stats.skipped_unmanaged.append(role.hermes_profile)
        return
    if target.is_file() and not soul_needs_update(role):
        print(f"already synced profile SOUL: {target}")
        stats.skipped_synced.append(role.hermes_profile)
        return
    distillate = staged_distillate(role)
    if dry_run:
        print(f"would write profile SOUL: {target}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(soul_install_text(distillate, role), encoding="utf-8")
    stats.written.append(target)


def install(dry_run: bool = False, harmonize_memory: bool = False) -> InstallStats:
    if not dry_run:
        assert_trusted_install()
    roles = load_roles()
    missing = [str(r.staged_soul) for r in roles if not r.staged_soul.is_file()]
    if missing:
        raise FileNotFoundError(f"missing staged SOUL files: {', '.join(missing)}")
    stats = InstallStats(written=[], skipped_synced=[], skipped_unmanaged=[], harmonized=[])
    for role in roles:
        install_soul(role, dry_run, stats)
        if not dry_run:
            install_profile_stubs(role, dry_run, harmonize_memory, stats)
    return stats


def verify() -> list[str]:
    errors: list[str] = []
    for role in load_roles():
        soul_path = profile_paths_for_slug(role.hermes_profile) / "SOUL.md"
        if not soul_path.is_file():
            errors.append(f"missing profile SOUL: {soul_path}")
            continue
        text = soul_path.read_text(encoding="utf-8")
        if role.soul_id and role.soul_id not in text:
            errors.append(f"profile SOUL missing soul_id {role.soul_id!r}: {soul_path}")
        if MANAGED_MARKER not in text:
            errors.append(f"profile SOUL missing managed marker: {soul_path}")
            continue
        expected = staged_distillate(role)
        actual = installed_soul_body(text)
        if actual != expected:
            errors.append(f"profile SOUL drift from staging: {soul_path}")
        if not role.staged_soul.is_file():
            errors.append(f"staged SOUL missing in repo: {role.staged_soul}")
    return errors


def sync(dry_run: bool = False, harmonize_memory: bool = False) -> int:
    """Verify first; install only when profiles drift or are missing."""
    errors = verify()
    if not errors:
        print("profiles already synced with bin/agents staging")
        return 0
    if dry_run:
        print("profile sync needed — dry-run install:")
        install(dry_run=True, harmonize_memory=harmonize_memory)
        return 0
    stats = install(dry_run=False, harmonize_memory=harmonize_memory)
    print(
        f"profile sync: wrote {len(stats.written)} file(s); "
        f"harmonized={len(stats.harmonized)} "
        f"skipped synced={len(stats.skipped_synced)} unmanaged={len(stats.skipped_unmanaged)}"
    )
    errors = verify()
    if errors:
        for err in errors:
            print(err)
        return 1
    print("profile verification passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Hermes profiles from bin/agents staging.")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--sync", action="store_true", help="Verify first; install only if drift/missing.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--harmonize-memory",
        action="store_true",
        help="Integratively merge template USER/MEMORY stubs (backup first); never blind overwrite.",
    )
    parser.add_argument(
        "--force-memory",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()
    harmonize_memory = args.harmonize_memory or args.force_memory
    if not args.install and not args.verify and not args.sync:
        parser.error("choose --install, --verify, and/or --sync")
    if args.sync:
        code = sync(dry_run=args.dry_run, harmonize_memory=harmonize_memory)
        if code != 0:
            return code
        if args.verify:
            return 0
    if args.install:
        stats = install(dry_run=args.dry_run, harmonize_memory=harmonize_memory)
        if not args.dry_run:
            print(
                f"profiles: wrote {len(stats.written)} file(s); "
                f"harmonized={len(stats.harmonized)} "
                f"skipped synced={len(stats.skipped_synced)} unmanaged={len(stats.skipped_unmanaged)}"
            )
    if args.verify and not args.sync:
        errors = verify()
        if errors:
            for err in errors:
                print(err)
            return 1
        print("profile verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
