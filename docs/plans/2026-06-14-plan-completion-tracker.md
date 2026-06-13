# Plan Completion Tracker — Meta-Plan (youngest → oldest)

> **Date:** 2026-06-14 · **Owner repo:** orama-system (L3) · **Status:** living tracker
> **Scope:** every *dated* plan/spec across the 3 repos — AlphaClaw (L1), Perpetua-Tools (L2),
> orama-system (L3). Sorted **youngest → oldest**. Finish the most recent first, then work down.

## How to use this tracker

- **Order:** top-down (newest first), per the completion directive. Update a row's status as you go.
- **`Open` signal:** count of `- [ ]` checkboxes in the doc — a rough proxy for unfinished work.
  `0` can mean *done* **or** *prose/gate-style* (no checkboxes) — those get 🔍 (confirm before skipping).
- **Status key:** ⬜ to-finish (N open items) · 🔍 review (no checkboxes — confirm done vs prose) ·
  ✅ done · ⤵️ superseded. Edit the Status cell as plans close out.
- **No December-2025 dated plans exist** in `/docs/` — the dated corpus starts `2026-04-13`. Undated
  reference docs (wiki/, LESSONS, MIGRATION, ADRs, contracts) are intentionally excluded (not plans).

## Canonical anchors (read first)

- Tri-repo migration: **[`Perpetua-Tools/docs/2026-05-31-tri-repo-alignment-completion-plan.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/2026-05-31-tri-repo-alignment-completion-plan.md)** (+ its `MIGRATION.md` gate ladder)
- ⚠ **Active blocker:** PT `main` is churned to detached HEAD by a concurrent Cursor agent — land PT edits via the GitHub API and confirm a stable checkout before any PT code work.

## Backlog (youngest → oldest)

| # | Date | Repo | Status (open items) | Plan | Path |
|---|------|------|---------------------|------|------|
| 1 | 2026-06-12 | orama | 🔍 review | Perpetua Orama Thin Skill Wrappers Implementation Plan | `docs/superpowers/plans/2026-06-12-perpetua-orama-thin-skill-wrappers.md` |
| 2 | 2026-06-10 | orama | 🔍 review | oramasys-method Skill — Eval Report & Dogfood Findings | `docs/plans/2026-06-10-oramasys-method-skill-eval.md` |
| 3 | 2026-05-31 | PT | 🔍 review | Tri-Repo Migration & Consolidation — Alignment & Completion Plan | `docs/2026-05-31-tri-repo-alignment-completion-plan.md` |
| 4 | 2026-05-31 | PT | 🔍 review | Track B+C — Claude-Desktop-LLM submodule + real MCPB | `docs/plans/2026-05-31-track-bc-claude-desktop-mcpb.md` |
| 5 | 2026-05-31 | PT | 🔍 review | Gate 2 Implementation Plan — Work Items #4, #6, #7 | `docs/plans/2026-05-31-gate2-implementation-plan.md` |
| 6 | 2026-05-29 | orama | 🔍 review | v1.1 Definitive Execution Plan — Rename · Frugality · Tiered OpenRou | `docs/plans/2026-05-29-03-v1.1-definitive.md` |
| 7 | 2026-05-29 | orama | 🔍 review | 2026-05-29-01 — Cursor plan: `/oramasys` rename + tiered OpenRouter  | `docs/plans/2026-05-29-01-cursor-PLAN.md` |
| 8 | 2026-05-28 | orama | 🔍 review | v1.1 Release Plan — Orama × Perpetua-Tools Frugality & Harness Optim | `docs/plans/2026-05-28-v1.1-frugality-harness-release.md` |
| 9 | 2026-05-25 | orama | ⬜ 23 open | Perpetua-Tools MCP + net_utils Migration — Design Spec | `docs/superpowers/specs/2026-05-25-pt-mcp-netutils-migration-design.md` |
| 10 | 2026-05-24 | orama | ⬜ 52 open | Periscope L4 Glass — Implementation Plan | `docs/plans/2026-05-24-periscope-l4-integration-plan.md` |
| 11 | 2026-05-24 | orama | 🔍 review | Git Worktrees for Parallel Agents — Design Spec | `docs/superpowers/specs/2026-05-24-worktree-parallel-agents-design.md` |
| 12 | 2026-05-24 | orama | 🔍 review | 2026-05-24 Security Review Debug and Fix Notes | `docs/2026-05-24-security-review-debug-and-fix-notes.md` |
| 13 | 2026-05-23 | orama | ⬜ 13 open | Security Remediation Plan — Post PR Review (2026-05-23) | `docs/plans/2026-05-23-security-remediation-plan.md` |
| 14 | 2026-05-23 | orama | ⬜ 10 open | CLAUDE-instru Progressive Weaning — Autoplan | `docs/plans/2026-05-23-claude-instru-weaning-autoplan.md` |
| 15 | 2026-05-22 | PT | 🔍 review | RAG Memory Pipeline — v1 Backport Release Notes | `docs/2026-05-22-rag-backport-v1-release-notes.md` |
| 16 | 2026-05-22 | orama | 🔍 review | RAG v1 Backport — What Shipped (2026-05-22) | `docs/2026-05-22-rag-v1-backport-shipped.md` |
| 17 | 2026-05-22 | orama | 🔍 review | AlphaClaw Wiring Audit + Migration + v2.1 Satellite Plan | `docs/plans/2026-05-22-alphaclaw-wiring-migration-v2-satellites.md` |
| 18 | 2026-05-21 | orama | ⬜ 38 open | RAG Memory Pipeline v1 — Implementation Plan | `docs/superpowers/plans/2026-05-21-rag-memory-v1-plan.md` |
| 19 | 2026-05-21 | orama | ⬜ 18 open | gstack Optional Git Submodule — Implementation Plan | `docs/superpowers/plans/2026-05-21-gstack-optional-submodule-plan.md` |
| 20 | 2026-05-21 | orama | 🔍 review | Technical Review: RAG Memory Pipeline & gstack Submodule Integration | `docs/2026-05-21-002--RAG-Gstack-Review--Antigravity-Gemini-3.5-Flash-Preview.md` |
| 21 | 2026-05-21 | orama | 🔍 review | Design: Minimal RAG Memory Pipeline + gstack Optional Submodule | `docs/superpowers/specs/2026-05-21-rag-memory-gstack-design.md` |
| 22 | 2026-05-21 | orama | 🔍 review | Critique: RAG + Memory + Optional gstack Planning Set | `docs/2026-05-21-001--Critique-RAG-ChatGPT-codex-GPT-5.5.md` |
| 23 | 2026-05-20 | PT | 🔍 review | Perpetua-Tools — Remaining Codex Review Fixes | `docs/superpowers/plans/2026-05-20-codex-review-remaining-fixes.md` |
| 24 | 2026-05-20 | orama | ⬜ 39 open | cc-openclaw Master Alignment Implementation Plan | `docs/superpowers/plans/2026-05-20-cc-openclaw-master-alignment.md` |
| 25 | 2026-05-20 | orama | 🔍 review | cc-openclaw Master Alignment Design (2026-05-20) | `docs/superpowers/specs/2026-05-20-cc-openclaw-master-alignment-design.md` |
| 26 | 2026-05-19 | orama | ⬜ 3 open | Plan: gbrain Embeddings as Optional Feature of code-review-graph | `docs/plans/2026-05-19-gbrain-crg-embedding-integration.md` |
| 27 | 2026-05-17 | orama | ⬜ 95 open | Salvage Translation + v1 IP-Aware Backend Discovery — Implementation | `docs/superpowers/plans/2026-05-17-salvage-translation-v1-discovery.md` |
| 28 | 2026-05-17 | orama | 🔍 review | Salvage Code Translation — Design Spec | `docs/superpowers/specs/2026-05-17-salvage-translation-design.md` |
| 29 | 2026-05-16 | orama | ⬜ 46 open | Web-App Orchestration Implementation Plan | `docs/superpowers/plans/2026-05-16-web-app-orchestration.md` |
| 30 | 2026-05-14 | orama | ⬜ 18 open | RC-1 Master Orchestration Plan — Parallel Agent Dispatch | `docs/superpowers/specs/2026-05-14-rc1-orchestration-master-plan.md` |
| 31 | 2026-05-14 | orama | ⬜ 10 open | Salvage Contribution Plan — Divergent Build → Canonical `oramasys/pe | `docs/superpowers/specs/2026-05-14-salvage-plugins-design.md` |
| 32 | 2026-05-14 | orama | 🔍 review | docs/v2 Enrichment — Canonical As-Built + OQ Resolution Design | `docs/superpowers/specs/2026-05-14-docs-v2-enrichment-design.md` |
| 33 | 2026-05-14 | orama | 🔍 review | `docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md` | `docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md` |
| 34 | 2026-05-08 | orama | 🔍 review | 2026-05-08 — V1 Persistent Supervisor Brainstorm | `docs/2026-05-08-v1-supervisor-brainstorm.md` |
| 35 | 2026-05-04 | orama | 🔍 review | Git Tag Conflict & Feature Regression Analysis | `docs/recovery/2026-05-04-gemini-3-flash-recovery-analysis.md` |
| 36 | 2026-04-28 | orama | 🔍 review | Perpetua-Tools & orama-system — Master Revamp Plan (2026-Q2) | `docs/2026-04-28-perpetua-orama-master-revamp.md` |
| 37 | 2026-04-26 | orama | ⬜ 4 open | Hardware Model Routing — Part 2 Plan | `docs/tripartite-plan/2026-04-26-hardware-model-routing-004-PART2-PLAN.md` |
| 38 | 2026-04-26 | orama | 🔍 review | Twin System Session State — April 26, 2026 | `docs/2026-04-26-session-state-plan.md` |
| 39 | 2026-04-26 | orama | 🔍 review | Plan: Hardware-Enforced Model Routing & Shared Intelligence | `docs/tripartite-plan/2026-04-26-gemini-002-PLAN.md` |
| 40 | 2026-04-26 | orama | 🔍 review | Hardware-Bound Model Routing Repair Plan | `docs/tripartite-plan/2026-04-26-codex-001-PLAN.md` |
| 41 | 2026-04-26 | orama | 🔍 review | Hardware-Bound Model Routing — Final Merged Plan | `docs/tripartite-plan/2026-04-26-MERGED-hardware-model-routing-003-PLAN.md` |
| 42 | 2026-04-24 | orama | 🔍 review | Orama History Recovery | `docs/recovery/2026-04-24-001-orama-history-recovery.md` |
| 43 | 2026-04-24 | orama | 🔍 review | Git Safety Guardrails | `docs/recovery/2026-04-24-003-git-safety-guardrails.md` |
| 44 | 2026-04-24 | orama | 🔍 review | Commit Salvage Matrix | `docs/recovery/2026-04-24-002-commit-salvage-matrix.md` |
| 45 | 2026-04-20 | PT | ⬜ 37 open | LM Studio Auto-Discovery & Three-Repo Claude Code Automation — Imple | `docs/wiki/2026-04-20-LM-Studio-autodiscovery-PLAN.md` |
| 46 | 2026-04-20 | PT | 🔍 review | LM Studio Auto-Discovery & Three-Repo Claude Code Automation | `docs/wiki/2026-04-20-LMStudio-autodiscovery-design.md` |
| 47 | 2026-04-16 | AlphaClaw | ⬜ 5 open | Session Lessons — 2026-04-16 | `docs/superpowers/plans/2026-04-16-session-lessons.md` |
| 48 | 2026-04-13 | AlphaClaw | ⬜ 22 open | AlphaClaw macOS Compatibility PR Implementation Plan | `docs/superpowers/plans/2026-04-13-alphaclaw-macos-pr.md` |

## Notes

- This tracker is **generated from a mine of the three `docs/` trees** (canonical refs: PT/orama
  `origin/main`, AlphaClaw `origin/feature/MacOS-post-install`). Re-mine and regenerate after large
  doc changes.
- High open-item plans worth triaging first (by signal): Salvage Translation (95), Periscope L4 (52),
  Web-App Orchestration (46), cc-openclaw Master Alignment (39), RAG Memory v1 (38), LM Studio
  Auto-Discovery (37), PT-MCP net_utils migration (23), AlphaClaw macOS PR (22).
- Many `🔍 review` rows are likely already shipped (release notes, "what shipped", design specs that
  fed an execution plan) — confirm and mark ✅/⤵️ rather than re-doing.
