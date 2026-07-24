#!/usr/bin/env python3
"""audit_engine.py -- unified identity classification engine.

Phase 1 of docs/plans/2026-07-24-unified-identity-audit-integrated-plan.md.
Single source of truth for approved Git author/committer identities,
consumed by repo_hygiene.py, check_identity.sh, and audit_attribution.sh
(Phase 2, not yet wired -- this module is the engine only).

Design constraints from the plan (do not violate without updating the
plan doc too):
  - No broad vendor-domain approval as a trust mechanism.
  - No universal GitHub-bot wildcard (*[bot]@users.noreply.github.com).
  - No implicit Gmail dot-normalization -- aliases are listed explicitly.
  - Private owner identities NEVER enter this file or identity-policy.json
    -- they stay in the existing private_literal_values() / local-file
    mechanism, resolved separately (see is_approved_identity()'s docstring
    for the exact resolution order).
  - Fail closed: a missing or malformed policy file is a rejection for
    every identity, not a silent pass-through.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_POLICY_FILENAME = "identity-policy.json"
_SUPPORTED_VERSION = 1


class IdentityPolicyError(Exception):
    """Policy file missing, unreadable, malformed, or unsupported version.
    Callers must treat this as fail-closed (reject the identity), never as
    fail-open."""


@dataclass(frozen=True)
class ClassificationResult:
    approved: bool
    reason: str
    matched_kind: str = ""  # "human" | "human_alias" | "agent" | "repo_bot" | "private" | ""


def _engine_dir() -> Path:
    return Path(__file__).resolve().parent


def load_policy(policy_path: Optional[Path] = None) -> dict:
    """Load and minimally validate identity-policy.json. Raises
    IdentityPolicyError on any problem -- callers must fail closed, not
    catch this and silently proceed as if no identity were approved."""
    path = policy_path or (_engine_dir() / _POLICY_FILENAME)
    if not path.is_file():
        raise IdentityPolicyError(f"identity policy file missing: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IdentityPolicyError(f"identity policy file unreadable/invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise IdentityPolicyError("identity policy file must be a JSON object")
    version = data.get("version")
    if version != _SUPPORTED_VERSION:
        raise IdentityPolicyError(
            f"unsupported identity policy version {version!r}; "
            f"this engine only supports version {_SUPPORTED_VERSION}"
        )
    for required in ("human_identities", "agent_identities", "repo_bot_identities"):
        if required not in data:
            raise IdentityPolicyError(f"identity policy missing required key: {required}")
    return data


def _private_identity_ok(
    name: str, email: str, root: Path, private_literal_values_fn
) -> bool:
    """Resolution order per plan section 4.3: public tracked policy first
    (handled by the caller before this is ever reached), then the
    existing repo-local private owner policy, then (not implemented here
    -- out of Phase 1 scope) a tightly controlled env override.
    """
    private_emails = {v.casefold() for v in private_literal_values_fn(root, "owner_gmail")}
    private_names = [v.casefold() for v in private_literal_values_fn(root, "owner_name")]
    name_tokens = private_names or ["cyre"]
    return email.casefold() in private_emails and any(
        token in name.casefold() for token in name_tokens
    )


def is_approved_identity(
    name: str,
    email: str,
    *,
    root: Path,
    repo_name: str = "",
    policy_path: Optional[Path] = None,
    private_literal_values_fn=None,
) -> ClassificationResult:
    """Classify (name, email) against the unified policy. Fail-closed: any
    IdentityPolicyError propagates to the caller rather than being
    swallowed into an approval.

    Resolution order (plan section 4.3):
      1. public tracked policy (this file's human_identities / aliases /
         agent_identities / repo_bot_identities);
      2. existing repo-local private owner policy, via
         private_literal_values_fn (injected so callers reuse their own
         already-established private-literal resolution rather than this
         engine reimplementing it independently);
      3. env override -- NOT implemented in Phase 1, intentionally: the
         plan calls this "tightly controlled" and it has no existing
         precedent to preserve compatibility with, unlike steps 1-2.
    """
    policy = load_policy(policy_path)
    name_lc, email_lc = name.strip().casefold(), email.strip().casefold()

    for entry in policy["human_identities"]:
        if entry["email"].casefold() == email_lc and entry["name"].casefold() == name_lc:
            return ClassificationResult(True, "approved human identity", "human")
        for alias in entry.get("aliases", []):
            if alias.casefold() == email_lc and entry["name"].casefold() == name_lc:
                return ClassificationResult(True, "approved human identity (alias)", "human_alias")

    for entry in policy["agent_identities"]:
        if entry["email"].casefold() == email_lc:
            allowed = entry.get("allowed_names", [])
            if not allowed or name in allowed:
                return ClassificationResult(True, "approved agent identity", "agent")
            return ClassificationResult(
                False,
                f"email {email!r} is an approved agent identity, but name {name!r} "
                f"is not in its allowed_names {allowed!r}",
            )

    repo_bots = policy["repo_bot_identities"].get(repo_name, [])
    if email_lc in {b.casefold() for b in repo_bots}:
        return ClassificationResult(True, f"approved bot identity for {repo_name}", "repo_bot")

    if private_literal_values_fn is not None:
        if _private_identity_ok(name, email, root, private_literal_values_fn):
            return ClassificationResult(True, "approved private owner identity", "private")

    return ClassificationResult(False, f"identity {name!r} <{email!r}> not found in policy")
