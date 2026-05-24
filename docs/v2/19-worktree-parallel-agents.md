# 19 — Git Worktrees for Parallel Agents

> **Quick reference.** Full design rationale in `docs/superpowers/specs/2026-05-24-worktree-parallel-agents-design.md`.
> Applies to: orama-system, Perpetua-Tools. Excludes: periscope, AlphaClaw.

---

## TL;DR — Decision in 5 Seconds

```
Will this agent WRITE files AND another agent is also writing?
  Yes → create a worktree.  Run: scripts/worktree-bootstrap.sh <repo> <branch> <slug>
  No  → use the canonical checkout.  Done.
```

---

## 1. When to Create a Worktree

### 4-Quadrant Rule

|                      | Isolated writes? **No** | Isolated writes? **Yes** |
|----------------------|------------------------|--------------------------|
| **Parallel agents?** **No**  | Canonical ✅ | Canonical ✅ |
| **Parallel agents?** **Yes** | Canonical ✅ | **Worktree** ✅ |

**Worktree triggers — ALL must be true:**
1. Agent will write/modify files
2. Another agent is concurrently writing to the same repo
3. The work lives on a separate named branch

**Stay on canonical — ANY of these is enough:**
- Read-only work (code review, semantic search, test runs against committed code)
- Sequential work (one agent at a time)
- Task completes faster than ~30s worktree bootstrap time

### Decision Tree

```
Will this agent write files?
├─ No  → Canonical. Done.
└─ Yes → Is another agent already writing to canonical?
          ├─ No  → Canonical. Done.
          └─ Yes → git worktree. Run worktree-bootstrap.sh.
```

---

## 2. Canonical Worktree Location

```
~/Documents/oramasys/worktrees/<slug>/
```

**Slug format:** `yyyy-mm-dd-<brief-purpose>` — e.g. `2026-05-24-worktree-doctrine`

Why external to the repo directory:
- Avoids `.gitignore` conflicts with tracked files
- Prevents macOS Finder `* 2` dedup contamination
- Lets multiple orama-family repos share the same hub at `~/Documents/oramasys/worktrees/`

---

## 3. Bootstrap

```bash
# One command — idempotent, safe to re-run
scripts/worktree-bootstrap.sh <repo-path> <branch> <slug> [gbrain-source-id]

# Example
scripts/worktree-bootstrap.sh \
  ~/Documents/Terminal\ xCode/claude/OpenClaw/orama-system \
  feat/my-feature \
  2026-05-24-my-feature \
  orama-src
```

Bootstrap does (in order):
1. **Pre-flight**: removes stale `.git/*.lock` files; detects orphan refs with spaces
2. **`git worktree add`** `~/Documents/oramasys/worktrees/<slug>` `-b <branch>` (or attaches if the worktree already exists)
3. **`.gbrain-source`**: writes from argument, or copies from canonical if omitted
4. **`.gitignore`**: appends macOS dedup patterns (`*\ 2/`, `*\ 2.*`, `*\ 3/`, `*\ 3.*`)
5. **Port offset**: assigns `ENV_OFFSET = index × 100`, writes `.worktree-env`
6. **Prints summary**: worktree path, branch, ENV_OFFSET, gbrain source

---

## 4. Port Allocation

Hardware baseline (2026-05-24): **1 Windows RTX3080 (LM Studio) + Mac (Ollama)**.

```
Canonical / index 0:
  AlphaClaw  3000   |  orama-api    8001
  PT         8000   |  orama-portal 8002
  Ollama    11434   |  LM Studio Win 1234

Worktree index N (ENV_OFFSET = N × 100):
  AlphaClaw  3000+N×100  |  orama-api    8001+N×100
  PT         8000+N×100  |  orama-portal 8002+N×100
```

Example — worktree-1 (N=1): AlphaClaw=3100, PT=8100, orama-api=8101, orama-portal=8102

`bootstrap.sh` writes `ENV_OFFSET=N` to `.worktree-env`. AlphaClaw and PT started inside a
worktree MUST source this file. Cursor `.cursor/environment.json` is updated by bootstrap.

**Why static offsets:** 2–5 agents on one machine; static is simpler than dynamic discovery
and collision-free within the supported range.

---

## 5. GPU / Inference Coordination

**Single chokepoint rule:** All inference routes through PT's `backend_resolver.py` +
`dispatch_models.py`. No agent ever POSTs directly to Ollama or LM Studio.

```
Agent (any worktree)
  → PT instance on its offset port (8000, 8100, 8200 …)
    → backend_resolver selects endpoint
      → Win LM Studio :1234 (heavy — serialized by HTTP server)
      → Mac Ollama :11434 (light — concurrent)
```

When 2+ worktrees run simultaneously:
- Each starts its own PT instance on its offset port
- Each PT routes to the same Win endpoint (`$LM_STUDIO_WIN_ENDPOINTS`)
- Win LM Studio HTTP server serializes heavy-model requests naturally — no extra lock needed
- Mac Ollama (`qwen3.5:9b-nvfp4` + `bge-m3`) handles light-model concurrency

**Multi-Win future (not yet implemented):** see Datum 8 in dogfood notes; PT dispatcher
needs dynamic endpoint re-read + round-robin before this matters.

---

## 6. CRG (`graph.db`) Coordination

`graph.db` lives in the canonical checkout. Worktrees **never rebuild it**.

```python
# ✅ From any worktree — query canonical graph
mcp__code-review-graph__query_graph_tool(
    repo_root="/path/to/canonical/orama-system"
)

# ✅ Rebuild only from canonical checkout (post-merge)
mcp__code-review-graph__build_or_update_graph_tool()

# ❌ Never rebuild from inside a worktree
```

---

## 7. GBrain per Worktree

Every worktree needs a `.gbrain-source` file (kubectl-style context pin). Bootstrap writes it.

```bash
# Verify
cat .gbrain-source          # should print a source ID, e.g. "orama-src"

# For doc-only worktrees: point to parent's source
echo "orama-src" > .gbrain-source

# For code worktrees with substantially diverged branches: create a new source
gbrain sources add --name worktree-<slug>-src --path .
echo "worktree-<slug>-src" > .gbrain-source
```

---

## 8. Pre-flight Checklist

Run before `git worktree add` (bootstrap does this automatically):

```bash
# 1. Remove stale lock files (macOS Finder / interrupted git ops)
find .git -name "*.lock" -delete

# 2. Check for orphan refs with spaces (blocks git fetch)
find .git/refs -name "* *" -print
# If any found: git update-ref -d "refs/heads/<bad ref with space>"

# 3. Check for macOS dedup junk (contaminates git status)
ls | grep " 2$" || true
# If found: rm -rf "directory name 2/"
```

---

## 9. Cleanup (After Work Completes)

**Always use `finishing-a-development-branch`** — it handles `git worktree remove` correctly.

```bash
# From inside the worktree
# Invoke the superpowers:finishing-a-development-branch skill
# It will: verify tests → offer merge/PR/keep/discard → run git worktree remove
```

Manual cleanup (if skill unavailable):
```bash
# 1. From canonical checkout:
git worktree remove ~/Documents/oramasys/worktrees/<slug>

# 2. Verify
git worktree list

# 3. Delete branch if merged
git branch -d <branch>
git push origin --delete <branch>
```

**Never `rm -rf` a worktree directory directly** — it leaves a dangling entry in `git worktree list`.

---

## 10. Dogfood Defenses (from `.experience-log/dogfood-notes.md`)

| Datum | Problem | Defense |
|-------|---------|---------|
| D1 | Orphan refs with spaces block `git fetch` | bootstrap pre-flight: `find .git/refs -name "* *"` |
| D2 | Fresh worktrees don't inherit `.gbrain-source` | bootstrap always writes it |
| D3 | Duplicate `docs/v2/` prefixes | always `ls docs/v2/` before picking a number |
| D4 | `/autoplan` from non-git dir breaks Step 0 | always `cd` to repo root before skill invocation |
| D5 | Stale `.git/*.lock` files block checkout | bootstrap pre-flight: `find .git -name "*.lock" -delete` |
| D6 | `* 2/`, `* 3/` dirs from macOS dedup | bootstrap appends dedup patterns to `.gitignore` |
| D7 | `.cursor/environment.json` port collisions | bootstrap writes `ENV_OFFSET`; ports offset by N×100 |
| D8 | Multi-Win pool ignores extra devices | future PT enhancement; current: 1 Win is correct |

---

## 11. Invocable Skill

For real-time agent guidance during a worktree session:

```
~/.claude/skills/using-git-worktrees/SKILL.md
```

Invoke with `/using-git-worktrees` or via the `Skill` tool.

---

## Related Docs

- Design spec: `docs/superpowers/specs/2026-05-24-worktree-parallel-agents-design.md`
- Dogfood log: `.experience-log/dogfood-notes.md` (in `worktree-doctrine` worktree)
- Bootstrap script: `scripts/worktree-bootstrap.sh`
- Build order: `docs/v2/04-build-order.md`
