# Unified Identity Audit System — Integrated Cross-Repo Plan

**Date:** 2026-07-24  
**Status:** PLAN — review before implementation  
**Primary implementation repo:** `diazMelgarejo/orama-system`  
**Plan branch:** PR #197 — `2026-07-19-002-fleet-mesh-oob-fixes`  
**Affected downstream repo:** `diazMelgarejo/Perpetua-Tools`  
**Related active PT work:** PR #276 — `security/alphaclaw-tls-proxy-scaffold`  
**Source reviewed:** `plan-unified-identity-audit.md`

---

## 1. Executive Decision

The source plan identifies the correct root cause: approved Git identities are encoded independently in three enforcement paths, so partial updates produce contradictory results and trigger unnecessary history-rewrite attempts.

The correct architecture is still:

```text
one public policy file
        +
one policy engine
        +
multiple compatibility entry points
```

However, the source proposal must be tightened before implementation:

1. Preserve all current attribution behavior, not only identity matching.
2. Do not approve arbitrary vendor-domain email addresses.
3. Do not approve every GitHub bot through a broad wildcard.
4. Keep private owner identities in the existing private/local policy channel, not in a tracked public JSON file.
5. Validate the policy schema and fail closed when tracked policy is missing or malformed.
6. Preserve the exact CLI, environment-variable, output, and exit-code contracts of existing shell entry points.
7. Synchronize executable and data files with correct file modes.
8. Keep PT PR #276 scoped to AlphaClaw TLS; identity-governance synchronization should be a separate, mechanically generated PT change.

---

## 2. Grounded Current State

### 2.1 Three independent identity sources exist

| Enforcement path | Current source | Current role |
|---|---|---|
| `scripts/review/repo_hygiene.py` | `APPROVED_IDENTITIES` set | Repo-hygiene configured-identity checks |
| `scripts/git/audit_attribution.sh` | `ALLOWED_HUMAN_AE`, bot lists, `author_ok()` | Commit-range author audit plus banned-attribution and co-author checks |
| `scripts/git/check_identity.sh` | exact-address checks plus vendor-domain suffixes | Cursor-scoped local configured-identity guard |

PR #197 already demonstrates the fragmentation: the Gmail alias was added independently to all three locations.

### 2.2 Existing behavior that must not be lost

The unified engine must preserve these contracts from `audit_attribution.sh`:

- inspect author and committer metadata;
- scan commit bodies for banned and private forbidden attribution;
- invoke `check_commit_message.sh` for co-author policy;
- audit `HEAD`, `main`, and `origin/main` summaries;
- honor `GIT_AUDIT_RANGE`;
- honor `GIT_AUDIT_STRICT=1`;
- preserve the existing tabular summary and diagnostic output sufficiently for CI and operators;
- retain repo-specific preferred bot reporting.

The unified engine must preserve these contracts from `check_identity.sh`:

- enforce only in Cursor agent contexts;
- allow non-Cursor human and agent workflows to pass through unchanged;
- read the existing private owner-email mechanism;
- print the configured identity before evaluation;
- retain compatible success/failure exit codes and actionable errors.

### 2.3 Orama remains canonical

`orama-system/scripts/git/sync-attribution-guard-scripts.sh` is the established canonical-to-downstream synchronization path. PT should consume the policy engine and public policy file through this mechanism rather than develop an independent implementation.

### 2.4 PT PR #276 remains separate

PT PR #276 is a focused AlphaClaw TLS proxy scaffold. It should not absorb identity-audit refactoring. Mixing the two would recreate the scope-drift problem this consolidation is intended to prevent.

The PT identity-sync result should therefore land through one of these controlled paths:

1. a dedicated generated PT synchronization PR after the Orama implementation is approved; or
2. a later explicit sync commit on a PT integration branch whose sole purpose is guard parity.

---

## 3. Target Architecture

```text
orama-system/scripts/git/
├── identity-policy.json
├── identity-policy.schema.json
├── audit_engine.py
├── banned_attribution_lib.sh
├── audit_attribution.sh
├── check_identity.sh
├── check_commit_message.sh
├── verify-git-guards.sh
├── verify-guard-parity.sh
└── sync-attribution-guard-scripts.sh

orama-system/scripts/review/
└── repo_hygiene.py

Perpetua-Tools/scripts/git/
└── synchronized byte-identical copies of the canonical public policy,
    engine, wrappers, and supporting guard files
```

### Ownership boundaries

| Concern | Canonical owner |
|---|---|
| Public approved identities | `identity-policy.json` |
| Policy structure | `identity-policy.schema.json` |
| Identity classification | `audit_engine.py` |
| Commit-range orchestration | `audit_engine.py` CLI |
| Banned/private attribution patterns | existing `banned_attribution_lib.sh` and private local files |
| Wrapper compatibility | `audit_attribution.sh`, `check_identity.sh` |
| Repo hygiene integration | `repo_hygiene.py` imports the engine |
| Cross-repo parity | sync + parity scripts |

---

## 4. Public Policy Model

### 4.1 Proposed tracked file

Path:

```text
scripts/git/identity-policy.json
```

Recommended shape:

```json
{
  "$schema": "identity-policy.schema.json",
  "version": 1,
  "description": "Canonical public Git author/committer identity policy.",
  "human_identities": [
    {
      "name": "cyre",
      "email": "diazmelgarejo@gmail.com",
      "aliases": ["lawrence.melgarejo@gmail.com"],
      "note": "Explicitly approved Gmail aliases for the same operator"
    },
    {
      "name": "cyre",
      "email": "lawrence@cyre.me"
    },
    {
      "name": "cyre",
      "email": "lawrence@bettermind.ph"
    }
  ],
  "agent_identities": [
    {"email": "codex@openai.com", "allowed_names": ["Codex"]},
    {"email": "claude@anthropic.com", "allowed_names": ["Claude"]},
    {"email": "noreply@anthropic.com", "allowed_names": []},
    {"email": "cursoragent@cursor.com", "allowed_names": ["Cursor Agent"]},
    {"email": "kimi-agent@kimi.ai", "allowed_names": ["Kimi Agent"]},
    {"email": "cloud-kimi-agent@kimi.ai", "allowed_names": ["Cloud Kimi Agent"]},
    {"email": "noreply@coderabbit.ai", "allowed_names": ["CodeRabbit"]}
  ],
  "repo_bot_identities": {
    "orama-system": [
      "cursor[bot]@users.noreply.github.com"
    ],
    "Perpetua-Tools": [
      "dependabot[bot]@users.noreply.github.com",
      "coderabbitai[bot]@users.noreply.github.com"
    ]
  }
}
```

### 4.2 Explicitly rejected policy shortcuts

#### No broad vendor-domain approval

Do not carry forward `vendor_domains` as an approval mechanism. Domain ownership does not prove the account is an authorized repository author, and suffix matching expands trust without review.

Vendor domains may be retained only as diagnostics—for example, to explain that an unapproved address belongs to a recognized vendor—but not as an allow rule.

#### No universal GitHub-bot wildcard

Do not use:

```text
*[bot]@users.noreply.github.com
```

as a global approval rule. Approve explicit repo-scoped bot identities instead.

#### No implicit Gmail normalization

Do not algorithmically normalize every Gmail local part by removing dots. Store each approved alias explicitly. This avoids surprising equivalence rules and keeps the audit trail reviewable.

### 4.3 Private identities stay private

The existing `private_owner_email_ok()` mechanism must remain supported. Private identities must not be copied into `identity-policy.json` or synchronized into public repositories.

Resolution order should be:

1. public tracked policy;
2. existing repo-local private owner policy;
3. tightly controlled environment override, when explicitly enabled.

---

## 5. Schema and Fail-Closed Rules

Add:

```text
scripts/git/identity-policy.schema.json
```

The schema must enforce:

- supported integer `version`;
- required top-level collections;
- syntactically valid email strings;
- unique primary emails and aliases after case normalization;
- no identity appearing in conflicting categories;
- repo bot keys limited to explicit repository names;
- no universal `*[bot]` pattern;
- no vendor-domain approval list;
- no unknown top-level keys unless deliberately versioned.

### Failure behavior

- Missing or malformed tracked policy: fail closed with a clear path and parse/schema error.
- Missing private policy: continue using public policy.
- Invalid optional environment override: reject the override and report it; do not silently ignore malformed entries.
- Unsupported policy version: fail closed.

The engine may use a small internal validator to avoid a new runtime dependency, or JSON Schema validation if the repository already provides a compatible dependency. The test suite must validate both the schema and the loader behavior.

---

## 6. Unified Engine Contract

Path:

```text
scripts/git/audit_engine.py
```

### 6.1 Public Python API

```python
load_policy(repo_root: Path | None = None) -> IdentityPolicy
is_approved_identity(name: str, email: str, *, repo_name: str, repo_root: Path) -> ApprovalResult
check_configured_identity(repo_root: Path, *, cursor_scoped: bool = True) -> IdentityCheckResult
audit_commit_range(repo_root: Path, revision: str, *, strict: bool) -> AuditReport
```

Use structured result objects rather than booleans alone. Each decision should expose:

- approved/rejected;
- matched rule category;
- matched canonical identity;
- source: public policy, private policy, environment override, or repo bot policy;
- human-readable reason.

This improves diagnostics without changing wrapper exit behavior.

### 6.2 Approval sequence

1. Normalize surrounding whitespace and email case.
2. Match exact human name/email or an explicitly listed alias.
3. Match exact agent email and, where configured, an allowed name.
4. Match exact repo-scoped bot email.
5. Consult the existing private owner-email mechanism.
6. Consult an optional exact-email environment override only when explicitly enabled.
7. Reject.

### 6.3 Environment override

Use an exact-email list such as `ORAMA_APPROVED_EMAILS`, but constrain it:

- comma-separated exact emails only;
- disabled in CI unless `ORAMA_ALLOW_IDENTITY_ENV_OVERRIDE=1` is also set;
- never supports domain or glob entries;
- diagnostics must state that approval came from an environment override;
- tests must prove the override cannot bypass banned-attribution or co-author checks.

### 6.4 Audit responsibilities

The engine must absorb the repeated Git metadata traversal while preserving external helpers where they remain canonical:

- identity classification: Python engine;
- banned/private literal matching: existing shell library may remain behind a wrapper initially, or be migrated only in a separately reviewed phase;
- commit-message/co-author policy: existing `check_commit_message.sh` remains canonical in phase 1.

Do not rewrite every guard subsystem merely because identity approval is being centralized.

---

## 7. Compatibility Wrappers

### 7.1 `audit_attribution.sh`

Keep the file and its operational interface. It becomes a thin launcher, but must forward:

- positional history-count behavior where currently supported;
- `GIT_AUDIT_RANGE`;
- `GIT_AUDIT_STRICT`;
- repository root;
- existing diagnostics and exit semantics.

The engine CLI should provide a compatibility mode, for example:

```bash
exec python3 "$SCRIPT_DIR/audit_engine.py" audit \
  --repo "$REPO_ROOT" \
  --history-count "${1:-79}"
```

Environment handling can remain inside the engine so CI YAML does not change.

### 7.2 `check_identity.sh`

Keep Cursor scoping and configured-identity output. The shell wrapper should only resolve paths and exec:

```bash
exec python3 "$SCRIPT_DIR/audit_engine.py" configured-identity \
  --repo "$REPO_ROOT" \
  --cursor-scoped
```

### 7.3 `repo_hygiene.py`

Import the engine through a stable module path and delegate identity policy only. Do not couple the entire hygiene scanner to CLI output parsing.

A minimal integration should call `check_configured_identity()` or `is_approved_identity()` and translate the structured result into the existing hygiene error format.

---

## 8. Cross-Repo Synchronization

### 8.1 Update the Orama sync manifest

The current synchronization loop treats every copied file as executable (`install -m 0755`). Split it into two groups.

#### Executable files (`0755`)

```text
audit_engine.py
audit_attribution.sh
check_identity.sh
other existing shell/Python guard executables
```

#### Data/schema files (`0644`)

```text
identity-policy.json
identity-policy.schema.json
```

### 8.2 Update parity verification

`verify-guard-parity.sh` must include:

- byte parity for `audit_engine.py`;
- byte parity for `identity-policy.json`;
- byte parity for `identity-policy.schema.json`;
- executable-bit checks for wrappers/engine;
- non-executable data-file mode checks where portable;
- explicit reporting when PT has stale or missing files.

### 8.3 PT integration sequence

1. Implement and test in Orama.
2. Run the sync script into a clean PT checkout.
3. Verify parity.
4. Run PT guard and CI tests.
5. Open a dedicated PT synchronization PR.
6. Do not modify PT PR #276 unless its owner explicitly elects to rebase or merge the separate sync result later.

This preserves PT PR #276’s TLS scope and prevents unrelated governance changes from obscuring its security review.

---

## 9. Test Strategy

### 9.1 Engine unit tests

Add `tests/test_audit_engine.py` covering:

- exact human identity;
- explicit Gmail alias;
- wrong human name with a name-bound address;
- exact agent identity;
- allowed and disallowed agent names;
- repo-specific approved bots;
- bot approved in PT but rejected in Orama, and vice versa;
- unknown GitHub bot rejection;
- vendor-domain address rejection;
- private owner-email approval;
- exact environment override;
- CI override disabled by default;
- malformed config;
- unsupported config version;
- duplicate/conflicting policy entries;
- case and whitespace normalization;
- missing policy file.

### 9.2 Commit-range regression tests

Cover:

- approved author and committer;
- rejected author;
- banned attribution in author, committer, and body;
- invalid co-author line;
- `GIT_AUDIT_RANGE` selection;
- strict and non-strict exits;
- history-count mode;
- summary output compatibility.

### 9.3 Wrapper contract tests

Run the shell wrappers as subprocesses and assert:

- existing command forms still work;
- environment variables are honored;
- exit codes remain stable;
- paths containing spaces work;
- output contains actionable identity details without leaking private policy values.

### 9.4 Repo hygiene integration tests

Update `tests/test_repo_hygiene.py` to prove:

- the hygiene path reads the same canonical policy;
- adding one identity fixture changes all three enforcement results consistently;
- removing an identity causes all three enforcement paths to reject it;
- hygiene remains unaffected outside Cursor-scoped identity enforcement where that is the current contract.

### 9.5 Cross-repo parity tests

Add or update tests so the synchronized PT copy is verified against Orama’s canonical files. The test should fail when either code or policy data drifts.

---

## 10. Phased Implementation

### Phase 0 — Behavior inventory

Before editing, capture golden outputs and exit codes for:

```bash
bash scripts/git/check_identity.sh
bash scripts/git/audit_attribution.sh
GIT_AUDIT_RANGE=<range> GIT_AUDIT_STRICT=1 bash scripts/git/audit_attribution.sh
python3 scripts/review/repo_hygiene.py .
```

Record approved/rejected fixtures for every currently supported identity and bot.

### Phase 1 — Policy and engine

- add `identity-policy.json`;
- add `identity-policy.schema.json`;
- add loader and structured identity classification;
- preserve private-policy integration;
- add engine unit tests.

No wrappers change until this phase is green.

### Phase 2 — One consumer at a time

1. switch `repo_hygiene.py` to the engine and run its suite;
2. switch `check_identity.sh` and run local-hook tests;
3. switch `audit_attribution.sh` and run commit-range/CI tests.

This makes regressions attributable and avoids a three-entry-point flag day.

### Phase 3 — Cross-repo sync

- update sync file groups and modes;
- update parity verification;
- sync into a clean PT checkout;
- run PT tests;
- create a dedicated PT guard-sync PR.

### Phase 4 — Cleanup

Only after all consumers are green:

- remove hardcoded public identity lists from the three old locations;
- retain compatibility comments pointing to `identity-policy.json`;
- document the single-edit procedure;
- close or annotate stale autofix PRs as superseded by policy consolidation.

---

## 11. Acceptance Criteria

The work is complete only when all of the following are true:

- [ ] One tracked public identity policy exists in Orama.
- [ ] One engine performs all public identity classification.
- [ ] Private owner identities remain outside tracked public policy.
- [ ] No broad vendor-domain approval remains.
- [ ] No universal GitHub-bot wildcard remains.
- [ ] Existing banned-attribution and co-author protections are preserved.
- [ ] Existing wrapper commands, environment variables, output expectations, and exit codes remain compatible.
- [ ] `repo_hygiene.py`, `check_identity.sh`, and `audit_attribution.sh` produce consistent decisions from one policy.
- [ ] Policy schema and fail-closed behavior are tested.
- [ ] Orama-to-PT synchronization copies executables and data files with correct modes.
- [ ] Guard parity includes engine, policy, and schema.
- [ ] Orama CI is green.
- [ ] PT CI is green on a dedicated sync branch.
- [ ] PT PR #276 remains independently reviewable and contains no unrelated identity-audit refactor.

---

## 12. Recommended Commit Structure

Avoid the source plan’s single large commit. Use reviewable, bisectable commits:

1. `test(identity): capture current guard behavior and compatibility contracts`
2. `feat(identity): add canonical policy schema and audit engine`
3. `refactor(hygiene): delegate configured identity checks to audit engine`
4. `refactor(git): route local identity guard through audit engine`
5. `refactor(git): route commit attribution audit through audit engine`
6. `chore(git): sync policy engine and schema to partner repos`
7. `docs(git): document single-source identity policy workflow`

Each commit must pass its targeted tests before the next consumer migrates.

---

## 13. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Central engine becomes a single point of failure | Fail-closed loader, schema tests, wrapper compatibility tests |
| Refactor silently drops banned/co-author checks | Golden behavior tests before migration; phased consumer conversion |
| Public policy leaks private owner addresses | Preserve private local mechanism; prohibit private entries in tracked JSON |
| Broad trust expansion | Exact identities and repo-scoped bots only |
| Sync script marks JSON executable | Separate executable and data copy lists |
| PT drifts after sync | Extend parity script and CI checks |
| PR #197 scope expands further | This commit adds the plan only; implementation should be separately reviewed or explicitly approved as a follow-up stack |
| PT PR #276 review is obscured | Keep identity synchronization in a dedicated PT PR |

---

## 14. Final Recommendation

Approve the consolidation objective with the amendments in this document.

The decisive principle is:

> **Centralize decisions without broadening trust, and preserve every enforcement contract before deleting duplicated code.**

The original plan correctly identifies duplication as the root cause. This integrated version converts that insight into a security-preserving, cross-repo migration that is testable, reversible by phase, and compatible with the active PR #197 and PR #276 workstreams.
