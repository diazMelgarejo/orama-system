from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml


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
    """A single root-verification result, shared by two call sites:

    1. Gemini archive verification (this module's ``verify_gemini``) --
       intentionally distinct from the legacy string errors returned by
       ``verify()``: the latter audits wrapper roots, while these establish
       that the foreign Gemini root can be recovered from its archive.
    2. The Antigravity/shared-agent topology audit
       (``install_thin_skill_wrappers.verify_antigravity_root`` /
       ``audit_antigravity_root``), whose status vocabulary ("missing",
       "shared-root", "divergent", "unreadable") describes root topology,
       not archive recoverability.
    """

    slug: str
    status: str
    detail: str
    operator_next_action: str = ""


def _validate_frontmatter(source_text: str) -> str:
    frontmatter = ""
    if source_text.startswith("---"):
        # Normalize CRLF before the fence match: a file authored/edited on
        # Windows (e.g. `---\r\n...\r\n---\r\n`) otherwise fails the \n---
        # regex entirely and is silently treated as "no frontmatter",
        # indistinguishable from a genuinely frontmatter-less file.
        normalized = source_text.replace("\r\n", "\n")
        match = re.search(r"^---\n(.*?)\n---", normalized, re.DOTALL)
        if match:
            try:
                parsed = yaml.safe_load(match.group(1))
            except yaml.YAMLError as exc:
                # Malformed YAML is a real defect in the source, not the
                # same thing as "no frontmatter" -- silently downgrading it
                # to empty (as a bare `except Exception` used to) hides a
                # broken skill card behind output indistinguishable from one
                # that legitimately had no frontmatter at all.
                raise ValueError(f"malformed YAML frontmatter: {exc}") from exc
            if isinstance(parsed, dict):
                # `allowed` keys are carried through into the generated
                # adapter's frontmatter as-is. `drop` keys are recognized,
                # intentionally-unsupported Gemini/Claude metadata (e.g.
                # `dependencies`, `allowed-tools`) that the thin adapter
                # format has no representation for, so they are silently
                # omitted rather than rejected outright. Anything in
                # neither set is unrecognized and raises below, so a typo
                # or genuinely new key can't be dropped by accident.
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
    """Raised when another reconciliation owns the live-root reconciliation
    lock (see ``_lock_path`` for why the lock is keyed on the live root and
    not the archive root)."""


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def _tree_sha256(path: Path) -> str:
    """Return a deterministic digest of a skill directory.

    Reconciliation receipts live inside the archive directory, so they are
    deliberately excluded from the content digest they attest to.

    A nonexistent path and an existing-but-empty directory both mean "no
    content" and must hash identically -- a fresh install writes this digest
    for a slug that has no live directory yet, and verify later recomputes it
    against the archive directory _write_receipt itself creates (which then
    exists, containing only the excluded .receipt.json). Returning a bare ""
    for "doesn't exist" but a real sha256-of-empty-input for "exists but
    empty" made every fresh install fail verify against its own receipt.
    """
    digest = hashlib.sha256()
    if not path.is_dir():
        return digest.hexdigest()
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


def _lock_path(root: Path) -> Path:
    """The lock lives beside the LIVE root being mutated, not the archive
    root. The real CLI timestamps a fresh --archive-root per invocation
    (see Task 3/4's own example commands), so two invocations against the
    same live root but different archive roots would each acquire their own
    lock file and never contend -- the thing that actually needs
    serialization is the live directory, so that is what the lock is keyed
    on."""
    return root / ".reconcile.lock"


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
    source_root.mkdir(parents=True, exist_ok=True)
    lock_path = _lock_path(source_root)
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


def force_unlock_gemini(root: Path, slug: str) -> dict[str, object]:
    """Explicit, logged recovery for a lock whose owner process is gone."""
    lock_path = _lock_path(root)
    if not lock_path.exists():
        raise FileNotFoundError(f"{slug}: no reconciliation lock at {lock_path}")
    try:
        payload = _read_lock_payload(lock_path)
    except ReconcileLockHeldError:
        # An unreadable/corrupt payload can never belong to a live, well-
        # behaved writer -- a normal exit always leaves well-formed JSON, so
        # corruption here means the writer was killed between O_CREAT|O_EXCL
        # succeeding and the payload write completing. That crash is itself
        # sufficient evidence the writer is gone: refusing to force-unlock
        # in this state (identically to "someone else holds a valid lock")
        # would leave no recovery path at all except an unsafe manual `rm`
        # outside every safety check this function exists to provide.
        print(
            f"force-unlock {slug}: stale lock at {lock_path} has an unreadable/corrupt "
            "payload (writer likely crashed mid-write); clearing it",
            file=sys.stderr,
        )
        lock_path.unlink()
        return {}
    if _pid_is_live(payload.get("pid")):
        raise ReconcileLockHeldError(f"{slug}: lock owner PID {payload.get('pid')} is still live")
    print(
        f"force-unlock {slug}: stale lock pid={payload.get('pid')} "
        f"started_at={payload.get('started_at')} source_digest={payload.get('source_digest')}",
        file=sys.stderr,
    )
    lock_path.unlink()
    return payload


def _index_lock_path(index_path: Path) -> Path:
    return index_path.with_name(".index.json.lock")


def _acquire_index_lock(index_path: Path, attempts: int = 50, delay: float = 0.02) -> Path:
    """Short-lived exclusive lock guarding the shared index.json
    read-modify-write in ``_write_receipt`` below.

    The main reconciliation lock (``_lock_path``) is deliberately keyed on
    the LIVE root, not the archive root, because two runs against the same
    live root but different (timestamped) archive roots are the documented
    normal case. But that also means two concurrent reconciliations against
    *different* live roots can share the same archive-parent index.json with
    no lock in common between them -- a plain read-modify-write there would
    let the loser of that race silently drop its own index entry. This lock
    closes that specific gap. It only ever guards a few milliseconds of I/O,
    so a bounded spin-wait is the right trade-off over failing outright:
    legitimate concurrent runs against different live roots must not
    spuriously fail just because they momentarily collide here.
    """
    index_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = _index_lock_path(index_path)
    for _ in range(attempts):
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            time.sleep(delay)
            continue
        os.close(descriptor)
        return lock_path
    raise ReconcileLockHeldError(
        f"archive index lock held at {lock_path}; giving up after {attempts} attempts"
    )


def _release_index_lock(lock_path: Path) -> None:
    lock_path.unlink(missing_ok=True)


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

    index_path = archive_root.parent / "index.json"
    index_lock = _acquire_index_lock(index_path)
    try:
        try:
            index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
        except json.JSONDecodeError as exc:
            raise ValueError(f"{slug}: archive index is invalid JSON") from exc
        if not isinstance(index, dict):
            raise ValueError(f"{slug}: archive index must be an object")
        index[slug] = archive_root.name
        # Atomic swap: allocate a unique temporary file in the destination
        # directory using tempfile.mkstemp, write and flush payload, os.fsync
        # the file descriptor to guarantee on-disk durability, then os.replace
        # over the real index.json. A deterministic .tmp name was prone to race
        # conditions and stale file pickup.
        index_dir = index_path.parent
        index_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp_index_str = tempfile.mkstemp(
            prefix=".index.json.tmp.",
            dir=index_dir,
            text=True,
        )
        tmp_index_path = Path(tmp_index_str)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(json.dumps(index, indent=2, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp_index_path, index_path)
            # Fsync parent directory for full crash-durability where supported
            try:
                dir_fd = os.open(str(index_dir), os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except OSError:
                pass
        except BaseException:
            _remove_path(tmp_index_path)
            raise
    finally:
        _release_index_lock(index_lock)

    # Only write the receipt file itself once the shared index has been
    # durably updated to point at it. The original order wrote the receipt
    # FIRST: on an index failure (e.g. corrupt index.json) that left an
    # orphaned, valid-looking .receipt.json behind, and a LATER run against
    # the same archive_root would then treat this slug as fully reconciled
    # -- the idempotence check below only required the receipt to exist --
    # even though the index never recorded it and live had already been
    # rolled back to its unreconciled state by the caller.
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def reconcile_gemini(
    root: Path,
    archive_root: Path,
    only: set[str],
    ownership_lookup: Callable[[str], GeminiOwnership],
    canonical_root: Path | None = None,
) -> list[Path]:
    """Archive-first reconciliation using Task 2 ownership manifest.

    canonical_root anchors a repo-relative canonical_path (the normal manifest
    shape, e.g. "bin/orama-system/skills/code-review/SKILL.md") for the
    filesystem symlink Task 2's "link" action creates. Without it, a relative
    canonical_path would resolve against the calling process's CWD, so the
    same on-disk symlink and the receipt describing it would only happen to
    agree with each other -- both computed from whatever directory the CLI
    happened to be invoked from -- without ever being checked against the
    real canonical location. A caller-supplied absolute canonical_path is
    used as-is regardless of canonical_root (adapter/cross-repo-adapter
    actions embed canonical_path as descriptive text, not a filesystem
    target, and are unaffected by this)."""
    if not only:
        raise ValueError("Gemini reconciliation requires at least one --only slug")
    lock_path = acquire_reconcile_lock(archive_root, root, only)
    changed: list[Path] = []
    try:
        root.mkdir(parents=True, exist_ok=True)
        for slug in sorted(only):
            live = root / slug
            try:
                # Contract: a KeyError from ownership_lookup means "this
                # slug has no ownership record", nothing else. The concrete
                # CLI lookup (`lambda s: ownership_dict[s]`) only ever
                # raises KeyError for that reason; a different
                # ownership_lookup implementation must preserve that
                # contract rather than raising KeyError for an unrelated
                # internal error.
                ownership = ownership_lookup(slug)
            except KeyError:
                raise ValueError(f"{slug}: not approved for Gemini reconciliation; add an ownership record first")

            if ownership.action == "preserve-external":
                raise ValueError(f"{slug}: preserve-external action cannot be reconciled")

            canonical_target = Path(ownership.canonical_path)
            if ownership.action == "link" and not canonical_target.is_absolute():
                if canonical_root is None:
                    raise ValueError(
                        f"{slug}: canonical_path '{ownership.canonical_path}' is repo-relative "
                        "but reconcile_gemini was not given canonical_root to anchor it against"
                    )
                canonical_target = (canonical_root / canonical_target).resolve()

            source_digest = _tree_sha256(live)
            source_text = ""
            if live.exists():
                skill_md = live / "SKILL.md"
                if skill_md.is_file() and not live.is_symlink():
                    source_text = skill_md.read_text(encoding="utf-8")

            if ownership.action == "link":
                # Fast path only: if live is ALREADY a correctly-pointed
                # symlink, there is nothing to reconcile. Deliberately
                # produces no receipt (this slug may never have been
                # archived through this engine at all -- it may simply have
                # been hand-linked correctly already) -- the general,
                # receipt-based idempotence check below is what governs
                # every OTHER "already done" case, including a link that
                # WAS reconciled through this engine on a prior run.
                if live.is_symlink() and live.resolve() == canonical_target.resolve():
                    continue
                if live.is_symlink():
                    raise ValueError(f"{slug}: existing Gemini symlink targets a different canonical card")

            archive_skill = archive_root / slug
            # General idempotence, for every action kind: a receipt at this
            # exact archive_root proves this slug's reconciliation into this
            # exact batch already completed successfully -- receipt-write is
            # now the LAST step of a fully successful run (see the
            # swap/receipt atomicity fix above), so archive_skill existing
            # WITHOUT a receipt means an earlier attempt got as far as
            # archiving and then failed before finishing, which correctly
            # falls through to the FileExistsError below rather than being
            # treated as done. This subsumes the "link" check above for
            # actions it doesn't cover (adapter, cross-repo-adapter) instead
            # of re-deriving expected output from whatever is currently live
            # -- which, on a second run, is already the GENERATED output, not
            # the original source, and comparing generated-against-generated
            # is not a comparison against the plan's actual archived source
            # of truth.
            #
            # Existence of ``.receipt.json`` alone is not trusted -- a
            # receipt can only mean "done" if it is actually parseable and
            # actually describes the archive directory it sits in. A
            # corrupt or truncated receipt (hand-edited, or left behind by
            # a version of this tool predating the index-before-receipt
            # ordering above) falls through to the FileExistsError below
            # instead of being silently treated as proof of completion.
            existing_receipt_path = archive_skill / ".receipt.json"
            if archive_skill.exists() and existing_receipt_path.exists():
                try:
                    existing_receipt = json.loads(existing_receipt_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    existing_receipt = None
                if (
                    isinstance(existing_receipt, dict)
                    and existing_receipt.get("slug") == slug
                    and existing_receipt.get("archive_digest") == _tree_sha256(archive_skill)
                ):
                    continue
            if live.exists():
                if archive_skill.exists():
                    raise FileExistsError(f"{slug}: archive already exists at {archive_skill}")
                shutil.copytree(live, archive_skill)
                archive_digest = _tree_sha256(archive_skill)
                if source_digest != archive_digest:
                    raise RuntimeError(f"{slug}: archive digest does not match source")
            else:
                # archive_skill does not exist yet (nothing to copy for a
                # fresh install). _tree_sha256 of a nonexistent path now
                # returns the same "no content" digest verify will later
                # recompute against the archive dir _write_receipt creates.
                archive_digest = _tree_sha256(archive_skill)

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

                had_live = live.exists()
                if had_live and _tree_sha256(live) != source_digest:
                    raise RuntimeError(f"{slug}: Gemini source changed before reconciliation commit")

                # The receipt is the ONLY proof a reconciliation happened and
                # the ONLY thing verify_gemini can check for recoverability
                # (P1-2). A swap that lands but whose receipt fails to write
                # (e.g. a corrupt archive index.json) is exactly the
                # unrecoverable state this plan exists to prevent, so receipt
                # failure is treated identically to swap failure: restore the
                # previously-live content, or -- for a slug with no prior
                # content -- remove the fresh install entirely, so the net
                # effect of a failed reconciliation is always "as if it never
                # ran."
                live_moved_aside = False
                try:
                    if had_live:
                        os.replace(live, rollback)
                        live_moved_aside = True
                    os.replace(stage, live)
                    _write_receipt(
                        archive_root, slug, source_digest, archive_digest, final_target_kind, canonical_target
                    )
                except BaseException:
                    # `live` is only safe to touch here if whatever
                    # currently sits at that path is NOT the still-intact,
                    # untouched original -- which is true when there never
                    # was a live original to protect (not had_live), or when
                    # the live->rollback move already completed
                    # (live_moved_aside). If had_live is True and that first
                    # move is what failed, `live` still holds the pristine
                    # original and `rollback` was never created:
                    # unconditionally deleting `live` here (the old
                    # behavior) would destroy the original outright, and the
                    # follow-up os.replace(rollback, live) would then raise
                    # a masking FileNotFoundError instead of letting the
                    # real error propagate.
                    safe_to_touch_live = not had_live or live_moved_aside
                    if safe_to_touch_live:
                        # Clears the new content if the stage->live swap
                        # succeeded but the receipt did not (safe no-op if
                        # the swap itself is what failed), then restores the
                        # previous content from rollback when there was one.
                        _remove_path(live)
                        if had_live:
                            os.replace(rollback, live)
                    raise
                if had_live:
                    _remove_path(rollback)
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
            elif not Path(expected_target).exists():
                # Path.resolve() is non-strict: it happily returns a
                # syntactically resolved path even when the final component
                # doesn't exist. A symlink whose canonical target was since
                # deleted (repo reorganized) still matches the string
                # comparison above, so this needs an explicit existence
                # check or a dangling link silently "passes" verification.
                findings.append(RootFinding(slug, "failed", f"{slug}: canonical target no longer exists: {expected_target}"))
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
