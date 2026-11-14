# Plan — Adopt steipete/agent-scripts by pointer, then dedupe

**Status:** plan only. No installer, clone, or symlink is added by this
document.
**Date:** 2026-11-14
**Base:** orama-system PR #498 tip after the OpenHands allowlist commit.
This branch is stacked on that tip and must not be folded into PR #498.
**Source note:** operator brief `pete-Steinberger.md` (2026-11-14).
**Upstream inspected:** [steipete/agent-scripts](https://github.com/steipete/agent-scripts)
`main` README and `skills/` listing (54 skill directories) on 2026-11-14.
**Local corpora counted:** `bin/orama-system/skills/` = 65 directories on
this branch. Perpetua-Tools `.agent/skills` and `vendor/` mirrors were not
re-listed file-by-file in this pass; Phase 1 does that before any deletion.
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

Do not clone that repo from `install.sh` or `platform/windows/install.ps1`.
A previous local commit on `main` (`b57021ff`) mixed that bootstrap into
the Hermes fallback doc fix. That commit stays off this branch. Installer
wiring is a later phase, and only after this plan is accepted.

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
git clone https://github.com/steipete/agent-scripts.git ~/Projects/agent-scripts
ln -s ~/Projects/agent-scripts ~/.agent-scripts
```

`~/.agent-scripts` is the path agents in this stack should follow. Upstream's
own `scripts/sync-skills` assumes `~/Projects/agent-scripts` and rewrites
`~/.codex/skills` and `~/.claude/skills`. Do not run it in Phase 0. It can
hide orama skill links that are already on this Mac.

Run upstream `scripts/sync-skills` only after reading its dry-run behavior.
It rewrites `~/.codex/skills` and `~/.claude/skills`. That can collide with
orama skill symlinks already on this Mac. Phase 0 stops and asks before
the first real sync.

### Phase 1 — Evidence, still no deletes

1. Record upstream `git rev-parse HEAD` and the `AGENTS.MD` headings that
   match local archives, crawlers, risk labels, review gates, and
   stop-and-ask.
2. List every skill root, not a sample: `bin/orama-system/skills/` (65),
   Perpetua-Tools `.agent/skills`, `vendor/ecc-tools` skill trees, and the
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

The 11 skills overlapping with upstream portable workflows (fable5-git-rebase-safety,
git-file-deletion-guard, git-history-surgery, git-pending-push-guard, oramasys-method,
security, shell-hygiene, stacked-pr-naming, using-git-worktrees, whatsapp-qr-gateway,
plus firecrawl with no upstream equivalent) were reviewed against the deference test.
Each adds at least one stack-binding rule (hardware, identity, GossipBus, Telos, CIDF,
or OSSF) beyond upstream's general guidance, so none qualify for dedupe.

**54 skills summoned** (no upstream equivalent — local-only capabilities binding
the orama-system stack). **11 skills kept** (overlap upstream but add stack-binding
rules). **0 skills shrunk.**

54 summoned skills: agent-coordination-heartbeat, agent-methodology, antigravity-agent,
archive, cline-openclaw-agent, cline-wandb, clinepass-deepseek-flash, code-review,
codex-mcp-debugging, codex-openclaw-agent, cursor-agent, cursor-pr-body, deep-research,
ecc-sync, fable5-tier-based-routing, first-run-setup, glm52-fallback, gossip-bus,
guard-sync-divergence-guard, hardware-affinity-gate, hermes-agent, hermes-harness,
icloud-escape-move, kimi-agent, local-inference, mcp-install, mcp-orchestration,
no-sleep-chains, omniroute, openclaw-add-channel, openclaw-add-cron, openclaw-add-script,
openclaw-add-secret, openclaw-dream-setup, openclaw-new-agent, openclaw-restart,
openclaw-skills, openclaw-status, openclaw-stow, openrouter-fallback, orama-afrp,
orama-cidf, orama-gstack, orama-repo-rules, periscope-ecc, perpetua-config,
perpetua-hardware, perpetua-startup-intelligence, perpetua-tools, pt-orama-harness-integration,
self-discovery, self-improve, skillify, wanda-wandb.

11 kept skills: fable5-git-rebase-safety, firecrawl, git-file-deletion-guard,
git-history-surgery, git-pending-push-guard, oramasys-method, security, shell-hygiene,
stacked-pr-naming, using-git-worktrees, whatsapp-qr-gateway.

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
| orama-system | 65 skills, AGENTS.md + CLAUDE.md pointer | Pointer added (Phase 2); all skills kept/summoned |
| Perpetua-Tools | .agent/skills (14), GossipBus, perpetua_core.db | Pointer to be added to PT AGENTS.md/CLAUDE.md |
| ECC (everything-claude-code) | vendor/ecc-tools, ../agent-skills sibling | Symlink via upstream sync-skills (dry-run first) |
| gstack | Not yet present locally | Pointer when present |
| gbrain | $HOME/code/OpenClaw/gbrain/, 59 skills | Separate project (Garry Tan); no steipete refs; no integration |
| agentic-stack | Not yet present locally | Pointer when present |

**Sync strategy:** Upstream `scripts/sync-skills` rewrites `~/.codex/skills` and
`~/.claude/skills`. Do not run it blindly — it can collide with orama skill
symlinks already on this Mac. Phase 0 stops and asks before the first real sync.
Run with `--dry-run` first, review, then execute.

**Cross-repo coordination:** GossipBus (orchestrator/gossip_bus.py in PT) remains
the intra-host coordination bus. steipete AGENTS.MD does not replace GossipBus,
OSSF, or the commit-identity hook. Each repo's skills stay canonical in their
own repo; upstream skills are exposed via tracked relative symlinks only.

**Phase 4 prerequisite:** Phases 0–2 must be accepted before Phase 4 (installer)
is considered. Phase 4 stacks on this plan branch only.

### Phase 4 — Installer, separate PR

- No-op when git is missing or the destination exists and is not the
  expected clone or symlink.
- `git pull --ff-only` only. Never `--force`.
- Never run `sync-skills` from the installer.

That PR stacks on this plan branch only after Phases 0–2 are accepted.
It does not retarget PR #498.

## 5. Non-goals

- Copying MIT skill bodies into `bin/orama-system/skills/`.
- Replacing GossipBus, OSSF, or the commit-identity hook with upstream hooks.
- Resolving `stash@{0}` on local `main` (periscope thin-wrapper, W&B model
  pin, hardware cache with a workstation path, and the rejected installer
  hunks). Leave that stash for its owner.
- Cleaning untracked `487.tsv`, `488.tsv`, `489.tsv`, `SKILL.md.*.bak`, or
  `__pycache__` on the main checkout. Those were not part of this plan.

## 6. Acceptance

- This file is the only addition on
  `docs/2026-11-14-steipete-agent-scripts-adoption-plan`.
- `install.sh` and `platform/windows/install.ps1` match PR #498 parent
  history (no `steipete/agent-scripts` block).
- PR #498 still contains exactly one Hermes/Cursor doc commit
  (`52f61ca1`) plus the OpenHands allowlist commit, and does not contain
  this plan.
