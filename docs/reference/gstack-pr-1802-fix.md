# PR: Guard `decideResume()` against poisoned checkpoint — fixes #1802

**Target repo:** `garrytan/gstack`  
**Fixes:** issue #1802  
**Confirmed by:** independent user case (same mechanism, same version 1.52.2.0)

---

## What happened (confirmed root cause)

The autopilot ran repeated jobs that were SIGTERM'd on timeout
(logs: "Job 693/724/726 hit per-job timeout, aborting").
One of those interrupted runs left `~/.gbrain/import-checkpoint.json`
with `dir` = `/Users/.../orama-system` — **the repo root, not a
`~/.gstack/.staging-ingest-*` directory**.

The next `gstack-gbrain-sync.ts` run (via autopilot) called
`decideResume()`, which:
1. Read `checkpoint.dir` = repo root
2. `existsSync(stagingDir)` → true
3. `statSync(stagingDir).isDirectory()` → true
4. **Returned `{ kind: "resume", stagingDir: repoRoot }`** — no further validation

`gstack-memory-ingest.ts` set `stagingDir = repoRoot`, ran
`gbrain import`, then the `finally` block called
`cleanupStagingDir(stagingDir)` = `rmSync(repoRoot, { recursive: true, force: true })`.

**The entire repository was deleted from disk.** Commits were preserved
on GitHub; untracked files were lost.

---

## The fix — two-layer defense

### Layer 1: `decideResume()` in `gstack-gbrain-sync.ts`

At line ~172, before returning `{ kind: "resume" }`, add a path
ownership check:

```typescript
export function decideResume(): ResumeVerdict {
  const cp = readGbrainCheckpoint();
  if (!cp || !cp.dir) return { kind: "no-checkpoint" };
  const stagingDir = cp.dir;

  // ── NEW: ownership guard ──────────────────────────────────────
  // Only honor a checkpoint whose dir is provably a gstack-owned
  // staging directory. A poisoned checkpoint (e.g. checkpoint.dir
  // = repo root after a SIGTERM while CWD was the repo) would
  // otherwise cause cleanupStagingDir to rm -rf the entire repo.
  const stagingPrefix = resolve(GSTACK_HOME, ".staging-ingest-");
  const resolved = (() => { try { return realpathSync(stagingDir); } catch { return null; } })();
  const isOwned = resolved !== null && resolved.startsWith(stagingPrefix);
  if (!isOwned) {
    // Log a warning so the user knows we skipped a poisoned checkpoint
    // and will restage from scratch.
    console.error(
      `[sync:memory] checkpoint.dir "${stagingDir}" is not a gstack staging dir ` +
      `(expected prefix: ${stagingPrefix}). Skipping resume to prevent data loss. ` +
      `Delete ~/.gbrain/import-checkpoint.json to suppress this warning.`
    );
    return { kind: "stale-staging-missing", stagingDir };
  }
  // ── END NEW ───────────────────────────────────────────────────

  if (!existsSync(stagingDir)) {
    return { kind: "stale-staging-missing", stagingDir };
  }
  try {
    const st = statSync(stagingDir);
    if (!st.isDirectory()) return { kind: "stale-staging-missing", stagingDir };
  } catch {
    return { kind: "stale-staging-missing", stagingDir };
  }
  return {
    kind: "resume",
    stagingDir,
    processedIndex: cp.processedIndex ?? 0,
    totalFiles: cp.totalFiles ?? 0,
  };
}
```

Add the needed imports at top of the file (if not already present):
```typescript
import { realpathSync } from "fs";
import { resolve } from "path";
```

### Layer 2: `cleanupStagingDir()` in `gstack-memory-ingest.ts`

Fail-closed belt-and-suspenders at the deletion site itself
(line ~1263):

```typescript
function cleanupStagingDir(dir: string): void {
  // ── NEW: delete-site ownership guard ──────────────────────────
  // Even if the call site passes the wrong path, refuse to rm -rf
  // anything that doesn't look like a gstack staging directory.
  // This is the last line of defense before disk data is destroyed.
  const stagingPrefix = resolve(GSTACK_HOME, ".staging-ingest-");
  let canonDir: string;
  try {
    canonDir = realpathSync(dir);
  } catch {
    // Can't resolve = can't confirm ownership = abort.
    console.error(`[gbrain] WARN: cleanupStagingDir: could not resolve "${dir}"; skipping.`);
    return;
  }
  if (!canonDir.startsWith(stagingPrefix)) {
    // BUG GUARD: refuse to delete a directory we don't own.
    // This case should never be reached after the decideResume fix above,
    // but defense-in-depth means we check here too.
    console.error(
      `[gbrain] BUG: cleanupStagingDir called on non-staging path "${dir}" ` +
      `(resolved: "${canonDir}"); refusing rm -rf to prevent data loss.`
    );
    return;
  }
  // ── END NEW ───────────────────────────────────────────────────
  try {
    rmSync(dir, { recursive: true, force: true });
  } catch {
    // best-effort
  }
}
```

---

## Why these two layers

| Layer | What it blocks |
|---|---|
| `decideResume()` | Poisoned checkpoint never becomes `stagingDir` in the first place |
| `cleanupStagingDir()` | Even if a future code path bypasses `decideResume`, the delete site refuses |

The bug is a **trust failure**, not a path resolution accident. The
fix is fail-closed: if we can't prove the path is ours, we refuse.

---

## Regression test to ship with the PR

```typescript
// gstack-gbrain-sync.test.ts (new test)
import { describe, it, expect, beforeEach } from "bun:test";
import { mkdtempSync, mkdirSync, writeFileSync, existsSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import { decideResume, readGbrainCheckpoint } from "../bin/gstack-gbrain-sync.ts";

describe("decideResume: poisoned checkpoint safety", () => {
  let fakeHome: string;
  let fakeGstack: string;
  let fakeGbrain: string;
  let fakeRepo: string;

  beforeEach(() => {
    fakeHome = mkdtempSync(join(tmpdir(), "gstack-test-"));
    fakeGstack = join(fakeHome, ".gstack");
    fakeGbrain = join(fakeHome, ".gbrain");
    fakeRepo   = join(fakeHome, "my-repo");
    mkdirSync(fakeGstack, { recursive: true });
    mkdirSync(fakeGbrain, { recursive: true });
    mkdirSync(join(fakeRepo, ".git"), { recursive: true });
    writeFileSync(join(fakeRepo, "important.py"), "# do not delete\n");
    // Inject env vars for the module
    process.env.GSTACK_HOME = fakeGstack;
    process.env.HOME = fakeHome;
  });

  it("returns stale-staging-missing when checkpoint.dir is repo root", () => {
    // Write poisoned checkpoint pointing at the repo root
    writeFileSync(
      join(fakeGbrain, "import-checkpoint.json"),
      JSON.stringify({ dir: fakeRepo, totalFiles: 10, processedIndex: 3 })
    );
    const verdict = decideResume();
    expect(verdict.kind).toBe("stale-staging-missing");
    // Confirm the repo was NOT deleted
    expect(existsSync(join(fakeRepo, "important.py"))).toBe(true);
    expect(existsSync(join(fakeRepo, ".git"))).toBe(true);
  });

  it("returns stale-staging-missing when checkpoint.dir is /", () => {
    writeFileSync(
      join(fakeGbrain, "import-checkpoint.json"),
      JSON.stringify({ dir: "/" })
    );
    expect(decideResume().kind).toBe("stale-staging-missing");
  });

  it("returns resume when checkpoint.dir is a real staging dir", () => {
    const stagingDir = join(fakeGstack, `.staging-ingest-${process.pid}-12345`);
    mkdirSync(stagingDir, { recursive: true });
    writeFileSync(
      join(fakeGbrain, "import-checkpoint.json"),
      JSON.stringify({ dir: stagingDir, totalFiles: 10, processedIndex: 3 })
    );
    const verdict = decideResume();
    expect(verdict.kind).toBe("resume");
    if (verdict.kind === "resume") {
      expect(verdict.stagingDir).toBe(stagingDir);
    }
  });

  it("returns stale-staging-missing when checkpoint.dir uses .. to escape staging root", () => {
    const stagingDir = join(fakeGstack, `.staging-ingest-123/../../my-repo`);
    mkdirSync(join(fakeGstack, ".staging-ingest-123"), { recursive: true });
    writeFileSync(
      join(fakeGbrain, "import-checkpoint.json"),
      JSON.stringify({ dir: stagingDir })
    );
    expect(decideResume().kind).toBe("stale-staging-missing");
  });
});
```

---

## Immediate mitigation (before upstream fix lands)

1. **Delete the poisoned checkpoint:**
   ```bash
   rm -f ~/.gbrain/import-checkpoint.json
   ```

2. **Check for poisoned checkpoints before every sync:**
   ```bash
   cp_dir=$(python3 -c "import json; d=json.load(open('$HOME/.gbrain/import-checkpoint.json')); print(d.get('dir',''))" 2>/dev/null)
   if [[ -n "$cp_dir" ]] && [[ "$cp_dir" != "$HOME/.gstack/.staging-ingest-"* ]]; then
     echo "POISON: checkpoint.dir=$cp_dir — deleting before it deletes your repo"
     rm -f ~/.gbrain/import-checkpoint.json
   fi
   ```

3. **Add to ~/.zshrc** so it runs before every sync:
   ```bash
   # gbrain checkpoint safety guard (issue garrytan/gstack#1802)
   function gbrain_check_checkpoint() {
     local f="$HOME/.gbrain/import-checkpoint.json"
     [ -f "$f" ] || return
     local d
     d=$(python3 -c "import json; print(json.load(open('$HOME/.gbrain/import-checkpoint.json')).get('dir',''))" 2>/dev/null)
     if [[ -n "$d" ]] && [[ "$d" != "$HOME/.gstack/.staging-ingest-"* ]]; then
       echo "[safety] Removing poisoned gbrain checkpoint (dir=$d)" >&2
       rm -f "$f"
     fi
   }
   gbrain_check_checkpoint
   ```

4. **macOS immutability on critical repos** (strongest guard — doesn't depend on gstack fixing anything):
   ```bash
   for repo in \
     "$OPENCLAW_ROOT/orama-system" \
     "$OPENCLAW_ROOT/perplexity-api/Perpetua-Tools" \
     "$OPENCLAW_ROOT/AlphaClaw"; do
     chflags -R uchg "$repo/.git"
     echo "Protected .git in: $repo"
   done
   # Undo with: chflags -R nouchg <path>
   ```

---

## GitHub issue comment to post on #1802

> **Confirmed same root cause — independent case, v1.52.2.0**
>
> Hit exactly this. The trigger was repeated autopilot SIGTERM timeouts
> (logs: "Job hit per-job timeout, aborting") while gbrain was syncing
> the orama-system repo. One of those interrupted runs left
> `import-checkpoint.json` with `dir` = the repo root. The next
> autopilot run hit the resume path and `rm -rf`'d the entire directory.
>
> Confirmed by `fs_usage` trace: `bun.48174554` called
> `unlinkat [-2]//Users/.../orama-system` at 09:59. Repo was restored
> from GitHub.
>
> The proposed fix in the issue description is exactly right. I've
> drafted a PR with the two-layer guard (decideResume + cleanupStagingDir)
> + regression test. Ready to submit — checking here first for any
> in-progress fix to avoid duplication.

---

*Written June 2026. gstack v1.52.2.0, gbrain v0.33.3.0, macOS darwin 25.5.0*
