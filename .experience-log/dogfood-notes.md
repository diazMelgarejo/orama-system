# Worktree Dogfood Notes — Live Capture

> Captured while writing the worktree doctrine FROM a worktree.
> Each entry = real friction or insight that should fold into the canonical doc.

## Datum 1 — Orphan refs with spaces block `git fetch`
- Trigger: `git fetch origin` failed with `fatal: bad object refs/heads/2026-04-24-001-orama-salvage 2`
- Root cause: a `refs/heads/*` entry with a literal space in the name (likely from macOS Finder duplication or `cp -r` of `.git`)
- Doctrine implication: §Pre-flight checklist must include "no orphan refs with spaces" + a one-liner to detect/cleanup:
  ```bash
  find .git/refs -name "* *" -print
  git update-ref -d "refs/heads/<bad ref>"  # quote literally
  ```
- Severity: blocks new worktree creation if `--no-checkout` not used; we got lucky and `worktree add` proceeded anyway

## Datum 2 — Fresh worktrees do NOT inherit `.gbrain-source`
- Trigger: new worktree at `~/Documents/oramasys/worktrees/worktree-doctrine` had no `.gbrain-source` file
- Root cause: `.gbrain-source` is a tracked file in the parent, but a fresh worktree from `origin/main` only checks out files at that commit. If parent's pin was added locally without committing, it doesn't propagate.
- Doctrine implication: §Worktree bootstrap must include:
  ```bash
  echo "<gbrain-source-id>" > .gbrain-source  # OR copy from parent
  ```
- Best practice: commit the `.gbrain-source` to the canonical branch so worktrees inherit it. We did this earlier for periscope.
- For doc-only work: pointing at the parent's source is fine (we did `orama-src`). For code work in a worktree where the branch diverges substantially, create a per-worktree source.

## Datum 3 — `docs/v2/` had duplicate `18-` prefix
- Trigger: `ls docs/v2/` showed BOTH `18-master-alignment-v2-migration-plan.md` AND `18-periscope-l4-glass.md`
- Doctrine implication: numbering convention for `docs/v2/` is "first one wins; conflicts allowed but ugly." Note for future: a `docs/v2/INDEX.md` would surface this.
- Action: our new doc uses `19-` to avoid further collision.

## Datum 4 — Working directory matters for `/autoplan`
- Trigger: we initially invoked `/autoplan` from `OpenClaw/` which is NOT a git repo
- Impact: autoplan's Step 0 (base branch detection) would have failed or fallen back to `main` with no actual git context. Review-log writes would have been orphaned.
- Doctrine implication: §Pipeline entry must require `git rev-parse --show-toplevel` to succeed BEFORE invoking any review skill. Worktrees give you this for free since each worktree IS a git toplevel.

## Datum 5 — Stale `.git/*.lock` files accumulate
- Trigger (earlier in this session, in Perpetua-Tools): dozens of stale `.git/HEAD 2.lock`, `.git/index 9.lock` files from interrupted git operations dating back to April
- Root cause: macOS Finder copying `.git`, or git crashes, or duplicate-file deduplication
- Doctrine implication: §Pre-flight check must include:
  ```bash
  find .git -name "*.lock" -delete
  ```
- Severity: blocks `git checkout`, `git stash`, `git worktree add`. Common gotcha on macOS with shared NAS/Time Machine folders.

## Datum 6 — Untracked `* 2/`, `* 3/` directories from macOS dedup
- Trigger: `git status` showed dozens of `.claude/skills 2/`, `orchestrator/agent_launcher 2.py`, etc.
- Root cause: macOS Finder "Keep Both Files" dedup, often from iCloud sync or duplicated workspaces
- Doctrine implication: per-worktree `.gitignore` should include `*\ 2/`, `*\ 2.*`, `*\ 3/`, `*\ 3.*` patterns. Or run a `scripts/cleanup-macos-dupes.sh` as part of worktree bootstrap.
- This is the most common source of "why is git status so dirty?" on this stack.

## Datum 7 — `.cursor/environment.json` carries port/daemon config
- Trigger: when planning parallel agent dispatch, we noticed `.cursor/environment.json` declares ULTRATHINK_PORT=8001, PORTAL_PORT=8002, ALPHACLAW_PORT=3000 + terminal autostart commands
- Doctrine implication: if 2+ agents share `.cursor/environment.json` (i.e., both running in the same Cursor workspace pointed at sibling worktrees), they'll fight over the same ports.
- Solution sketch: per-worktree port offset (worktree-doctrine = 8101/8102/3100, worktree-feature-X = 8201/8202/3200). Need an `ENV_OFFSET` convention.

---

## Open questions for the brainstorm
1. Naming convention: `~/Documents/oramasys/worktrees/<slug>` (our current pattern) vs `<repo>/.worktrees/<slug>` (in-repo) vs centralized `~/.worktrees/<repo>-<slug>/`?
2. Port allocation: static offsets per worktree (collision risk) or dynamic port discovery on bootstrap?
3. LM Studio GPU contention: serialize via filesystem lock at `~/.openclaw/state/win-gpu.lock` or via PT's existing dispatch queue?
4. CRG graph.db is per-repo, not per-worktree. Two worktrees + parallel `build_or_update_graph_tool` calls = corruption risk. Lock the build?
5. Conductor handles worktree lifecycle when invoked from inside it — what about direct `git worktree add` users? Need a shared cleanup convention.
6. When does an agent get a NEW worktree vs a NEW BRANCH on existing worktree? Decision tree needed.

## Datum 8 — Multi-Windows device pool support is an open TODO
- Surfaced by D4 brainstorm answer
- Current state: PT's backend_resolver reads `WIN_CODER_ENDPOINTS` (comma-separated) from env
- Gap: dispatcher needs to (a) re-read endpoints periodically OR support LAN-discovery push, (b) round-robin across N online devices, (c) only queue when ALL devices busy
- Doctrine implication: §LM Studio coordination must reference this as a future enhancement; current behavior degrades to "single Win device, others ignored" if endpoints aren't all reachable at startup
- Action: spawn separate task in PT to harden dispatcher (out of scope for the doctrine itself)
