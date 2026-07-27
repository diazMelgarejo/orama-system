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
| `curl -o /tmp/cursor-install.sh && bash /tmp/cursor-install.sh` | `mktemp -t cursor-install.XXXXXX` + `chmod 700` + `trap` cleanup + review before `bash` |

Shared `/tmp` names are symlink-replaceable between download and execute.

---

## 4. Hermes spawn `status` (bounded health)

| Bad | Good |
| --- | --- |
| `AIAgent.chat('Reply with: HERMES_OK')` in status | `kill -0` on recorded PID + command-line match on `hermes_harness.py` |
| Full model request for liveness | Optional **inference smoke test** only when labeled, with explicit timeout |

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
