#!/usr/bin/env python3
"""Gate Hermes/profile installers on a verified orama-system checkout.

Security invariants before writing to $HERMES_HOME or ~/.openclaw workspaces:
  - Operator may set ORAMA_TRUST_HERMES_SYNC=1 after manual review.
  - ORAMA_SKIP_HERMES_SYNC=1 skips all Hermes materialization (install.sh).
  - Default: tree-twin sync with origin/main via reanchor_scan (Fable-5 doctrine).
  - ORAMA_VERIFY_COMMIT_SIG=1 requires a GPG-verified HEAD (and origin/main on main)
    signed by a key in ORAMA_ALLOWED_GPG_FINGERPRINTS (comma-separated).

Detailed reasons are logged to .local/verify-trusted-install.log only.
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_NAME = "verify-trusted-install.log"
logger = logging.getLogger(__name__)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def resolve_repo_root() -> Path:
    script = Path(__file__).resolve()
    top = _git(script.parent.parent.parent, "rev-parse", "--show-toplevel")
    if top.returncode == 0 and top.stdout.strip():
        return Path(top.stdout.strip())
    return script.parent.parent.parent


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def _allowed_gpg_fingerprints() -> set[str]:
    raw = os.environ.get("ORAMA_ALLOWED_GPG_FINGERPRINTS", "").strip()
    if not raw:
        return set()
    return {fp.strip().upper().replace(" ", "") for fp in raw.split(",") if fp.strip()}


def _normalize_fingerprint(value: str) -> str:
    return value.strip().upper().replace(" ", "")


def _fingerprint_matches(actual: str, allowed: set[str]) -> bool:
    actual_norm = _normalize_fingerprint(actual)
    if not actual_norm or actual_norm in {"N/A", "G"}:
        return False
    for candidate in allowed:
        cand_norm = _normalize_fingerprint(candidate)
        if not cand_norm:
            continue
        if actual_norm == cand_norm:
            return True
        shorter, longer = (cand_norm, actual_norm) if len(cand_norm) <= len(actual_norm) else (actual_norm, cand_norm)
        if len(shorter) >= 8 and longer.endswith(shorter):
            return True
    return False


def _commit_signer_fingerprint(root: Path, ref: str) -> str | None:
    proc = _git(root, "show", "-s", "--format=%GF", ref)
    if proc.returncode != 0:
        return None
    fp = proc.stdout.strip()
    return fp or None


def verify_commit_signature(root: Path, ref: str) -> tuple[bool, str]:
    """Optional GPG gate — enabled with ORAMA_VERIFY_COMMIT_SIG=1."""
    if not _truthy("ORAMA_VERIFY_COMMIT_SIG"):
        return True, "signature check skipped (set ORAMA_VERIFY_COMMIT_SIG=1 to require)"

    allowed = _allowed_gpg_fingerprints()
    if not allowed:
        return False, (
            "ORAMA_VERIFY_COMMIT_SIG=1 requires ORAMA_ALLOWED_GPG_FINGERPRINTS "
            "(comma-separated maintainer key fingerprints)"
        )

    proc = _git(root, "verify-commit", ref)
    if proc.returncode != 0:
        return False, f"commit {ref[:12]} is not GPG-verified (git verify-commit failed)"

    signer = _commit_signer_fingerprint(root, ref)
    if not signer or not _fingerprint_matches(signer, allowed):
        return False, f"commit {ref[:12]} signer not in ORAMA_ALLOWED_GPG_FINGERPRINTS policy"

    return True, f"GPG-verified {ref[:12]} (allowed signer)"


def log_local(root: Path, ok: bool, reason: str) -> None:
    # `reason` is always a short human-readable status string built from
    # truncated commit SHAs (head_sha[:12]) and GPG *fingerprints* -- a
    # fingerprint is the public identifier used to verify a signature, not
    # a secret; no private key material or token ever flows through this
    # function. Kept in .local/ (gitignored) rather than stdout/CI logs
    # purely to keep routine CI output terse, not because the content is
    # sensitive.
    path = root / ".local" / LOG_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    line = f"{stamp}\t{'OK' if ok else 'FAIL'}\t{reason}\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def _branch_synced_with_main(root: Path, branch_name: str, head_sha: str) -> tuple[bool, str]:
    remote = _git(root, "rev-parse", "--verify", "origin/main")
    if remote.returncode != 0:
        return False, "origin/main not available"
    origin_sha = remote.stdout.strip()
    if branch_name == "main":
        if head_sha != origin_sha:
            return False, f"main HEAD {head_sha[:12]} != origin/main {origin_sha[:12]}"
        return True, "main matches origin/main"

    scan_script = root / "scripts" / "git" / "reanchor_scan.sh"
    if not scan_script.is_file():
        return False, "reanchor_scan.sh missing"
    result = subprocess.run(
        ["bash", str(scan_script), str(root), "origin/main", "heads"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode not in (0, 2):
        return False, "reanchor_scan failed"
    scan_ref_re = re.compile(r"^\s+(\S+)\s+(.+)$")
    for line in result.stdout.splitlines():
        match = scan_ref_re.match(line)
        if not match or match.group(1) != branch_name:
            continue
        status = match.group(2)
        if "MERGED/in-main" in status:
            return True, f"branch {branch_name} tree-twin in main"
        if "NEEDS-REANCHOR" in status:
            return False, f"branch {branch_name} needs reanchor onto main"
        if "NO-TWIN" in status or "ORPHAN" in status:
            return False, f"branch {branch_name} not synchronized with main"
    return False, f"branch {branch_name} sync status unknown"


def trusted_install_allowed(root: Path) -> tuple[bool, str]:
    if _truthy("ORAMA_SKIP_HERMES_SYNC"):
        return False, "ORAMA_SKIP_HERMES_SYNC is set"
    if _truthy("ORAMA_TRUST_HERMES_SYNC"):
        return True, "operator override ORAMA_TRUST_HERMES_SYNC=1"

    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch.returncode != 0:
        return False, "not a git repository"
    branch_name = branch.stdout.strip()

    head = _git(root, "rev-parse", "HEAD")
    if head.returncode != 0:
        return False, "cannot resolve HEAD"
    head_sha = head.stdout.strip()

    dirty = _git(root, "status", "--porcelain", "--", "bin/agents", "bin/orama-system/skills/hermes-harness")
    if dirty.returncode != 0:
        return False, "git status failed for harness paths"
    if dirty.stdout.strip():
        return False, "uncommitted changes under bin/agents or hermes-harness"

    synced, sync_reason = _branch_synced_with_main(root, branch_name, head_sha)
    if not synced:
        return False, sync_reason

    ok_sig, sig_reason = verify_commit_signature(root, head_sha)
    if not ok_sig:
        return False, sig_reason

    if branch_name == "main":
        remote = _git(root, "rev-parse", "--verify", "origin/main")
        if remote.returncode != 0:
            return False, "origin/main not available for signature verification"
        ok_origin_sig, origin_sig_reason = verify_commit_signature(root, remote.stdout.strip())
        if not ok_origin_sig:
            return False, origin_sig_reason

    return True, f"trusted checkout @ {head_sha[:12]} ({sync_reason}; {sig_reason})"


def public_message(ok: bool) -> str:
    """CodeQL-safe status line — never embed branch names, SHAs, or topology."""
    return "trusted install check passed" if ok else "trusted install check failed"


def _configure_logging(quiet: bool) -> logging.Logger:
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(logging.Formatter("%(message)s"))

    root_logger = logging.getLogger(__name__)
    root_logger.handlers.clear()
    root_logger.addHandler(stderr_handler)
    root_logger.setLevel(logging.WARNING if quiet else logging.INFO)
    root_logger.propagate = False

    stdout_logger = logging.getLogger(f"{__name__}.stdout")
    stdout_logger.handlers.clear()
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(logging.Formatter("%(message)s"))
    stdout_logger.addHandler(stdout_handler)
    stdout_logger.setLevel(logging.INFO)
    stdout_logger.propagate = False
    return stdout_logger


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify trusted install preconditions.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    stdout_logger = _configure_logging(args.quiet)
    root = resolve_repo_root()
    ok, reason = trusted_install_allowed(root)
    log_local(root, ok, reason)
    if not args.quiet:
        stdout_logger.info(public_message(ok))
        if ok:
            logger.info("trusted install check passed")
        else:
            logger.error("trusted install check failed")
            logger.error("see .local/verify-trusted-install.log — never prints topology to stdout")
            logger.error(
                "hint: git fetch origin main && git pull --ff-only; "
                "review bin/agents; or ORAMA_TRUST_HERMES_SYNC=1 after manual review"
            )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
