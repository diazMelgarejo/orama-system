---
name: gstack
description: >-
  gstack v1.12.2.0 integration sub-skill. Full routing table for web browsing,
  QA, shipping, planning reviews, design, DX audits, retros, and GBrain.
  Activates for: /browse, /qa, /ship, /review, /investigate, /design-review,
  /canary, /benchmark, /retro, gbrain, gstack skills, web browsing, QA testing,
  deploy, design review, canary monitoring, performance benchmarks.
version: 1.0.0
license: Apache 2.0
compatibility: claude-code
parent_skill: orama-system
gstack_version: "1.12.2.0"
gstack_install: "~/.claude/skills/gstack (global-git)"
---

# gstack Integration

gstack v1.12.2.0 is the agent skill framework for web browsing, planning,
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

## Available Skills

| Skill | Purpose |
|-------|---------|
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
|--------|--------|
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

| Source | ID | Pages | Federated? |
|--------|----|-------|-----------|
| AlphaClaw | `gstack-code-claw-4dc4a8f3-aa4479` | ~478 | yes |
| Perpetua-Tools | `gstack-code-ools-27e2b79c-df8a28` | ~725 | yes |
| orama-system | `orama-src` | ~191 | no (isolated) |
| periscope | `periscope-src` | ~14 | yes |

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
            --source gstack-code-claw-4dc4a8f3-aa4479 --skip-failed
gbrain sync --repo "$PT_ROOT" \
            --source gstack-code-ools-27e2b79c-df8a28 --skip-failed
gbrain sync --repo "$ORAMA_ROOT" \
            --source orama-src --skip-failed
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

### Quick Reference

| Symptom | Fix |
|---------|-----|
| `No database URL` in a script | `set -a; source ~/.gbrain/.env; set +a` first |
| `prepared statement does not exist` | set `"prepare": false` in config.json, restart procs |
| Resync left per-repo source stale | `sync --repo "<quoted>" --source <id>` — never bare `--repo` |
| `git pull failed in /Users/.../claude/` | non-fatal space-in-path; fs import still proceeds |
| N unacknowledged `createVersion` failures | add `--skip-failed` to sync |
| `gbrain get docs/MIGRATION` → not found | slug is lowercased: `docs/migration` |
| autopilot wedged 12h+ | kill via lock pid, clear lock, apply `prepare:false`, restart |
| autopilot pid cwd is `/`, sources stale + 0-page dupes | `launchctl unload ~/Library/LaunchAgents/com.gbrain.autopilot.plist`; remove orphan sources; fix plist `WorkingDirectory` or use manual `/sync-gbrain` (mode 6) |

## Symbol vs Text Search

For SYMBOL questions (def, refs, callers, callees), use `gbrain code-def / code-refs / code-callers / code-callees` — graph data. For TEXT with exact strings, regex, or file globs, use Grep. Never default to Grep first for code questions.
