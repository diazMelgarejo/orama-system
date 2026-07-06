# Lessons — orama-system

> **Canonical path**: `docs/LESSONS.md`<br/>
> **Previous path**: `.claude/lessons/LESSONS.md` (now redirects here)<br/>
> **Purpose**: GitHub-auditable persistent memory across all ECC, AutoResearcher, and Claude sessions.<br/>
> **Cross-repo companions**:
> - [Perpetua-Tools/docs/LESSONS.md](../../perplexity-api/Perpetua-Tools/docs/LESSONS.md) · [GitHub](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/LESSONS.md)
> - [AlphaClaw/docs/Lessons.MD](../../AlphaClaw/docs/Lessons.MD) · [GitHub](https://github.com/diazMelgarejo/AlphaClaw/blob/feature/MacOS-post-install/docs/Lessons.MD)
>
> **Cross-repo lesson index** (shared knowledge — check here when a problem spans repos):
>
> | Topic | Canonical doc | Also in |
> |-------|--------------|---------|
> | macOS ` 2`/` 3` dupes in `.git/` internals | [AlphaClaw wiki/07](../../AlphaClaw/docs/wiki/07-duplicate-files.md) | This file §2026-05-27 + §2026-05-31 |
> | No sleep chains (`sleep N && cmd`) | [skills/no-sleep-chains/SKILL.md](../bin/orama-system/skills/no-sleep-chains/SKILL.md) | This file §2026-05-16 |
> | Git identity + Cursor commit policy | [docs/wiki/08-git-hygiene-and-branching.md](wiki/08-git-hygiene-and-branching.md) | AlphaClaw `scripts/git/check_identity.sh` |
> | gbrain pooler write failures + resync | [gstack/SKILL.md §GBrain Ops](../bin/orama-system/gstack/SKILL.md) | This file §2026-05-30 |
> | Migration gate ladder (Gate 0→4) | [PT docs/MIGRATION.md](../../perplexity-api/Perpetua-Tools/docs/MIGRATION.md) | This file §2026-05-30 T7 survey |
> | Hermes integration authority (envelope + thin wrappers) | [hermes-universal-invocation-protocol.md](../bin/orama-system/skills/hermes-harness/references/hermes-universal-invocation-protocol.md) | PT [LESSONS.md §2026-06-28](../../perplexity-api/Perpetua-Tools/docs/LESSONS.md) |
> | LAN peer Mac↔Win (Hermes operator playbook) | [lan-peer-self-talk.md § Operator playbook](../bin/orama-system/skills/hermes-harness/references/lan-peer-self-talk.md#operator-playbook) | [docs/guides/lan-peer-mac-win-operator.md](guides/lan-peer-mac-win-operator.md) |
> | Mac↔Win co-orchestrator (file inbox + ws-peer GO) | [mac-co-orchestrator-playbook.md](../bin/orama-system/skills/hermes-harness/references/mac-co-orchestrator-playbook.md) | PT [LESSONS.md §2026-06-28](../../perplexity-api/Perpetua-Tools/docs/LESSONS.md) |
> | AlphaClaw branch roles + invariants | [AlphaClaw CLAUDE.md](../../AlphaClaw/CLAUDE.md) | AlphaClaw wiki/01 |
>
> **Architecture authority**: [2026-05-14--UNIFIED-ABSORPTION-PLAN.md](2026-05-14--UNIFIED-ABSORPTION-PLAN.md)
> **Navigation hub**: [CLAUDE-instru.md](../../../CLAUDE-instru.md)
>
> **Rules**:
>
> - Read this file at the start of every session
> - Prepend new entries at the top of the Sessions Log (newest first)
> - Keep entries dated and agent-tagged (`ECC | AutoResearcher | Claude`)
> - For organized, deep-dive explanations see the **[wiki →](wiki/README.md)**
> - For agent behavioral rules see **[SKILL.md →](../SKILL.md)**

---

## continuous-learning-v2

This repo uses [continuous-learning-v2](https://github.com/affaan-m/everything-claude-code/tree/main/skills/continuous-learning-v2).

- Instincts: `.claude/homunculus/instincts/inherited/orama-system-instincts.yaml`
- Import command: `/instinct-import .claude/homunculus/instincts/inherited/orama-system-instincts.yaml`

---

## Sessions Log

---

### 2026-07-07 — PR description append-only lesson (Codex failure + remediation) | Claude

**Session:** PR #141 lesson recording
**Incident:** Codex agent violated the append-only principle by replacing PR #141's description with the latest delta instead of preserving the original corpus and appending updates below it.

**What went wrong:**
1. Codex overwrote the PR description — erasing the original purpose, non-goals, and validation notes that served as historical review artifacts.
2. Codex then created a "companion lesson file" (`docs/lessons/2026-07-07-pr-description-append-only.md`) instead of adding the lesson to canonical `docs/LESSONS.md` — the exact anti-pattern it was documenting. The companion file was an orphan; nothing referenced it from the main LESSONS.md.

**Root cause:** Applying the anti-pattern while documenting it. Instead of preserving + appending to the canonical location, Codex created a new file in a new location — the same clobber behavior it was trying to prevent.

**Lessons learned:**

1. **PR descriptions are historical review artifacts.** Preserve the original purpose, non-goals, constraints, and validation notes at the top. Add later repair notes below in an append-only log section (e.g., `## Append-only update log`). Never replace the original corpus with the latest summary.

2. **Canonical lesson files are the only durable record.** When recording a lesson, add it to the canonical LESSONS.md Sessions Log per its own rules ("Prepend new entries at the top"). Creating companion files in side directories produces orphans that future agents won't discover.

3. **Do not edit large files through truncated connector content.** If a file is too large for the connector, do not rewrite it. Instead: (a) add to the canonical file via a targeted edit at the documented insertion point, or (b) if the file truly cannot be accessed, record the lesson in the Sessions Log with a cross-reference to the context that enables future graduation.

4. **The remedy must not repeat the disease.** An agent that fixes a clobbering bug by creating a new sidecar file (instead of appending to the canonical location) has not fixed the underlying pattern failure.

**Remediation applied:**
- PR #141 body restored: original summary/purpose/non-goals/validation notes preserved at top; later changes appended under `## Append-only update log`.
- Companion lesson file deleted from `docs/lessons/` — lesson moved to this canonical Sessions Log entry.
- Codex's attempted `docs/LESSONS.md` edit was reverted (connector returned truncated file; replacing it would have deleted unseen historical lessons).

**Cross-references:**
- PR #141: https://github.com/diazMelgarejo/orama-system/pull/141
- This lesson also recorded in Perpetua-Tools `.agent/memory/semantic/LESSONS.md` (lesson ID TBD)

---

### 2026-07-04 — Fable-5 LLM Council (Tasks 1-2 complete, Task 3 ready) + WhatsApp MVP documented | Claude