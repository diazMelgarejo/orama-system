# 14 — GBrain Checkpoint Poisoning: `rm -rf` of Repo Root

**Affects:** gstack v1.52.2.0, gbrain v0.33.3.0  
**Upstream:** [garrytan/gstack#1802](https://github.com/garrytan/gstack/issues/1802)  
**Severity:** Critical (irreversible filesystem deletion of working repo)  
**Date discovered:** 2026-06-02  

---

## TL;DR

The gbrain autopilot deleted the entire `orama-system` working directory via `rm -rf`. Root cause: a poisoned `~/.gbrain/import-checkpoint.json` (written when an autopilot job was SIGTERM'd mid-sync) had `dir` = the repo root. The next sync's resume path trusted that value without validating it was a gstack staging directory, then called `cleanupStagingDir(repoRoot)` → `rmSync(repoRoot, { recursive: true, force: true })`.

Repo was restored from GitHub. Commits were intact; untracked files would have been lost.

---

## Root Cause

### The failure chain

1. **Autopilot SIGTERM loop.** gbrain autopilot cycle jobs hit the 600-second timeout repeatedly:
   ```
   Job 693 (autopilot-cycle) hit per-job timeout (600000ms), aborting
   [cycle.extract] aborted (SIGTERM)
   ```
   During each interrupted run, gbrain wrote `~/.gbrain/import-checkpoint.json` for the memory-ingest resume feature (added in PR #1611).

2. **Checkpoint poisoned.** One interrupted run left the checkpoint with `dir` = `/Users/.../orama-system` — the **repo root**, not a `~/.gstack/.staging-ingest-<pid>-<ts>/` temp directory.

3. **Resume path trusts checkpoint blindly.** In `gstack-gbrain-sync.ts`, `decideResume()` reads the checkpoint and checks only:
   ```typescript
   existsSync(stagingDir)         // true — it's the real repo
   statSync(stagingDir).isDirectory() // true — it's a directory
   ```
   No ownership validation. Returns `{ kind: "resume", stagingDir: repoRoot }`.

4. **`GSTACK_INGEST_RESUME_DIR` set to repo root.** The orchestrator passes this to `gstack-memory-ingest.ts` as the staging directory.

5. **`finally` block deletes it.** After `gbrain import` runs, the cleanup fires:
   ```typescript
   // gstack-memory-ingest.ts:1713
   cleanupStagingDir(stagingDir);  // → rmSync(repoRoot, { recursive: true, force: true })
   ```

6. **`orama-system` deleted.** Confirmed by `fs_usage` trace: `bun.48174554` called `unlinkat [-2]//Users/.../orama-system` at 09:59:13 on 2026-06-02.

### Why the autopilot kept timing out

The autopilot cycle runs `gbrain import` with transaction-mode Supabase pooler. Each import session embeds ~60k pages and intermittently hits:
```
batch error (100 link rows lost): write CONNECTION_CLOSED aws-1-ap-northeast-1.pooler.supabase.com:5432
```
These connection drops caused import to stall, hitting the 600s ceiling, SIGTERM, checkpoint written.

---

## The Fix (upstream PR needed)

Two-layer defense — see `docs/references/gstack-pr-1802-fix.md` for the full diff.

### Layer 1: `decideResume()` in `gstack-gbrain-sync.ts`

Before returning `{ kind: "resume" }`, validate ownership:

```typescript
const stagingPrefix = resolve(GSTACK_HOME, ".staging-ingest-");
const resolved = (() => { try { return realpathSync(stagingDir); } catch { return null; } })();
if (resolved === null || !resolved.startsWith(stagingPrefix)) {
  console.error(`[sync:memory] checkpoint.dir "${stagingDir}" is not a staging dir; skipping resume.`);
  return { kind: "stale-staging-missing", stagingDir };
}
```

### Layer 2: `cleanupStagingDir()` in `gstack-memory-ingest.ts`

Belt-and-suspenders at the delete site:

```typescript
function cleanupStagingDir(dir: string): void {
  const stagingPrefix = resolve(GSTACK_HOME, ".staging-ingest-");
  let canonDir: string;
  try { canonDir = realpathSync(dir); } catch { return; }  // can't verify = don't delete
  if (!canonDir.startsWith(stagingPrefix)) {
    console.error(`[gbrain] BUG: cleanupStagingDir on non-staging path "${dir}"; refusing.`);
    return;
  }
  try { rmSync(dir, { recursive: true, force: true }); } catch { /* best-effort */ }
}
```

### Status

- Issue #1802 open, no fix merged as of 2026-06-02
- Comment posted confirming our case: https://github.com/garrytan/gstack/issues/1802#issuecomment-4589699900
- **Fix implemented + verified** (32 + 23 tests green) on local branch `fix/1802-staging-ownership-guard` in `~/.claude/skills/gstack`, steelmanned by a 4-model panel (Gemini, Codex, gpt-4o, qwen3.5-27b).
- **Shipped design** (marker + structural + `.git` tripwire, fail-closed): [`reference/gstack-1802-submission-package.md`](../reference/gstack-1802-submission-package.md) — supersedes the v1 two-guard draft.
- **Reusable method** dogfooded into orama: [`reference/multi-channel-steelman.md`](../reference/multi-channel-steelman.md).
- **SUBMITTED 2026-06-02:** gstack PR [#1827](https://github.com/garrytan/gstack/pull/1827) (mitigation) + gbrain issue [#1728](https://github.com/garrytan/gbrain/issues/1728) (prevention); linked on #1802. Fix kept active on this machine's gstack branch.

---

## Mitigations Applied

### 1. Shell guard in `~/.zshrc` (runs on every shell start)

```bash
function _gbrain_check_checkpoint() {
  local f="$HOME/.gbrain/import-checkpoint.json"
  [ -f "$f" ] || return
  local d
  d=$(python3 -c "import json; print(json.load(open('$HOME/.gbrain/import-checkpoint.json')).get('dir',''))" 2>/dev/null)
  if [[ -n "$d" ]] && [[ "$d" != "$HOME/.gstack/.staging-ingest-"* ]]; then
    echo "[safety] gbrain checkpoint.dir=$d is not a staging dir — removing (gstack#1802)" >&2
    rm -f "$f"
  fi
}
_gbrain_check_checkpoint
```

### 2. Manual pre-sync check

Before any `/sync-gbrain` or gbrain autopilot session:
```bash
rm -f ~/.gbrain/import-checkpoint.json
```

### 3. macOS immutability on repo `.git` dirs (optional, strongest guard)

```bash
chflags uchg "/path/to/repo/.git"
# Undo: chflags nouchg "/path/to/repo/.git"
```
A recursive delete against an immutable inode fails outright — this guard is independent of gstack behavior.

---

## Recovery

All commits were on GitHub, so restore is a simple reclone:
```bash
git clone https://github.com/diazMelgarejo/orama-system.git \
  "$OPENCLAW_ROOT/orama-system"
```

Untracked files that hadn't been pushed would be permanently lost. Keep important untracked artifacts in the repo or a separate backup.

---

## Prevention Rules Going Forward

1. **Delete `~/.gbrain/import-checkpoint.json` before any manual `/sync-gbrain` run** — the shell guard handles automated sessions but a manual run from inside a repo directory is still risky until upstream fixes land.

2. **Run `/sync-gbrain` from `~/.openclaw` or a neutral directory**, never from inside the indexed repo. The CWD at SIGTERM time is what gets written into the checkpoint.

3. **Watch for repeated autopilot SIGTERM patterns** in `~/.gbrain/autopilot.err`:
   ```
   Job NNN (autopilot-cycle) hit per-job timeout (600000ms), aborting
   ```
   If this appears more than 2× in a row, the checkpoint is likely poison — delete it.

4. **File upstream bug reports.** The community is `garrytan/gstack` GitHub issues. The fix is a 10-line TypeScript change with a regression test — suitable for a first-time PR.

---

## Reference

- Upstream issue: https://github.com/garrytan/gstack/issues/1802
- Our comment: https://github.com/garrytan/gstack/issues/1802#issuecomment-4589699900
- Full fix + test: [`docs/references/gstack-pr-1802-fix.md`](../references/gstack-pr-1802-fix.md)
- fs_usage trace confirming deletion: `~/Documents/2026-06-01-orama-system-Terminal-Output.txt`
