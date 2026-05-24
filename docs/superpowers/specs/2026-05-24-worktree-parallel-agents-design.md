# Git Worktrees for Parallel Agents — Design Spec

**Date:** 2026-05-24
**Branch:** feat/worktree-doctrine
**Scope:** orama-system + Perpetua-Tools only (periscope + AlphaClaw excluded)
**Author:** cyre
**Status:** Approved — proceeding to implementation plan

> This spec was written FROM a worktree (`~/Documents/oramasys/worktrees/worktree-doctrine`),
> dogfooding the very workflow it describes. Eight real friction datums were captured in
> `.experience-log/dogfood-notes.md` and resolved into specific defenses below.

---

## Goal

Give a human operator (or an orchestrator) a decision under 5 seconds:
**Does this task need its own worktree?** If yes: how do I bootstrap, run, and tear it down safely
on a single Mac with one Win RTX3080, without port collisions, GPU fights, or CRG corruption?

Target: **2–5 parallel agents on one machine**. Not theoretical cluster scaling.

---

## Section 1 — Architecture: When to Use a Worktree

### The 4-Quadrant Rule

```
                      ISOLATION NEEDED?
                      No              Yes
                 ┌──────────────┬───────────────────┐
      Writes?  Y │ Bad idea     │ WORKTREE ✅        │
                 ├──────────────┼───────────────────┤
                 N │ Canonical ✅ │ Canonical ✅      │
                 └──────────────┴───────────────────┘
```

**Use a worktree when ALL of:**
1. The agent will WRITE files (not just read/analyze)
2. The work is isolated from another agent's concurrent writes
3. The agent operates on a separate named branch

**Use the canonical checkout when ANY of:**
- Read-only analysis (code review, semantic search, test runs against committed code)
- Sequential work (one agent at a time)
- The task completes faster than worktree bootstrap time (~30s)

### Decision Tree (copy this to CLAUDE.md)

```
Will this agent write files?
  └─ No  → Use canonical checkout. Done.
  └─ Yes → Is another agent already writing to canonical?
               └─ No  → Use canonical. Done.
               └─ Yes → Create a worktree. Bootstrap with worktree-bootstrap.sh.
```

### Canonical Location

```
~/Documents/oramasys/worktrees/<slug>/
```

Where `<slug>` = `<yyyy-mm-dd>-<brief-purpose>` (e.g. `2026-05-24-worktree-doctrine`).

**Why external to the repo directory:** avoids `.gitignore` issues, macOS Finder dedup
contamination of tracked files, and allows multiple orama-family repos to share the hub.

---

## Section 2 — Components

Six artifacts ship with this doctrine:

| # | Artifact | Path | Purpose |
|---|----------|------|---------|
| 1 | Canonical doc | `orama-system/docs/v2/19-worktree-parallel-agents.md` | Full reference + decision tree |
| 2 | Cross-repo nav | `OpenClaw/CLAUDE-instru.md` §Worktrees | One-paragraph hook into canonical doc |
| 3 | orama-system stub | `orama-system/CLAUDE.md` §Worktrees | Points to canonical doc |
| 4 | Perpetua-Tools stub | `Perpetua-Tools/CLAUDE.md` §Worktrees | Points to canonical doc |
| 5 | Invocable skill | `~/.claude/skills/using-git-worktrees/SKILL.md` | Agents invoke this for real-time guidance |
| 6 | Bootstrap script | `orama-system/scripts/worktree-bootstrap.sh` | One-command idempotent setup |

### Bootstrap Script Contract (`worktree-bootstrap.sh`)

Accepts: `<repo-path> <branch> <slug> [gbrain-source-id]`

Steps (idempotent — safe to re-run):
1. Pre-flight: check no stale `.git/*.lock`, no orphan refs with spaces
2. `git worktree add ~/Documents/oramasys/worktrees/<slug> -b <branch>` (or attach if exists)
3. Write `.gbrain-source` from argument or copy from canonical
4. Write `.gitignore` lines: `*\ 2/`, `*\ 2.*`, `*\ 3/`, `*\ 3.*` (macOS dedup junk)
5. Print assigned port offset and ENV_OFFSET value

---

## Section 3 — Data Flow

### Bootstrap → Work → Cleanup

```
Human/Orchestrator
      │
      ▼
worktree-bootstrap.sh <repo> <branch> <slug> [gbrain-source]
      │
      ├─ Pre-flight checks (locks, orphan refs)
      ├─ git worktree add
      ├─ .gbrain-source written
      ├─ macOS dedup .gitignore entries added
      └─ Port offset printed
      │
      ▼
Agent works in ~/Documents/oramasys/worktrees/<slug>/
      │
      ├─ Writes files, runs tests
      ├─ git add / git commit on isolated branch
      └─ (optional) git push origin <branch>
      │
      ▼
superpowers:finishing-a-development-branch skill
      │
      ├─ Verifies tests pass
      ├─ Presents: merge / PR / keep / discard
      └─ On merge or discard: git worktree remove <path>
```

### Port Allocation: Static ENV_OFFSET per Worktree Index

Worktree index = sequential number assigned at bootstrap time (0 = canonical, 1 = first worktree, etc.)

```
Base ports (canonical / index 0):
  AlphaClaw:   3000   Ollama: 11434
  PT:          8000   LM Studio Win: 1234
  orama-api:   8001   LM Studio Mac: 1234 (optional fallback only)
  orama-portal:8002

Per worktree (offset = index × 100):
  worktree-1:  3100, 8100, 8101, 8102
  worktree-2:  3200, 8200, 8201, 8202
  worktree-3:  3300, 8300, 8301, 8302
  worktree-4:  3400, 8400, 8401, 8402
```

`ENV_OFFSET` written to worktree root `.worktree-env` file. AlphaClaw and PT must be started
with these ports when running in a non-canonical worktree. Cursor IDE `.cursor/environment.json`
must be updated accordingly (bootstrap script does this).

### GPU Coordination: PT Dispatch Queue (not filesystem lock)

All inference (Mac Ollama + Win LM Studio) routes through PT's `backend_resolver.py` +
`dispatch_models.py`. This is the single chokepoint.

**Rule:** No agent ever POSTs directly to LM Studio or Ollama. Always via PT dispatch.

When 2+ worktrees run agents simultaneously:
- Each worktree starts its own PT instance on its offset port (e.g., 8100, 8200)
- Each PT instance queues requests through the shared Win endpoint (`$LM_STUDIO_WIN_ENDPOINTS`)
- First-come-first-served; no additional locking needed (HTTP server serializes)
- Mac Ollama (`qwen3.5:9b-nvfp4`) handles light models concurrently; Win RTX3080 serializes heavy

**Out of scope (future):** multi-Win-device round-robin (see Datum 8 in dogfood notes).

### CRG (`graph.db`) Coordination: Query Against Canonical

`graph.db` lives in the canonical checkout. Worktrees do NOT rebuild it.

```
# In any worktree agent — query canonical graph, don't rebuild
mcp__code-review-graph__query_graph_tool(repo_root="/path/to/canonical/orama-system")

# Only rebuild from canonical checkout, never from a worktree
# (run post-merge in canonical)
mcp__code-review-graph__build_or_update_graph_tool()
```

This avoids concurrent writes to `graph.db` from multiple worktrees.

---

## Section 4 — Error Handling (from Dogfood)

Eight datums from `.experience-log/dogfood-notes.md` → eight defenses:

| Datum | Symptom | Defense | Where |
|-------|---------|---------|-------|
| D1 | `git fetch` fails: `bad object refs/heads/... 2` | Pre-flight: `find .git/refs -name "* *" -print` → `git update-ref -d` | bootstrap.sh |
| D2 | Fresh worktree missing `.gbrain-source` | Bootstrap always writes it (arg or copy from canonical) | bootstrap.sh |
| D3 | Duplicate `18-` prefix in `docs/v2/` | Numbering note in canonical doc: always `ls docs/v2/` before picking number | canonical doc |
| D4 | `/autoplan` from non-git dir breaks Step 0 | Canonical doc: always `cd` to repo root before invoking skills | canonical doc |
| D5 | Stale `.git/*.lock` files block operations | Pre-flight: `find .git -name "*.lock" -delete` | bootstrap.sh |
| D6 | `* 2/`, `* 3/` untracked dirs from macOS dedup | Bootstrap adds patterns to `.gitignore`; add to per-worktree | bootstrap.sh |
| D7 | `.cursor/environment.json` port collision | Bootstrap writes `ENV_OFFSET` to `.worktree-env`; ports offset by index×100 | bootstrap.sh |
| D8 | Multi-Win device pool ignores extra devices | Out of scope for doctrine; noted as future PT enhancement | canonical doc footnote |

---

## Section 5 — Testing the Doctrine

Five verification approaches (in order of cost):

1. **Bootstrap idempotency**: run `worktree-bootstrap.sh` twice on same slug → second run no-ops cleanly, no duplicate entries in `git worktree list`

2. **2-agent dogfood** (this session): write doctrine FROM worktree-doctrine, use finishing-a-development-branch to clean up → proves the loop closes

3. **Parallel write test**: create 2 worktrees on the same repo, have each write to a different file, commit independently, verify no cross-contamination in `git log --all`

4. **CRG no-rebuild test**: query `query_graph_tool` from a worktree with `repo_root=<canonical>` → results match canonical; worktree's own `graph.db` is absent (never created)

5. **5-agent stress test** (pre-Phase 2 integration): 5 parallel worktrees, each with PT on offset port, all posting inference via their local PT → Win LM Studio serializes, no 500s, no GPU OOM; Mac Ollama handles light models concurrently

---

## Open Questions Resolved

| OQ | Resolution |
|----|------------|
| OQ1 — worktree location | `~/Documents/oramasys/worktrees/<slug>/` — external hub, not in-repo |
| OQ2 — port allocation | Static index×100 offset; written to `.worktree-env` by bootstrap |
| OQ3 — GPU serialization | PT dispatch queue is the chokepoint; no separate filesystem lock |
| OQ4 — CRG concurrency | Worktrees query canonical `graph.db` via `repo_root=`; no parallel rebuilds |
| OQ5 — lifecycle (no Conductor) | `finishing-a-development-branch` skill handles `git worktree remove`; human runs it |
| OQ6 — worktree vs branch | Parallel+writes → worktree; serial or reads-only → canonical |

---

## Out of Scope

- AlphaClaw CLAUDE.md stub (excluded per user instruction)
- Periscope CLAUDE.md stub (excluded per user instruction)
- Multi-Win device pool hardening (Datum 8 — separate PT task)
- Auto-port discovery (static offsets sufficient for 2–5 agents)
- Worktree NFS/iCloud-sync support (use local APFS only)
