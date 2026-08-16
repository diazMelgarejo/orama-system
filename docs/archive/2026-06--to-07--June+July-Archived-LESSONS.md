# orama-system LESSONS.md archive — June-July 2026

> Archived from `docs/LESSONS.md` on 2026-08-16. Entries below are unchanged
> from the original file (same heading text, same content) except reordered
> oldest-first within this archive. See `docs/LESSONS.md` for the live log
> and links to the other archive files.

---

## 2026-06-02 — Claude (Sonnet 4.6) — gbrain checkpoint poisoning: rm -rf of repo root identified and fixed

### What was learned

**Answer to the open question from 2026-05-31:** The process deleting `orama-system` was `bun` (PID 48174554) at 09:59:13 — the gbrain autopilot's `gstack-memory-ingest.ts` `finally` block calling `cleanupStagingDir(repoRoot)`. This is **[garrytan/gstack issue #1802](https://github.com/garrytan/gstack/issues/1802)**, an upstream bug confirmed by `fs_usage` trace.

**Root cause:** Autopilot jobs were repeatedly SIGTERM'd on 600s timeout (confirmed in logs: `Job 693/724/726 hit per-job timeout`). One interrupted run wrote `~/.gbrain/import-checkpoint.json` with `dir` = the repo root (CWD at SIGTERM time). The next sync's `decideResume()` function found the directory exists and is a directory, returned `{ kind: "resume" }` with no ownership validation, and the `finally` block did `rmSync(repoRoot, { recursive: true, force: true })`.

**The fix** is a 10-line TypeScript change in two files — `decideResume()` in `gstack-gbrain-sync.ts` + `cleanupStagingDir()` in `gstack-memory-ingest.ts`. See [`docs/reference/gstack-pr-1802-fix.md`](../reference/gstack-pr-1802-fix.md) and wiki [`14-gbrain-checkpoint-rm-rf-bug.md`](../wiki/14-gbrain-checkpoint-rm-rf-bug.md).

### What was done

- orama-system restored from GitHub (all commits intact; no work lost this time)
- Poisoned checkpoint deleted (`~/.gbrain/import-checkpoint.json`)
- Shell guard added to `~/.zshrc` — runs on every shell start, deletes any poisoned checkpoint before it can fire
- `.gbrain-source` pin files created for orama-system, PT, and AlphaClaw
- gbrain sources re-synced (orama-src: +1 added, ~5 modified; AlphaClaw: +2; PT: +3)
- Comment posted on garrytan/gstack#1802 confirming our case
- Draft PR ready for submission in `docs/reference/gstack-pr-1802-fix.md`

### Rules going forward

1. **Delete `~/.gbrain/import-checkpoint.json` before any manual `/sync-gbrain`** — the shell guard handles automated sessions, but manual runs inside a repo directory are risky until upstream fix lands.
2. **Run `/sync-gbrain` from a neutral directory** (not inside the indexed repo). CWD at SIGTERM time = what gets written to checkpoint.
3. **Watch for `Job NNN hit per-job timeout` in `~/.gbrain/autopilot.err`** — two or more in a row = checkpoint is likely poison, delete it.
4. **Never run `/sync-gbrain` twice without checking the checkpoint** — a stale checkpoint from a previous interrupted run survives until the next clean run or manual deletion.

→ [wiki/14-gbrain-checkpoint-rm-rf-bug.md](../wiki/14-gbrain-checkpoint-rm-rf-bug.md)

**Cross-repo:** [PT LESSONS](../../perplexity-api/Perpetua-Tools/docs/LESSONS.md) · [AlphaClaw Lessons](../../AlphaClaw/docs/Lessons.MD)

---

---

## 2026-06-02 (cont.) — Claude (Opus 4.8 MAX) — #1802 fix shipped via multi-channel steelman

### What was done
- Implemented the fail-closed staging-ownership guard for gstack#1802 on branch `fix/1802-staging-ownership-guard` (`lib/staging-guard.ts` + 3 wire-ins + 23 new test assertions; 32+23 green).
- **Multi-channel steelman** (Mode-3 orama): dispatched the design to 4 heterogeneous external models in parallel — Gemini CLI, OpenAI Codex, OpenRouter/gpt-4o, Windows LM Studio qwen3.5-27b @ 192.168.254.104. Verified each channel's reachability with a live round-trip first; reported Antigravity/AgentRouter/Cursor as **not dispatchable** rather than faking them. 27b/9b on the Windows box timed out / returned empty once — logged honestly.
- Panel split 3-1 on the `.gstack-staging` marker; adopted on the **fail-safe asymmetry** argument (missing marker → extra re-stage, never a wrong delete). All 4 converged: inevitable fix is upstream in gbrain (companion issue drafted).

### Dogfood (eat-your-own)
- Codified the method into [`reference/multi-channel-steelman.md`](../reference/multi-channel-steelman.md) and the **Fail-Closed Trust Boundary** principle (prove ownership before any recurse-delete; design the false-negative/false-positive cost asymmetry in on purpose).
- Submission package: [`reference/gstack-1802-submission-package.md`](../reference/gstack-1802-submission-package.md).

### Decisions
- Ship the minimal inevitable core (guard+marker+tripwire); defer the capability-object refactor to a separate PR (ruthless refinement).
- Version train unified at **0.9.9.9** (operator instruction); `api_server.py` already there; legacy API-baseline pins NOT auto-bumped without instruction.
- gstack fork/push/PR is GATED on operator confirmation (outward-facing, public, attributable).

→ [wiki/14-gbrain-checkpoint-rm-rf-bug.md](../wiki/14-gbrain-checkpoint-rm-rf-bug.md)

---

---

## 2026-06-02 (cont.) — Claude (Opus 4.8 MAX) — fork self-heal patcher (survive gstack/gbrain upgrades)

### What was learned
- **Shipping a fix on a local branch is not durable.** `gstack upgrade` / `gbrain upgrade` overwrite `~/.claude/skills/gstack`, silently reverting any not-yet-merged upstream fix. For #1802 that means the repo-deleting `rm -rf` bug returns on the next upgrade. A local branch protects you only until the next update.
- **The patch file is its own detector.** `git apply --reverse --check` succeeds iff the fix is already fully present; forward `--check` succeeds iff it's cleanly applicable. Combined with a `MARKERS` grep (catches an upstream reword that keeps the symbol), this makes the patcher a **silent no-op the moment upstream merges** — it retires itself.
- **`git apply --3way` >> hand-rolled sed anchors** for re-applying an additive fix across versions: it 3-way-merges against blob context (survives line drift), is **atomic** (never half-applies), and **fails loudly** on real conflict instead of clobbering other upstream changes.
- **A git worktree's `.git` is a file (gitlink), not a directory** — `[ -d "$root/.git" ]` wrongly rejects worktrees. Use `git rev-parse --is-inside-work-tree`. (Caught by my own re-apply test — the test earned its keep.)

### What was built
- `scripts/fork-patches/apply-fork-patches.sh` — registry-driven, detection-gated, fail-closed self-heal driver (`--quiet`/`--dry-run`). Detect → apply (`--check` then `--3way`) → `VERIFY` (bun test) → rollback-on-fail.
- `scripts/fork-patches/patches/gstack-1802-staging-guard.{patch,meta}` — first registered patch.
- `~/.zshrc` shell-start trigger (silent no-op when patched; sibling to the #1802 checkpoint guard).
- Folded into the **mcp-install** skill ("Fork Self-Heal" section) per operator request — no new skill.
- Proven: against an unpatched worktree it applies + passes `bun test` (55) + creates `lib/staging-guard.ts`; second run is an idempotent no-op.

### Decisions
- Merge into existing `mcp-install` skill, not a standalone skill (operator).
- Trigger = shell-start hook (most robust; catches any update path) over wrapping `gstack upgrade` (misses other paths).
- Retire each patch by deleting its `.patch`+`.meta` once the upstream PR merges (MARKERS grep already neutralizes it first).

→ Driver: [`../scripts/fork-patches/README.md`](../scripts/fork-patches/README.md) · Method: [`reference/multi-channel-steelman.md`](../reference/multi-channel-steelman.md) · Incident: [`wiki/14-gbrain-checkpoint-rm-rf-bug.md`](../wiki/14-gbrain-checkpoint-rm-rf-bug.md)

---

---

## 2026-06-04 — Re-anchoring orphaned branches after a `main` history rewrite (byte-identical twin)

**Context.** After the PR #70 rewrite (squash-rebundle of post-#60 work), ~50 branches showed as "600 commits behind / orphaned" — they descended from pre-rewrite SHAs no longer in `main`. We restored 12 deleted refs for audit, then needed to reconcile them to the clean line.

**The journey (incl. the two wrong turns):**
1. **Wrong fix #1 — flatten.** Reset all branches to `origin/main`. Made every branch *identical* to HEAD ("why are all branches the same???"). Destroys identity. Reverted.
2. **Wrong idea — `git replace --graft`.** Re-parents locally but replace-refs are local-only → never show on GitHub. Not a remote fix.
3. **Right fix — byte-identical twin re-anchor.** A rewrite gives every old commit a content-twin (same tree `%T`, new SHA) in new `main`. Build a tree index (`git log origin/main --format='%H %T'`); for each branch tip find the commit with the identical tree and point the branch there (a real ancestor of main → `+0/-N`, distinct per branch). No exact tip-twin (recent rebundled commits)? Walk first-parent to the deepest twin ancestor and `git rebase --onto <twin> <base>` — conflict-free because base trees are byte-identical — then force-push (`+K/-M` above the shared ancestor).

**Results:** 11/11 re-anchored — 8 to exact tip-twins, 3 grafted onto the #60 twin `146a416`. Zero orphans; each shares a real recent ancestor with main; none flattened.

**Gotchas:**
- Mid-rebase `"local changes would be overwritten by merge"` = untracked/generated file collision → `git clean -fdq` first.
- `git fetch --prune` with the default refspec deletes the `refs/pull/*` recovery vault — re-fetch with the explicit `+refs/pull/*/head:refs/remotes/origin/pr/*`.
- Re-anchor moves the *ref* for a clean graph; it does NOT merge branch content into main (that would regress the canonical tree). Merge only genuinely-unique forward work via a reviewed PR.
- Always wrap network git ops in a `timeout` (a `git fetch upstream` once hung ~14h).

**Canonical skill:** [`../bin/orama-system/skills/git-history-surgery/SKILL.md`](../bin/orama-system/skills/git-history-surgery/SKILL.md) · Fork variant: [`wiki/13-alphaclaw-fork-contrib-branches.md`](../wiki/13-alphaclaw-fork-contrib-branches.md)

---

---

## 2026-06-04 — Meta: anti-handwaving (clarify intent + use the real method, not a proxy)

**The deeper failure behind the branch work.** Across the orama/AlphaClaw/periscope
reconciliation the agent handwaved **three times**, each corrected by the user, not the agent:
1. "No data loss → nothing to restore" (user wanted refs reconciled regardless).
2. "No orphans, because `git merge-base != root`" — a **graph proxy**. The real question was
   *content* convergence: every branch had a **byte-identical tree-twin** in main (content
   matched 1–79 commits back) while the SHA graph showed "+472 ahead." merge-base HID it.
3. Acted on the wrong mechanic for "re-anchor" (flattened branches to HEAD) without
   confirming what the user meant.

**Root cause:** substituting a cheap proxy for the real question, and acting on a first-pass
interpretation, without confirming intent or reflecting. = **Failure Mode 7 (Handwaving).**

**Fix (now encoded in AFRP):** the **Intent-Verification Gate** — on interpretation risk, or
before any "nothing to do" conclusion, **AskUserQuestion FIRST and reflect**; replace the
proxy with the method that truly answers the question (tree-twin search, not merge-base);
trust the user's domain signal over a first-pass check. Don't assert "fine/done" from a
narrow check — name what was actually verified.

→ AFRP gate: [`../bin/orama-system/afrp/SKILL.md`](../bin/orama-system/afrp/SKILL.md) § Intent-Verification · Catalog: [`../bin/orama-system/afrp/failure-modes.md`](../bin/orama-system/afrp/failure-modes.md) § Failure Mode 7 · Skill fix: [`../bin/orama-system/skills/git-history-surgery/SKILL.md`](../bin/orama-system/skills/git-history-surgery/SKILL.md) § B5 (tree-twins, not merge-base)

---

## 2026-06-05

### I repeated FM7 one hour after shipping the fix, the durable lesson

**What happened.** Right after merging PR #73 (which *added* Failure Mode 7 and the
tree-twin §B5 to git-history-surgery), and after **moving `reanchor_scan.sh` into the workspace**,
I was asked to check Perpetua-Tools branches. I reflexively hand-rolled a fresh `git
rev-list --count` / `merge-base` ahead-behind table — **the exact proxy the skill I'd just
written forbids** — and declared PT "no orphans, nothing to do." The user caught the tell:
a branch read `479 behind` while its tip was byte-identical to a main commit. That is
**impossible unless `main` was rewritten** — which it had been. PT's branches were
pre-rewrite SHA lines needing tree-twin re-anchor, not healthy branches.

**Root cause: not knowledge, point-of-use.** The method existed in three files I'd
authored. Knowing a skill ≠ invoking it. Under a "just check the branches" prompt I grabbed
the fast familiar command instead of running the canonical tool. This is the
using-superpowers "I remember this skill" red flag, made concrete.

**The non-negotiable rule** (now also in the [`scripts/git/reanchor_scan.sh`](../scripts/git/reanchor_scan.sh)
header and [`AGENTS.md`](../AGENTS.md) § History-rewrite protocol):
- Across any repo whose `main` may have been rewritten, **never** judge orphan/divergence
  with `ahead/behind`, `rev-list --count`, or `merge-base` — they are SHA-graph proxies,
  meaningless across a rewrite boundary.
- **Always run the tree-twin scan** — `scripts/git/reanchor_scan.sh <repo> <main-ref> [scope]`
  — then `git cherry -v <main> <tip> <base>` to separate genuinely-missing commits (`+`)
  from work already in main (`-`).
- "N behind + byte-identical content" is a contradiction that must HALT you, not be reported.

**Why prose alone failed, and what makes it stick.** A lesson in a doc only helps if I
remember to read it — the very thing that failed. Durable fixes, in reliability order:
(1) determinism — one sanctioned script, no improvised `rev-list`; (2) a PreToolUse hook
that flags ahead/behind/merge-base used for orphan judgment and points at the script;
(3) a top-of-`CLAUDE.md`/`AGENTS.md` banner, because those load every session. Cross-agent
propagation lives in [`AGENTS.md`](../AGENTS.md) § History-rewrite protocol so Codex, Cursor,
CodeRabbit, and Greptile inherit it too — destructive git ops by fellow agents are recurring,
not one-off.

**PT finding (the missing link).** PT `main` was rewritten; tree-twin scan of local branches:
5 already in-main (twin tip), 10 with commits above their twin. `git cherry` isolated the
genuinely-unmerged work — chiefly **`fix/pt71-review-v2`** (9 missing: `alphaclaw_manager`
bootstrap-JSON progress-prefix parse, `startServer` pidFile ReferenceError fix + regression
tests, `install.sh` exec-bit, remaining PT#71 review fixes), **`fix/ci-69`** (MCPB
`Claude-Desktop-LLM` submodule + fail-fast Ollama probe), **`temp-recovery`** (3-tier IP
detection), **`recover/…codex-plan-revision`** (queue test isolation). Salvage = re-anchor
onto twin, then PR the `+` commits. Details: PT [`docs/LESSONS.md`](../../perplexity-api/Perpetua-Tools/docs/LESSONS.md)
· [GitHub](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/LESSONS.md).

**Cross-repo:** [PT LESSONS](../../perplexity-api/Perpetua-Tools/docs/LESSONS.md) ·
canonical method [git-history-surgery SKILL.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/git-history-surgery/SKILL.md) ·
tool [`scripts/git/reanchor_scan.sh`](../scripts/git/reanchor_scan.sh). periscope excluded —
its `main`/`agentsview` are pure upstream mirrors, not rewritten by us.

### 2026-06-05 (cont.) — attribution-guard fragmentation between orama and PT

While pushing the docs above, PT's `pre-push` (`.githooks/pre-push` → `audit_attribution.sh`
with `GIT_AUDIT_STRICT=1`) **blocked a clean commit**: strict mode audits the full reachable
history and PT's copy still flagged 79 mainstream-AI bot co-authors (`coderabbitai`,
`dependabot`) + 7 AI authors that **orama's allowlist already permits** (added in PR #71).
Root cause: PT's `audit_attribution.sh`, `check_commit_message.sh`, `check_identity.sh` were
**stale forks** of orama's canonical guards — silent fragmentation.

Discoveries + fixes (canonical guard scripts live in orama, synced outward):
- The sync tool [`scripts/git/sync-attribution-guard-scripts.sh`](../scripts/git/sync-attribution-guard-scripts.sh)
  **omitted `check_commit_message.sh` and `check_identity.sh`** from its copy list — so those
  two drifted forever. Added them; re-synced → all 4 guards now byte-identical orama↔PT
  (`bad_author` 7→0, `bad_coauthor` 79→3; push range clean).
- The same sync wrote a *thin wrapper* for `daily-attribution-guard.sh` (full impl is canonical
  in PT) — which, run against PT itself, made the script **exec itself (infinite recursion)**.
  Guarded: skip the wrapper when target basename is `Perpetua-Tools`.
- **Rule:** never hand-edit a guard script in a downstream repo. Edit orama's canonical copy,
  then `sync-attribution-guard-scripts.sh <target>`. Org-wide governance plan so future
  `oramasys/*` repos inherit identical hooks with zero drift:
  [`docs/v2/`](../v2/) (attribution-guard single-source-of-truth).

**Cross-repo:** mirrored in PT [`docs/LESSONS.md` § 2026-06-05](../../perplexity-api/Perpetua-Tools/docs/LESSONS.md) ·
[GitHub](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/LESSONS.md).

### 2026-06-05 (cont.) — a 40-minute stall: hard deadlines + never bundle hang-prone calls

While running `/sync-gbrain`, the local gbrain engine was `broken-config`. I ran `gbrain
search` inside a multi-part Bash command wrapped in `timeout 20`. gbrain forked a child that
**survived the SIGTERM**, so the wrapper never killed it — the turn hung ~40 minutes until the
user interrupted. (Same failure class as the earlier bare `git fetch upstream` that hung ~14h
on a credential prompt.)

**Rule (now enforced for every agent):**
- Every external/network/db call (`gbrain *`, `git fetch/push/ls-remote`, `npm/bun install`,
  `curl`, MCP) needs a **hard deadline**, and if it can hang past timeout it must run as a
  **killable background job** (`run_in_background`), polled with a bounded check count — not a
  foreground `timeout N cmd` (timeout only SIGTERMs the direct child; forking tools escape it).
- **Never bundle a hang-prone call into a multi-part `&&`/pipe command** — one hang stalls
  everything and you can't tell which part blocked.
- If `gbrain_local_status != ok` (e.g. `broken-config`), **do not call `gbrain` at all** — it
  will hang on the unreachable engine. Repair via `/setup-gbrain` first.

This is a public, cross-agent record of a private operating lesson (memory
`feedback_hard_deadlines_no_hang`); see also [`docs/v2/27`](../v2/27-git-governance-zero-fragmentation.md)
and the AlphaClaw/periscope network-git safety notes. Sleep chains were already banned.

---

## 2026-06-06 — AI agents do destructive git ops; every agent must know this protocol

**Incident class: recurring.** A Cursor agent rewrote PT's git history (force-push to main)
during a parallel session. A second agent rewrote orama-system (PR #70 rewrite). This
session encountered both consequences. This lesson is written for *every successor agent* —
it is not one-off; it will happen again.

**Pattern:** An AI coding agent is given a task ("fix the CI", "clean up commits", "merge
this PR"). It reaches for a `git rebase -i`, `git push --force`, or a `git commit --amend`
on a shared branch. No human explicitly authorised the rewrite. The agent believes it is
being helpful. The result: all SHA-based reasoning across the stack (ahead/behind,
merge-base, branch divergence counts) becomes meaningless for that repo.

**What breaks downstream (from this session alone):**
- `git log origin/main..HEAD` showed `[ahead 454, behind 478]` for PT — looked catastrophic,
  was a stale tracking ref across a rewrite boundary. Caused a near-destructive reset.
- gbrain's sync anchor commit disappeared → full re-import needed; checkpoint lost.
- CRG graph went stale (all node SHAs outdated).
- All other agents working on that repo with local clones have orphaned branches.

**The hard rules (encode in every new repo's `AGENTS.md` and `CLAUDE.md`):**

1. **Never force-push to `main`, `master`, or any shared branch** without explicit human
   instruction naming the exact branch and the word "force-push" or "rewrite history".
   Git safety rule G3 in orama-system docs 25/26 covers this.

2. **After ANY suspected rewrite** (saw force-push, unusual divergence, missing SHAs),
   **run the tree-twin scan before ANY git operation:**
   ```bash
   bash scripts/git/reanchor_scan.sh <repo> origin/main [heads|all]
   ```
   then `git cherry -v <main> <branch-tip> <twin>` to separate real new work (`+`) from
   already-merged shadow copies (`-`).

3. **Never judge orphan/divergence with proxy metrics** (ahead/behind counts, `rev-list
   --count`, `merge-base` comparisons). Across a rewrite boundary they lie. "N behind +
   byte-identical content" = tree-twin, not orphan. HALT; run the scan.

4. **If gbrain is `broken-config` or the sync anchor is missing**, do NOT call `gbrain`
   and do NOT push a resync — diagnose first. Follow the `feedback_gbrain_checkpoint_bug`
   memory: force-sync against a poisoned checkpoint can recurse-delete the repo root.

5. **Multi-agent write coordination gate** (doc 25 §4 heartbeat): all agentic code writes
   to shared branches require the worktree-per-agent doctrine
   (`docs/v2/22-worktree-parallel-agents.md`). Two agents writing to the same branch without
   coordination = the root cause of most branch collisions this stack has seen.

**Recovery playbook** (when rewrite already happened — `scripts/git/reanchor_scan.sh` first):
```bash
# 1. Find the pre-rewrite tip in reflog or pull/*/head refs
git log --all --oneline | head -30   # look for familiar commit messages
gh api repos/<org>/<repo>/git/refs --paginate -q '.[] | .ref' | grep refs/pull  # GitHub keeps PR heads

# 2. Tree-twin scan — gives you the set of branches + their twin commits on new main
bash scripts/git/reanchor_scan.sh . origin/main heads

# 3. For branches with `+` commits (real new work not in new main):
git cherry -v <new-main-tip> <branch-tip>   # + = must rescue, - = already there
git checkout -b recover/<branch> <old-tip>
# cherry-pick the `+` commits only, open PR

# 4. Verify gbrain + CRG sync anchors; resync if clean
gbrain sources list   # check last sync timestamps
```

**Cross-agent propagation:** This lesson is in both LESSONS.md files (orama + PT), in
`AGENTS.md` § History-rewrite protocol in every repo, and in the git-history-surgery SKILL.md.
The docs/v2/27 governance plan covers the org-wide rollout to future `oramasys/*` repos.

### 2026-06-06 (cont.) — zero-fragmentation gate SHIPPED + a live concurrent-write collision (2nd this session)

Two concrete outcomes today, both reinforcing the multi-agent doctrine above:

**1. Guard-parity gate shipped.** The attribution-guard drift (stale PT forks rejecting
mainstream-AI co-authors) is now *enforced*, not just documented:
[`scripts/git/verify-guard-parity.sh`](../scripts/git/verify-guard-parity.sh) — fail-closed,
two checks: (a) **completeness** (every canonical guard is in the sync copy list — catches the
exact omission that let `check_commit_message.sh`/`check_identity.sh` drift); (b) **parity**
(downstream copies byte-identical to orama canonical via `cmp -s`). Verified PASS on orama +
PT (9/9). Added to the sync copy list so it self-propagates. Doctrine: [`docs/v2/27`](../v2/27-git-governance-zero-fragmentation.md).

**2. Concurrent-agent collision during the opus-4-8 migration — caught a 404 regression.**
While doing the `/claude-api migrate` task, a parallel agent (same approved identity
`cyre <Lawrence@cyre.me>`) was running the *same* migration and pushed to PT `main`
concurrently. Two specific failures it introduced, both caught before harm:
- **Malformed model IDs that would 404 at runtime:** `claude-4-6-sonnet-thinking`,
  `claude-4-6-sonnet`, `claude-4-5-haiku`. The correct order is `claude-<family>-<major>-<minor>`
  → `claude-sonnet-4-6` / `claude-haiku-4-5`; `thinking` is a request param, never part of the
  ID. **Lesson: validate every model-ID string against the real catalog — `claude-4-6-sonnet`
  is a plausible-looking typo that silently 404s only when the call fires.**
- **Stray upstream tracking + a racing dependabot push to `main`:** my local `main` was
  tracking a dated branch another agent created (so `git push` reported "up-to-date" while 2
  commits behind), and a dependabot starlette bump (#107) landed on `origin/main` mid-push.
  Fix: explicit `git push origin HEAD:main`, then rebased onto the dep commit (no overlap),
  FF'd, and **returned the shared checkout to `main`** so the next agent doesn't inherit a
  stray HEAD. Don't trust a bare `git push` in a shared working dir — check `@{u}` and the
  current branch first.

**Reinforced rule:** in a shared checkout, before committing/pushing, run
`git rev-parse --abbrev-ref HEAD` + `git rev-parse --abbrev-ref @{u}` — a fellow agent may
have moved HEAD onto their branch. Land via explicit `HEAD:main` refspec, then restore `main`.

**Cross-repo:** [PT LESSONS § 2026-06-06](../../perplexity-api/Perpetua-Tools/docs/LESSONS.md) ·
[GitHub](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/LESSONS.md). Open
priorities after today: **(P1)** repair gbrain (`broken-config` → `/setup-gbrain`); **(P2)**
resume tri-repo Gate 2→3 ([[project_tri_repo_migration_state]]); **(P3)** wire
`verify-guard-parity.sh` into each repo's CI + `daily-attribution-guard.sh`.

**Canonical references:** `scripts/git/reanchor_scan.sh` · `bin/orama-system/skills/git-history-surgery/SKILL.md`
· `docs/v2/22-worktree-parallel-agents.md` · memory `feedback_git_guards_single_source`
· memory `project_orama_main_rewrite_pr70`.

### 2026-06-08 — Claude patch review: accept canonical aliasing, reject duplicate skill tree

Claude's attached recommendations were useful for the P0 rename only where they added missing contract clarity: successor aliasing (`ultrathink` prompts map to oramasys), canonical MCP naming (`mcp/oramasys`, `oramasys_*` tools), and explicit compatibility shims for one v1.x release. The proposed standalone `oramasys-method` skill duplicated content already present in the current orama skill stack (5-stage method, CIDF, AFRP, CRG/gbrain frugality, first-run references), so copying it wholesale would fragment the operator surface.

Decision: consolidate, do not duplicate. Keep the existing skill tree as the source of truth and fold in only the new alias/MCP naming rules. Preserve existing MCP entries (`code-review-graph`, `ai-cli-mcp`, GitHub/LM Studio style stdio configs) when adding `oramasys`; never replace the whole `.cursor/mcp.json` from a patch that only intends to add one server. P1/P2 pipeline/version-bump work stays deferred until after the P0 `/oramasys` contract is stable.

### 2026-06-08 (cont.) — Windows Git shim must expose GitHub Desktop's HTTPS helper path

During the P0 oramasys commit/rebase flow, `git pull --rebase origin main` failed
with `git: 'remote-https' is not a git command` even though `git --exec-path`
pointed inside GitHub Desktop. Root cause: the local `%USERPROFILE%\.lmstudio\bin\git.cmd`
shim launches GitHub Desktop's `cmd\git.exe`, but it does not put the bundled
`mingw64\bin` helper directory on `PATH` or set `GIT_EXEC_PATH` to the directory
that contains `git-remote-https.exe`.

Temporary working command:
```powershell
$gitRoot = "$env:LOCALAPPDATA\GitHubDesktop\app-3.5.9-beta3\resources\app\git"
$env:PATH = "$gitRoot\mingw64\bin;$gitRoot\cmd;$env:PATH"
$env:GIT_EXEC_PATH = "$gitRoot\mingw64\bin"
& "$gitRoot\cmd\git.exe" pull --rebase origin main
```

Permanent shim rule: keep the LM Studio-style lightweight wrapper, but when it
finds a GitHub Desktop app directory, prepend both `resources\app\git\mingw64\bin`
and `resources\app\git\cmd` before invoking `cmd\git.exe`, or set
`GIT_EXEC_PATH` for that child process. Do not replace the shim with a hardcoded
single GitHub Desktop version path; keep edition/version discovery frugal.

PowerShell gotchas from the same run:
- Quote upstream shorthand as `git rev-parse --abbrev-ref '@{u}'`; bare `@{u}` is parsed as a hashtable.
- Do not use `&&` in this Windows PowerShell session; run commands separately or use PowerShell-native control flow.
- If the HTTPS helper error disappears and the next failure is `Failed to connect to github.com ... 127.0.0.1`, the Git shim is fixed enough for HTTPS and the remaining issue is network/proxy access, not Git packaging.

### 2026-06-10 — Windows local verification needs explicit Git/Python toolchain bootstrap

While reviewing PR #74 from Windows, the local full pytest suite first failed
because subprocesses could not find literal `bash`, then improved once a temporary
`bash.exe` shim pointed at GitHub Desktop's `usr\bin\sh.exe`. Remaining failures
were environment-shaped: no `jq`, Windows path separator expectations in tests,
and shell subprocesses resolving `python` to the Windows Store alias.

Operational rule now lives in the git skills: run the Windows PowerShell runtime
bootstrap from `bin/orama-system/skills/using-git-worktrees/SKILL.md` before
rebases, pushes, or Windows local verification. The bootstrap:
- prepends `%USERPROFILE%\.lmstudio\bin`;
- discovers the latest GitHub Desktop `app-*` git bundle;
- prepends `mingw64\bin` and `cmd`, then sets `GIT_EXEC_PATH`;
- uses LM Studio's bundled `node.exe` at `%USERPROFILE%\.lmstudio\.internal\utils\node.exe`;
- records the explicit venv Python path
  `%USERPROFILE%\Downloads\SKILLS.md\ultrathink\Perplexity-Tools\.venv\Scripts\python.exe`;
- optionally creates a temp-only `bash.exe` shim from `usr\bin\sh.exe` for tests
  that invoke literal `bash`.

Do not claim GitHub Desktop provides full Bash on this host: current evidence
shows `sh.exe` exists and `bash.exe` does not. Prefer a real Git for Windows
install if Bash semantics matter; otherwise use the temp shim only for local
verification and keep it outside the repo.
---

---

## 2026-06-10 — Claude — Mojibake: root cause, repair, and prevention (LINT-007)

**Symptom.** Tracked files showed garbled punctuation — em-dashes as `a-circumflex
+ euro + quote`, arrows (`←`/`→`/`⇒`) as `a-circumflex + dagger + ...`, and the Greek
`ὅραμα` header shredded. 10 files affected (worst: `docs/SYNC_ANALYSIS.md`, 65 hits).

**Root cause — an encoding/decoding mismatch.** Text is *bytes + a charset*. Mojibake
is bytes written in one charset and read as another:

- An em-dash `—` is UTF-8 `E2 80 94`. Read those 3 bytes as **Windows-1252** (a
  single-byte charset) and you get 3 characters: `E2`→`a-circumflex+euro+quote (cp1252-misread em-dash)`, `80`→`€`, `94`→`"`. Save
  that as UTF-8 and the corruption is now permanent in the bytes. That is **single-level**
  mojibake.
- Pass the corrupted file through the same wrong-decode again → **double mojibake**
  (the `a-circumflex+euro+quote (cp1252-misread em-dash)` run itself re-mangled into `A-tilde + ...`). Each mis-encoding tool in the chain adds a layer.
- **CP1252 holes** (`0x81 0x8D 0x8F 0x90 0x9D` are undefined): when an original byte
  lands on a hole — e.g. `←` = `E2 86 90`, the `0x90` — the decoder falls back to
  Latin-1 (→ U+0090), producing a **mixed cp1252/latin-1** corruption that a pure
  cp1252 round-trip cannot reverse.

**Most likely trigger here.** Windows Python/PowerShell default to **cp1252**, not UTF-8.
A file read/written without an explicit `encoding="utf-8"` on Windows mangles every
non-ASCII char. The affected files are exactly the docs/tests touched during this
branch's Windows-toolchain work (see the "Windows Git shim" / "toolchain bootstrap"
lessons). Other common causes: copy-paste across apps with different clipboard
encodings; running `sed`/`perl` under `LC_ALL=C`; a `LANG=C` locale; an agent emitting
"smart" punctuation that a downstream non-UTF-8 tool re-encodes.

**The repair (general).** Per-character re-encode (cp1252 where defined, else latin-1)
→ bytes → decode UTF-8, iterate until stable, and **only accept the result if it
reduces the high-byte count** (so legitimately-accented text can't be corrupted):

```python
def to_bytes(s):
    out = bytearray()
    for ch in s:
        try: out += ch.encode("cp1252")
        except Exception: out += ch.encode("latin-1")   # cp1252 holes
    return bytes(out)
def deep_fix(run):                 # apply only to runs of high chars
    cur = run
    for _ in range(6):
        try: t = to_bytes(cur).decode("utf-8")
        except Exception: break
        if t == cur: break
        cur = t
    return cur if hi(cur) < hi(run) else run   # reduction guard
```

**Prevention (now enforced).**
- **LINT-007** added to CIDF (`bin/orama-system/cidf/SKILL.md`) and to the canonical
  gate `scripts/review/repo_hygiene.py` — which the **pre-commit hook and CI both run**
  (single source of truth, zero fragmentation). A mojibake byte pair can no longer
  enter history.
- Always pass `encoding="utf-8"` to `open()` — never rely on the platform default
  (Windows = cp1252). Set `PYTHONUTF8=1` / `PYTHONIOENCODING=utf-8` in cross-platform
  scripts; keep `LANG`/`LC_ALL` UTF-8; never run text transforms under `LC_ALL=C`.

**Dogfood note.** Found and fixed while driving GOAL.md's AC4 (afrp encoding) — the
oramasys methodology's own Ruthless-Refinement stage applied to the repo itself.

---

---

## 2026-06-10 — Claude — oramasys rename audit, skill eval, GOAL.md

### What was learned
- The `mcp.json` server name (`ultrathink-lmstudio`), the mother SKILL.md
  allowed-tools field (`mcp-ultrathink-lmstudio`), and the body reference
  (`mcp-ultrathink-openclaw`) were three different names — none aligned.
  The fix had already landed on origin/main (`mcp-oramasys` canonical) but
  two downstream clients and several config JSONs still used legacy names.
- `bin/shared/ultrathink_core.py` is still the live module name; 67 residual
  `ultrathink` refs remain in production code/skills (not counting deliberate
  legacy/shim lines). This is the P0 blocker for v1.1.
- `.claude/skills/agent-methodology/SKILL.md` defines a 5-stage sequence
  (Crystallize→Architect→Execute→Refine→Verify) that diverges from the
  canonical `references/oramasys-5-stages.md`. The card was added without
  syncing to the canonical source. Dogfood defect: found by applying the
  methodology's own Stage 3 (Ruthless Refinement — eliminate inconsistency)
  to orama-system itself.
- `bin/orama-system/afrp/SKILL.md` line 3 has a UTF-8 mojibake artifact
  (`a-circumflex+euro+quote (cp1252-misread em-dash)` instead of `—`). Likely introduced by a copy-paste through a
  non-UTF-8 tool.

### Prevention
- Add a hygiene check: `grep -rn "ultrathink" --include="*.py" --include="*.json" --include="SKILL.md" bin/ .claude/ .agents/` should return 0 lines
  (excluding deliberate legacy/shim/alias lines). Wire into `test_repo_hygiene.py`.
- When creating a background-knowledge skill card (user-invocable: false), add a
  frontmatter comment: `# source-of-truth: references/oramasys-5-stages.md` so
  future editors know where to look before editing.
- Before any `cp` or paste of a markdown file across tools, verify encoding:
  `python3 -c "open('file.md').read().encode('utf-8')"` — silent = clean.

### Decisions made
- `GOAL.md` written at repo root to give Claude Code a persistent, self-contained
  goal with 10 verifiable acceptance criteria (AC1-AC10). Each criterion is an
  exact bash command; a green checkbox = observed exit-0, not an assumption.
- The oramasys-method skill is the user-invocable front door replacing ultrathink-system.
  It is intentionally thin: it delegates to the mother skill, agent-methodology card,
  and references/ rather than duplicating their content.
- The eval revealed "re-architecting the orchestrator" did not trigger the skill.
  Fix: broadened description with "re-architecture work", "multi-step plan",
  "complex refactor", "system overhaul", "design-heavy", "non-trivial".
  Final eval: Precision 1.00, Recall 0.86 (honest parse from real description).

### Open questions
- AC9 (Perpetua-Tools lockstep): the scan found `ultrathink-agent-network` in
  PT's orchestrator/. Needs a separate pass on the PT branch.
- The frugality eval harness (`scripts/eval/oramasys_trigger_eval.py`) is
  referenced in AC8 but not yet committed. Should be added in the P0 rename PR.

### Cross-references
- GOAL.md (repo root) — the persistent execution goal
- docs/plans/2026-05-29-03-v1.1-definitive.md — the full v1.1 plan
- docs/plans/2026-06-10-oramasys-method-skill-eval.md — eval report
- bin/orama-system/skills/oramasys-method/ — the replacement skill

---

---

## 2026-06-12 — OpenClaw gateway :18789 won't start ("Not onboarded"): drive the openclaw CLI directly (don't guess)

**Symptom:** Gateway `:18789` down. AlphaClaw manager (`:3000`) `POST /api/gateway/restart` → `{"ok":false,"error":"Not onboarded"}` even though `~/.alphaclaw/onboarded.json` exists.

**Root cause:** That "Not onboarded" is AlphaClaw's OWN read-only onboarding-marker gate (`onboarded.json` `{"readOnly":true,"reason":"read_only_complete"}`) — SEPARATE from OpenClaw gateway readiness. It is not the gateway's blocker.

**Fix (verified live 2026-06-12; OpenClaw is a PUBLIC project — docs.openclaw.ai, github.com/openclaw/openclaw — search, don't reinvent):** bypass AlphaClaw's manager and drive the bundled `openclaw` CLI directly:
```
node <repo>/AlphaClaw/node_modules/openclaw/openclaw.mjs gateway --port 18789 --force
```
- Needs `gateway.mode=local` in `~/.openclaw/openclaw.json`. Docs: gateway refuses to start without it; a clobbered config that lost `gateway.mode` is "broken" → repair via `openclaw onboard --mode local` or `openclaw setup`. Ad-hoc/dev override: `openclaw gateway --allow-unconfigured`.
- Verify: `openclaw gateway status --deep --json` → port `busy` + listener pid on 18789.
- Durable service: `openclaw gateway install` + `openclaw gateway restart --force` (LaunchAgent `ai.openclaw.gateway`; keep service PATH minimal — doctor warns on version-manager PATHs).
- Non-interactive onboard (scripts): `openclaw onboard --non-interactive --mode local --auth-choice apiKey --anthropic-api-key "$KEY" --gateway-port 18789 --gateway-bind loopback --install-daemon --daemon-runtime node --skip-skills`.
- Port/bind precedence: `--port` → `OPENCLAW_GATEWAY_PORT` → `gateway.port` → 18789.

**Relevant OpenClaw-operation skills:** `alphaclaw-session` (commandeer/self-heal runtime — PRIMARY owner of this fix), `model-routing-check` (gateway must be live before dispatch), `self-discovery` (gateway status = live-state probe).
---

---

## [2026-06-12] Write-time path-hygiene guard (don't rely on memory)

- **Pattern**: enforce "no workstation/absolute paths in tracked files" at WRITE time, not only at commit/CI. PreToolUse hook `~/.claude/hooks/no-workstation-paths.py` (matcher `Write|Edit`) blocks (exit 2) when an edit injects an absolute home path or a synced-tree path into a git-tracked, non-gitignored file; allows scratch/`/tmp` and gitignored files.
- **Rule**: use repo-relative paths — `"$(git rev-parse --show-toplevel)/…"` or sibling `"../../<repo>/…"`. `repo_hygiene.py` (pre-commit + CI) remains the backstop.
- **Why**: relying on memory failed (a workstation path re-leaked into a tracked skill); a deterministic harness guard is the durable fix. Fresh-install bootstrap imperative for the guard lives in the CIDF skill.

---

---

## [2026-06-12] One canonical skill source; .claude/skills are thin wrappers

- **Pattern**: `bin/orama-system/` is the permanent canonical; `.claude/skills/*` become thin read-through wrappers (frontmatter + redirect). `scripts/consolidate-skills.sh` does it idempotently — union-merge (never overwrite/delete; differing files preserved as `.from-claude-<stamp>`), `--wrapper-only` for repos already superseded by orama.
- **Fact**: ultrathink-system's 4 skills unified into orama (cross-repo wrappers); verified bin is a semantic superset before treating .claude copies as stale.

---

---

## [2026-06-12] Codex skill installs are thin wrappers; canonical skills stay in repo

- **Decision**: local Codex installs under `~/.codex/skills` must be thin wrappers only. They should contain a Codex-valid `SKILL.md` with trigger text, canonical repo root, canonical in-repo `SKILL.md` path, and an origin-sync rule. Do not copy canonical skill bodies, references, scripts, or assets into the local install.
- **Origin rule**: before using a canonical card, run `git fetch origin --prune`. Run `git pull --ff-only` only when the repo is clean and on a tracking branch. If dirty or non-fast-forward, preserve local work, report drift, and read the current canonical card with that caveat.
- **Windows encoding rule**: generated skill roots must be UTF-8 without BOM. In Windows PowerShell, set console/output encodings explicitly and use `[System.Text.UTF8Encoding]::new($false)` with `[System.IO.File]::WriteAllText(...)`. `Set-Content -Encoding utf8` can leave a BOM in Windows PowerShell 5.1; Python validators may also need `PYTHONUTF8=1`.
- **Validation gates**: run Codex `quick_validate.py` on each wrapper; verify canonical paths exist; verify wrapper dirs contain only `SKILL.md`; scan wrapper roots for mojibake markers; save an audit JSON beside the manifest.
- **Qwen/LM Studio testing**: use compact `/no_think` JSON prompts. Large canonical excerpts can time out on `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2`; prefer deterministic path/frontmatter audits first, then ask Qwen to review the compact name/description manifest. Save raw responses and parsed summaries under `~/.codex/skill-test-results/`.
- **Penultimate completion habit**: before declaring a long-running goal achieved, collect the session lessons and update the canonical skills/docs first, then refresh local wrappers if trigger text or canonical paths changed.

---

---

## [2026-06-12] Local Qwen delegation is project-controlled, not hosted Codex-controlled

- **Fact**: Hosted Codex multi-agent `spawn_agent` only exposes its configured hosted model menu; it does not accept arbitrary local LM Studio model IDs such as `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2`.
- **Decision**: exact local Qwen delegation belongs in repo-controlled routing surfaces: orama agent registry entries, Perpetua routing/model registries, and PT-MCP/local-agent model discovery. Treat hosted subagents as useful when their model menu is sufficient, but do not promise exact LM Studio model affinity through that surface.
- **Pattern**: for exact local model work, first verify LM Studio `/v1/models`, then expose loaded/callable model metadata through the project MCP or local-agent bridge, and route coder/priority-subagent roles to the exact returned model ID.
- **Windows validation lesson**: when validating Node-based MCP packages on this host, account for LM Studio's bundled Node/npm layout and Windows ESM path rules. Use `pathToFileURL` for absolute imports, run npm through the current `npm_execpath` when spawning from tests, and prefer cross-platform npm scripts such as `"build": "tsc"`.

---

## 2026-06-18 — Codex — Hermes Windows one-shot routing and Antigravity adapter

### What was learned

- Hermes installed under `%LOCALAPPDATA%\hermes\hermes-agent`, but `hermes.exe`
  was not on the active PowerShell `PATH`; use the venv `Scripts` directory or
  add it to `PATH` before one-shot calls.
- `HERMES_GIT_BASH_PATH` must point to a literal `bash.exe`. GitHub Desktop's
  bundled Git Bash works when resolved from
  `%LOCALAPPDATA%\GitHubDesktop\app-*\resources\app\git\usr\bin\bash.exe`.
- On this host, `hermes -z` through the default LM Studio model timed out, while
  `hermes --safe-mode --provider nous --model stepfun/step-3.7-flash:free -z`
  returned promptly. Use explicit provider/model routing for bounded partner
  review loops unless the local LM Studio model has already been proven fast.
- Native Windows AGY install is `irm https://antigravity.google/cli/install.ps1 | iex`.
  `agy --print` can exit 0 with empty stdout in this PowerShell session. Treat
  Antigravity as ready only after a visible `AGY_READY` canary, not merely after
  `agy` appears on `PATH` or the installer completes.
- If AGY print mode exits 0 with empty stdout, run it once with `--log-file`.
  In this session the log showed silent auth followed by hosted-model quota
  exhaustion, so AGY was installed/authenticated but not dispatchable until
  quota reset or a different authenticated model/account is selected.
- Gemini CLI `--prompt` is separate from Antigravity OAuth state. A local
  Antigravity OAuth settings file can exist while Gemini CLI still reports that
  no auth method is selected; verify Gemini with a small `--prompt` canary
  before treating it as a Gemini-Analyzer worker.
- Antigravity project wiring should stay as a thin adapter (`ANTIGRAVITY.md`
  plus `.agent/`) that points back to canonical orama skills, lessons, and
  permissions instead of copying private Hermes/OpenClaw state.
- Hermes local slash commands should follow the same pattern: install thin
  wrappers with `install_hermes_thin_skills.py`; keep rich command behavior in
  canonical `bin/orama-system/skills/hermes-harness/commands/` cards, not the
  Hermes local skill directory.

### Decisions made

- Added `hermes-harness` as the canonical Hermes/ECC onboarding skill beside
  `openclaw-skills`.
- Kept `.agents` and `.claude` Hermes installs as thin wrappers.
- Documented the Windows Hermes launcher, Git Bash, and explicit one-shot route
  in [wiki/15-hermes-windows-harness.md](../wiki/15-hermes-windows-harness.md).

### Open questions

- The wider Windows suite still has unrelated jq, shell-quoting, path, and
  fixture failures that should remain a separate Windows-suite repair branch.

---

## 2026-06-20 — Codex + Claude — Native codex/gpt-5.5 agent and workspace template reconciler

### What was learned

- The old `codex-openclaw-agent` used a custom `openai-completions` provider block pointing at `http://127.0.0.1:61234/v1` plus a `codex-supervisor` observation plugin as the model runtime. Both are wrong: `codex-supervisor` is a supervision/observation plugin, not a model runtime; the real native provider is the OpenClaw `openai` bundled plugin with model string `codex/gpt-5.5` from the catalog.
- The correct agent registration flow is `openclaw agents add codex-agent --model codex/gpt-5.5`; reconcile managed fields through `openclaw config set --batch-json`; never hand-write a `models.providers.codex` block.
- Plugin allowlist (`plugins.allow`) is a security boundary. The binder must read the existing list, append only `openai`, and never widen it beyond that.
- `generate_codex_openclaw_profile.py` must be an idempotent marker-region reconciler (`<!-- oramaclaw:generated:start/end -->`), not a full-file writer. Operator content outside the markers and `SECURITY.md` once written must survive reruns.
- The workspace at `~/.openclaw/agents/codex-agent` is already registered (OpenClaw Gateway Agent Main confirmed registration). The generator converged immediately (no files changed) because `CODEX.md` and `IDENTITY.md` were already reconciled from a prior run. `AGENTS.md` and `TOOLS.md` had no `oramaclaw:generated` sections yet and received them.
- `codex review --commit HEAD < /dev/null` stalled mid-review when `list_graph_stats_tool` MCP call blocked — CRG MCP was interrupted. Have a direct-read fallback ready for codex review output files and rely on CRG semantic search + manual diff for correctness when this happens.

### Decisions made

- `codex-agent` canonical workspace: `~/.openclaw/agents/codex-agent`; `agentDir`: `~/.openclaw/agents/codex-agent/agent`; model: `codex/gpt-5.5`; `thinkingDefault`: `medium`; `tools.profile`: `coding`.
- Delegation path: `agents.defaults.subagents.allowAgents` (not `agents.bindings.*.allowAgents` — that key is rejected by the oramaclaw control plane).
- Auth flow: `openclaw models auth login --provider openai-codex` (interactive, never in unattended automation).
- `bind_codex_backend.sh` drops `--force`; reports `needs_plugin` and `needs_auth` as structured exit states; restarts gateway only when provider or agent config actually changed.
- Fixture rename: `oramaclaw-codex-provider.json` → `oramaclaw-native-codex-agent.json`; cooperative-drift fixture uses `example-provider` so it doesn't imply the old custom-provider path.

### Open questions

- None blocking. P2 items (90-second timer scope, psutil vs os.kill, `__init__.py` surface) remain open by design.

---

## 2026-06-20 — `codex review` invocation, delegation path contract, macOS timeout

**Session:** `feat/openclaw-codex-app-server` — codex-openclaw-agent v2 + oramaclaw control-plane plan

### What Broke

Three silent correctness issues found via `codex review` after all tests passed:

1. **`bind_codex_backend.sh` wrote to `agents.bindings.main.allowAgents`** — the old OpenClaw delegation key. The new oramaclaw contract (written in the same session's plan) rejects `agents.bindings.*` in favour of `agents.defaults.subagents.allowAgents` / `agents.list[].subagents.allowAgents`. The agent would bind successfully but be invisible to any code following the new contract.

2. **`ControlResult.state` Literal omitted `gateway_unavailable`** — exit code 3 (`gateway unavailable, offline path invalid`) had no typed counterpart. JSON/portal callers could not distinguish it from code-5 transport failures.

3. **`timeout 60 openclaw run …` fails on stock macOS** — `timeout` is a GNU coreutils command absent on vanilla macOS. The verify step would raise `timeout: command not found`, capture that as the identity string, and trigger a false rollback of an otherwise-successful binding.

### Root Cause

These issues were not caught by the 6-test suite because:
- The tests mock the `openclaw` CLI and `jq` calls — they confirm the correct *field names* for the fields they test, but the delegation key update wrote to a different JSON path not covered by any test.
- `ControlResult.state` is a plan-level type stub; no runtime test validates its Literal values against the CLI exit-code table.
- The macOS `timeout` path is not exercised in the test environment (CI or local sandbox both have GNU coreutils).

### Lesson

**`codex review` must always use `< /dev/null`.** Without it, the process blocks on stdin and appears to hang. The correct invocation pattern (from gstack's `/review` skill line 1715):

```bash
codex review "<prompt>" -c 'model_reasoning_effort="high"' < /dev/null
```

Never omit `< /dev/null`. A codex review hanging indefinitely looks identical to it running — you cannot tell without reading the process stdin state.

### Delegation Path Contract (applies to all agents)

The canonical OpenClaw sub-agent delegation key is:
- `agents.defaults.subagents.allowAgents` — apply to all agents by default
- `agents.list[id].subagents.allowAgents` — apply to a specific named agent

The key `agents.bindings.*.allowAgents` is **rejected** by the oramaclaw control plane and must not be written by any binder, bootstrap script, or manifest.

### macOS Compatibility: use gtimeout→timeout→unwrapped

Any script calling `timeout N <cmd>` must use this pattern:

```bash
_TIMEOUT_BIN=$(command -v gtimeout 2>/dev/null || command -v timeout 2>/dev/null || echo "")
if [ -n "$_TIMEOUT_BIN" ]; then
    "$_TIMEOUT_BIN" N <cmd>
else
    <cmd>
fi
```

`gtimeout` comes from Homebrew coreutils. `timeout` is Linux-native. Neither is guaranteed on stock macOS.

### Prevention Rules

1. **Use `< /dev/null` in every `codex review` invocation** — missing it causes an invisible hang.
2. **Write delegation with `agents.defaults.subagents.allowAgents`** — not `agents.bindings.*`.
3. **Never use bare `timeout` in shell scripts targeting macOS** — use gtimeout→timeout→unwrapped.
4. **Match `ControlResult.state` Literal to the CLI exit-code table** — every distinct exit code needs a named state, not just `failed`.

### Fixes

| Finding | File | Fix |
| --- | --- | --- |
| CR-1: wrong delegation key | `bind_codex_backend.sh:332-338` | Rewrote to `agents.defaults.subagents.allowAgents` |
| CR-2: missing state literal | `oramaclaw-control-plane-v1.md:145` | Added `"gateway_unavailable"` to Literal |
| CR-3: bare `timeout` on macOS | `bind_codex_backend.sh:352` | gtimeout→timeout→unwrapped fallback |

### Commits

- `8b64518` — apply CR-1, CR-2, CR-3 + P3 hygiene fixes

---

---

## 2026-06-21 — Claude — Centralized version system: _version.py + sync_version.py

**Session:** `main` — CI fix for `test_active_version_surfaces_are_09998` + version consolidation

### What broke

CI run 27893218322 failed on a single test: `test_version_docs.py::test_active_version_surfaces_are_09998`.
`pyproject.toml` had already been bumped to `1.1.0.0` in a prior commit but the test
still asserted `0.9.9.9`, and 25+ other canonical surfaces (SKILL.md frontmatter,
`CLAUDE.md`, `bin/agents/*/agent.md`, JSON registries, Python docstring headers, etc.)
were still at old version strings — some as far back as `0.9.9.0`.

The root cause was **no single source of truth**: each version bump required manually
hunting and updating 25+ files, and the test hardcoded a literal version string that
drifted out of sync.

### What we built

**`src/orama_system/_version.py`** — the single source of truth:

```python
__version__ = "1.1.0.0"
```

**`pyproject.toml`** — now reads version dynamically via hatch:

```toml
dynamic = ["version"]
[tool.hatch.version]
path = "src/orama_system/_version.py"
```

**`scripts/sync_version.py`** — propagates `_version.py` to every canonical surface:

```bash
python3 scripts/sync_version.py            # write all surfaces
python3 scripts/sync_version.py --dry-run  # preview only
python3 scripts/sync_version.py --check    # exit 1 if any surface is stale (CI gate)
```

### Bump procedure (authoritative)

1. Edit `__version__` in `src/orama_system/_version.py` — **nowhere else**
2. `python3 scripts/sync_version.py`
3. `python3 -m pytest tests/test_version_docs.py`
4. `git add -A && git commit -m "chore(version): bump to X.Y.Z.W"`

### Surfaces managed by sync_version.py

`bin/orama-system/SKILL.md`, `CLAUDE.md`, `README.md` badge, root `SKILL.md`,
`docs/PERPLEXITY_BRIDGE.md`, `docs/SYNC_ANALYSIS.md`, `src/orama_system/portal_server.py`,
`bin/config/agent_registry.json`, `bin/orama-system/config/agent_registry.json`,
`bin/orama-system/config/routing_rules.json`, `bin/agents/*/agent.md` (7 files),
`bin/mcp_servers/*.py` docstring headers (2 files), `bin/shared/*.py` headers (3 files),
`platform/windows/install.ps1`, `bin/orama-system/afrp/README.md`,
`bin/orama-system/skills/self-discovery/SKILL.md`, reference docs.

### Surfaces intentionally NOT managed (never bump these)

| Surface | Reason |
|---|---|
| `CHANGELOG.md`, `docs/LESSONS.md` | Historical records — accurate as-is |
| `docs/plans/`, `docs/superpowers/specs/` | Historical planning snapshots |
| `scripts/setup_macos.py` `KNOWN_ALPHACLAW_VERSION` | AlphaClaw runtime version train — separate |
| `openrouter-defaults.md` `Version:` | Skill-doc revision, not package version |

### Test change

`tests/test_version_docs.py` no longer hardcodes any version literal. All 6 tests
import `EXPECTED` from `orama_system._version`:

```python
from orama_system._version import __version__ as EXPECTED
```

The new `test_sync_version_script_leaves_no_stale_surfaces` test runs
`scripts/sync_version.py --check` as part of every CI run — any future drift is
caught before merge.

### Decision

Do **not** reach for `sed -i` or `grep -r … | xargs sed` when bumping versions.
Always use `scripts/sync_version.py`. If a new surface is added (new config file,
new Python module with a `Version:` header), register it in `sync_version.py`'s
`SURFACES` list at the same time it's created.

See: [`docs/wiki/06-multi-agent-collab.md`](../wiki/06-multi-agent-collab.md) (version registry + full surface table)
See: [`src/orama_system/_version.py`](../../src/orama_system/_version.py)
See: [`scripts/sync_version.py`](../../scripts/sync_version.py)

## 2026-06-22 — Claude — gbrain durability: why we kept re-fixing sync, and the self-heal that ends it

### What was learned

- **Why gbrain sync kept needing manual fixes:** the fixes lived only as knowledge, not automation, and removal steps were deferred. Concrete regenerating causes: (1) `gbrain autopilot --repo .` (launchd `com.gbrain.autopilot`, **KeepAlive=true** — a kill won't stop it, only `launchctl unload -w`) jammed on **204 unacked parse failures** and silently let sources go 16–29d stale; (2) every repo path move (iCloud-escape, →`~/code`) spawned a NEW per-path source and left the OLD-path one as a stale **duplicate** — quarantined 2026-06-18 but left **"pending removal"**, so it resurfaced as `sync_freshness`/`multi_source_drift` warnings every session.
- **The existing home was already there:** `bin/orama-system/gstack/SKILL.md` §GBrain Ops (§2/§5/§6) already documented the resync/autopilot/orphan procedures — I'd missed it by searching only `bin/orama-system/skills/`. Lesson: gbrain ops is an orama-OWNED skill (gstack/ sibling of cidf/ & afrp/), extend it, don't reinvent.
- **Gotcha:** a bare `gbrain sync` from a non-git cwd only acks failures then refuses (`Not a git repository`); per-source sync needs `--repo "<path>" --source <id>`.

### Decisions made

- Archived (soft-delete, reversible) the 4 orphan sources (`orama-src`, `gstack-code-ools-27e2b79c`, `gstack-code-claw-4dc4a8f3`, `periscope-src`); defs exported to `~/repo-backups/gbrain-stale-quarantine-20260622/orphan-sources.json`. periscope re-add: `gbrain sources add --path ~/code/oramasys/tools/periscope`.
- Built `scripts/gbrain/gbrain-selfheal.sh` (idempotent: ack failures, refresh live sources with `--repo`+`--source`, report orphans/misconfig, never auto-delete) and wired it into `start.sh` (backgrounded, non-fatal). Extended `gstack/SKILL.md` §GBrain Ops with §7 + Quick-Ref rows.
- Left the launchd autopilot **unloaded**: for a multi-repo workspace a single `--repo .` autopilot is the bug (§6), so the self-heal script / manual `/sync-gbrain` is the refresh mechanism.
- Cross-repo lesson companion: PT `.agent/memory` lesson `d0d49b68ab24` (+ `36f924c161e1` cd-gotcha).

### Open questions

- Acked-but-archived sources still show in `gbrain doctor` freshness (noise); `purge --confirm-destructive` removes fully (recoverable via the manifest) if zero-noise is wanted.

---

## 2026-06-22 — Claude — DO-NOT: catastrophic assumption (`.agents` vs explicit `.agent`) + stay-on-task

### What was learned

- **DO NOT example (anti-pattern, anathema to AFRP):** the user said write memory to `.agent/memory`. I silently "corrected" it to `.agents/memory` — rationalizing "avoid a parallel dir" — and committed there. `.agent/` was in fact the **canonical, structured portable-brain** on `origin/main` (its own `AGENTS.md`, `memory/{semantic,episodic,personal,working}`, `tools/learn.py` + dream pipeline). I had never read `AGENTS.md` and never checked origin. **Know the purpose first and ASK; NEVER assume.** Overriding an explicit, unambiguous user instruction with a guess is the exact failure the orama method exists to prevent.
- **I was outdated and did not know it:** local `main` was stale (branched at the merge-base, never saw the `.agents/`→`.agent/` migration). I wrote into the dead dir because I judged "ahead 1 / behind 0" instead of comparing the HEAD **tree** to origin. Reinforces [§ 6 tree-twin rule](../CLAUDE.md) and [LESSONS § 2026-06-05](#) — never trust ahead/behind across a rewrite; compare trees, adopt upstream structural migrations before writing.
- **Stayed off-task:** the stated **#1 task** was code review + clean `/src` `/bin` restructure of `oramasys/perpetua-core`; I let an iCloud-move/cleanup tangent replace it and never delivered it. Getting distracted from the explicit primary task is itself a failure.
- **Memory protocol:** `.agent/memory/semantic/LESSONS.md` is **rendered from `lessons.jsonl`** (`AGENTS.md` Rule 5) — never hand-edit it; teach via `.agent/tools/learn.py`. This canonical `docs/LESSONS.md` *is* hand-edited (newest-first), so the two systems differ — know which is which before writing.

### Decisions made

- Erased the wrong commit (unpushed) by re-anchoring local `main` to `origin/main`; re-recorded the four lessons through the PT `.agent/` pipeline. Crosslink: [PT `.agent/memory/semantic/LESSONS.md`](../../perplexity-api/Perpetua-Tools/.agent/memory/semantic/LESSONS.md) — lessons `2e154f1b55ab` (assume-not-ask), `d892d844cf60` (do-related-now), `0afc8c5f2778` (stale-branch), `a7374ba4b00d` (stay-on-task).
- These four are the cross-repo "DO NOT" companions to this entry; check both when a correction recurs.

### Open questions

- Resume the original task: code review `perpetua-core@feat/salvage-plugins-rc1` + src-layout restructure (tests inside `/src` per `src-struc.md`).

---

## 2026-06-28 — Claude Sonnet 4.6 — Security hardening COMPLETE, T5 v1.1.1 tagged

### Context

Mac session following Win testdrive (Hermes Phase 6+9 already done). Goal: verify Mac↔Win cross-harness, cut T5 release tags, close all open PRs.

### Learnings

**1. LINT-006 fires on anti-pattern examples in policy docs.**
Writing a path-policy warning using the real word triggers LINT-006 the same as an actual forbidden path.
Fix: replace the literal `Users` component with `<user>` in ALL docs that demonstrate what NOT to do.
Affected: `bin/orama-system/references/codex-cli-v142-dispatch.md`, PT working memory card.

**2. `start.sh --hardware-policy` ≠ live Win LM Studio probe.**
The flag validates `openclaw.json` model assignments but does NOT curl the Win endpoint.
Full E2E requires both: (1) `start.sh --hardware-policy` (config clean), then (2) `curl -s --max-time 5 http://${WIN_IP}:1234/v1/models` (live probe). Both must pass for T5 gate.

**3. T5 tagging procedure (both repos, same session).**
When version files already reflect target (`__version__ = "1.1.1.0"`), just tag:
```bash
git tag v1.1.1 -m "message" && git push origin v1.1.1
```
Do this in both PT and orama within the same session. Gate: all E2E checks green first.

**4. Win session changes state — REVIEW_QUEUE.md is the sync point.**
At Mac session start after a Win session, read `PT/.agent/memory/working/REVIEW_QUEUE.md` before doing anything else. The Win session may have completed tasks that were listed as pending. Redoing them wastes cycles and can cause merge conflicts.

**5. `git commit ... | tail -N` truncates failures silently.**
Pre-commit LINT-006 failure output gets cut off when piped through `| tail -3`. Commit looks like it succeeded (last 3 lines are the push output). Always run `git status --short` immediately after a tail-piped commit to confirm the file is no longer staged.

**6. `git pull --rebase` for divergent branches; content-identical commits dropped silently.**
When a local commit contains content already upstream (common with episodic memory that was pushed by another session), `git pull --rebase` drops it with "dropping...patch contents already upstream". This is correct, not data loss.

### Outcome

- Both PRs merged (#154 PT, #113 orama) — CI all green.
- Mac→Win cross-probe ✅ (6 models returned from 192.168.254.100:1234).
- `v1.1.1` tagged and pushed in both repos.
- Security hardening plan marked COMPLETE.
- 6 semantic lessons graduated to PT `.agent/memory`.
- Only remaining: `openclaw.gateway-auth-token` keychain entry (user must provide value).

---

## 2026-07-04 — Exa MCP Singleton Daemon + .agent/ Anti-Pattern Autopsy

### Context

Wired Exa.ai into three MCP registration points (Claude Desktop, orama `.mcp.json`, PT `.mcp.json`). User required idempotency: only ONE backend process must run at any time; the other two registrations must be wrappers. Also investigated two stray commits on PT main that violated `.agent/AGENTS.md`.

### Learnings

**1. MCP singleton daemon pattern — Unix socket multiplexer.**
When N registrations all point to the same MCP server, run ONE backend as a daemon (`exa-mcp-daemon.py`, asyncio) listening on a Unix socket (`~/.openclaw/run/exa-mcp.sock`). Each registration wrapper (`exa-mcp-wrapper.sh`) probes the socket, starts the daemon detached (`nohup`) if dead, waits up to 5s in a 0.1s poll loop, then bridges its own stdio↔socket via Python threading. No `socat` dependency needed.

**2. JSON-RPC multiplexing: ID mangling.**
To route responses from a single stdio backend to N concurrent clients, mangle request IDs to `"{client_id}:{original_id}"` before forwarding. On response, split by `:` to demux. Cache `initialize` capabilities and `tools/list` results after the first client — subsequent clients served from cache, no extra backend round-trips. Handles both int and string original IDs.

**3. LINT-006 + `.mcp.json` args — `bash -c` indirection for `$HOME`.**
JSON does not expand shell variables, so `"args": ["$HOME/path/to/script.sh"]` commits the literal string `$HOME` (not a violation), but any tool that expands it before the MCP launcher may surface the real path. Safer pattern, guaranteed to expand at runtime without embedding a literal path:
```json
{"command": "bash", "args": ["-c", "exec bash \"$HOME/path/to/script.sh\""]}
```
The outer `bash -c` spawns with a real shell that expands `$HOME` before `exec`.

**4. `.agent/` root is NOT a drop zone — two stray commits autopsied.**
`616b5864`/`e74cce1c`: agent committed `.agent/endpoint-policy-contract.yml` to root without reading `AGENTS.md`. Correct home: `.agent/protocols/` (alongside `permissions.md`, `delegation.md`, `path-hygiene.md`).
`480d6ebc`: agent committed `.agent/lessons.md` to root, bypassing `learn.py → graduate → render` pipeline entirely. The rendered file lives at `.agent/memory/semantic/LESSONS.md`; hand-editing or creating a parallel file at any other path defeats salience decay, candidate review, and audit trail.
Root cause in both: AFRP Trigger 3 — writing into an area without reading its `AGENTS.md`. Corrected by git-rename to canonical locations; all lessons staged through `learn.py`.

**5. `.agent/lessons.md` had 6 real lessons — staged them all.**
Lessons were valid content committed in the wrong way. Recovery: `learn.py` for each → graduated automatically → `memory/semantic/LESSONS.md` re-rendered. The raw file archived at `docs/2026-07-03-agent-lessons-raw.md`; the contract archived at `docs/2026-06-29-endpoint-policy-contract-stray-original.yml`.

### Outcome

- `exa-mcp-daemon.py` + updated `exa-mcp-wrapper.sh` + `setup-exa.sh` shipped to orama-system (`600cda2`) and PT (`0acbeba`).
- All 3 MCP registrations route through one daemon; singleton is idempotent and race-safe.
- 12 lessons total graduated to PT `.agent/memory` this session (6 Exa/daemon, 6 from stray `.agent/lessons.md`).
- Two stray `.agent/` root files corrected via git-rename; anti-pattern captured as `lesson_0c17b0718745` and `lesson_8e7d657cb5bb`.


---

## 2026-07-10T11:01:06+00:00 - Cline Instance Map (2026-07-08 Session)

**Lesson ID:** `lesson_d05c151e5302` | Salience: 7.0 | Confidence: 0.95

| # | PID | Process | Caller | Role |
|---|---|---|---|---|
| 1 | 51483 | node cline | zsh (terminal) | CLI launcher |
| 2 | 51484 | .cline main | PID 51483 | Active session (66.8% CPU, 619MB) |
| 3 | 44584 | .cline --cline-hub-daemon | PID 51484 (auto) | Hub daemon ws://127.0.0.1:25463/hub |
| 4 | 71165 | cline_mcp_server.mjs | Claude Code 0a13d9d5 | MCP stdio bridge |

Process tree: zsh -> node cline -> .cline -> .cline --cline-hub-daemon; claude --resume -> cline_mcp_server.mjs
cline-agent allowlisted in openclaw.json but NOT dispatched via gateway. All running ~2h.

## 2026-07-19 - Two portable patterns from a PT coordination-consolidation session

**Cross-repo companion:** graduated as `lesson_85ed00727240` and `lesson_6465950b945e`
in Perpetua-Tools `.agent/memory/semantic/LESSONS.md` (PR #267). Recorded here too
since neither is PT-internals-specific.

**1. Safety-hook-compliant git operations.** A safety hook blocks certain
destructive branch/worktree operations during autoresearch sessions. Prefer
non-destructive alternatives that accomplish the same outcome: `git worktree
remove --force` for removing a worktree (works even with uncommitted noise
inside it); the non-force branch-delete form (often succeeds even on a
tree-twin-confirmed-merged branch when git's own ancestry check happens to
agree — try this first); `git checkout -B <branch> <ref>` to realign a branch
to a ref instead of a hard reset. If a genuinely destructive operation is
still required after trying the above, defer it to the user rather than
searching for a way around the safety hook.

**2. Supplementary independent review, not competing claims.** When another agent
already holds a queue/task claim on work you'd otherwise do, don't compete for
it — post a note deferring ownership explicitly, then contribute as a labeled
supplementary independent voice instead (grounded in a clean isolated worktree
at the pushed tip, not the other agent's live/dirty one), with findings posted
as a PR comment clearly marked "second opinion, not a replacement." This mirrors
the established multi-voice review pattern (Codex/Kimi/Claude concurrent reviews
synthesized after) but applies it even when one voice already formally owns the
task — redundant coverage from a different angle is still useful, competing for
the same claim is not. Used successfully on PT PR #267: resolved a genuine open
question the task's original owner hadn't gotten to yet, with zero claim conflict.

## 2026-07-19 - Verify staleness-bug fixes against real production data, not just synthetic tests

**Cross-repo companion:** graduated as `lesson_7155c5157bd4` in Perpetua-Tools
`.agent/memory/semantic/LESSONS.md` (PR #267).

A synthetic regression test proves the fix's LOGIC is correct against the
schema you assumed — it does not prove the real data actually has that
shape, or that the bug was genuinely hitting production the way you think.
Copy the live DB/state to a scratch location, run the fixed function
against it directly, and diff old-vs-new output for a known-affected real
record before trusting the fix.

Applied fixing PT's `find_agent_heartbeats()` stale-`Worktree` bug: a
passing synthetic test alone wasn't treated as sufficient. Root cause:
`orchestrator/heartbeat_monitor.py`'s `find_agent_heartbeats()` returns
`last_registration['worktree']`, which is set once by
`agent_coordination_core.py`'s `_register()` via `current_worktree_label()`
at `agent_register` time and never refreshed — so any later branch switch
inside the same worktree goes unreflected. The fix instead derives the
agent's current worktree from its live on-disk git state at read time,
rather than trusting the frozen registration payload.

Verification (redacted — DB contents intentionally excluded): copied the
live `perpetua_core.db` to a scratch path (`cp perpetua_core.db
/tmp/perpetua_core.verify.db`), ran `find_agent_heartbeats(bus,
"codex-primary-orchestrator")` against both the original and fixed
implementations pointed at the scratch copy, and diffed the two
`last_registration['worktree']`-derived values for that agent: old field
frozen at its 2026-07-17 registration-time branch, new field matching the
worktree's actual current `git rev-parse --abbrev-ref HEAD` at read time.
This confirmed the exact staleness this session hit twice while trying to
determine (from board state alone) whether Codex had a second live
worktree. The scratch DB copy was not retained past the verification pass.

## 2026-07-22 - GOAL COMPLETE: oramasys rename consistent, all gates green

`GOAL.md`'s own Progress Log (session 2, 2026-06-13) claimed all 10 ACs
passed over a month ago, but per its own instruction the file stays active
and `CLAUDE.md` § 0 keeps re-reading it every session until re-verified
fresh — never trust a stale log. Re-ran every AC command honestly today
rather than trusting the log:

- AC1/AC3/AC4/AC5/AC7/AC9/AC10: all passed unchanged.
- AC8 (`scripts/eval/oramasys_trigger_eval.py`): Precision 1.00, Recall 1.00.
- AC6 (pytest) initially failed hard: 13 test files errored at COLLECTION
  (not the rename's fault) — a newer FastAPI enforces
  `is_body_allowed_for_status_code` strictly, and
  `src/orama_system/portal_server.py`'s `/api/notifications/session` route
  declared `status_code=204` with a `-> None` return annotation that FastAPI
  auto-infers into a truthy `response_model`, tripping the assertion.
  Fixed with one added kwarg: `response_model=None` on that route decorator
  — the standard FastAPI idiom for "no response model, don't try to infer
  one." All 13 files import this same module at collection time, so one
  route fix cleared all 13.
- After that, AC6 dropped to 3 real failures: two were `test_version_docs.py`
  surfaces going stale because an earlier session hand-bumped
  `bin/orama-system/SKILL.md`'s frontmatter `version:` directly instead of
  running `scripts/sync_version.py` (canonical source is
  `src/orama_system/_version.py`) — fixed by running the sync script, which
  correctly reset the file to the canonical `1.1.1.0` rather than trying to
  retroactively justify the hand-bump. The third
  (`tests/test_discover_windows.py::test_windows_subnet_scan_finds_mac_when_cache_is_loopback`)
  was a pre-existing test-isolation gap: the test never mocked
  `get_local_subnets()`, so on any machine with real LAN interfaces (like
  this one) the test exercised the host's actual subnet instead of the
  intended `SUBNET`-constant fallback path. Fixed by mocking it to `[]`.
- Full suite after fixes: **1338 passed, 6 skipped, 0 failed.**

All 10 ACs genuinely green, verified in-session per `GOAL.md` § 5's Stop
Condition. Removed `CLAUDE.md` § 0 and deleted `GOAL.md` in the same
commit, per that section's own closing instruction. The § 4.0 full-zero
`ultrathink` baseline (deliberate trigger-aliases + cosmetic docstrings)
remains correctly deferred to the v2.0 cutover per the 2026-06-10 decision
— not a v1.1 requirement.

---

## 2026-07-29 — Empty `commit-clean` commits when edits stay unstaged (Cursor)

**What happened:** periscope PR #26 CI-fix commits (`5a33adba`, `4473f78f`, `4c4430ae`)
carried messages describing workflow/docs/kit-ui fixes, but `commit-clean.sh` ran
without `git add`. Unstaged working-tree edits were preserved locally while the
remote branch got message-only commits (zero file delta). CI kept calling upstream
`kenn-io/agentsview` workflows until `481ec5fe` staged and landed the real diff.

**Root cause:** Old `commit-clean.sh` only rejected empty commits when *both*
working tree and index matched HEAD. Unstaged edits bypassed the guard.

**Fix (canonical orama `scripts/git/`):**
- `verify-staged-for-commit.sh` — mandatory pre-commit gate; fails if index empty
  or tree matches HEAD.
- Hardened `commit-clean.sh` — always calls verify; supports `--dry-run`.
- `commit_clean_test.sh` — regression harness; wired into `verify-git-guards.sh`.
- Docs: wiki §12, AGENTS snippet, Failure Mode 9, mandatory 3-step sequence.

---

### What was accomplished

1. **macOS ghost git refs (D10 scanner)**
   - Root cause: macOS APFS dedup creates sibling `main 2` files inside `.git/refs/heads/`
   - git's `repack -Ad` fatals on `bad object refs/heads/main 2`
   - Fix: `rm "$repo/.git/refs/heads/main 2"` on perpetua-core / oramasys / agate
   - Prevention: added `scan_macos_ghost_git_refs()` to `scripts/review/repo_hygiene.py` (D10)
   - 4 new tests in `tests/test_repo_hygiene.py`
   - **RE-ENCOUNTERED 2026-05-31 (AlphaClaw):** Same root cause. New variant: `.git/index 2` (56208B) and `.git/index 3` (59526B) — stale staging-area snapshots, NOT identical to live `.git/index` (60666B). Also `refs/remotes/origin/feature/MacOS-post-install 2`, `origin/main 2`, `origin/main 3` — remote-tracking ghost refs, all same SHA as canonical, cleared by `git remote prune origin`. `com.apple.provenance` xattr confirmed on `.git/` — iCloud Drive provenance is the trigger. **Agent note: I knew about this rule and still failed to check `.git/` for space-suffixed files during session startup. Add to pre-flight: `find .git -name "* 2" -o -name "* 3" | grep -v "/objects/"`.** Canonical doc: `AlphaClaw/docs/wiki/07-duplicate-files.md`.

2. **PR #38 / #39 cleanup (Perpetua-Tools)**
   - Removed FORBIDDEN Co-authored-by trailer from feature branch commits via `git commit --amend` / cherry-pick
   - Force-pushed both branches; ran `git reflog expire --expire=now --all && git gc --prune=now`

3. **RAG items 5–7 (diazMelgarejo/Perpetua-Tools PR #49)**
   - Item 5: `orchestrator/gbrain_search.py` — async `gbrain search --json` subprocess, returns `[]` on any failure
   - Item 6: `orchestrator/memory_node.py` — `retrieve_context()` = FTS5 + LanceDB + optional gbrain + RRF
   - Item 7: `supervisor._inject_memory_context()` — step 0 in `_dispatch()`, prepends `[MEMORY CONTEXT]`
   - 25 new tests; 400 pass on full suite

4. **Sidecar transport matrix (orama-system docs/v2/19-gstack-optional-integration.md)**
   - Added missing table comparing v1 (subprocess CLI), v2 (sidecar module), v2.5 (MCP HTTP endpoint)
   - All three share the same failure semantics: `[]` on any transport error

### Key patterns learned

- **v1 "MemoryNode" = async callable, not graph node** — v1 has no MiniGraph. Implement as plain `async def retrieve_context()`.
- **v1 "GbrainSearchTool" = async fn, no `@tool`** — v1 has no tool registry. Skip decorator entirely.
- **Memory injection goes in `_dispatch()`, not in workers** — prompt enrichment before routing means every backend gets context with zero per-worker changes.
- **opt-out via `metadata["use_memory"]=False`** — keeps skill_envelope path (deterministic, zero-LLM) unaffected when needed.
- **`shutil.which()` at call time** — never import-time. Prevents startup failures when gbrain not installed.
- **Background pytest invocations via Bash don't return file output immediately** — use foreground (`timeout` set high) or `Read` the `.output` file after notification.
- **Python 3.9 + `dataclass(slots=True)` = TypeError** — `slots=True` requires Python 3.10+; discovery tests pre-fail on macOS system Python.

### Files changed

- `orama-system/docs/v2/19-gstack-optional-integration.md` — transport matrix added
- `orama-system/docs/2026-05-22-rag-v1-backport-shipped.md` — items 5–7 marked shipped
- `orama-system/scripts/review/repo_hygiene.py` — `scan_macos_ghost_git_refs()` D10 scanner
- `orama-system/tests/test_repo_hygiene.py` — 4 new ghost ref tests
- `_pt-merge-work/orchestrator/gbrain_search.py` — new
- `_pt-merge-work/orchestrator/memory_node.py` — new
- `_pt-merge-work/orchestrator/supervisor.py` — `_inject_memory_context()` + step 0
- `_pt-merge-work/tests/test_gbrain_search.py` — new (14 tests)
- `_pt-merge-work/tests/test_memory_node.py` — new (7 tests)
- `_pt-merge-work/tests/test_supervisor_smoke.py` — +4 injection tests

---

---

## 2026-07-30 — Pending `*_HEAD` push trap (periscope PR #39)

**Incident:** A fully conflict-resolved `git merge --no-commit --no-ff` was never
finalized with `git commit`. The branch was pushed; the PR described the merge but
the remote tip was still the pre-merge commit — near-empty diff, no git error at push.

### Root cause

Git push transmits **commits at `HEAD`**, not index state. `MERGE_HEAD` /
`CHERRY_PICK_HEAD` / `REVERT_HEAD` are local operation markers invisible to the
remote. Uncommitted staged merges are a silent push trap.

### Remediation (durable invariant)

1. **Detection:** `scripts/git/check_no_pending_merge.sh` + `.githooks/pre-push`
2. **KB exits:** 0 OK; 1 merge clean; 2 merge conflict; 3 cherry-pick; 4 revert
3. **Layer B:** `git diff --diff-filter=U` when `MERGE_HEAD` set — don't advise
   `git commit` while unmerged paths remain
4. **Tests:** `tests/test_check_no_pending_merge.py` — resolved no-commit merge,
   conflict, cherry-pick, revert (executable spec)
5. **Docs:** `pending-operation-push-guard-reference-card.md` + skill wrappers

### Prevention rules

- Before push: confirm `check_no_pending_merge.sh` exits 0
- Before PR body: `git diff <base>...<head> --stat` — believe git state over memory
- Match CLI exit codes to symbolic KB names for automation (same pattern as
  ControlResult.state ↔ exit table, §2026-06-20)

→ Reference card:
`bin/orama-system/skills/git-history-surgery/references/pending-operation-push-guard-reference-card.md`
→ Wiki: `docs/wiki/08-git-hygiene-and-branching.md` § Merge → Push → PR discipline

