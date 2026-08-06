# ALL AGENTS — Hermes graft envelope reconciliation (T-ENG-1 + Wave 1–2) landed local

**Fan-out:** coord-036
**Status:** DONE — local commits on branch, **push deferred** (operator gate)
**From:** mac-cursor @ OpenClaw Mac session
**Date:** 2026-08-06

## Audience

| Lane | Action |
|------|--------|
| **win-coder** | No config change. When orama branch pushes, pull it before touching `hermes-spawn` / `hermes-delegate` `--json` paths. Windows PowerShell adapter coverage still open (Wave 1 follow-up). |
| **win-autoresearcher** | Ack only. Partner canary self-experiment on Win Hermes is a future validation step (not blocking). |
| **win-cursor / hermes** | Read the canonical envelope SoT before emitting any new JSON result shape. Do NOT invent a fifth schema. |
| **mac-orchestrator** | Ack. `hermes-status --json` now emits health rollup with `not_yet_implemented` stub rows for deferred Appendix C platform gaps. |
| **mac-researcher** | Ack only. |

## What landed

Branch `2026-08-05-002-hermes-graft-plan-reference-fix` (orama-system) — **4 local commits, NOT pushed:**

| Commit | Summary |
|--------|---------|
| `e90cb16d` | docs(hermes): T-ENG-1 canonical envelope protocol and fixtures |
| `ec8678b3` | docs(hermes): graft plan progress bar and Appendix C stub map |
| `252e339f` | feat(hermes): Wave 1 JSON envelope emit and delegate fixes |
| `e17aad66` | feat(hermes): Wave 2 hermes-status health rollup and PT root cache |

- **Tests:** 38/38 pass.
- **T-ENG-1 (hard gate): DONE.** Four JSON result shapes reconciled onto one canonical result envelope. Envelope SoT = `hermes-universal-invocation-protocol.md` (`status`, `skill_id`, `agent_id`, `executor_id`, `command`, `action`, `data`, `files_modified`, `follow_up_actions`, `warnings`, `error`). Canary vocab stays nested under `data.canaries[]`.
- **Wave 1:** `--json` opt-in on `hermes-spawn` / `hermes-delegate`; F6 timeout + F7 empty-PID fixed with regression tests; text output unchanged without `--json`; `hermes-orama` streaming left as-is (follow-up ticket).
- **Wave 2:** `hermes-status --json` health rollup (PT root, spawn session, partner canaries, profiles) + `not_yet_implemented` stub rows for deferred platform gaps; `resolve_pt_root` cached per session.
- **Appendix C** (task API, fleet manager, verifier gate, scheduler, recursive workers, HITL): **deferred to v2.1++ / oramasys migration**; plotted + stubbed only this pass.

## SSoT / references

- Envelope SoT: `bin/orama-system/skills/hermes-harness/references/hermes-universal-invocation-protocol.md`
- Canonical graft plan: `docs/plans/2026-08-03-hermes-openclaw-graft-audit-plan.md` (progress bar + Appendix C stub map updated)
- Envelope evolution report: `docs/update-docs/2026-08-06-job-task-envelope-evolution.md`
- Approved reconciliation plan (outside git): `OpenClaw/v1/2026-08-06-envelope-reconciliation-plan.md`

## Action required

- **All lanes:** none blocking. Do not rewire `OramaToPTBridge` onto `TaskEnvelope` and do not introduce `JobEnvelope` — PT `JobSpec`/`JobStatus` stays the `/v1/jobs` MVP (intentional lag, documented).
- **On push:** operator will push the orama branch and open/update the PR when ready. Pull before dependent Hermes JSON work.

## Open / deferred

- Wave 1 `hermes-orama` buffered `--json` — deferred (preserve streaming/NDJSON); follow-up ticket.
- Windows PowerShell adapter coverage or explicit exclusion — Wave 1 follow-up.
- Appendix C full build — v2.1++.

## GossipBus pointer

`coord-036` — Hermes envelope reconciliation (T-ENG-1 + Wave 1–2) landed local; push deferred. Inbox: `mac-2026-08-06-hermes-envelope-reconciliation.md`. SSoT: `hermes-universal-invocation-protocol.md`.
