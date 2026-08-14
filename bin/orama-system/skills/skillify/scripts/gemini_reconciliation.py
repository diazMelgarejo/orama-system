from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class GeminiOwnership:
    owner: str
    action: str
    canonical_slug: str
    canonical_path: str
    metadata_policy: str


def load_gemini_ownership(manifest_path: Path) -> dict[str, GeminiOwnership]:
    if not manifest_path.exists():
        return {}
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    skills = data.get("skills", {})
    return {
        slug: GeminiOwnership(
            owner=v["owner"],
            action=v["action"],
            canonical_slug=v["canonical_slug"],
            canonical_path=v["canonical_path"],
            metadata_policy=v["metadata_policy"]
        ) for slug, v in skills.items()
    }


@dataclass(frozen=True)
class RootFinding:
    """One Gemini-root verification result.

    Gemini findings are intentionally distinct from the legacy string errors
    returned by ``verify()``: the latter audits wrapper roots, while these
    establish that the foreign Gemini root can be recovered from its archive.
    """

    slug: str
    status: str
    detail: str
    operator_next_action: str = ""


import yaml

def _validate_frontmatter(source_text: str) -> str:
    frontmatter = ""
    if source_text.startswith("---"):
        match = re.search(r"^---\n(.*?)\n---", source_text, re.DOTALL)
        if match:
            try:
                parsed = yaml.safe_load(match.group(1))
            except Exception:
                parsed = {}
            if isinstance(parsed, dict):
                allowed = {"name", "description", "user-invocable", "when_to_use", "effort"}
                drop = {"version", "license", "compatibility", "allowed-tools", "sub_skills", "dependencies", "triggers"}
                
                for key in parsed:
                    if key not in allowed and key not in drop:
                        raise ValueError(f"unsupported frontmatter key: {key}")
                
                new_fm = {}
                # Maintain some logical order
                for key in ["name", "description", "when_to_use", "effort", "user-invocable"]:
                    if key in parsed:
                        new_fm[key] = parsed[key]
                if new_fm:
                    frontmatter = "---\n" + yaml.safe_dump(new_fm, default_flow_style=False, sort_keys=False) + "---\n"
    return frontmatter


def gemini_adapter(ownership: GeminiOwnership, source_text: str = "") -> str:
    frontmatter = ""
    if ownership.metadata_policy == "validated":
        frontmatter = _validate_frontmatter(source_text)
    return f"{frontmatter}# Generated Gemini adapter\n\nCanonical target: {ownership.canonical_path}\n"


def cross_repo_wrapper(ownership: GeminiOwnership, source_text: str = "") -> str:
    frontmatter = ""
    if ownership.metadata_policy == "validated":
        frontmatter = _validate_frontmatter(source_text)
    return f"{frontmatter}# Cross-Repo Gemini Adapter\n\nCanonical target: \"{ownership.canonical_path}\"\n\nPERPETUA_TOOLS_PATH is not set.\n"


class ReconcileLockHeldError(RuntimeError):
    """Raised when another reconciliation owns the archive-root lock."""


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def _tree_sha256(path: Path) -> str:
    """Return a deterministic digest of a skill directory.

    Reconciliation receipts live inside the archive directory, so they are
    deliberately excluded from the content digest they attest to.
    """
    if not path.is_dir():
        return ""
    digest = hashlib.sha256()
    for child in sorted(path.rglob("*"), key=lambda candidate: candidate.relative_to(path).as_posix()):
        relative = child.relative_to(path).as_posix()
        if relative == ".receipt.json":
            continue
        digest.update(relative.encode("utf-8"))
        if child.is_symlink():
            digest.update(b"L")
            digest.update(os.readlink(child).encode("utf-8"))
        elif child.is_file():
            digest.update(b"F")
            digest.update(child.read_bytes())
        elif child.is_dir():
            digest.update(b"D")
    return digest.hexdigest()


def _recognized_symlink_error_numbers() -> set[int]:
    return {
        value
        for name in ("EPERM", "ENOSYS", "EOPNOTSUPP")
        if isinstance((value := getattr(errno, name, None)), int)
    }


def create_relative_link(target: Path, source: Path) -> None:
    """Create a directory link from ``target`` to ``source`` without an
    absolute link payload, so the foreign root remains relocatable."""
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(os.path.relpath(source, target.parent), target_is_directory=True)


def write_generated_wrapper(target: Path, source: Path) -> None:
    """Write the narrow fallback used only when this filesystem cannot link."""
    target.mkdir(parents=True, exist_ok=False)
    target.joinpath("SKILL.md").write_text(
        "# Generated Gemini compatibility wrapper\n\n"
        f"Canonical target: {source}\n",
        encoding="utf-8",
    )


def _lock_path(archive_root: Path) -> Path:
    return archive_root / ".reconcile.lock"


def _pid_is_live(pid: object) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _read_lock_payload(lock_path: Path) -> dict[str, object]:
    try:
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReconcileLockHeldError(f"reconciliation lock held at {lock_path}; payload is unreadable") from exc
    if not isinstance(payload, dict):
        raise ReconcileLockHeldError(f"reconciliation lock held at {lock_path}; payload is invalid")
    return payload


def acquire_reconcile_lock(archive_root: Path, source_root: Path, only: set[str]) -> Path:
    """Atomically acquire a reconciliation lock; never reclaim it implicitly."""
    archive_root.mkdir(parents=True, exist_ok=True)
    lock_path = _lock_path(archive_root)
    payload = {
        "pid": os.getpid(),
        "started_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source_digest": _tree_sha256(source_root),
        "slugs": sorted(only),
    }
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        held_payload = _read_lock_payload(lock_path)
        state = "stale candidate" if not _pid_is_live(held_payload.get("pid")) else "active"
        raise ReconcileLockHeldError(
            f"reconciliation lock held ({state}) at {lock_path}; use explicit force-unlock after review"
        ) from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as lock_file:
            json.dump(payload, lock_file, sort_keys=True)
            lock_file.write("\n")
    except BaseException:
        lock_path.unlink(missing_ok=True)
        raise
    return lock_path


def release_reconcile_lock(lock_path: Path) -> None:
    lock_path.unlink(missing_ok=True)


def force_unlock_gemini(archive_root: Path, slug: str) -> dict[str, object]:
    """Explicit, logged recovery for a lock whose owner process is gone."""
    lock_path = _lock_path(archive_root)
    if not lock_path.exists():
        raise FileNotFoundError(f"{slug}: no reconciliation lock at {lock_path}")
    payload = _read_lock_payload(lock_path)
    if _pid_is_live(payload.get("pid")):
        raise ReconcileLockHeldError(f"{slug}: lock owner PID {payload.get('pid')} is still live")
    print(
        f"force-unlock {slug}: stale lock pid={payload.get('pid')} "
        f"started_at={payload.get('started_at')} source_digest={payload.get('source_digest')}",
        file=sys.stderr,
    )
    lock_path.unlink()
    return payload


def _write_receipt(
    archive_root: Path,
    slug: str,
    source_digest: str,
    archive_digest: str,
    final_target_kind: str,
    canonical_target: Path,
) -> None:
    receipt_path = archive_root / slug / ".receipt.json"
    
    if final_target_kind == "symlink":
        target_str = str(canonical_target.resolve())
    else:
        # Keep the raw path for adapters (e.g., $PERPETUA_TOOLS_PATH or relative)
        target_str = str(canonical_target)

    receipt = {
        "slug": slug,
        "source_digest": source_digest,
        "archive_digest": archive_digest,
        "final_target_kind": final_target_kind,
        "canonical_target": target_str,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    index_path = archive_root.parent / "index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"{slug}: archive index is invalid JSON") from exc
    if not isinstance(index, dict):
        raise ValueError(f"{slug}: archive index must be an object")
    index[slug] = archive_root.name
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def reconcile_gemini(root: Path, archive_root: Path, only: set[str], ownership_lookup: Callable[[str], GeminiOwnership]) -> list[Path]:
    """Archive-first reconciliation using Task 2 ownership manifest."""
    if not only:
        raise ValueError("Gemini reconciliation requires at least one --only slug")
    lock_path = acquire_reconcile_lock(archive_root, root, only)
    changed: list[Path] = []
    try:
        root.mkdir(parents=True, exist_ok=True)
        for slug in sorted(only):
            live = root / slug
            try:
                ownership = ownership_lookup(slug)
            except KeyError:
                raise ValueError(f"{slug}: not approved for Gemini reconciliation; add an ownership record first")

            if ownership.action == "preserve-external":
                raise ValueError(f"{slug}: preserve-external action cannot be reconciled")

            canonical_target = Path(ownership.canonical_path)

            if ownership.action == "link":
                if live.is_symlink() and live.resolve() == canonical_target.resolve():
                    continue
                if live.is_symlink():
                    raise ValueError(f"{slug}: existing Gemini symlink targets a different canonical card")

            source_digest = _tree_sha256(live)
            source_text = ""
            if live.exists():
                skill_md = live / "SKILL.md"
                if skill_md.is_file():
                    source_text = skill_md.read_text(encoding="utf-8")

            archive_skill = archive_root / slug
            if live.exists():
                if archive_skill.exists():
                    raise FileExistsError(f"{slug}: archive already exists at {archive_skill}")
                shutil.copytree(live, archive_skill)
                archive_digest = _tree_sha256(archive_skill)
                if source_digest != archive_digest:
                    raise RuntimeError(f"{slug}: archive digest does not match source")
            else:
                archive_digest = ""

            stage = root / f".{slug}.reconcile-staging"
            rollback = root / f".{slug}.reconcile-rollback"
            _remove_path(stage)
            _remove_path(rollback)
            try:
                if ownership.action == "adapter":
                    stage.mkdir(parents=True, exist_ok=False)
                    if ownership.owner == "perpetua":
                        stage.joinpath("SKILL.md").write_text(cross_repo_wrapper(ownership, source_text), encoding="utf-8")
                        final_target_kind = "cross-repo-adapter"
                    else:
                        stage.joinpath("SKILL.md").write_text(gemini_adapter(ownership, source_text), encoding="utf-8")
                        final_target_kind = "adapter"
                else:
                    try:
                        create_relative_link(stage, canonical_target)
                        final_target_kind = "symlink"
                    except OSError as exc:
                        if exc.errno not in _recognized_symlink_error_numbers():
                            raise
                        write_generated_wrapper(stage, canonical_target)
                        final_target_kind = "generated-wrapper"

                if live.exists() and _tree_sha256(live) != source_digest:
                    raise RuntimeError(f"{slug}: Gemini source changed before reconciliation commit")
                if live.exists():
                    os.replace(live, rollback)
                    try:
                        os.replace(stage, live)
                    except BaseException:
                        # Defense in depth: finally block restores rollback, but this inner rescue
                        # restores it immediately before propagating the staging failure.
                        os.replace(rollback, live)
                        raise
                    _remove_path(rollback)
                else:
                    os.replace(stage, live)
                _write_receipt(
                    archive_root, slug, source_digest, archive_digest, final_target_kind, canonical_target
                )
                changed.append(live)
            finally:
                _remove_path(stage)
                if not live.exists() and rollback.exists():
                    os.replace(rollback, live)
                _remove_path(rollback)
    finally:
        release_reconcile_lock(lock_path)
    return changed


def _gemini_slugs(root: Path, only: set[str] | None) -> set[str]:
    if only is not None:
        return only
    if not root.is_dir():
        return set()
    return {entry.name for entry in root.iterdir() if not entry.name.startswith(".") and (entry.is_dir() or entry.is_symlink())}


def verify_gemini(root: Path, archive_parent: Path, only: set[str] | None = None) -> list[RootFinding]:
    """Verify the inbound Gemini root and the archive receipt for every slug."""
    findings: list[RootFinding] = []

    index_path = archive_parent / "index.json"
    if not index_path.exists() and (archive_parent.parent / "index.json").exists():
        archive_parent = archive_parent.parent
        index_path = archive_parent / "index.json"

    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        index = {}
    except json.JSONDecodeError:
        index = {}
    if not isinstance(index, dict):
        index = {}

    for slug in sorted(_gemini_slugs(root, only)):
        live = root / slug
        batch = index.get(slug)
        if not isinstance(batch, str) or Path(batch).name != batch:
            findings.append(RootFinding(slug, "failed", f"{slug}: archive receipt index entry is missing"))
            continue
        receipt_path = archive_parent / batch / slug / ".receipt.json"
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            findings.append(RootFinding(slug, "failed", f"{slug}: archive receipt is missing or invalid"))
            continue
        archive_skill = receipt_path.parent
        actual_archive_digest = _tree_sha256(archive_skill)
        expected_keys = {"slug", "source_digest", "archive_digest", "final_target_kind", "canonical_target"}
        if not isinstance(receipt, dict) or any(key not in receipt for key in expected_keys):
            findings.append(RootFinding(slug, "failed", f"{slug}: archive receipt is incomplete"))
            continue
        if receipt["slug"] != slug or receipt["source_digest"] != actual_archive_digest or receipt["archive_digest"] != actual_archive_digest:
            findings.append(RootFinding(slug, "failed", f"{slug}: archive receipt digest or slug does not match archive"))
            continue
        final_target_kind = receipt["final_target_kind"]
        if final_target_kind not in {"symlink", "generated-wrapper", "adapter", "cross-repo-adapter"}:
            findings.append(RootFinding(slug, "failed", f"{slug}: unsupported final target kind in receipt"))
            continue
        
        canonical_target_raw = str(receipt["canonical_target"])
        if final_target_kind == "symlink":
            expected_target = str(Path(canonical_target_raw).resolve())
            if not live.is_symlink() or str(live.resolve()) != expected_target:
                findings.append(RootFinding(slug, "failed", f"{slug}: canonical target does not match receipt"))
        else:
            wrapper = live / "SKILL.md"
            if live.is_symlink() or not wrapper.is_file():
                findings.append(RootFinding(slug, "failed", f"{slug}: generated wrapper does not match receipt"))
            else:
                text = wrapper.read_text(encoding="utf-8")
                if final_target_kind == "generated-wrapper":
                    expected_target = str(Path(canonical_target_raw).resolve())
                    if expected_target not in text:
                        findings.append(RootFinding(slug, "failed", f"{slug}: generated wrapper does not match receipt"))
                else:
                    if canonical_target_raw not in text:
                        findings.append(RootFinding(slug, "failed", f"{slug}: generated adapter does not match receipt"))
    return findings
