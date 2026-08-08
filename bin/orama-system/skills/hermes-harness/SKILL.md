---
name: hermes-harness
description: >-
  Onboards Hermes Agent as a cross-harness operator shell for PT-orama and ECC
  workflows. Use when installing Hermes, importing ECC/orama skills into Hermes,
  configuring Nous Portal or LM Studio providers, adding Hermes beside OpenClaw,
  or dispatching Hermes, Gemini, AGY, and Codex CLI coding partners.
version: 1.1.2.0
license: Apache 2.0
compatibility: hermes, codex, claude-code, windows, openclaw, ecc, agy
agent_compatibility:
  - Hermes
  - Codex
  - Claude
  - OpenClaw
  - AGY
  - Cursor
layer: "1 — Operator shell (pairs with openclaw-skills fabric)"
upstream: https://github.com/NousResearch/hermes-agent
upstream_path: $HERMES_HOME/hermes-agent
parent_skill: orama-system
origin: ECC Hermes setup, Hermes/OpenClaw migration, and cross-harness docs
triggers:
  - hermes setup
  - hermes onboarding
  - nous portal
  - hermes openclaw migration
  - ecc harness
  - cross-harness
  - install codex cli on windows
  - update all agent comms
  - update the board
  - post to the whiteboard
  - notify all peers
allowed-tools: bash, file-operations, web-search
---

# Hermes Harness

## Legacy slug symlinks (whole-folder redirects)

These slugs are directory symlinks into this skill — edit here, not at the
legacy path:

| Legacy slug | Symlink target |
| --- | --- |
| `hermes-agent` | `hermes-harness` |
| `pt-orama-harness-integration` | `hermes-harness` |

Slash-command discovery aliases (same content as `commands/<name>/`):

| Discovery path | Canonical command |
| --- | --- |
| `hermes-harness/hermes-delegate` | `commands/hermes-delegate` |
| `hermes-harness/hermes-orama` | `commands/hermes-orama` |
| `hermes-harness/hermes-spawn` | `commands/hermes-spawn` |

Absorption map: [`references/hermes-skill-absorption-map.md`](references/hermes-skill-absorption-map.md).

## Dispatch lanes (do not conflate)

| Lane | What runs | orama commands |
| ---- | --------- | -------------- |
| **L-H1** | Native Hermes `delegate_task` children | Interactive Hermes session only (not PT scripts) |
| **L-PT** | PT `spawn_hermes_agent()` / `hermes_harness.py` | `hermes-orama`, `hermes-delegate`, `hermes-spawn` |
| **L-Fleet** | `coord_pulse` → `cursor-agent` | Win/Mac fleet queues; not these slash commands |

`hermes-delegate` is **L-PT** — parallel PT workers, **not** `delegate_task`.
`subagent/win-*` git branches are **L-Fleet** coordination fiction.

Canonical: [`references/hermes-dispatch-taxonomy.md`](references/hermes-dispatch-taxonomy.md)
Graft registry: [`references/openclaw-pattern-graft-registry.md`](references/openclaw-pattern-graft-registry.md)
Paths: [`references/openclaw-workspace-path-doctrine.md`](references/openclaw-workspace-path-doctrine.md)
— never `$OPENCLAW_ROOT` in committed prose.

## 🔧 Setup (GLM-5.2 Fallback)

```bash
source ~/.openclaw/openclaw-glm52-env 2>/dev/null && echo "✅ GLM-5.2 Fallback Activated" || true
```

When LM Studio, Ollama, or other Hermes-accessible models are unavailable, this
task queue can execute via GLM-5.2. **No additional setup required**—the
environment variables are already sourced by start.ps1.

---

## Purpose

Use Hermes as an operator shell that consumes durable PT-orama/ECC skills,
prompts, MCP conventions, and cross-harness rules. Keep OpenClaw as the
runtime gateway/agent fabric.

## When to Use

- A Windows or Mac operator needs Hermes installed or repaired.
- Hermes must consume orama/OpenClaw/ECC skills without copying private state.
- Nous Portal, LM Studio, OpenRouter, Gemini, AGY, or Codex CLI are being wired as coding partners.
- A Hermes/OpenClaw artifact must become a reusable skill, command, hook, doc, or issue.

## Instructions

Detailed setup, pulse cadence, Windows onboarding, verification, and partner
dispatch live in [`references/ossf-operating-procedures.md`](references/ossf-operating-procedures.md).
Command cards: `commands/*/SKILL.md`. Protocol:
[`references/hermes-universal-invocation-protocol.md`](references/hermes-universal-invocation-protocol.md).

## Boundaries

Match `openclaw-skills` operational rigor. Hermes is operator shell; OpenClaw owns fabric.

### Always Do

- Normalize every dispatch to the universal envelope (core + harness extensions).
- Run bootstrap gate before non-trivial partner dispatch.
- Keep Hermes imports sanitized and reproducible (thin wrappers ≤ 60 lines).
- Use environment variables for machine-specific paths (`$ORAMA_SYSTEM_PATH`, `$HERMES_HOME`).
- Treat Hermes and OpenClaw as harnesses that consume canonical skills.
- `git fetch origin --prune` before reading canonical skill bodies.
- Route `openclaw-*` skills through `openclaw-skills` protocol, never Hermes inline.
- Return core result shape (`status`, `files_modified`, `follow_up_actions`) on every dispatch.
- Verify `bash.exe`, partner CLIs, and provider reachability before dispatch.
- Integrate multiple plans per [`references/plan-integration.md`](references/plan-integration.md).

### Ask First

- Writing Hermes config files that include credentials or provider accounts.
- Starting long-running gateways, cron jobs, or remote dispatch surfaces.
- Letting Hermes, Gemini, AGY, or Codex modify files directly.
- Dispatching Mac-only OpenClaw fabric skills on Windows (expect `blocked` envelope).
- Graduating lessons to PT memory without user-visible summary in the result.

### Never Do

- Commit API keys, OAuth tokens, raw `~/.hermes` exports, personal memory, or
  local-only business artifacts.
- Replace OpenClaw procedures with Hermes guesses.
- Maintain shadow copies of PT-orama/ECC skill bodies in Hermes home.
- Commit absolute workstation paths in repo content or envelopes.
- Let worker agents commit, deploy, delete, or change account settings without
  explicit confirmation.
- Hardcode LAN IP literals in skills, plans, or docs; resolve endpoints via env vars only.
- Hardcode LM Studio model IDs from memory; fetch exact IDs from `/v1/models`.
- Silent fallback when `hardware-affinity-gate` returns `NEVER`.

## References

- [`references/update-all-agents-comms.md`](references/update-all-agents-comms.md)
  — GossipBus + inbox fanout recipe
- [`references/lan-peer-coordination.md`](references/lan-peer-coordination.md)
  — queues, pulse-gate, record-success, inbox drops
- [`references/plan-integration.md`](references/plan-integration.md)
  — merge multiple plans into one canonical doc
- [`references/lan-peer-self-talk.md`](references/lan-peer-self-talk.md)
  — Mac↔Win operator playbook (SSOT) ·
  [`docs/guides/lan-peer-mac-win-operator.md`](../../../../docs/guides/lan-peer-mac-win-operator.md)
- [`../git-history-surgery/references/safe-cross-host-sync-reference-card.md`](../git-history-surgery/references/safe-cross-host-sync-reference-card.md)
  — stash-first Mac↔Win `main` sync (non-destructive)
- [`references/hermes-universal-invocation-protocol.md`](references/hermes-universal-invocation-protocol.md)
  — envelope, layers, result superset
- [`references/hermes-skill-absorption-map.md`](references/hermes-skill-absorption-map.md)
  — Hermes → orama absorption status (redirects + supersets)
- [`references/hermes-ecc-fork-inventory.md`](references/hermes-ecc-fork-inventory.md)
- [`references/ecc-hermes-cross-harness.md`](references/ecc-hermes-cross-harness.md)
- [`references/hermes-ecc-fork-inventory.md`](references/hermes-ecc-fork-inventory.md)
- [`../../references/codex-cli-v142-dispatch.md`](../../references/codex-cli-v142-dispatch.md)
  — Codex CLI v0.142.x profiles (fanout / bounded / interactive)
- [`../openclaw-skills/SKILL.md`](../openclaw-skills/SKILL.md)
- [`../mcp-orchestration/SKILL.md`](../mcp-orchestration/SKILL.md)

## Post-Review Micro-Remediation

When addressing review findings (CodeRabbit or human) on an open PR: cluster
findings by root cause, fix once at the abstraction level, keep every commit
mechanically attributable to its failure class, and never accumulate revert
chains — reset to a safety-ref-protected ancestor instead when policy allows.

When a finding touches a file shared between PT and orama-system: check the
sibling repo's copy for the same bug before assuming it's isolated (Phase 6 —
cross-repo synchronization), fix both locally, verify full parity with a real
diff, and push once per repo to the existing open PR branch on each side —
never close one PR and open a new one to represent the same synchronized
edit. `pt-orama-harness-integration` redirects here for exactly this reason.

Full doctrine: [`references/post-review-micro-remediation.md`](../../references/post-review-micro-remediation.md)
