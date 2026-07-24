# Plan: Unified Identity Audit System — Single Source of Truth

**Date:** 2026-07-24  
**Status:** Phases 1-2 DONE (merged 2026-07-24T08:41 UTC via PR #217 "feat(identity):
unified audit engine — Phases 1–2" + PR #218 "docs+fix: identity-audit background
plan + repo_hygiene exemption bug"). Phases 3-4 still pending.  
**Target:** PR #197 branch (`2026-07-19-002-fleet-mesh-oob-fixes`)  
**Scope:** orama-system (Perpetua-Tools receives changes via existing sync script)

> This plan was filed and, in parallel, independently implemented + merged
> under a different worktree/branch (`2026-07-24-005b-identity-audit-plan`)
> before this filing's own "awaiting approval" gate was seen — a live
> concurrent-agent collision, not an approved-then-executed sequence. The
> shipped config is named `scripts/git/identity-policy.json` (this plan
> proposed `allowed-identities.json`); `scripts/git/audit_engine.py` exists
> on main as planned, with `repo_hygiene.py`/`check_identity.sh`/
> `audit_attribution.sh` now thin wrappers delegating to it.
>
> **Remaining scope (Phases 3-4, not yet done):**
> - Phase 3 — Perpetua-Tools sync manifest + parity verification (this
>   plan's own "Scope" line above says PT "receives changes via existing
>   sync script" — verify that actually ran/works against the shipped
>   `identity-policy.json` naming).
> - Phase 4 — doc cleanup + close the stale autofix PRs #209-214 this
>   plan's §2.2 identifies as the original symptom.

---

## 1. Executive Summary

The identity audit system uses **3 independent scripts** with **3 separate hardcoded allowlists** to check the same thing: "is this git author approved?" When one list was updated but the other two weren't, CI passed one gate then failed the next — causing 6 redundant autofix PRs (#209-#214) that all tried to rewrite commit history instead of fixing the real problem.

This plan consolidates everything into **one JSON config file + one Python engine**. All existing entry points become thin wrappers. Adding a new approved email requires **one edit to one JSON file**.

---

## 2. Problem Statement

### 2.1 Current Architecture (3 Separate Systems)

| # | Script | Language | Allowlist Format | Called By |
|---|--------|----------|-----------------|-----------|
| 1 | `scripts/review/repo_hygiene.py` | Python | `APPROVED_IDENTITIES` frozenset of `(name, email)` tuples | CI `ci.yml` -> "Repo hygiene gate" |
| 2 | `scripts/git/audit_attribution.sh` | Bash | `ALLOWED_HUMAN_AE` space-separated string | CI `ci.yml` -> "Audit branch commit attribution" |
| 3 | `scripts/git/check_identity.sh` | Bash | Hardcoded `if [[ "$email" == "..." ]]` checks | `verify-git-guards.sh` -> local hooks + CI |

### 2.2 The Bug That Caused 6 Redundant PRs

PR #197 added commits authored by `cyre <owner-gmail-dot-variant>`. The identity check failed because this email wasn't in any of the three allowlists. The fix was simple: add the email. But:

- Only `repo_hygiene.py` was updated (my fix `5cc958b6`)
- `audit_attribution.sh` still rejected it -> CI failed at "Audit branch commit attribution"
- `check_identity.sh` still rejected it -> local hooks failed
- The Cursor bot responded by creating PRs #209-#214, all attempting `git rebase --exec 'git commit --amend --author=...'`
- All 6 rewrite PRs were redundant because the correct fix was updating 2 more allowlists, not rewriting history

### 2.3 Historical Evidence of High Churn — NEEDS RE-DERIVATION

**Verification note (2026-07-24):** the original draft's evidence table
below cited 8 commit SHAs as a "12+ touches in 3 months" churn history.
Checking each against actual `git log` output, at least 3 of the 8 point
to commits with **no relation** to identity-audit scripts at all
(`ec2d525a` is a `src/` layout refactor; `c66c2aa4` — cited as the
plan's centerpiece "wrong allowlist array" incident — is a
hardware-affinity-gate skill addition). Two more are imprecise
paraphrases of otherwise-real commits. This table has been removed
rather than filed with fabricated evidence.

**What IS independently verified**, directly against current tracked
files:

- The core structural claim holds: `scripts/review/repo_hygiene.py`'s
  `APPROVED_IDENTITIES` (line 48) and `scripts/git/audit_attribution.sh`'s
  `ALLOWED_HUMAN_AE` (line 15) are two real, independently-hardcoded
  allowlists as of this commit — the underlying "3 separate lists" problem
  this plan addresses is real, not fabricated.
- The single concrete incident this plan's §2.2 is built on (PR #197's
  `cyre <owner-gmail-dot-variant>` identity rejected by two of the
  three checkers after only one was updated) is real: commit `5cc958b6`
  is genuinely `fix: add cyre <owner-gmail-dot-variant> to
  APPROVED_IDENTITIES whitelist`.

**Before implementing:** re-derive the actual churn history with
`git log --oneline -- scripts/git/check_identity.sh
scripts/git/audit_attribution.sh scripts/review/repo_hygiene.py` and cite
real SHAs, or drop the frequency claim and rely on the structural
argument alone (three independent lists is a real design smell
regardless of how often it has been touched).

The "email approved in one list, not another" bug class is real regardless
of exact frequency: the PR #197 incident (`5cc958b6`, verified above) is
one confirmed instance, and the structural argument (three independent
lists means N update sites for every new identity) means it will recur
by construction, not because of any specific past incident count.

---

## 3. Proposed Architecture

### 3.1 Design Principle: One Config, One Engine, Many Wrappers

```
scripts/git/
├── allowed-identities.json          <-- ONE config file (all approved emails)
├── audit_engine.py                  <-- ONE engine (all checking logic)
├── banned_attribution_lib.sh        <-- existing (ban patterns, unchanged)
├── audit_attribution.sh             <-- thin wrapper (15 lines, was 150)
├── check_identity.sh                <-- thin wrapper (10 lines, was 80)
├── check_commit_message.sh          <-- unchanged
└── verify-git-guards.sh             <-- unchanged

scripts/review/
└── repo_hygiene.py                  <-- imports audit_engine.is_approved_author
```

### 3.2 The Config File: `scripts/git/allowed-identities.json`

```json
{
  "$schema": "allowed-identities.schema.json",
  "description": "Approved git author/committer identities. All 3 audit entry points read this file. Edit here only -- never hardcode in scripts.",
  "version": 1,
  "human_identities": [
    {"name": "cyre", "email": "<owner-gmail-primary>", "note": "primary Gmail -- see local-only identity registry, not spelled out in tracked docs"},
    {"name": "cyre", "email": "<owner-gmail-dot-variant>", "note": "Gmail dot-variant (same mailbox) -- see local-only identity registry"},
    {"name": "cyre", "email": "lawrence@cyre.me", "note": "custom domain"},
    {"name": "cyre", "email": "lawrence@bettermind.ph", "note": "PH domain"}
  ],
  "agent_identities": [
    {"name": "Codex", "email": "codex@openai.com"},
    {"name": "Claude", "email": "claude@anthropic.com"},
    {"name": "Kimi Agent", "email": "kimi-agent@kimi.ai"},
    {"name": "Cloud Kimi Agent", "email": "cloud-kimi-agent@kimi.ai"}
  ],
  "bot_patterns": [
    "*[bot]@users.noreply.github.com",
    "cursor[bot]@users.noreply.github.com",
    "dependabot[bot]@users.noreply.github.com",
    "coderabbitai[bot]@users.noreply.github.com"
  ],
  "vendor_domains": [
    "openai.com", "anthropic.com", "cursor.com", "cursor.sh",
    "google.com", "github.com", "microsoft.com", "kimi.ai",
    "coderabbit.ai", "deepseek.com", "perplexity.ai", "x.ai"
  ]
}
```

### 3.3 The Engine: `scripts/git/audit_engine.py`

Single Python module providing three functions consumed by all entry points:

| Function | Used By | Purpose |
|----------|---------|---------|
| `is_approved_author(name, email)` | `repo_hygiene.py`, `check_identity.sh` | Check one identity against the config |
| `audit_commit_range(repo, range, strict)` | `audit_attribution.sh` | Audit all commits in a git range |
| `check_configured_identity(repo)` | `check_identity.sh` | Check `git config user.name/email` |

**Checking logic (one unified flow):**

1. Exact `(name.lower(), email.lower())` match in `human_identities`
2. Exact email match in `agent_identities` (name flexible for agents)
3. Email matches a `bot_patterns` glob (e.g., `*[bot]@users.noreply.github.com`)
4. Email domain matches a `vendor_domains` suffix (e.g., `@openai.com`)
5. Email matches `ORAMA_APPROVED_EMAILS` env var (for CI injection without file edits)

### 3.4 The Wrappers

**`scripts/git/audit_attribution.sh`** (was ~150 lines, now ~15):

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RANGE="${GIT_AUDIT_RANGE:-HEAD~79..HEAD}"
STRICT_FLAG=""
[[ "${GIT_AUDIT_STRICT:-}" == "1" ]] && STRICT_FLAG="--strict"
exec python3 "$SCRIPT_DIR/audit_engine.py" \
  --repo "$REPO_ROOT" --commits "$RANGE" $STRICT_FLAG
```

**`scripts/git/check_identity.sh`** (was ~80 lines, now ~10):

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
exec python3 "$SCRIPT_DIR/audit_engine.py" --repo "$REPO_ROOT" --config
```

**`scripts/review/repo_hygiene.py`** (replace `check_identity()` body):

```python
import sys
_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR.parent / "git"))
from audit_engine import is_approved_author

def check_identity(root: Path) -> list[str]:
    """Delegate to unified audit engine."""
    import os
    name = run_git(root, "config", "user.name").stdout.strip()
    email = run_git(root, "config", "user.email").stdout.strip()
    if os.getenv("GITHUB_ACTIONS") == "true" and not name and not email:
        return []
    # Scope check: only enforce in Cursor environments
    is_cursor = (
        os.environ.get("CURSOR_SESSION_ID") or os.environ.get("CURSOR_TRACE_ID")
        or "cursor" in name.lower() or "@cursor.com" in email.lower()
    )
    if not is_cursor:
        return []
    if is_approved_author(name, email):
        return []
    return [f"git identity mismatch: {name or '<unset>'} <{email or '<unset>'}>"]
```

---

## 4. Cross-Repo: Perpetua-Tools

### 4.1 Key Finding: PT Has No Identity Audit Scripts

Search confirmed PT has **zero** identity audit scripts of its own:
- No `audit_attribution.sh`, no `check_identity.sh`, no `APPROVED_IDENTITIES`
- PT receives all git guard scripts via `sync-attribution-guard-scripts.sh` from orama-system

### 4.2 Existing Sync Chain

```
orama-system/scripts/git/           <-- canonical source of truth
         |
         |-- sync-attribution-guard-scripts.sh --> $PT_TARGET/scripts/git/
         |
         +-- CI (ci.yml)
```

### 4.3 What Changes for PT

**Nothing new to create in PT.** The existing sync script copies files from orama's `scripts/git/` to PT's `scripts/git/`. Adding `allowed-identities.json` and `audit_engine.py` to the sync list means PT automatically gets the unified system.

**Update needed:** `sync-attribution-guard-scripts.sh` copy list:

```bash
# Add these two lines to the for loop in sync-attribution-guard-scripts.sh:
for rel in \
  allowed-identities.json \          # NEW
  audit_engine.py \                  # NEW
  cursor-hooks-id.sh \
  hooks/commit-msg.strip-coauthor \
  # ... rest unchanged
```

### 4.4 Post-Sync Layout (Both Repos)

```
# In BOTH repos after sync:
scripts/git/
├── allowed-identities.json          # NEW
├── audit_engine.py                  # NEW
├── banned_attribution_lib.sh        # existing, unchanged
├── audit_attribution.sh             # REWRITTEN: thin wrapper
├── check_identity.sh                # REWRITTEN: thin wrapper
├── check_commit_message.sh          # unchanged
├── verify-git-guards.sh             # unchanged
└── ... (rest unchanged)
```

---

## 5. CI Integration

### 5.1 No Changes to `.github/workflows/ci.yml`

All existing step names and commands stay identical. The scripts they call still exist and exit the same way -- they just delegate to the unified engine underneath.

```yaml
# BEFORE (current):
- name: Repo hygiene gate
  run: python3 scripts/review/repo_hygiene.py .

- name: Audit branch commit attribution (PR commits)
  run: bash scripts/git/audit_attribution.sh

# AFTER (identical YAML -- only internals change):
- name: Repo hygiene gate
  run: python3 scripts/review/repo_hygiene.py .

- name: Audit branch commit attribution (PR commits)
  run: bash scripts/git/audit_attribution.sh
```

### 5.2 One-Pass Commit Strategy

```
Single commit on PR #197:

    refactor: unify identity audit into one engine + one config

    - Add scripts/git/allowed-identities.json: single source of truth for
      all approved git author/committer identities. Human, agent, bot, and
      vendor domain entries in one structured JSON file.

    - Add scripts/git/audit_engine.py: unified Python engine replacing
      identity-check logic duplicated across 3 scripts. All entry points
      (audit_attribution.sh, check_identity.sh, repo_hygiene.py) delegate
      to this engine via import or thin wrapper.

    - Rewrite audit_attribution.sh: 150 lines -> 15 lines, thin wrapper
      that calls audit_engine.py --commits.

    - Rewrite check_identity.sh: 80 lines -> 10 lines, thin wrapper that
      calls audit_engine.py --config.

    - Update repo_hygiene.py: replace check_identity() body with import
      of audit_engine.is_approved_author().

    - Add tests/test_audit_engine.py: parametrized tests covering all 5
      identity matching rules (human, agent, bot, vendor, env override).

    - Update sync-attribution-guard-scripts.sh: add allowed-identities.json
      and audit_engine.py to the copy list for Perpetua-Tools sync.

    Fixes the root cause of #209-#214: partial allowlist updates across
    independent hardcoded lists. Adding an approved identity now requires
    exactly one edit to allowed-identities.json.
```

---

## 6. Migration Steps

| Step | Action | Effort | Risk |
|------|--------|--------|------|
| 1 | Create `allowed-identities.json` from merged data of all 3 scripts | 10 min | None -- new file |
| 2 | Create `audit_engine.py` with full logic + CLI | 1 hr | None -- new file, proven logic |
| 3 | Rewrite `audit_attribution.sh` as thin wrapper | 10 min | None -- same CLI interface |
| 4 | Rewrite `check_identity.sh` as thin wrapper | 10 min | None -- same CLI interface |
| 5 | Update `repo_hygiene.py` to import `audit_engine` | 10 min | None -- import + delegate |
| 6 | Add `allowed-identities.json` and `audit_engine.py` to sync script copy list | 5 min | None -- one-line additions |
| 7 | Create `tests/test_audit_engine.py` with parametrized cases | 30 min | None -- new tests |
| 8 | Run CI on test branch to verify all 3 gates pass | 15 min | Low -- wrappers are thin |
| 9 | Merge to PR #197 | 5 min | Low -- already verified |
| 10 | Sync to PT via existing `sync-attribution-guard-scripts.sh` | 5 min | None -- already wired |

**Total effort: ~2.5 hours**  
**Risk: Very low** -- every entry point keeps the same CLI contract. Zero changes to CI YAML.

---

## 7. Benefits

| Before (3 separate) | After (1 unified) |
|---------------------|-------------------|
| Add email -> edit **3 files** (Python + Bash + Bash) | Add email -> edit **1 JSON file** |
| 3 formats: frozenset, space-string, if-chain | **1 format**: JSON |
| Risk: partial updates -> 6 broken PRs (#209-#214) | **Impossible** to partially update |
| ~230 lines of identity-check logic | ~80 lines engine + 20 lines JSON + 25 lines wrappers |
| No schema validation | JSON schema can validate structure |
| Hard to test (3 test paths) | **One pytest module** covers everything |
| Can't extend without code changes | `ORAMA_APPROVED_EMAILS` env var extends at runtime |
| Each script has its own edge case handling | **One consistent** matching policy everywhere |

---

## 8. Open Questions

1. **Env var override name**: `ORAMA_APPROVED_EMAILS` (comma-separated) is proposed. Should this also support `.verboten-literals.local`-style key-value format for consistency with the existing private attribution system?

2. **Bot pattern granularity**: Currently `*[bot]@users.noreply.github.com` is a broad wildcard that accepts any GitHub bot. Should specific bot identities be listed individually in `agent_identities` for audit trail purposes?

3. **Vendor domain wildcard safety**: `vendor_domains` suffix matching could accidentally approve a subdomain of a vendor that isn't actually their agent service (e.g., `someapp.openai.com`). Is suffix matching sufficient or should exact domain matching be required?

4. **PT CI doesn't currently run identity checks**: Should the PT CI workflow be updated to call `audit_attribution.sh` after sync, or is local hook installation sufficient?

---

## 9. Appendix: Full Engine Pseudocode

```python
# audit_engine.py -- core logic

def is_approved_author(name: str, email: str) -> bool:
    cfg = _load_config()  # reads allowed-identities.json once, cached
    name_lc = name.strip().lower()
    email_lc = email.strip().lower()

    # 1. Human: exact name + email
    for entry in cfg["human_identities"]:
        if entry["name"].lower() == name_lc and entry["email"].lower() == email_lc:
            return True

    # 2. Agent: email match (name flexible)
    for entry in cfg["agent_identities"]:
        if entry["email"].lower() == email_lc:
            return True

    # 3. Bot: glob pattern match
    for pattern in cfg["bot_patterns"]:
        if fnmatch.fnmatch(email_lc, pattern.lower()):
            return True

    # 4. Vendor: domain suffix match
    domain = email_lc.split("@")[-1] if "@" in email_lc else ""
    for suffix in cfg["vendor_domains"]:
        if domain == suffix or domain.endswith(f".{suffix}"):
            return True

    # 5. Environment override
    if email_lc in _env_approved_emails():
        return True

    return False  # FAIL-CLOSED: not in any allowlist
```

The engine is **fail-closed by design**: every identity must match at least one rule. No implicit approvals, no wildcard defaults, no "if it doesn't match the deny list, allow it" logic.
