---
name: using-git-worktrees
description: >
  Git worktree lifecycle for parallel agents on the orama-system stack.
  Invoke when: starting parallel agent work, bootstrapping a worktree, asking
  "should I use a worktree?", debugging port collisions, cleaning up a finished
  worktree, or any mention of worktree, parallel agents, ENV_OFFSET, or
  worktree-bootstrap.
---

# Using Git Worktrees — orama-system Stack

> Real-time guidance. Full doctrine: `orama-system/docs/v2/19-worktree-parallel-agents.md`
> Hardware baseline (2026-05-24): 1 Win RTX3080 (LM Studio) + Mac Ollama.

---

## Step 0 — Should You Use a Worktree?

Ask two questions:

1. **Will this agent write files?**
2. **Is another agent currently writing to the same repo?**

```
Both yes? → Worktree.  Run Step 1.
Either no? → Use canonical checkout.  Stop here.
```

---

## Step 1 — Bootstrap

```bash
# From the canonical repo root
scripts/worktree-bootstrap.sh <repo-path> <branch> <slug> [gbrain-source-id]

# Example
scripts/worktree-bootstrap.sh \
  ~/Documents/Terminal\ xCode/claude/OpenClaw/orama-system \
  feat/my-feature \
  2026-05-24-my-feature \
  orama-src
```

Bootstrap handles automatically (no manual steps needed):
- ✅ Removes stale `.git/*.lock` files
- ✅ Warns on orphan refs with spaces
- ✅ Creates `~/Documents/oramasys/worktrees/<slug>/`
- ✅ Writes `.gbrain-source`
- ✅ Appends macOS dedup patterns to `.gitignore`
- ✅ Assigns `ENV_OFFSET = worktree_index × 100`
- ✅ Writes `.worktree-env` with offset port vars
- ✅ Updates `.cursor/environment.json` if present

---

## Step 2 — Enter and Configure

```bash
cd ~/Documents/oramasys/worktrees/<slug>
source .worktree-env    # loads ENV_OFFSET, port vars

# Verify gbrain pin
cat .gbrain-source      # should show e.g. "orama-src"

# Verify port offset
echo "AlphaClaw: $ALPHACLAW_PORT  PT: $PT_PORT"
```

---

## Step 3 — Work Rules While in a Worktree

### Inference (GPU)
- **Never POST directly to LM Studio or Ollama.** Always via PT.
- Start PT on your offset port: `PT_PORT=$PT_PORT python -m perpetua_tools.server`
- Win LM Studio serializes heavy models automatically — no extra lock needed.

### CRG (graph.db)
```python
# ✅ Query canonical graph — always pass repo_root
mcp__code-review-graph__query_graph_tool(
    repo_root="/path/to/canonical/orama-system"
)

# ❌ Never build graph from inside a worktree
# mcp__code-review-graph__build_or_update_graph_tool()  ← blocked in worktrees
```

### Port Map (ENV_OFFSET = N × 100, where N = worktree index)

| Service | Canonical | Worktree-1 | Worktree-2 |
|---------|-----------|------------|------------|
| AlphaClaw | 3000 | 3100 | 3200 |
| PT | 8000 | 8100 | 8200 |
| orama-api | 8001 | 8101 | 8201 |
| portal | 8002 | 8102 | 8202 |

---

## Step 4 — Cleanup (ALWAYS use finishing-a-development-branch)

```
Invoke: superpowers:finishing-a-development-branch
```

The skill will:
1. Verify tests pass
2. Ask: merge / PR / keep / discard
3. On merge or discard → run `git worktree remove <path>` automatically

**Manual fallback only if skill unavailable:**
```bash
# From canonical checkout:
git worktree remove ~/Documents/oramasys/worktrees/<slug>
git worktree list    # verify removed
git branch -d <branch>
```

⚠️ **Never `rm -rf` the worktree directory** — leaves dangling entry in `git worktree list`.

---

## Quick Diagnostics

```bash
# List all active worktrees
git worktree list

# Check for stale locks (run from canonical .git parent)
find .git -name "*.lock" -print

# Check for orphan refs with spaces
find .git/refs -name "* *" -print

# Check gbrain pin
cat .gbrain-source

# Check port config
cat .worktree-env
```

---

## Pre-flight Defenses (Dogfood Datums)

| Symptom | Fix |
|---------|-----|
| `git fetch` fails: `bad object refs/heads/... 2` | `find .git/refs -name "* *"` then `git update-ref -d "refs/heads/<name>"` |
| `git checkout` / `git stash` blocked | `find .git -name "*.lock" -delete` |
| `.gbrain-source` missing in new worktree | `echo "<source-id>" > .gbrain-source` |
| `git status` shows dozens of `* 2/` dirs | Bootstrap adds dedup `.gitignore`; also `rm -rf *\ 2/` |
| Port collision with sibling worktree | Check `.worktree-env`; ENV_OFFSET must differ per worktree |
| `/autoplan` Step 0 fails (base branch) | `cd` to a git repo root before invoking any skill |

---

## Scope

Applies to: **orama-system**, **Perpetua-Tools**
Does not apply to: periscope, AlphaClaw (excluded from worktree doctrine)
