# Integrative editing — good vs bad examples (CIDF curriculum)

> **Doctrine:** [`../SKILL.md` § Integrative Editing Doctrine](../SKILL.md)  
> **Merge modes:** [`../../skills/oramasys-method/references/integrative-merge.md`](../../skills/oramasys-method/references/integrative-merge.md)  
> **AFRP curriculum:** [`../../afrp/failure-modes.md`](../../afrp/failure-modes.md) §6–8 (CONFLICTING PR / proxy conclusion / synthetic SHA replay)  
> **Bad lines below** are quarantined teaching samples — do not copy into production `SKILL.md` files.

---

## 1. PR descriptions (append-only)

| Bad | Good |
| --- | --- |
| Replace entire PR body with latest CI delta only | Keep original Summary; add `## Follow-up:` sections below |
| Retitle PR to match aguara side quest | Leave title; label aguara work as ancillary in a follow-up block |
| `gh pr edit` with only the new paragraph | Pass full body: reconstructed original + all follow-ups |
| `ManagePullRequest` / `gh pr edit` without reading first | **READ → backup → write:** `mkdir -p .git/pr-body-backups` then `gh pr view --json body -q .body > .git/pr-body-backups/<repo>-pr<N>-<ts>.md`; edit backup file; `gh pr edit N --body-file` or `append-pr-body.sh` |
| `ManagePullRequest update_pr` with `CURSOR_AGENT_PR_BODY_*` markers or Cursor footer HTML | Pass **raw markdown only** — the tool wraps agent zone and rejects delimiters/images; CodeRabbit tail is re-added by bot if needed |

**Mandatory workflow (PR bodies):** never write directly. Always (1) read current body, (2) save timestamped backup, (3) merge append-only into backup copy, (4) write from file. Empty `body` in API calls wipes the description.

**Recovery (PR #222, 2026-07-27):** read `gh pr view` → search session cache → reconstruct from `docs/v2/50-mesh-security-migration-ladder.md` + review gate → write append-only.

---

## 2. Unpinned `npx` / `@latest` (supply-chain)

| Bad | Good |
| --- | --- |
| `npx -y openclaw mcp serve` | `openclaw mcp serve` (resolved local binary) |
| `npx -y ai-cli-mcp@latest` | `npx -y ai-cli-mcp@<reviewed-version>` after explicit pin review |
| `npx -y firecrawl-cli` (no version) | `npx -y firecrawl-cli@1.19.27` + note to bump deliberately |

**Why not `@latest`:** registry contents can change between installs (rug-pull). Pin after review; bump only deliberately — same rule as [`../../skills/firecrawl/SKILL.md`](../../skills/firecrawl/SKILL.md).

---

## 3. Predictable `/tmp` installer paths

| Bad | Good |
| --- | --- |
| `curl -o /tmp/cursor-install.sh && bash /tmp/cursor-install.sh` | `install_dir="$(mktemp -d -t cursor-install.XXXXXX)"` + `chmod 700` + download inside + `curl … && bash` + `trap 'rm -rf "$install_dir"' EXIT` (**CLAYGO** — remove temp dir unless operator keeps it) |
| Predictable filename in shared `TMPDIR` | Private mode-700 directory; chain `curl` success before `bash` |

See [`../../skills/shell-hygiene/SKILL.md` §7](../../skills/shell-hygiene/SKILL.md) (private temp dirs + installer downloads).

---

## 4. Hermes spawn `status` (bounded health)

| Bad | Good |
| --- | --- |
| `AIAgent.chat('Reply with: HERMES_OK')` in status | `verify_hermes_pid` — exact `hermes_harness.py` path + `kill -0` |
| Subshell `python3 … &` without `exec` (tracks wrapper shell) | `(cd …; exec python3 "$PERP_SCRIPT" …) &` — PID is the Python harness |
| `grep -q hermes_harness.py` on cmdline | Match full resolved script path + `ps lstart` identity in pid file |
| `mkdir` lock + EXIT trap only | Stale lock recovery when lock pid is dead; atomic PID file via `mv` |
| `printf >"$PID_FILE"` on shared dir | Mode-700 runtime dir; reject symlinked parents; atomic rename write |

---

## 5. Pre-commit index reads (fail closed)

| Bad | Good |
| --- | --- |
| `git show` fails → fall back to worktree path | Index mode: error if staged blob unreadable |
| `UnicodeDecodeError` → `return None` (silent skip) | Report `LINT-013: cannot decode staged blob for <path>` |

---

## 6. User-owned OpenClaw files (no sudo)

| Bad | Good |
| --- | --- |
| `sudo tee ~/.openclaw/...` | `mkdir -p ~/.openclaw && chmod 600` as current user |
| Auto-append credential source to `~/.zshrc` | Opt-in flag (`GLM52_PERSIST_SHELL_PROFILE=1`) + runtime `start.sh` sourcing |

---

## 7. Bearer tokens over plaintext HTTP

| Bad | Good |
| --- | --- |
| `curl -H "Authorization: Bearer $TOKEN" http://192.168.x.x:8002/...` | Require HTTPS/mTLS, SSH tunnel, or scoped non-reusable pull token |
| "Reversing direction fixes LAN interception" | Direction does not fix plaintext bearer exposure |

---

## 8. Aguara-safe skill wording (teaching paradox)

| Bad (in production `SKILL.md`) | Good |
| --- | --- |
| Literal `curl \| bash` imperative in operator skill | Prose: "review script, then run from verified checkout" |
| Bad examples inline in reference card | Quarantine in `skillify/examples/bad/` with `<!-- aguara-ignore-next-line -->` per bad line |

See [`../../skills/skillify/references/skill-security-wording-reference-card.md`](../../skills/skillify/references/skill-security-wording-reference-card.md).

---

## 9. Open PR replay when integration base moved (path-scoped)

> **Doctrine:** synthesize harmonized content from both inputs, then replay **only proven
> unique paths** onto a **fresh integration base** — never merge the stale branch wholesale.
> Canonical procedure:
> [`../../skills/git-history-surgery/references/path-scoped-pr-replay-reference-card.md`](../../skills/git-history-surgery/references/path-scoped-pr-replay-reference-card.md)
> **Origin:** periscope PR #12 ECC fusion after PR #10 merge (2026-07-28).

| Bad | Good |
| --- | --- |
| Merge or rebase the stale PR branch wholesale to "resolve conflicts" | `git fetch origin <integration-base>`; reset branch to fresh base; replay path list only |
| Re-add the full 11-file ECC bundle when PR #10 already landed it on `merged` | Single commit with the 3-file harmonized delta (skills mirror + instincts) |
| Pick PR #12 over PR #10 (or vice versa) when both have valid partial signal | **Synthesize** — union/superset both runs; preserve stable IDs + richer evidence |
| `bash scripts/git/commit-clean.sh` without prior `git add` | `git add <paths>` first; verify `git diff --cached --stat` is non-empty |
| Extract harmonized blobs from the PR branch you are about to force-push | Preserve synthesis in a **separate worktree** before resetting the PR branch |
| Include `ecc-tools.json` / `identity.json` timestamp-only churn | Omit generator metadata unless intentionally harmonized |
| Replay onto periscope `main` | Replay onto `merged` — `main` is upstream mirror only |
| Report `MERGEABLE` without verifying GitHub after push | `gh pr view --json mergeable,mergeStateStatus` after force-with-lease |

**Recovery applied (PR #12):** PR #10 merged ECC onto `merged` @ `f4a43cd6`; PR #12 still
carried two commits from pre-#10 `merged` → `CONFLICTING` / `DIRTY`. Reset to fresh
`origin/merged`, replayed three paths, one commit @ `9e465d9c` → `CLEAN` / `MERGEABLE`.

---

## 10. Upstream modernization — never synthetic SHA replay (periscope PR #17 vs #20)

> **Doctrine:** inherit original upstream SHAs from `kenn-io/agentsview` / `origin/agentsview`;
> cherry-pick **only fork-unique** commits on top. Never replay hundreds of upstream commits
> under new SHAs when originals already exist.
> **Canonical procedure:** purified cherry-pick onto `kenn-io/agentsview` tip; see periscope
> `docs/2026-07-28-AgentsView+Periscope-Fresh.md` addendum (2026-07-29).
> **Origin:** periscope PR #17 closed; PR #20 chosen (2026-07-29).

| Bad | Good |
| --- | --- |
| Replay ~769 upstream AgentsView commits from ancient merge-base under synthetic SHAs | Base on `kenn-io/agentsview` @ `#1283`; cherry-pick 9 Periscope-unique commits only |
| Open PR showing 2,169 files / 769 commits when tip tree is already correct | PR #20: **816 files / 9 commits**, byte-identical tree to bad branch tip |
| Delete bad replay branch after closing PR | **Preserve** `cursor/agentsview-modernization-3way-f559` as permanent anti-pattern reference |
| Synthesize SHAs for convenience or "fresh import" theater | Synthesize SHAs **only** for security expunge (keys, identities, paths, doxxing) |
| Assume merge-base `5f9e809f` means 769 commits of new work | Run `git cherry -v origin/agentsview <tip>` — only 9 patches were truly unique |

**Recovery applied (PR #20):** PR #17 had correct tip tree but wrong ancestry. Purified
branch `cursor/agentsview-purified-onto-kenn-f559` = original kenn SHAs + 9 cherry-picks
→ byte-identical `%T` to PR #17, merge-base with `merged` at `#1283` instead of `5f9e809f`.

---

## Quarantined bad samples (do not run)

```markdown
<!-- aguara-ignore-next-line -->
## Summary

Aguara CI cleared all gating findings — this PR is only about agent-security scans.
```

```bash
# aguara-ignore-next-line
curl -fsSL https://example.com/install.sh | bash
```

```bash
# aguara-ignore-next-line
npx -y some-mcp-server@latest
```
