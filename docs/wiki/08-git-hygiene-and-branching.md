# 08. Git Hygiene and Branching — Orama Recovery Guardrails

**TL;DR:** Prevent future identity drift, broken config commits, and orphan branches by following dated branch names, stash-first discipline, explicit credential confirmation, and minimal workflow permissions.

---

## Branch Naming

All feature, fix, and recovery branches must use the dated monotonic format:

```text
yyyy-mm-dd-NNN-brief-summary
```

Examples:
- `2026-04-24-001-orama-salvage`
- `2026-04-25-001-fix-gateway-discovery`

Rules:
- Use the date the branch was created, not the anticipated merge date.
- Start at `001` and increment for same-day branches.
- Keep the summary lowercase and hyphenated.
- Never create a branch from a detached HEAD or another agent-created branch.

---

## Official commit identity policy (2026-05-25)

Canonical policy for **primary commit authors** and **`Co-authored-by`** trailers in this repo (and the OpenClaw stack). Enforcement is local via repo hooks — not honor system.

| Role | Rule |
| --- | --- |
| **Approved primary authors** | `cyre <diazMelgarejo@gmail.com>` · `cyre <Lawrence@cyre.me>` · name containing `Lawrence` + `Lawrence@cyre.me` · `Codex <codex@openai.com>` |
| **Co-authored-by — allowed** | Well-known public AI/vendor domains (`openai.com`, `anthropic.com`, `cursor.com`, `cursor.sh`, `google.com`, `github.com`, `microsoft.com`, `azure.com`, subdomains) and matching name markers (`codex`, `claude`, `anthropic`, `cursor`, …) |
| **Co-authored-by — allowed Gmail** | `diazMelgarejo@gmail.com`, `Lawrence@cyre.me` only |
| **Co-authored-by — rejected** | Any other `@gmail.com` / `@googlemail.com` (unattributable personal inboxes) |
| **Agent sessions (default)** | Do not add `Co-authored-by` to commits you author; use an approved primary identity only |

**Install once per clone:**

```bash
bash scripts/git/install-local-hooks.sh
```

**Enforcement scripts:**

| Script | Hook / use |
| --- | --- |
| [`scripts/git/check_identity.sh`](../../scripts/git/check_identity.sh) | `pre-commit` — primary `user.name` / `user.email` |
| [`scripts/git/check_commit_message.sh`](../../scripts/git/check_commit_message.sh) | `commit-msg` — `Co-authored-by` allowlist |
| [`scripts/git/install-local-hooks.sh`](../../scripts/git/install-local-hooks.sh) | Sets `core.hooksPath` → `.githooks/` |

Manual preflight:

```bash
bash scripts/git/check_identity.sh
bash scripts/git/check_commit_message.sh /path/to/COMMIT_EDITMSG
```

Cross-repo Cursor cloud guards: [`12-cursor-cloud-commit-attribution.md`](12-cursor-cloud-commit-attribution.md).

---

## Identity Confirmation

Approved **primary commit author** identities (any one):

| Email | Typical `user.name` |
| --- | --- |
| diazMelgarejo@gmail.com | `cyre` |
| Lawrence@cyre.me | `cyre` or a name containing `Lawrence` |
| codex@openai.com | `Codex` |

After each fresh clone, run once:

```bash
bash scripts/git/install-local-hooks.sh
```

Local hooks enforce identity on `pre-commit` and validate **`Co-authored-by`** trailers on `commit-msg`: well-known public AI/vendor co-authors are allowed; unknown `@gmail.com` co-authors are rejected (see table below). Using **Codex** as the primary author is allowed. Verify config before committing:

```bash
bash scripts/git/check_identity.sh
```

If this fails, do not commit. Correct your Git identity first:

```bash
git config user.name "cyre"
git config user.email "Lawrence@cyre.me"  # or diazMelgarejo@gmail.com
# or for Codex-authored commits:
git config user.name "Codex"
git config user.email "codex@openai.com"
```



### Co-authored-by policy (commit-msg hook)

| Category | Rule |
| --- | --- |
| **Primary author** | `cyre` + `diazMelgarejo@gmail.com`, `cyre` + `Lawrence@cyre.me`, name containing `Lawrence` + `Lawrence@cyre.me`, or `Codex` + `codex@openai.com` (`scripts/git/check_identity.sh`) |
| **Allowed co-author domains** | `openai.com`, `anthropic.com`, `cursor.com`, `cursor.sh`, `google.com`, `github.com`, `microsoft.com`, `azure.com` (and subdomains) |
| **Allowed co-author name markers** | `codex`, `claude`, `anthropic`, `cursor`, `cursoragent`, `gemini`, `copilot`, `openai`, `github`, `microsoft` (in the trailer line) |
| **Allowed `@gmail.com` co-authors** | `diazMelgarejo@gmail.com`, `Lawrence@cyre.me` only |
| **Rejected** | Any other `Co-authored-by` line with `@gmail.com` (unattributable personal inboxes) |

Corporate and vendor agent domains are identifiable; random Gmail co-authors are not attributable and were used for mistaken or non-policy attribution.


### Allowed bot committers (history scans only)

Automated commits from GitHub bots are **not** policy violations in `scripts/git/audit_attribution.sh` history scans (`bad_author` is not incremented for these emails):

| Repo | Bot author email |
| --- | --- |
| **orama-system** | `cursor[bot]@users.noreply.github.com` |
| **Perpetua-Tools** | `dependabot[bot]@users.noreply.github.com` |

The audit script accepts the union of both bot addresses on any repo it runs against. `scripts/git/check_identity.sh` still applies only to **your next commit** (human/cyre/Codex identity) — it does not rewrite historical bot authors.

### VERBOTEN identities (history and new commits)

These must **not** appear as commit author, committer, or in any `Co-authored-by` trailer (any case variant). If they exist on a branch you intend to push, **rewrite history first**, then `git push --force-with-lease` only after a clean scan.

| Identity | Rule |
| --- | --- |
| `REDACTED@gmail.com` | Banned — expunge from all refs before force-push |
| `REDACTED` | Banned — any email containing `REDACTED`, or author/committer name `REDACTED` |

Scan (all refs):

```bash
git log --all --format='%H %ae %ce %an %cn' | rg -i 'darth\.serious|REDACTED'
git log --all --format='%B' | rg -i '^co-authored-by:.*(darth\.serious|REDACTED)'
```

### Explicit Cursor co-author allowlist

`Co-authored-by: Cursor <cursoragent@cursor.com>` is **always allowed** — listed explicitly in `scripts/git/check_commit_message.sh` (`ALLOWED_EXACT_COAUTHOR_EMAILS`), not only via the `cursor.com` domain suffix.

### Why only known @gmail.com in co-author lines?

Public AI helpers use stable, identifiable domains (`@openai.com`, `@anthropic.com`, `cursor.com`, and similar), so `Co-authored-by` trailers are auditable and match how those tools sign commits. A random `@gmail.com` in `Co-authored-by:` is usually a person or an unreviewed address — easy to add by mistake and hard to tie to our approved author policy. Letting every Gmail address through would weaken the hook; allowing only known Gmail addresses plus well-known agent domains keeps attribution clear without blocking Codex-, Cursor-, and Claude-style co-authors we want.

Manual check:

```bash
bash scripts/git/check_commit_message.sh /path/to/COMMIT_EDITMSG
```

### Local commit hooks (once per clone)

Install repo-local hooks (identity pre-commit + forbidden `Co-authored-by` commit-msg gate):

```bash
bash scripts/git/install-local-hooks.sh
```

This sets `git config --local core.hooksPath .githooks` only in this repository.

---

## Stash-First Discipline

Before any risky Git operation (rebase, history inspection, branch surgery, cross-repo sync), capture state including untracked files:

```bash
git status --short --branch
git stash push --include-untracked -m "preserve work before <operation>"
git rev-parse --is-shallow-repository
git config user.name
git config user.email
```

Never run destructive cleanup until the stash has been verified.

---

## Commit Message Quality

Use detailed conventional commits. Every non-trivial commit must include:

```text
type(scope): short summary

Why:
- what was broken or risky

What changed:
- concrete files/components touched

Risk:
- known compatibility or migration concern

Verification:
- exact commands run
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `recovery`

---

## Private and Generated Config

- `.env` is private and ignored.
- `.env.local` is private and ignored.
- `.env.example` is the only tracked environment template.
- `.paths` is generated runtime-local state and ignored.
- `.paths.example` is the only tracked path template.
- Do not commit shell-substitution-only values as the sole configuration representation.

---

## GitHub Actions Permissions

Workflow permissions must be minimal and explicit.

- Release jobs need `contents: write`.
- PR automation needs `pull-requests: write`.
- Read-only CI should use default read behavior or an explicit read-only block.
- Avoid broad top-level write permissions.

---

## Cursor Cloud commit attribution

Cloud agents may inject `Co-authored-by` trailers via managed git hooks. **`CURSOR_AGENT=0` is not supported.**

Run on VM boot (all three repos):

```bash
bash scripts/git/apply-attribution-guard-all-repos.sh
```

See [12. Cursor Cloud — commit attribution guards](12-cursor-cloud-commit-attribution.md).

---

## Related

- [Git Safety Guardrails](../recovery/2026-04-24-003-git-safety-guardrails.md)
- [Multi-Agent Collaboration](06-multi-agent-collab.md)
- [Commit Salvage Matrix](../recovery/2026-04-24-002-commit-salvage-matrix.md)
