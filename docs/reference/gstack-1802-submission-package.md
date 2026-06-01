# gstack #1802 — Submission Package (shipped design)

> Version: 0.9.9.9 · 2026-06-02 · Branch `fix/1802-staging-ownership-guard` (local, verified, 32+23 tests green)
> Supersedes the v1 draft in `gstack-pr-1802-fix.md` (two-guard, name-only). This is the steelmanned v2.

---

## PART A — gstack PR (the mitigation, where the `rm -rf` lives)

**Title:** `fix(sync): fail-closed staging-dir ownership guard — prevent rm -rf of repo (#1802)`
**Base:** `garrytan/gstack:main` ← **Head:** `diazMelgarejo/gstack:fix/1802-staging-ownership-guard`

### Body

> **Fixes #1802.** `/sync-gbrain`'s memory-ingest resume path adopted gbrain's `import-checkpoint.json` `dir` field as the staging directory without proving it was one. A poisoned checkpoint — `dir` = the repo root, written when an autopilot `gbrain import` was SIGTERM'd while CWD was the repo — was adopted on the next run and then recursively deleted by `cleanupStagingDir()`, destroying the user's working tree. (Independent confirmation: `fs_usage` caught `bun … unlinkat …/orama-system`.)
>
> Root cause is a **trust failure, not path math**: the code deleted a path it never proved it owned.
>
> **Design — one predicate, two call sites, fail-closed.** New `lib/staging-guard.ts` exports `checkOwnedStagingDir(dir, gstackHome)`, the single definition of "safe to recurse-delete or resume into." Ownership requires ALL of:
> 1. **Resolvable** — `realpathSync` succeeds (collapses `..`/symlinks first).
> 2. **Structural** — canonical path is a *direct child* of `$GSTACK_HOME` named `.staging-ingest-*`.
> 3. **Not a repo** — no `.git` inside (screaming last-line tripwire).
> 4. **Minted by us** — a `.gstack-staging` marker, written by `makeStagingDir()`.
>
> Wired into both the resume gate (`decideResume`) and the deletion chokepoint (`cleanupStagingDir`, which covers the `finally` block *and* the SIGTERM handler).
>
> **Why the marker (steelman note).** A 4-model review panel split 3-1; the dissent held that the structural check alone suffices and the marker adds a missing-token failure mode. Adopted anyway because that failure mode is **fail-safe**: a missing marker forces an unnecessary re-stage (seconds), never a wrong delete. The marker can cost work but never data — that asymmetry settles it.
>
> **Scope.** This guards gstack's own `rm -rf` boundary. The *inevitable* fix is upstream in gbrain (checkpoint.dir should always be a gbrain-minted staging dir, never CWD) — filed as a companion issue. All four reviewers converged on that split.
>
> **Compatibility.** `decideResume()` gains an optional `gstackHome` param (default `GSTACK_HOME`); the sole caller is unchanged. Test baseline `regression-1611` grows 9 → 32 assertions; `gstack-memory-ingest` stays green (23).

### Files
```
 lib/staging-guard.ts                            |  95 ++++  (new)
 bin/gstack-memory-ingest.ts                     |  14 +    (marker mint + cleanup guard)
 bin/gstack-gbrain-sync.ts                       |  24 +-   (resume guard + injectable home)
 test/regression-1611-gbrain-sync-resume.test.ts | 128 +-   (#1802 poison matrix + unit matrix)
```

### Verification (run before opening PR)
```bash
cd ~/.claude/skills/gstack
bun test test/regression-1611-gbrain-sync-resume.test.ts   # 32 pass
bun test test/gstack-memory-ingest.test.ts                 # 23 pass
```

---

## PART B — gbrain companion issue (the prevention, at the source)

**Repo:** `garrytan/gbrain`
**Title:** `import-checkpoint.json `dir` can be the source repo / CWD — enforce staging-first checkpointing`

### Body

> Spun out of gstack#1802, where gstack's resume path `rm -rf`'d a repo because `import-checkpoint.json`'s `dir` was the repo root.
>
> **Ask:** `gbrain import <dir>` should guarantee that the checkpoint's `dir` is *always* the import target gbrain was given — and gstack always hands it a `~/.gstack/.staging-ingest-*` dir. The poison arose because, on SIGTERM mid-import, the persisted `dir` resolved to CWD (the repo) rather than the import argument.
>
> **Requests:**
> 1. Persist `dir` in the checkpoint as the **absolute, resolved import-target path** captured at import start — never re-derived from CWD on interrupt.
> 2. Consider a checkpoint `schema_version` + a self-describing `owner`/`kind` field so consumers can validate before acting.
> 3. Document the checkpoint contract in `docs/gbrain-sync.md` (what `dir` means, who owns cleanup).
>
> Downstream consumers (gstack) are adding a fail-closed ownership guard regardless (gstack#1802), but the durable fix is here: a checkpoint should only ever name a path gbrain created and owns.

---

## PART C — what shipped vs what's deferred

| | Shipped in this PR | Deferred (noted in PR) |
|---|---|---|
| Trust boundary | ✅ fail-closed guard at delete + resume | |
| Ownership proof | ✅ structural + marker + .git tripwire | |
| Capability object (`StagingDir` handle, resume copies into fresh owned dir) | | ◻️ future hardening (Codex/Gemini idea) |
| Root-cause prevention | | ◻️ gbrain companion issue (Part B) |

Ruthless-refinement call (orama Stage 3): ship the minimal inevitable core (guard + marker + tripwire); the capability refactor is gold-plating for a separate PR.
