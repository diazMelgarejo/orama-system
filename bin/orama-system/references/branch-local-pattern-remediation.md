# Branch-Local Pattern Remediation

Use this reference whenever CodeRabbit, CI, or a reviewer reports many comments across a moving PR branch. The goal is to fix the underlying contracts once, not apply a brittle checklist of surface edits.

## When to use

Use this card for:

- CodeRabbit review sweeps with many similar findings.
- Multi-agent remediation on one PR branch.
- Review comments that point to multiple files but one shared invariant.
- Branches where `main` and the PR head are moving at the same time.
- Final pre-merge cleanup rounds where accidental `main` edits would make conflicts worse.

## Core rule

```text
Work on the requested branch only. Cluster findings by invariant. Inspect each owning file once. Fix the abstraction, add focused regression coverage, then verify the branch head.
```

Do **not** turn a review into a flat checklist. A checklist encourages unrelated one-line patches that leave the root condition alive.

## Step 0 — Branch locality gate

Before any write:

```bash
git fetch origin
git branch --show-current
git rev-parse HEAD
git status --short
gh pr view <PR> --json headRefName,headRefOid,baseRefName,mergeable
```

Decision table:

| Situation | Action |
|---|---|
| User says “fix in PR branch” | Write only to the PR head branch. |
| User says “fix main” | Write only to `main`. |
| User changes target mid-session | Stop writing to previous target; verify new head before continuing. |
| You accidentally wrote to the wrong branch | Tell the operator immediately. Do not hide it with revert spam. |
| PR branch is non-mergeable | Do not assume rebase; first determine whether base should move, branch should rebase, or main should reset. |

## Step 1 — Cluster findings by shared invariant

Examples:

| Symptom cluster | Owning invariant |
|---|---|
| Many `open()` comments | Tracked-text files use explicit UTF-8 and context managers. |
| Many redaction comments | Persisted JSON/JSONL objects are sanitized recursively at the write boundary. |
| Many stale-state comments | State reducers fold append-only logs in event order and preserve stable metadata across delta events. |
| Many lifecycle comments | Candidate/lesson states live in exactly one lifecycle location; failed cleanup rolls back staged writes. |
| Many concurrency comments | Claim rows and events commit in one transaction. |
| Many docs-link comments | Canonical indexes point to roots, companions, and archive status explicitly. |

Fix the invariant at its owning abstraction. Do not patch each call site independently unless the invariant truly has no shared boundary.

## Step 2 — Frugal inspection

Inspect files in ownership order, once per file where possible:

1. Current PR info / branch head.
2. Changed-file list or review file list.
3. Owning source files.
4. Existing tests for those owners.
5. Docs only after runtime contracts are clear.

Avoid repeated full-file reads. Fetch line ranges when a comment gives precise lines. Fetch the full file only when replacing it or verifying interdependent sections.

## Step 3 — Apply cohesive commits

Prefer commits shaped like:

```text
fix(memory): sanitize persisted candidate records at boundary
fix(coordination): commit queue claim and event atomically
docs(fleet-mesh): index active and archived planning lineage
```

Each commit should close one contract. Avoid “fix comments” commits that mix unrelated runtime, docs, and formatting changes.

## Step 4 — Regression coverage

For each invariant, add the narrowest test that would have failed before the fix:

| Invariant | Regression shape |
|---|---|
| UTF-8 | Non-ASCII candidate/lesson/manifest read-write round trip. |
| Recursive redaction | Nested JSON object containing workstation path is sanitized before persistence. |
| Short write | Simulated partial `os.write` still writes full payload. |
| Lifecycle uniqueness | Failed prior-location removal rolls back staged file. |
| Atomic claim | Claim row and event are both present or both absent after failure. |
| Equivocation | Different authenticated observers are not penalized for matching provenance alone. |
| Branch-local docs | Old paths either remain as redirects or new indexes cite source/companion/archive status. |

## Step 5 — Verification before done

Run targeted tests first, then affected suite:

```bash
python -m pytest <targeted-tests> -q
python -m pytest <affected-suite> -q
git diff --check
git status --short
gh pr view <PR> --json headRefOid,mergeable,statusCheckRollup
```

For docs-only changes:

```bash
git diff --check
grep -R "../.." docs/next docs/archive | head
```

## Anti-patterns

- Editing `main` when the user asked for a PR branch.
- Reverting commits when the clean action is to reset to the common ancestor or rebase the PR branch.
- Accepting broad wildcards such as every noreply identity to satisfy attribution checks.
- Replacing an entire file from stale memory instead of refreshing current content.
- Deleting original source doctrine because a derived package exists.
- Treating milestone reports as root plans.
- Calling review complete while CI/checks are still unknown.

## Cross-reference guidance for skills

Skills that perform review, merge, or remediation work should link here from their “References” or “When review comments arrive” section:

- `code-review`
- `git-history-surgery`
- `gstack`
- `oramasys-method`
- `agent-methodology`
- `shell-hygiene`
- any future `autoresearch` / fan-out worker skill

Preferred wording:

```markdown
For multi-comment PR remediation, follow [Branch-Local Pattern Remediation](../../references/branch-local-pattern-remediation.md): work on the requested branch only, cluster findings by invariant, and fix the owning abstraction once.
```

## One-sentence memory

Pattern-level remediation beats checklist patching: **branch-local, invariant-first, one owner file per contract, one regression per failure class.**
