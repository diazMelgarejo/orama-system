---
name: gstack-toolchain
version: 1.0.0
description: >-
  Manage gstack and gbrain upgrades, fork-patch lifecycle, and co-author
  attribution allowlist. Use when upgrading gstack, reapplying fork patches,
  or adding a new canonical AI contributor to check_commit_message.sh.
user-invocable: true
triggers:
  - gstack upgrade
  - gbrain upgrade
  - fork patch
  - co-author allowlist
  - attribution policy
  - hermes contributor
---

# gstack-toolchain

Canonical procedures for keeping gstack, gbrain, and the orama-system
attribution guard in sync. All three touch overlapping ground — upgrade the
tool, keep the fork patches alive, keep the allowlist current.

---

## 1 — gstack upgrade (fork-patch strategy)

`~/.claude/skills/gstack` is a **forked checkout** of `garrytan/gstack`. The
fork carries local patches (currently `fix/1802-staging-ownership-guard`) that
upstream may not have merged yet. Fast-forward upgrades (`pull --ff-only`)
break because the local branch has diverged.

### Upgrade sequence

```bash
# 1. Stash any working-tree dirt (setup artifacts, etc.)
cd ~/.claude/skills/gstack
git stash

# 2. Fetch upstream and merge (NOT rebase — keeps patch history readable)
git fetch origin
git merge origin/main --no-edit
#    Expect conflicts only in files the patch touches (lib/staging-guard.ts,
#    bin/gstack-memory-ingest.ts, related tests). Resolve by taking --theirs
#    when upstream's version is a strict superset of the local patch.

# 3. Resolve conflicts — take upstream when it's additive
git checkout --theirs <conflicted-file> ...
git add <conflicted-file> ...
git commit --no-edit

# 4. Run setup to regenerate skill files
./setup

# 5. Re-apply fork patches (idempotent — no-ops if upstream already merged)
bash "$OPENCLAW_ROOT/orama-system/scripts/fork-patches/apply-fork-patches.sh"

# 6. Verify
cat VERSION   # should match upstream tag
```

### Conflict resolution rule

The `fix/1802-staging-ownership-guard` patch adds a fail-closed ownership
check before any recursive delete. When the same files conflict, check whether
upstream is:

- **A strict superset** (upstream adds `canonicalPath`, C5 error hardening,
  new regression tests on top of the guard) → take `--theirs`.
- **Divergent** (upstream removes or weakens the guard) → keep `--ours`,
  open an upstream PR.

If `apply-fork-patches.sh` prints `✓ already present (patched or upstream-merged)`,
the patch has been absorbed by upstream — retire the local patch from
`scripts/fork-patches/patches/` and remove the `fix/1802-*` branch entry
from `~/.zshrc`.

### zshrc guard (auto-heal on every shell)

```zsh
_ORAMA_FORK_HEAL="$OPENCLAW_ROOT/orama-system/scripts/fork-patches/apply-fork-patches.sh"
if [ -f "$_ORAMA_FORK_HEAL" ]; then
  fork-heal() { bash "$_ORAMA_FORK_HEAL" "$@"; }
fi
```

Run `fork-heal` manually after any upgrade to force-reapply. This is the same
idempotent script; it is safe to run repeatedly.

---

## 2 — gbrain upgrade

gbrain lives at `~/.gbrain/` (config) with the CLI installed via the gbrain
npm package. It does NOT carry a fork — upgrade is a straight package update.

```bash
# Check current version
gbrain --version

# Upgrade (prefer bun in this environment)
bun add -g gbrain@latest

# Verify config survived
gbrain doctor --fast
```

After a gbrain upgrade, verify `~/.gbrain/config.json` still points to
`ollama:bge-m3` for embeddings and the Supabase pgvector endpoint is intact.
If `gbrain doctor` reports a broken source, run `/sync-gbrain --full` to
reindex.

Known issue: gbrain#1802 checkpoint bug (import-checkpoint.json poisoned on
SIGTERM) was fixed in gstack#1827 + gbrain#1728. Confirm `gbrain doctor --fast`
shows no staging warnings after upgrade.

---

## 3 — Co-author attribution allowlist

The canonical allowlist lives in:

```
scripts/git/check_commit_message.sh
```

(relative to `orama-system` repo root — never edit the copy in PT or
AlphaClaw directly)

Two arrays control what passes:

| Array | Purpose |
|-------|---------|
| `WELL_KNOWN_COAUTHOR_DOMAIN_SUFFIXES` | Email domain → always allowed |
| `WELL_KNOWN_COAUTHOR_NAME_MARKERS` | Substring in name or email → always allowed |

### Adding a new AI contributor

1. Edit `scripts/git/check_commit_message.sh` (single source of truth).
2. Add the domain to `WELL_KNOWN_COAUTHOR_DOMAIN_SUFFIXES` AND the agent name
   to `WELL_KNOWN_COAUTHOR_NAME_MARKERS` (belt + suspenders).
3. Verify:
   ```bash
   tmp=$(mktemp)
   printf 'test\n\nCo-authored-by: Agent Name <agent@vendor.example>\n' > "$tmp"
   bash scripts/git/check_commit_message.sh "$tmp" && echo PASS
   rm "$tmp"
   ```
4. Sync to downstream repos:
   ```bash
   bash scripts/git/sync-attribution-guard-scripts.sh "$PT_PATH"
   ```
5. Commit:
   `chore(attribution): add <AgentName> (vendor.example) to co-author allowlist`

### Current approved AI contributors

| Agent | Email | Added |
|-------|-------|-------|
| Claude (Anthropic) | `noreply@anthropic.com` | founding |
| Codex (OpenAI) | `codex@openai.com` | founding |
| CursorAgent | `cursoragent@cursor.com` | 2026-05-xx |
| Gemini / Google agents | `*@google.com`, `*@google.dev` | founding |
| GitHub Copilot | `*@github.com` | founding |
| Hermes Agent (NousResearch) | `hermes@nousresearch.com` | 2026-06-21 |

Hermes is the orama-system **cross-harness operator shell** for Windows PT
workflows. Its commits are produced by the hermes-harness skill and are
indistinguishable from authorized agent work — treating them as `bad_coauthor`
is a false positive, not a security signal.

---

## 4 — Invariants

- **Never hand-edit the downstream copy** of `check_commit_message.sh` in PT
  or AlphaClaw — always edit orama-system's then sync. Drift causes silent
  `bad_coauthor` blocks on valid pushes.
- **Never fast-forward the gstack fork** past a patch that hasn't been
  confirmed absorbed. Use `merge`, not `rebase`, to preserve the patch commit
  as a legible landmark in history.
- **`apply-fork-patches.sh` is idempotent** — run it after every gstack
  upgrade without checking first. Cost: one grep per patch, ~10 ms.
- **gbrain checkpoint bug guard**: after any gbrain upgrade, run
  `gbrain doctor --fast`. If the checkpoint is corrupt, delete
  `~/.gbrain/import-checkpoint.json` and resync.
