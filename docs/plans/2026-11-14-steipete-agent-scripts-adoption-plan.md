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

Operator priority sections (local archives, crawlers, risk labels, review
gates, stop-and-ask) are not a separate top-level tree in the listing
fetched today. Treat them as headings inside `AGENTS.MD` until Phase 1
quotes the real headings. Do not invent section paths.

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
# or a symlink the operator already uses, such as ~/.agent-scripts
```

Run upstream `scripts/sync-skills` only after reading its dry-run behavior.
It rewrites `~/.codex/skills` and `~/.claude/skills`. That can collide with
orama skill symlinks already on this Mac. Phase 0 stops and asks before
the first real sync.

### Phase 1 — Evidence, still no deletes

1. Record upstream `git rev-parse HEAD` and the `AGENTS.MD` headings that
   match local archives, crawlers, risk labels, review gates, and
   stop-and-ask.
2. List Perpetua-Tools skill roots (`.agent/skills`, `vendor/ecc-tools`,
   any OpenClaw overlay) the same way as `bin/orama-system/skills/`.
3. For each row in §3, write one paragraph: same job, or only a shared
   verb. Attach file paths. No card is retired on a name match alone.

### Phase 2 — Pointer layer

Add a short pointer at the top of orama `AGENTS.md` / `CLAUDE.md` only:

```text
READ ~/Projects/agent-scripts/AGENTS.MD BEFORE ANYTHING (skip if missing).
```

Repo-specific rules stay below that line. Do not vendor `AGENTS.MD`.
Do not add the clone to `install.sh` or `install.ps1` in this phase.

### Phase 3 — Dedupe candidates

Only after Phase 1 paragraphs exist:

- Retire or shrink a local card when upstream is the same job and our card
  has no hardware, identity, GossipBus, Telos, or CIDF rule.
- Keep a local card when it binds this stack (OSSF, GLM fallback, peer TLS,
  commit identity, coordination board).
- One card per PR. Each PR names the upstream skill path it defers to.

### Phase 4 — Installer, separate PR

If Phase 0 sync is safe, a later PR may offer an **opt-in** bootstrap:

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
