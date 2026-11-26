# Plan — Adopt steipete/agent-scripts by pointer, then dedupe

**Status:** pointer plus an opt-in installer on this branch. The installer
clones into `~/.agent-scripts` and points `~/Projects/agent-scripts` at that
clone. This document does not vendor `AGENTS.MD`.
**Date:** 2026-11-14
**Base:** orama-system PR #498 tip after the OpenHands allowlist commit.
This branch was stacked on that tip and must not be folded into PR #498.
**Update 2026-11-26:** the six commits were re-applied on current `main` inside the
consolidated draft PR #531, and the installer clone is now pinned (Phase 4).
**Source note:** operator brief `pete-Steinberger.md` (2026-11-14).
**Upstream inspected:** [steipete/agent-scripts](https://github.com/steipete/agent-scripts)
`main` README and `skills/` listing (54 skill directories) on 2026-11-14.
**Local corpus counted:** `bin/orama-system/skills/` has 47 top-level
directories on this branch. An earlier 65 mixed that tree with nested
`openclaw-skills` cards and harness copies. Perpetua-Tools `.agent/skills`
has 14 directories. Its pointer is a Perpetua-Tools change, not this branch.
**Operator brief (binding for this plan):** summon steipete first, cite the
specific skill or rule, and dedupe the orama and Perpetua corpora in
deference to that prior art. Coopt and extend only where our card owns a
contract upstream does not.

## 1. Decision

Summon [steipete/agent-scripts](https://github.com/steipete/agent-scripts)
first for shared agent rules, guardrails, and portable workflows. Keep
orama-system and Perpetua-Tools canonical wherever they own runtime,
hardware, identity, coordination, or security contracts. Dedupe by
**pointer and retirement**, not by pasting upstream prose into our repos.

A plain `install.sh` does not clone. `--with-agent-scripts` clones
`steipete/agent-scripts` into `~/.agent-scripts` and makes
`~/Projects/agent-scripts` a symlink to that clone.
`platform/windows/install.ps1` is unchanged. A previous local commit on
`main` (`b57021ff`) mixed an installer bootstrap into the Hermes fallback
doc fix. That commit stays off this branch. The opt-in flag stays here and
does not retarget PR #498.

## 2. What upstream actually is

README (`AGENTS.MD`, `skills/`, `scripts/`, `hooks/`):

- Shared hard rules live in `AGENTS.MD`. Downstream repos are told to
  **pointer**, not copy: `READ ~/Projects/agent-scripts/AGENTS.MD BEFORE
  ANYTHING (skip if missing).`
- Skill discovery is `scripts/sync-skills` (Codex whole-root link, Claude
  flat per-skill links). Name collisions resolve agent-scripts first.
- `scripts/validate-skills` checks `skills/*/SKILL.md` front matter.
- Public OpenClaw skills are a **sibling** repo (`../agent-skills`),
  exposed by tracked relative symlinks. Repo-owned skills stay canonical
  in their own repo.

Those priority topics are rules inside `AGENTS.MD`, not skill-folder names.
Quoted from `main` on 2026-11-14. Do not import the surrounding personal
ops (Peter's Claw signature, `steipete` git identity, named Mac hosts,
`clawdbot@gmail.com`, Team-server coordinator).

| Brief phrase | Real upstream text | Cite this, not a copy |
| --- | --- | --- |
| Local archives | Routing: "Private/history: local archives first." PR/CI: "Discover in the local Gitcrawl archive first." | `AGENTS.MD` Routing and PR/CI. Crawler skills: `discrawl`, `slacrawl`, `wacrawl`, `telecrawl`, `notcrawl`. |
| macOS / Swift | "macOS app profile/test: sign local bundle…" Computer use falls back to `$peekaboo`. | Skills `swiftui-performance-audit`, `swiftui-view-refactor`, `swiftui-liquid-glass`, `swift-concurrency-expert`, `xcode-sync`, `mac-maintenance`, `peekaboo`. No orama port. |
| Production guardrails | "Push only when user asks…" "Destructive Git ops need explicit user request." "Team server deployments… require Peter's explicit per-deployment approval." | The rule shape (ask before push, reset, deploy). Our push authority stays our own. |
| Review gates | "Before every commit/land: `$autoreview` until no accepted/actionable finding." "assume generated code may come from weaker AI." | `github-deep-review` plus `$autoreview`. Our `code-review` and identity hook stay. |
| Stop and ask | "Conflict/problem: stop + ask." "Audience/destination unclear: ask." "Device/sensitivity/approval unclear: stop + ask." | `AGENTS.MD` Git and Core. Do not replace GossipBus with a second board. |

## 3. Overlap matrix (name-level, not yet a content merge)

| Upstream skill | Our closest card | Disposition to test |
| --- | --- | --- |
| `github-deep-review`, `github-project-triage`, `github-author-context` | `code-review`, `cursor-pr-body` | Cite upstream for generic review gates. Keep our PR-body and identity-hook rules. |
| `codex-debugging`, `codex-first` | `codex-openclaw-agent`, `codex-mcp-debugging` | Upstream for generic Codex debugging. Ours stay bound to OpenClaw/MCP. |
| `skill-cleaner` | `skillify` | Compare before retiring either. `skillify` owns our authoring contract. |
| `project-structure` | `orama-repo-rules` | Pointer for generic layout. Repo rules stay canonical here. |
| `browser-use` | none with that name (`firecrawl` is adjacent) | Summon upstream for browser workflows. Do not fork `scripts/browser-tools.ts`. |
| `whatsapp` | `whatsapp-qr-gateway` | Gateway stays ours. Chat ops may pointer upstream. |
| `openclaw-relay` | `openclaw-*` (10 cards) | Do not replace our operational cards. Compare relay-only behavior. |
| `maintainer-orchestrator` | `agent-coordination-heartbeat`, `gossip-bus` | GossipBus stays the same-machine bus. Do not import a second board. |
| Swift / Xcode / mac-maintenance cluster (8+ skills) | none | Summon only. No orama port. |

Everything else in the 54 upstream skills (Sonos, Twilio, domain DNS,
release tweets, and similar) is out of scope for dedupe. Agents may still
load them through the upstream mirror when present.

## 4. Phases

### Phase 0 — Operator clone, not an installer

Manual, per machine, skip if missing:

```text
git clone --no-checkout https://github.com/steipete/agent-scripts.git ~/.agent-scripts
git -C ~/.agent-scripts checkout --detach deb19f5896fa652c2731186f5d03bcd0193c123c && \
  mkdir -p ~/Projects && ln -s ~/.agent-scripts ~/Projects/agent-scripts
```

`~/.agent-scripts` is the clone. `~/Projects/agent-scripts` is the symlink,
which is the path upstream `scripts/sync-skills` and the pointer line both
use. Do not run `sync-skills` in Phase 0. It rewrites `~/.codex/skills` and
`~/.claude/skills` and can hide orama skill links already on this Mac.

Run upstream `scripts/sync-skills` only after reading its dry-run behavior.
It rewrites `~/.codex/skills` and `~/.claude/skills`. That can collide with
orama skill symlinks already on this Mac. Phase 0 stops and asks before
the first real sync.

### Phase 1 — Evidence, still no deletes

1. Record upstream `git rev-parse HEAD` and the `AGENTS.MD` headings that
   match local archives, crawlers, risk labels, review gates, and
   stop-and-ask.
2. List every skill root, not a sample: `bin/orama-system/skills/`
   (47 top-level directories), Perpetua-Tools `.agent/skills`,
   `vendor/ecc-tools` skill trees, and the
   OpenClaw overlay directories those trees symlink. One row per directory
   name: summon / keep / shrink. A shared verb is not a same job.
3. For each §3 row, one paragraph with both file paths. No card is retired
   on a name match. Retirement requires the deference test: upstream owns
   the portable workflow, and our card adds no hardware, identity,
   GossipBus, Telos, CIDF, or OSSF rule.

### Phase 2 — Pointer layer

Add a short pointer at the top of orama `AGENTS.md` / `CLAUDE.md` only:

```text
READ ~/Projects/agent-scripts/AGENTS.MD BEFORE ANYTHING (skip if missing).
```

Repo-specific rules stay below that line. Do not vendor `AGENTS.MD`.
Do not add the clone to `install.sh` or `install.ps1` in this phase.

### Phase 3 — Dedupe candidates (batched)

Completed 2026-11-14 as a single batched decision (not one card per PR):

- Retire or shrink a local card when upstream is the same job and our card
  has no hardware, identity, GossipBus, Telos, or CIDF rule.
- Keep a local card when it binds this stack (OSSF, GLM fallback, peer TLS,
  commit identity, coordination board).

**Result: 0 retired, 0 shrunk, 11 kept.**

`bin/orama-system/skills/` has 47 top-level directories. Eleven are kept.
The other 36 top-level directories are summoned. Nested `openclaw-skills`
cards and harness copies under `.agents` and `.claude` are not a second
corpus and are not retired from this count.

`firecrawl` is kept because this stack owns that workflow. Upstream has no
card of that name. The other ten kept cards overlap an upstream portable
workflow and also add a stack rule, so they fail the deference test for
retirement.

11 kept skills: fable5-git-rebase-safety, firecrawl, git-file-deletion-guard,
git-history-surgery, git-pending-push-guard, oramasys-method, security,
shell-hygiene, stacked-pr-naming, using-git-worktrees, whatsapp-qr-gateway.

### Phase 3.x — Ecosystem integration

How steipete/agent-scripts integrates into the orama + Perpetua-Tools + ECC +
gstack + gbrain + agentic-stack ecosystem:

**Pointer-first, not copy-first.** Each repo keeps its stack-specific skills
canonical. steipete/agent-scripts provides shared hard rules (AGENTS.MD) and
portable skills via symlink. Downstream repos use pointer-style AGENTS.MD:

```text
READ ~/Projects/agent-scripts/AGENTS.MD BEFORE ANYTHING (skip if missing).
```

Repo-specific rules stay below that line. Do not vendor AGENTS.MD.

**Repo roles:**

| Repo | Role in ecosystem | steipete integration |
|------|------------------|---------------------|
| orama-system | 47 top-level skills | Pointer added; 11 kept, 36 summoned |
| Perpetua-Tools | .agent/skills (14), GossipBus | Pointer belongs on the PT branch |
| ECC | vendor/ecc-tools, agent-skills sibling | sync-skills, dry-run first |
| gstack | When a checkout is present | Pointer when present |
| gbrain | Separate project | No steipete refs; no integration |
| agentic-stack | When a checkout is present | Pointer when present |

**Sync strategy:** Upstream `scripts/sync-skills` rewrites `~/.codex/skills` and
`~/.claude/skills`. Do not run it blindly — it can collide with orama skill
symlinks already on this Mac. Phase 0 stops and asks before the first real sync.
Run with `--dry-run` first, review, then execute.

**Cross-repo coordination:** GossipBus (orchestrator/gossip_bus.py in PT) remains
the intra-host coordination bus. steipete AGENTS.MD does not replace GossipBus,
OSSF, or the commit-identity hook. Each repo's skills stay canonical in their
own repo; upstream skills are exposed via tracked relative symlinks only.

### Phase 4 — Opt-in installer on this branch

`install.sh --with-agent-scripts`:

- Clone `steipete/agent-scripts` into `~/.agent-scripts`.
- Point `~/Projects/agent-scripts` at that clone with a symlink.
- Skip when git is missing, when `~/.agent-scripts` is not that origin, or
  when `~/Projects/agent-scripts` already exists and is not that symlink.
- Pin the clone to one reviewed upstream commit (`STEIPETE_REF` in `install.sh`,
  `deb19f5896fa`, upstream `main` on 2026-11-23). Clone with `--no-checkout`, then
  `git checkout --detach` the pinned commit, so nothing from the upstream tip lands on
  disk unless the pin checks out. A re-run keeps the pin and never follows the tip.
  Move the pin only on purpose, after reviewing the upstream diff, by editing the id
  or exporting `AGENT_SCRIPTS_REF` for one run. Check the origin URL first. Never
  `--force`.
- Never run `sync-skills` from the installer.
- `install.sh --help` lists the flag.

This stays on `docs/2026-11-14-steipete-agent-scripts-adoption-plan`. It does
not retarget PR #498. `platform/windows/install.ps1` is unchanged.

## 5. Non-goals

- Copying MIT skill bodies into `bin/orama-system/skills/`.
- Replacing GossipBus, OSSF, or the commit-identity hook with upstream hooks.
- Resolving `stash@{0}` on local `main` (periscope thin-wrapper, W&B model
  pin, hardware cache with a workstation path, and the rejected installer
  hunks). Leave that stash for its owner.
- Cleaning untracked `487.tsv`, `488.tsv`, `489.tsv`, `SKILL.md.*.bak`, or
  `__pycache__` on the main checkout. Those were not part of this plan.

## 6. Acceptance

- This branch adds the plan, the pointer lines in `AGENTS.md` and
  `CLAUDE.md`, and the opt-in block in `install.sh`.
- The clone directory is `~/.agent-scripts`. `~/Projects/agent-scripts` is
  the symlink to that clone.
- `platform/windows/install.ps1` has no `steipete/agent-scripts` block.
- PR #498 does not contain this plan.
