# Integrative editing — good vs bad examples (CIDF curriculum)

> **Doctrine:** [`../SKILL.md` § Integrative Editing Doctrine](../SKILL.md)  
> **Merge modes:** [`../../skills/oramasys-method/references/integrative-merge.md`](../../skills/oramasys-method/references/integrative-merge.md)  
> **Bad lines below** are quarantined teaching samples — do not copy into production `SKILL.md` files.

---

## 1. PR descriptions (append-only)

| Bad | Good |
| --- | --- |
| Replace entire PR body with latest CI delta only | Keep original Summary; add `## Follow-up:` sections below |
| Retitle PR to match aguara side quest | Leave title; label aguara work as ancillary in a follow-up block |
| `gh pr edit` with only the new paragraph | Pass full body: reconstructed original + all follow-ups |
| `ManagePullRequest` / `gh pr edit` without reading first | **READ → backup → write:** `gh pr view --json body -q .body > /tmp/pr-N-body-backup.md` then edit backup file, then `gh pr edit N --body-file` |

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
