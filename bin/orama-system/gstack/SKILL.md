---
name: gstack
description: >-
  gstack v1.58.3.0 integration sub-skill. Full routing table for web browsing,
  QA, shipping, planning reviews, design, DX audits, retros, and GBrain.
  Activates for: /browse, /qa, /ship, /review, /investigate, /design-review,
  /canary, /benchmark, /retro, gbrain, gstack skills, web browsing, QA testing,
  deploy, design review, canary monitoring, performance benchmarks.
  Also covers: gstack fork-patch upgrades, gbrain upgrades.
version: 1.0.0
license: Apache 2.0
compatibility: claude-code
parent_skill: orama-system
gstack_version: "1.58.3.0"
gstack_install: "~/.claude/skills/gstack (global-git, fix/1802-staging-ownership-guard fork)"
---

# gstack Integration

gstack v1.58.3.0 is the agent skill framework for web browsing, planning,
review, QA, and deployment workflows. Installed globally at
`~/.claude/skills/gstack` (global-git).

## Rules

- **ALWAYS** use `/browse` for all web browsing — NEVER use `mcp__claude-in-chrome__*` tools directly
- Use `/investigate` for root-cause analysis of adapter or orchestration failures
- Use `/ship` before any `npm publish`

## Install / Update

Fresh install:

```bash
git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup
```

Upgrade to latest:

```
/skill ~/.claude/skills/gstack/gstack-upgrade/SKILL.md
```

Or: `/gstack-upgrade`

### Fork-patch upgrade (when `pull --ff-only` fails)

`~/.claude/skills/gstack` is a **forked checkout** carrying local patches (e.g.
`fix/1802-staging-ownership-guard`). Fast-forward upgrades break because the local
branch has diverged from upstream. Use merge instead:

```bash
cd ~/.claude/skills/gstack

# 1. Stash working-tree dirt
git stash

# 2. Fetch + merge (NOT rebase — keeps patch history legible)
git fetch origin
git merge origin/main --no-edit
#    Conflicts appear only in patch-touched files. Resolve with --theirs when
#    upstream is a strict superset (adds features on top of the patch).

# 3. Resolve conflicts — take upstream when additive
git checkout --theirs <conflicted-file> ...
git add <conflicted-file> ...
git commit --no-edit

# 4. Regenerate skill files
./setup

# 5. Re-apply fork patches (idempotent — no-ops if upstream already merged them)
bash "$OPENCLAW_ROOT/orama-system/scripts/fork-patches/apply-fork-patches.sh"

# 6. Verify
cat VERSION
```

**Conflict resolution rule:** if `apply-fork-patches.sh` prints
`✓ already present (patched or upstream-merged)`, the patch is absorbed — retire
the patch file from `scripts/fork-patches/patches/` and remove the branch entry
from `~/.zshrc`.

**Active fork patches** (idempotent — safe to re-apply any time):

| Patch | What it fixes | Retire when |
| ----- | ------------- | ----------- |
| `gstack-1802-staging-guard` | Prevents gbrain autopilot SIGTERM from poisoning `import-checkpoint.json` | upstream `garrytan/gstack#1827` merges |
| `gstack-probe-timeout-30s` | Raises `PROBE_TIMEOUT_MS` from 5 s → 30 s (env-overridable via `GSTACK_PROBE_TIMEOUT_MS`); Supabase postgres cold-connect takes 20-25 s so 5 s causes false `broken-config` verdicts from `gstack-gbrain-detect` | upstream ships configurable probe timeout |

If `gstack-gbrain-detect` returns `gbrain_local_status: "broken-config"` after a fresh install or upgrade, run `fork-heal` first before diagnosing further — the probe timeout patch may have been reverted.

**zshrc guard (auto-heal on every shell):**
```zsh
_ORAMA_FORK_HEAL="$OPENCLAW_ROOT/orama-system/scripts/fork-patches/apply-fork-patches.sh"
[ -f "$_ORAMA_FORK_HEAL" ] && fork-heal() { bash "$_ORAMA_FORK_HEAL" "$@"; }
```
Run `fork-heal` manually after any upgrade — idempotent and safe to repeat.

### gbrain upgrade

gbrain is a **private GitHub repo** (`garrytan/gbrain`) — do NOT use npm/bun global install
(that installs a different unrelated package). Upgrade by pulling and rebuilding:

```bash
cd ~/gbrain
git pull
bun install
bun build --compile --outfile bin/gbrain src/cli.ts
bun link
gbrain --version
gbrain doctor --fast
```

**Mac:** confirm `~/.gbrain/config.json` still has `"prepare": false`
(Supabase pooler requires this) and `ollama:bge-m3` for embeddings.

**Windows:** confirm `embedding_model` is `llama-server:text-embedding-qwen3-embedding-8b-i1-gguf-q6-k`
and `LLAMA_SERVER_BASE_URL=http://localhost:1234/v1` is set (see Windows section below).

If `gbrain doctor` reports broken sources, run `/sync-gbrain --full`.

---

### gbrain — Windows / LM Studio Setup

Windows uses LM Studio (port 1234) instead of Ollama. gbrain talks to it via the
`llama-server` recipe, which uses the OpenAI-compatible `/v1/embeddings` endpoint.

**Required env var (add to PowerShell profile or session):**
```powershell
$env:LLAMA_SERVER_BASE_URL = "http://localhost:1234/v1"
```

**gbrain install (private repo, bun):**
```bash
# Bash / Git Bash
export PATH="/c/Users/$USER/.bun/bin:$PATH"
cd ~
git clone https://github.com/garrytan/gbrain.git
cd gbrain
bun install
bun build --compile --outfile bin/gbrain src/cli.ts
bun link
gbrain --version
```

**Brain init (Qwen3-Embedding-8B, 4096-dim — best for code):**
```bash
export LLAMA_SERVER_BASE_URL="http://localhost:1234/v1"
cd ~/gbrain && bun run src/cli.ts init \
  --pglite \
  --embedding-model "llama-server:text-embedding-qwen3-embedding-8b-i1-gguf-q6-k" \
  --embedding-dimensions 4096 \
  --yes
```

> **Why Qwen3 works now:** gbrain's `migrate.ts` (v45 facts, v55 query_cache) is patched
> to skip HNSW index creation when `embeddingDim > 4000` (pgvector HALFVEC HNSW cap).
> `content_chunks` was already guarded by `applyChunkEmbeddingIndexPolicy`.
> Exact scans are used instead — correct for a personal brain.
>
> **Fallback:** if Qwen3 is not loaded in LM Studio, use
> `--embedding-model "llama-server:text-embedding-nomic-embed-text-v1.5" --embedding-dimensions 768`

**Expected `~/.gbrain/config.json` on Windows:**
```json
{
  "engine": "pglite",
  "database_path": "C:\\Users\\<user>\\.gbrain\\brain.pglite",
  "embedding_model": "llama-server:text-embedding-qwen3-embedding-8b-i1-gguf-q6-k",
  "embedding_dimensions": 4096,
  "schema_pack": "gbrain-base-v2",
  "mcp": { "publish_skills": true },
  "self_upgrade": { "mode": "notify", "mode_prompted": true }
}
```

> `embedding_disabled` must NOT be present. If it appears (from a failed prior init),
> remove it manually and re-run `gbrain doctor --fast`.

**gbrain MCP server in Claude Code (`~/.claude.json` or settings UI):**
```json
{
  "mcpServers": {
    "gbrain": {
      "command": "cmd",
      "args": ["/c", "set LLAMA_SERVER_BASE_URL=http://localhost:1234/v1 && gbrain serve"],
      "env": { "LLAMA_SERVER_BASE_URL": "http://localhost:1234/v1" }
    }
  }
}
```

**Verification:**
```bash
export LLAMA_SERVER_BASE_URL="http://localhost:1234/v1"
gbrain doctor --fast
# Expect: Brain ready, embedding OK, 4096-dim
```

## Available Skills

| Skill | Purpose |
| ------- | --------- |
| `/browse` | Headless browser for web browsing and site docs |
| `/qa` | Systematically QA test a web application and fix issues |
| `/qa-only` | Report-only QA testing |
| `/design-review` | Designer's eye QA: visual inconsistency, spacing, contrast |
| `/design-html` | Generate production-quality HTML designs |
| `/design-shotgun` | Generate multiple AI design variants |
| `/design-consultation` | Understand your product and provide design guidance |
| `/review` | Pre-landing PR review |
| `/ship` | Ship workflow: detect + merge base branch, run tests, deploy |
| `/land-and-deploy` | Land and deploy workflow |
| `/canary` | Post-deploy canary monitoring |
| `/benchmark` | Performance regression detection |
| `/office-hours` | YC Office Hours — startup or project mode |
| `/plan-ceo-review` | CEO/founder-mode plan review |
| `/plan-eng-review` | Eng manager-mode plan review |
| `/plan-design-review` | Designer's eye plan review |
| `/plan-devex-review` | Interactive developer experience plan review |
| `/autoplan` | Auto-review pipeline |
| `/devex-review` | Live developer experience audit |
| `/retro` | Weekly engineering retrospective |
| `/investigate` | Systematic debugging with root cause investigation |
| `/document-release` | Post-ship documentation update |
| `/codex` | OpenAI Codex CLI wrapper |
| `/cso` | Chief Security Officer mode |
| `/learn` | Manage project learnings |
| `/careful` | Safety guardrails for destructive commands |
| `/freeze` | Restrict file edits to a specific directory |
| `/unfreeze` | Clear the freeze boundary set by /freeze |
| `/guard` | Full safety mode: destructive command warnings |
| `/setup-browser-cookies` | Import cookies from real Chromium browser |
| `/setup-deploy` | Configure deployment settings |
| `/setup-gbrain` | Set up gbrain for this coding agent |
| `/connect-chrome` | Pair a remote AI agent with your browser |
| `/gstack-upgrade` | Upgrade gstack to the latest version |
| `/skillify` | Create a new orama-system or gstack skill interactively |

## Skill Routing

When the user's request matches a skill below, invoke it via the Skill tool.
Multi-step workflows and quality gates produce better results than ad-hoc answers.
A false positive is cheaper than a false negative.

| Signal | Invoke |
| -------- | -------- |
| Product ideas, "is this worth building", brainstorming | `/office-hours` |
| Strategy, scope, "think bigger", "what should we build" | `/plan-ceo-review` |
| Architecture, "does this design make sense" | `/plan-eng-review` |
| Design system, brand, "how should this look" | `/design-consultation` |
| Design review of a plan | `/plan-design-review` |
| Developer experience of a plan | `/plan-devex-review` |
| "Review everything", full review pipeline | `/autoplan` |
| Bugs, errors, "why is this broken", "this doesn't work" | `/investigate` |
| Test the site, find bugs, "does this work" | `/qa` or `/qa-only` |
| Code review, check the diff, "look at my changes" | `/review` |
| Visual polish, design audit, "this looks off" | `/design-review` |
| Developer experience audit, try onboarding | `/devex-review` |
| Ship, deploy, create a PR, "send it" | `/ship` |
| Merge + deploy + verify | `/land-and-deploy` |
| Configure deployment | `/setup-deploy` |
| Post-deploy monitoring | `/canary` |
| Update docs after shipping | `/document-release` |
| Weekly retro, "how'd we do" | `/retro` |
| Second opinion, codex review | `/codex` |
| Safety mode, careful mode, lock it down | `/careful` or `/guard` |
| Restrict edits to a directory | `/freeze` or `/unfreeze` |
| Upgrade gstack | `/gstack-upgrade` |
| Save progress, "save my work" | `/context-save` |
| Resume, restore, "where was I" | `/context-restore` |
| Security audit, OWASP, "is this secure" | `/cso` |
| Make a PDF, document, publication | `/make-pdf` |
| Launch real browser for QA | `/open-gstack-browser` |
| Import cookies for authenticated testing | `/setup-browser-cookies` |
| Performance regression, page speed, benchmarks | `/benchmark` |
| Review what gstack has learned | `/learn` |
| Tune question sensitivity | `/plan-tune` |
| Code quality dashboard | `/health` |
| Create a new skill | `/skillify` |

## GBrain Configuration

Engine: **postgres** (Supabase pooler). Config: `~/.gbrain/config.json`.
DB URL lives in `~/.gbrain/.env` as `GBRAIN_DATABASE_URL` — sourced by `~/.zshrc`
and the MCP wrapper, NOT by non-interactive Bash shells.

> **Source IDs migrated 2026-06-17 (old → new).** After the 2026-06-14 security re-anchor,
> gbrain's `deriveCodeSourceId` moved from the legacy scheme (`orama-src`,
> `gstack-code-ools-…`, `gstack-code-claw-…`) to current per-worktree `gstack-code-<hash>` IDs,
> and all three repos were reindexed against current HEAD. **`.gbrain-source` pins already point
> at the CURRENT IDs** — query those. The old sources are stale (@2026-06-05), superseded, and
> **ARCHIVED 2026-06-22** via `gbrain sources archive` (soft-delete, reversible with
> `gbrain sources restore <id>`). Defs exported to BOTH
> `~/repo-backups/gbrain-stale-quarantine-20260618/` and `…-20260622/orphan-sources.json`
> (and code preserved in git). `periscope-src` was also archived — its path moved to
> `~/code/oramasys/tools/periscope`; re-add with
> `gbrain sources add --path ~/code/oramasys/tools/periscope` if periscope work resumes.
>
> **Lesson (do NOT leave "pending removal"):** these sat un-removed from 2026-06-18→06-22 and
> kept resurfacing as `sync_freshness`/`multi_source_drift` warnings every session. **Complete
> the archive in the same pass you decide it** — a deferred removal is a recurring false alarm.
> Note: archive is reversible but `gbrain doctor` still lists archived sources in freshness
> (noise, not breakage); `gbrain sources purge <id> --confirm-destructive` removes them fully
> (recoverable via the exported manifest above). The idempotent guard
> `scripts/gbrain/gbrain-selfheal.sh` surfaces orphan sources automatically.

| Repo | Current source ID (reindexed 2026-06-17) | Pages | Federated | Superseded ID (@06-05, quarantined) |
| ------ | ------ | ------- | ----------- | ------ |
| AlphaClaw | `gstack-code-alphaclaw-875d5b82` | ~476 | yes | `gstack-code-claw-4dc4a8f3-aa4479` (489p) |
| Perpetua-Tools | `gstack-code-078b0b90-f6179f` | ~736 | yes | `gstack-code-ools-27e2b79c-df8a28` (721p) |
| orama-system | `gstack-code-2159b4b9-595bce` | ~223 | yes (was isolated) | `orama-src` (306p) |
| periscope | `periscope-src` | ~14 | yes | — current (separate dormant repo, last commit 2026-04-19) |

Re-run setup: `/setup-gbrain`

## GBrain on Claude Desktop (MCP) — ported from the CLI

Claude Desktop uses a **separate** MCP config from the CLI:
`~/Library/Application Support/Claude/claude_desktop_config.json` (NOT `~/.claude.json`).
Port the same servers there (`gbrain` + `code-review-graph`) to give Desktop the CLI's tool
surface. Note: filesystem skills (`~/.agents/skills/`, `~/.claude/skills/`) are CLI-only — they
do not load in Desktop; the portable knowledge is the **MCP servers**, so register both.

**Gotcha (fixed 2026-06-14):** Desktop launches MCP servers with a **minimal PATH**
(`/usr/bin:/bin`) and does NOT inherit your shell. The `~/.bun/bin/gbrain` binary needs `bun`
on PATH, so a plain `gbrain serve` wrapper fails with `env: bun: No such file or directory`
and the server shows disconnected. The CLI works only because it inherits the terminal PATH.

**Canonical Desktop wrapper** (`.mcpServers.gbrain`) — source `.env` for the DB URL AND
prepend `~/.bun/bin`:

```json
{
  "command": "/bin/sh",
  "args": ["-c", ". \"$HOME/.gbrain/.env\"; export PATH=\"$HOME/.bun/bin:/opt/homebrew/bin:/usr/local/bin:$PATH\"; exec \"$HOME/.bun/bin/gbrain\" serve"]
}
```

Restart Claude Desktop after editing (MCP servers load at app start). Verify in a Desktop-like
minimal env before restarting:

```bash
env -i HOME="$HOME" PATH=/usr/bin:/bin /bin/sh -c '. "$HOME/.gbrain/.env"; export PATH="$HOME/.bun/bin:$PATH"; gbrain doctor --json' | head
```

`code-review-graph` is already PATH-safe (absolute `/opt/homebrew/bin/uvx` command) — no wrapper
needed. Back up the config (`cp … config.json config.json.bak-<ts>`) before editing.

## GBrain Ops — Failure Modes and Fixes

> Hard-won 2026-05-30 after an agent rewrote git history across all three repos.

### 0. Non-interactive shell missing DB URL

`GBRAIN_DATABASE_URL` is in `~/.gbrain/.env`, not in the environment of a Bash tool
shell. Always prefix:

```bash
set -a; source "$HOME/.gbrain/.env" 2>/dev/null; set +a
```

The "No database URL" message is diagnostic only — config.json intentionally omits
the URL; env wins over config.

### 1. Write failures: `prepared statement "x" does not exist` / `CONNECTION_CLOSED`

Cause: `config.json` `"prepare": true` against a Supabase pooler. Pooled reconnects
drop server-side prepared statements.

Fix:

```bash
cp ~/.gbrain/config.json "~/.gbrain/config.json.bak.$(date +%Y%m%d-%H%M%S)"
python3 -c "import json; p='$HOME/.gbrain/config.json'; d=json.load(open(p)); d['prepare']=False; json.dump(d,open(p,'w'),indent=2)"
```

Then restart any running gbrain process (autopilot, MCP server).

### 2. Correct resync after a git history rewrite

Two traps to avoid:

- `gbrain sync` (pin-aware, from inside a repo with a space in the path) calls
  `git pull` first and **fails silently** on `Terminal xCode`-style paths. Non-fatal
  but pulls nothing.
- `gbrain sync --repo "<path>"` without `--source` dumps into **`default`**, not the
  repo's pinned source.

**Always pass both `--repo` (quoted) and `--source`:**

```bash
set -a; source "$HOME/.gbrain/.env" 2>/dev/null; set +a
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw-v1}"
PT_ROOT="${PERPETUA_TOOLS_PATH:-${PERPETUA_TOOLS_ROOT:-$OPENCLAW_HOME/Perpetua-Tools}}"
ORAMA_ROOT="${ORAMA_INSTALL_DIR:-$REPO_ROOT}"
gbrain sync --repo "$OPENCLAW_HOME/AlphaClaw" \
            --source gstack-code-alphaclaw-875d5b82 --skip-failed
gbrain sync --repo "$PT_ROOT" \
            --source gstack-code-078b0b90-f6179f --skip-failed
gbrain sync --repo "$ORAMA_ROOT" \
            --source gstack-code-2159b4b9-595bce --skip-failed
gbrain sources list
```

`--skip-failed` also acknowledges stale `createVersion failed` history-rewrite
failures. Verify with `gbrain doctor --fast` → health should reach ~95.

### 3. Stale `createVersion failed` failures

Acknowledged by `--skip-failed` (above). `gbrain doctor` then shows `all acknowledged`.

### 4. `gbrain list` / `gbrain get` return wrong or empty results

- Without `--source`, `list`/`get` target **`default`**, not the pinned source.
- Slugs are **lowercased, `.md` stripped**: `docs/MIGRATION.md` → `docs/migration`.
- Verify indexing via content search: `gbrain search "<distinctive first line>"`.

### 5. Restarting a wedged autopilot daemon

```bash
PID=$(cat ~/.gbrain/autopilot.lock 2>/dev/null)
kill "$PID" 2>/dev/null
n=0; until ! kill -0 "$PID" 2>/dev/null; do n=$((n+1)); [ "$n" -ge 15 ] && kill -9 "$PID"; sleep 1; done
rm -f ~/.gbrain/autopilot.lock
pgrep -fl "gbrain autopilot" || echo "(stopped)"
```

Restart only after applying the `prepare:false` fix — otherwise it re-wedges
on the same pooler write failures.

### 6. Autopilot watching `/` (launchd cwd misconfig) — blocks sync, never refreshes

Symptom: `/sync-gbrain` code stage is refused (`autopilot active`); `gbrain sources list`
shows the real sources stuck at an old `last sync` **and** orphan `gstack-code-*` sources with
`0 pages`; the autopilot pid's cwd is `/`. Killing the pid just spawns a new one (KeepAlive).

Cause: `~/Library/LaunchAgents/com.gbrain.autopilot.plist` runs `~/.gbrain/autopilot-run.sh`
(`exec gbrain autopilot --repo '.'`) with **no `WorkingDirectory`**, so launchd starts it in `/`
and `--repo '.'` watches the filesystem root — useless work, but it holds the lock and blocks
manual sync. `gbrain autopilot --install` generated this without pinning a repo.

Fix (full remediation):

```bash
# 1. Stop the respawn — unload the KeepAlive agent (a plain kill won't stick)
launchctl unload ~/Library/LaunchAgents/com.gbrain.autopilot.plist
rm -f ~/.gbrain/autopilot.lock
# 2. Remove orphan 0-page sources (spawned by the misconfig or a re-anchor)
gbrain sources list                  # find the 0-page gstack-code-* dupes
gbrain sources remove <orphan-id>    # repeat per orphan
# 3. Re-pin each worktree to its POPULATED source
echo "<populated-source-id>" > <repo>/.gbrain-source
# 4. Reindex now-unblocked, from each repo root
/sync-gbrain --full
# 5. Reinstall autopilot CORRECTLY: add a WorkingDirectory to the plist (or `cd "$REPO"`
#    in autopilot-run.sh) so `--repo .` resolves to a real repo, then `launchctl load` —
#    OR leave it unloaded and rely on manual /sync-gbrain (safer for a multi-repo workspace).
```

A misconfigured autopilot is worse than none: it blocks manual sync while indexing nothing.

### 7. Durable self-heal — stop re-fixing the same rot (2026-06-22)

The failures in §2/§5/§6 recur because the fixes lived only as knowledge, not automation,
and removal steps were deferred. The idempotent guard
[`scripts/gbrain/gbrain-selfheal.sh`](../../../scripts/gbrain/gbrain-selfheal.sh) makes the
SAFE remediations automatic and SURFACES the rest:

- skips entirely if `gstack-gbrain-detect` says `gbrain_local_status != ok`;
- warns if autopilot's cwd is `/` (the §6 jam);
- acks transient failures and refreshes each LIVE source with `--repo "<path>" --source <id> --skip-failed`;
- reports orphan sources whose `local_path` is missing (quarantine candidates) — never auto-deletes.

Wire-in: `start.sh` calls it best-effort/non-fatal each session. Run manually any time:
`bash scripts/gbrain/gbrain-selfheal.sh`. Update its `PAIRS` map when a repo moves (and archive
the old source in the same pass).

Two gotchas it encodes:

- **Bare `gbrain sync` from a non-git cwd only acks failures, then refuses** with
  `Not a git repository: GBrain sync requires a git-initialized repo`. Per-source sync MUST
  `cd` into the repo (or pass `--repo "<path>"`) AND `--source <id>` (§2).
- **Prefer `gbrain sources archive` (reversible) over `remove`/`purge`** for orphans; always
  export the def first (`gbrain sources list --json | jq` → `~/repo-backups/…`) so it's
  restorable, and record where you put it.

**Multi-repo note:** a single `gbrain autopilot --repo .` can only watch one tree, so for this
multi-repo workspace the self-heal script (or manual `/sync-gbrain` per repo) is the refresh
mechanism — NOT the launchd autopilot, which is left unloaded (§6).

### Quick Reference

| Symptom | Fix |
| --------- | ----- |
| `No database URL` in a script | `set -a; source ~/.gbrain/.env; set +a` first |
| `prepared statement does not exist` | set `"prepare": false` in config.json, restart procs |
| Resync left per-repo source stale | `sync --repo "<quoted>" --source <id>` — never bare `--repo` |
| `git pull failed in /Users/.../claude/` | non-fatal space-in-path; fs import still proceeds |
| N unacknowledged `createVersion` failures | add `--skip-failed` to sync |
| `gbrain get docs/MIGRATION` → not found | slug is lowercased: `docs/migration` |
| autopilot wedged 12h+ | kill via lock pid, clear lock, apply `prepare:false`, restart |
| autopilot pid cwd is `/`, sources stale + 0-page dupes | `launchctl unload ~/Library/LaunchAgents/com.gbrain.autopilot.plist`; remove orphan sources; fix plist `WorkingDirectory` or use manual `/sync-gbrain` (mode 6) |
| `Not a git repository: GBrain sync requires…` | bare `gbrain sync` from a non-git cwd only acks failures; `cd` into the repo (or `--repo "<path>"`) + `--source <id>` (§7) |
| sources stale every session despite "fixing" | old-path duplicate sources left un-archived ("pending removal"); archive + export def in the SAME pass; run `scripts/gbrain/gbrain-selfheal.sh` (§7) |
| recurring gbrain rot in general | `bash scripts/gbrain/gbrain-selfheal.sh` (idempotent: ack + refresh live sources + report orphans/misconfig) |

## Symbol vs Text Search

For SYMBOL questions (def, refs, callers, callees), use `gbrain code-def / code-refs / code-callers / code-callees` — graph data. For TEXT with exact strings, regex, or file globs, use Grep. Never default to Grep first for code questions.
