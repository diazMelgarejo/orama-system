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
| **Approved primary authors** | Any configured `user.name` with `diazMelgarejo@gmail.com` or `Lawrence@cyre.me`; `Codex <codex@openai.com>` is also allowed |
| **Co-authored-by — allowed** | Well-known public AI/vendor domains (`openai.com`, `anthropic.com`, `cursor.com`, `cursor.sh`, `google.com`, `github.com`, `microsoft.com`, `azure.com`, subdomains) and matching name markers (`codex`, `claude`, `anthropic`, `cursor`, …) |
| **Co-authored-by — additionally allowed AI/vendor signals** | `google.dev`, `perplexity.ai`, `x.ai`; matching name markers `gemini`, `google`, `copilot`, `perplexity`, `grok` |
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
| **Primary author** | Any name with `diazMelgarejo@gmail.com` or `Lawrence@cyre.me`, or `Codex` + `codex@openai.com` (`scripts/git/check_identity.sh`) |
| **Allowed co-author domains** | `openai.com`, `anthropic.com`, `cursor.com`, `cursor.sh`, `google.com`, `github.com`, `microsoft.com`, `azure.com` (and subdomains) |
| **Additional allowed AI/vendor domains** | `google.dev`, `perplexity.ai`, `x.ai`, `coderabbit.ai`, `mistral.ai`, `deepseek.com`, `cohere.com`, `meta.com`, `sourcegraph.com`, `devin.ai`, `codeium.com` (and subdomains) |
| **Allowed co-author name markers** | `codex`, `claude`, `anthropic`, `cursor`, `cursoragent`, `gemini`, `google`, `copilot`, `openai`, `github`, `microsoft`, `perplexity`, `grok`, `coderabbit`, `coderabbitai`, `mistral`, `deepseek`, `cohere`, `llama`, `devin`, `cody`, `codeium`, `windsurf`, `qwen` (in the trailer line) |
| **Allowed `@gmail.com` co-authors** | `diazMelgarejo@gmail.com`, `Lawrence@cyre.me` only |
| **Rejected** | Any other `Co-authored-by` line with `@gmail.com` (unattributable personal inboxes) |

Corporate and vendor agent domains are identifiable; random Gmail co-authors are not attributable and were used for mistaken or non-policy attribution.

**Policy (2026-06-03): mainstream AI models and autonomous coding agents are allowed**
as authors, committers, and `Co-authored-by` — including `Cursor Agent <cursoragent@cursor.com>`
and `CodeRabbit <noreply@coderabbit.ai>`. The agent *identity* is never the thing we ban.
The single hard ban is the VERBOTEN auto-injected pattern (held in the gitignored private
pattern lib, stripped by `commit-msg.strip-coauthor` and caught by `audit_attribution.sh`
`banned_attribution_hit`). Cursor-environment detection (`is_cursor_environment` /
`is_cursor_agent`) is only a *proxy* for when to run the guard, since the Cursor environment
is where the VERBOTEN gets injected. Extend the allowlists above as new mainstream agents
appear; keep `check_commit_message.sh`, `check_identity.sh`, and `repo_hygiene.py` in sync.


### Allowed bot committers (history scans only)

Automated commits from GitHub bots are **not** policy violations in `scripts/git/audit_attribution.sh` history scans (`bad_author` is not incremented for these emails):

| Repo | Bot author email |
| --- | --- |
| **orama-system** | `cursor[bot]@users.noreply.github.com` |
| **Perpetua-Tools** | `dependabot[bot]@users.noreply.github.com` |

The audit script accepts the union of both bot addresses on any repo it runs against. `scripts/git/check_identity.sh` still applies only to **your next commit** (human/cyre/Codex identity) — it does not rewrite historical bot authors.

### Banned identities (private list — never in tracked docs)

Forbidden author, committer, and `Co-authored-by` tokens live only in **gitignored**
`.cursor/private/banned-attribution-patterns` (synced from `~/.cursor/openclaw/`).
They must **not** appear in code, commit messages, author fields, PR text, or wiki on GitHub.

If a branch fails scan, rewrite history before push:

```bash
bash /path/to/Perpetua-Tools/scripts/git/expunge-all-workspace-repos.sh
bash scripts/git/scan-tracked-banned-tokens.sh
GIT_AUDIT_RANGE=origin/main..HEAD GIT_AUDIT_STRICT=1 bash scripts/git/audit_attribution.sh
```

Re-introducing a banned identity after an expunge forces another full `main` + all-branch rewrite.

### Explicit co-author allowlist and domain-gate caveat

`Co-authored-by: Cursor <cursoragent@cursor.com>` is **always allowed** — listed explicitly in `scripts/git/check_commit_message.sh` (`ALLOWED_EXACT_COAUTHOR_EMAILS`), not only via the `cursor.com` domain suffix.

**`ALLOWED_GMAIL_COAUTHORS` only fires for `@gmail.com` / `@googlemail.com` addresses.** Any personal or org domain address (e.g. `user@cyre.me`, `user@bettermind.ph`) placed in `ALLOWED_GMAIL_COAUTHORS` will be silently denied — the `gmail_allowed()` gate is guarded by a `*@gmail.com` domain check and never runs for other domains. Fix: put all non-Gmail personal or org-domain addresses in `ALLOWED_EXACT_COAUTHOR_EMAILS` instead. (Learned 2026-06-22: `lawrence@cyre.me` was in `ALLOWED_GMAIL_COAUTHORS`; commits were rejected until it was moved to `ALLOWED_EXACT_COAUTHOR_EMAILS`.)

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

## Portable paths in tracked files (no workstation leaks)

`scripts/review/repo_hygiene.py` runs in CI (`tests/test_repo_hygiene.py::test_repo_hygiene_script_runs_clean`) and **fails the build** on any tracked file containing a hardcoded workstation path. This applies to docs, comments, and example commands — not just code. Two patterns are blocked:

- **Personal absolute paths** — `/Users/<name>/…` or `/home/<name>/…` where `<name>` is a real login. Use `~`, `$REPO_ROOT`, or a relative path.
- **Machine-specific OpenClaw layout** — the literal `…/claude/OpenClaw` workstation tree (with or without a `~`/`$HOME` prefix). Use `$OPENCLAW_ROOT`, `detect_openclaw_root()`, or `ORAMA_INSTALL_DIR`.

**`<name>` placeholder is NOT enough.** Swapping the login for `<name>` still exposes the parent directory tree (e.g. `/Users/<name>/Downloads/SKILLS.md/ultrathink/…`), which is also identifying. Same problem on Windows: `%USERPROFILE%\specific-subdir\subtree\`. Use the form that fits the context:

| Situation | Correct form |
|-----------|-------------|
| Path to a file inside this repo | Relative from the referencing file — `../filename` or `../../dir/file` |
| Path to repo root or sibling repos | `$OPENCLAW_ROOT`, `$REPO_ROOT`, `~` |
| Local-only reference with no repo anchor | Filename only — strip the entire parent path tree |
| Runnable shell example | Variable substitution (`"$OPENCLAW_ROOT/orama-system"`) |

Rule of thumb when writing a runnable example or recovery command in any `*.md`, script, or comment — substitute the root with a variable:

```bash
# WRONG — a literal /Users/<login>/…/claude/OpenClaw/orama-system leaks the
#         developer name + directory layout and fails CI.
# ALSO WRONG — <name> still exposes the Downloads/SKILLS.md/ultrathink subtree
# RIGHT — portable, passes hygiene:
git clone <url> "$OPENCLAW_ROOT/orama-system"
../Cross-Repo-Memory-Seed.md          # relative from the referencing file
```

Abbreviated placeholders like `/Users/.../foo` are fine (the segment after `/Users/` must start with a letter to match). The script and its own test are the only allowlisted files (they must name the pattern to test it). **Run `python3 scripts/review/repo_hygiene.py .` before committing docs that contain shell commands** — it is the same check CI runs. (Learned 2026-06-02: the #1802 incident write-ups themselves leaked workstation paths and red-CI'd `main`. Reinforced 2026-06-22 PR #123: even placeholder forms and Windows env vars expose subdirectory trees.)

**Prevention (catch it before history, not after).** The pre-commit hook (`.githooks/pre-commit`, activated by `bash scripts/git/install-local-hooks.sh`) runs the full `repo_hygiene.py` — the *same* check as CI — so a leaked path or token is blocked at commit time and never enters history. That makes the [`git-history-surgery`](../../bin/orama-system/skills/git-history-surgery/SKILL.md) scrub a last resort (only if something already landed before the hook was installed), not the routine. Install the hooks once per clone; CI is the backstop, the hook is the gate.

---

## GitHub Actions Permissions

Workflow permissions must be minimal and explicit.

- Release jobs need `contents: write`.
- PR automation needs `pull-requests: write`.
- Read-only CI should use default read behavior or an explicit read-only block.
- Avoid broad top-level write permissions.

---

## Windows batch file line endings (CRLF)

Windows `.cmd` and `.bat` files **MUST** use CRLF (`\r\n`) line endings.
A file with LF-only (`\n`) endings will silently fail or produce garbled output
because `cmd.exe` tokenises on `\r\n`.

**Git attributes — declare CRLF explicitly** in `.gitattributes`:

```gitattributes
*.cmd  text  eol=crlf
*.bat  text  eol=crlf
```

Without this, `core.autocrlf` may strip `\r` silently on checkout, breaking
files that work on the author's machine.

**Writing `.cmd` files from Python** — always open in binary mode and join with `\r\n`:

```python
lines = ["@echo off", "rem my script", "exit /b 0"]
with open("my.cmd", "wb") as f:
    f.write("\r\n".join(lines).encode("utf-8"))
```

**Verification:**

```bash
xxd my.cmd | grep -c "0d 0a"   # should equal line count
xxd my.cmd | grep -c "0d$"     # 0 = no stray bare CR
```

*Root cause discovered in PR #108 (`gstack-brain-sync.cmd` was LF-only, silently
broke cmd.exe shell dispatch on Windows).*

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
