<!-- /autoplan restore point: local gstack artifact, retained outside the repository -->
# Implementation Plan: OpenClaw → Hermes Skill Grafting

**Scope:** Farm operational patterns from `openclaw-skills` and enrich
`hermes-harness/commands` so Hermes instances can be controlled end-to-end with
the same rigor OpenClaw agents already have.

**Complexity:** **Large** — cross-tree architecture, existing absorption map,
PT runtime boundary, and thin-wrapper install path.

**Worktree:** `cursor/hermes-openclaw-graft-audit-f559` (from merged `main`)

**Sources:**

- **SOURCE (subset/inspiration):**
  `bin/orama-system/skills/openclaw-skills`
- **TARGET (superset for enrichment):**
  `bin/orama-system/skills/hermes-harness/commands`

<!-- AUTO-GENERATED cross-repo links -->

### Related research

- Job/task envelope evolution (MVP JobSpec / TaskEnvelope history): [`../update-docs/2026-08-06-job-task-envelope-evolution.md`](../update-docs/2026-08-06-job-task-envelope-evolution.md)

### orama-system (GitHub `main`)

| Path | Link |
| ---- | ---- |
| `bin/orama-system/skills/openclaw-skills` | [openclaw-skills](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/openclaw-skills) |
| `bin/orama-system/skills/hermes-harness/commands` | [commands](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/commands) |
| `bin/orama-system/skills/openclaw-skills/SKILL.md` | [SKILL.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/openclaw-skills/SKILL.md) |
| `bin/orama-system/skills/openclaw-skills/skills/openclaw-status/SKILL.md` | [SKILL.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/openclaw-skills/skills/openclaw-status/SKILL.md) |
| `bin/orama-system/skills/openclaw-skills/skills/openclaw-restart/SKILL.md` | [SKILL.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/openclaw-skills/skills/openclaw-restart/SKILL.md) |
| `bin/orama-system/skills/openclaw-skills/skills/openclaw-stow/SKILL.md` | [SKILL.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/openclaw-skills/skills/openclaw-stow/SKILL.md) |
| `bin/orama-system/skills/openclaw-skills/skills/openclaw-add-secret/SKILL.md` | [SKILL.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/openclaw-skills/skills/openclaw-add-secret/SKILL.md) |
| `bin/orama-system/skills/openclaw-skills/skills/openclaw-dream-setup/SKILL.md` | [SKILL.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/openclaw-skills/skills/openclaw-dream-setup/SKILL.md) |
| `bin/orama-system/skills/openclaw-skills/skills/openclaw-add-script/SKILL.md` | [SKILL.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/openclaw-skills/skills/openclaw-add-script/SKILL.md) |
| `bin/orama-system/skills/openclaw-skills/skills/openclaw-new-agent/SKILL.md` | [SKILL.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/openclaw-skills/skills/openclaw-new-agent/SKILL.md) |
| `bin/orama-system/skills/openclaw-skills/skills/openclaw-add-channel/SKILL.md` | [SKILL.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/openclaw-skills/skills/openclaw-add-channel/SKILL.md) |
| `bin/orama-system/skills/openclaw-skills/skills/openclaw-add-cron/SKILL.md` | [SKILL.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/openclaw-skills/skills/openclaw-add-cron/SKILL.md) |
| `bin/orama-system/skills/openclaw-skills/references/universal-skill-protocol.md` | [universal-skill-protocol.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/openclaw-skills/references/universal-skill-protocol.md) |
| `bin/orama-system/skills/openclaw-skills/references/recursive-spawn-protocol.md` | [recursive-spawn-protocol.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/openclaw-skills/references/recursive-spawn-protocol.md) |
| `bin/orama-system/skills/openclaw-skills/scripts/json-response.sh` | [json-response.sh](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/openclaw-skills/scripts/json-response.sh) |
| `bin/orama-system/skills/hermes-harness/SKILL.md` | [SKILL.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/SKILL.md) |
| `bin/orama-system/skills/hermes-harness/scripts/resolve_perp_harness.sh` | [resolve_perp_harness.sh](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/scripts/resolve_perp_harness.sh) |
| `bin/orama-system/skills/hermes-harness/scripts/hermes_spawn.sh` | [hermes_spawn.sh](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/scripts/hermes_spawn.sh) |
| `bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py` | [install_hermes_thin_skills.py](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py) |
| `bin/orama-system/skills/hermes-harness/scripts/install_hermes_profiles.py` | [install_hermes_profiles.py](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/scripts/install_hermes_profiles.py) |
| `bin/orama-system/skills/hermes-harness/scripts/verify_partner_canaries.py` | [verify_partner_canaries.py](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/scripts/verify_partner_canaries.py) |
| `bin/orama-system/skills/hermes-harness/scripts/dispatch_codex_partner.py` | [dispatch_codex_partner.py](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/scripts/dispatch_codex_partner.py) |
| `bin/orama-system/skills/hermes-harness/scripts/coord_pulse.ps1` | [coord_pulse.ps1](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/scripts/coord_pulse.ps1) |
| `bin/orama-system/skills/hermes-harness/scripts/coord_pulse.sh` | [coord_pulse.sh](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/scripts/coord_pulse.sh) |
| `bin/orama-system/skills/hermes-harness/references/hermes-skill-absorption-map.md` | [hermes-skill-absorption-map.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/references/hermes-skill-absorption-map.md) |
| `bin/orama-system/skills/hermes-harness/references/hermes-dispatch-taxonomy.md` | [hermes-dispatch-taxonomy.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/references/hermes-dispatch-taxonomy.md) |
| `bin/orama-system/skills/hermes-harness/references/openclaw-workspace-path-doctrine.md` | [openclaw-workspace-path-doctrine.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/references/openclaw-workspace-path-doctrine.md) |
| `bin/orama-system/skills/hermes-harness/references/openclaw-pattern-graft-registry.md` | [openclaw-pattern-graft-registry.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/references/openclaw-pattern-graft-registry.md) |
| `bin/orama-system/skills/hermes-harness/references/workspace-path-resolution.md` | [workspace-path-resolution.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/references/workspace-path-resolution.md) |
| `bin/orama-system/skills/hermes-harness/references/hermes-portable-brain-map.md` | [hermes-portable-brain-map.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/references/hermes-portable-brain-map.md) |
| `bin/orama-system/skills/hermes-harness/references/hermes-universal-invocation-protocol.md` | [hermes-universal-invocation-protocol.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/references/hermes-universal-invocation-protocol.md) |
| `bin/orama-system/skills/hermes-harness/references/openclaw-to-hermes-migration.md` | [openclaw-to-hermes-migration.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/references/openclaw-to-hermes-migration.md) |
| `bin/orama-system/skills/hermes-harness/references/update-all-agents-comms.md` | [update-all-agents-comms.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/references/update-all-agents-comms.md) |
| `bin/orama-system/skills/hermes-harness/commands/hermes-spawn/SKILL.md` | [SKILL.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/commands/hermes-spawn/SKILL.md) |
| `bin/orama-system/skills/hermes-harness/commands/hermes-delegate/SKILL.md` | [SKILL.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/commands/hermes-delegate/SKILL.md) |
| `bin/orama-system/skills/hermes-harness/commands/hermes-orama/SKILL.md` | [SKILL.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/commands/hermes-orama/SKILL.md) |
| `bin/orama-system/skills/hermes-harness/commands/pt-orama-council` | [pt-orama-council](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/commands/pt-orama-council) |
| `bin/orama-system/skills/hermes-harness/commands/pt-orama-review` | [pt-orama-review](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/commands/pt-orama-review) |
| `bin/orama-system/skills/hermes-harness/commands/pt-orama-delegate` | [pt-orama-delegate](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/commands/pt-orama-delegate) |
| `bin/orama-system/skills/hermes-harness/commands/pt-hardware-policy` | [pt-hardware-policy](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/commands/pt-hardware-policy) |
| `bin/orama-system/skills/hermes-harness/commands/lan-peer-self-talk` | [lan-peer-self-talk](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/commands/lan-peer-self-talk) |
| `bin/orama-system/skills/hermes-harness/commands/windows-hermes-setup` | [windows-hermes-setup](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/commands/windows-hermes-setup) |
| `bin/orama-system/skills/hermes-harness/commands/pt-orama-lesson-mining` | [pt-orama-lesson-mining](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/commands/pt-orama-lesson-mining) |
| `bin/agents/REGISTRY.yml` | [REGISTRY.yml](https://github.com/diazMelgarejo/orama-system/blob/main/bin/agents/REGISTRY.yml) |
| `tests/test_hermes_spawn.py` | [test_hermes_spawn.py](https://github.com/diazMelgarejo/orama-system/blob/main/tests/test_hermes_spawn.py) |
| `tests/test_resolve_perp_harness.py` | [test_resolve_perp_harness.py](https://github.com/diazMelgarejo/orama-system/blob/main/tests/test_resolve_perp_harness.py) |
| `tests/test_hermes_invoke_envelope.py` | [test_hermes_invoke_envelope.py](https://github.com/diazMelgarejo/orama-system/blob/main/tests/test_hermes_invoke_envelope.py) |
| `scripts/ci/run_agent_security_scans.sh` | [run_agent_security_scans.sh](https://github.com/diazMelgarejo/orama-system/blob/main/scripts/ci/run_agent_security_scans.sh) |
| `docs/plans/2026-08-03-hermes-openclaw-graft-audit-plan.md` | [2026-08-03-hermes-openclaw-graft-audit-plan.md](https://github.com/diazMelgarejo/orama-system/blob/main/docs/plans/2026-08-03-hermes-openclaw-graft-audit-plan.md) |
| `docs/update-docs/2026-08-06-job-task-envelope-evolution.md` | [blob on `2026-08-05-002-hermes-graft-plan-reference-fix`](https://github.com/diazMelgarejo/orama-system/blob/2026-08-05-002-hermes-graft-plan-reference-fix/docs/update-docs/2026-08-06-job-task-envelope-evolution.md) *(not yet on `main`)* |
| `bin/orama-system/skills/hermes-harness/commands/hermes-status/SKILL.md` (planned CREATE; not on disk yet) | (unresolved: path not found — Wave deliverable) |
| `bin/orama-system/skills/hermes-harness/references/quickstart.md` (planned CREATE; not on disk yet) | (unresolved: path not found — Wave deliverable) |
| `bin/orama-system/skills/hermes-harness/scripts/hermes_delegate.py` (planned CREATE; not on disk yet) | (unresolved: path not found — Wave deliverable) |
| `bin/orama-system/skills/hermes-harness/scripts/hermes_status.sh` (planned CREATE; not on disk yet) | (unresolved: path not found — Wave deliverable) |
| `bin/orama-system/skills/hermes-harness/scripts/json-response.sh` (planned CREATE; not on disk yet) | (unresolved: path not found — Wave deliverable) |
| `tests/test_hermes_status.py` (planned CREATE; not on disk yet) | (unresolved: path not found — Wave deliverable) |

### Perpetua-Tools (GitHub `main`)

| Path | Link |
| ---- | ---- |
| `src/hermes_harness.py` | [hermes_harness.py](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/src/hermes_harness.py) |

### Unresolved / corrected PT paths from plan prose

- `hermes_harness.py (plan assumed path)` — Actual tracked file: `src/hermes_harness.py` — see PT link below. Plan prose already notes no tracked file at the originally assumed path.
- `SPECS.md / docs/SPECS.md` — (unresolved: path not found)
- `orchestrator/hermes_harness.py` — (unresolved: path not found; use src/hermes_harness.py)
- Canonical PT Hermes runtime entrypoint: [`src/hermes_harness.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/src/hermes_harness.py)

<!-- /AUTO-GENERATED -->
---

## Progress (2026-08-06) — Wave 1–2 committed locally (no push)

**Branch:** `2026-08-05-002-hermes-graft-plan-reference-fix`  
**Tracking plan:** `OpenClaw/v1/2026-08-06-envelope-reconciliation-plan.md` (outside git, sibling to orama checkout)

```
Envelope reconciliation (Phases 0–5 local)  [████████████████████] 100%
  Phase 0  v1 plan artifact                 [████████████████████] 100%  done
  Phase 1  T-ENG-1 protocol + fixtures      [████████████████████] 100%  done
  Phase 2  Appendix C stub map (docs)        [████████████████████] 100%  done
  Phase 3  Wave 1 emit + F6/F7 fixes         [████████████████████] 100%  done
  Phase 4  Wave 2 hermes-status              [████████████████████] 100%  done
  Phase 5  git commit (local)                [████████████████████] 100%  done (push deferred)
```

| Phase | Item | State | Evidence |
| ----- | ---- | ----- | -------- |
| 0 | v1 plan + README index | **Done** | `OpenClaw/v1/2026-08-06-envelope-reconciliation-plan.md` |
| 1 | T-ENG-1 canonical protocol SoT | **Done** | `hermes-universal-invocation-protocol.md` — expanded shape, four-shape mapping, layer dictionary, bidirectional adapters |
| 1 | Envelope fixture tests | **Done** | `tests/test_hermes_invoke_envelope.py` — 12/12 pass |
| 2 | Appendix C → docs/next stub table | **Done** | See [Appendix C stub map](#appendix-c-stub-map-v21-deferred) below |
| 3 | `json-response.sh` canonical emitter | **Done** | `hermes-harness/scripts/json-response.sh` |
| 3 | `hermes-spawn --json` + F7 empty PID | **Done** | `hermes_spawn.sh` — `started_pid` preserved; macOS `Python` ps args match |
| 3 | `hermes-delegate --json` + F6 timeout | **Done** | `hermes_delegate.py` — wall-clock wait + non-blocking executor shutdown |
| 3 | F6 regression test | **Done** | `test_hermes_delegate.py` — 2/2 pass |
| 3 | `hermes-orama` streaming | **Scoped out** | unchanged this pass (per locked decision) |
| 4 | `hermes-status --json` + Appendix C stub rows | **Done** | `hermes_status.py`, `commands/hermes-status/SKILL.md` |
| 4 | `test_hermes_status.py` | **Done** | 3/3 pass |
| 4 | T-ENG-2 parallel canaries | **Done** | `verify_partner_canaries.py` — `ThreadPoolExecutor` |
| 4 | T-ENG-3 cache `resolve_pt_root` | **Done** | `resolve_perp_harness.sh` — `_RESOLVED_PT_ROOT_CACHE` |
| 5 | Commit + push | **Commit done** / push deferred | four logical local commits; push per user gate |

**Test snapshot (2026-08-06):** 38/38 pass — `test_hermes_invoke_envelope`, `test_hermes_status`, `test_hermes_delegate`, `test_hermes_spawn`, `test_resolve_perp_harness`.

### Appendix C stub map (v2.1++ deferred)

Plot each Appendix C platform gap to **reuse / stub / defer** — full build stays v2.1++.

| Appendix C gap | Reuse now (stub) | docs/next / code pointer | Full delivery |
| -------------- | ---------------- | ------------------------ | ------------- |
| Task API | Existing `/v1/jobs` + `JobSpec`/`JobStatus` | PT [`supervisor.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/supervisor.py); absorption plan | v2.1++ unified task API |
| Fleet manager | `FleetMode` / [`fleet_topology.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/fleet_topology.py) read-only facts | [`docs/next/fleet-mesh/`](../../docs/next/fleet-mesh/README.md), PT Phase-2 | v2.1++ |
| Verifier gate | Existing crystallization / dispatcher gate (orama) | absorption plan §6; `dispatcher.py` | v2.1++ server-side gate |
| Scheduler | `not_yet_implemented` in `hermes-status` subsystems | pending-work tracker | v2.1++ |
| Observability transport | Existing portal SSE / G7 scaffold (read-only mention) | [`G7-ASYNC-NOTIFICATIONS-ANALYSIS.md`](../../docs/next/fleet-mesh/G7-ASYNC-NOTIFICATIONS-ANALYSIS.md) | v2.1++ |
| Recursive workers | Explicitly out — `depth=0` lesson | absorption §4.1 | v2.1++ |
| HITL approval | Mesh HITL / control-plane auth where present | fleet-mesh PR #224 lineage | v2.1++ productization |

`hermes-status --json` exposes implemented subsystems (`pt_root`, `spawn_session`, `partner_canaries`, `profiles`) plus the Appendix C rows above as `not_yet_implemented` under `data.subsystems`.

---

## Requirements Restatement

You want to:

1. **Isolate comparison work** on a fresh branch + git worktree from **merged
   `main`** (not a feature PR branch).
2. Treat **`openclaw-skills/`** as the **source subset** — proven operational
   patterns for running/configuring OpenClaw agents (The Nine Skills + shared
   protocol/scripts).
3. Treat **`hermes-harness/commands/`** as the **target superset** — where
   durable Hermes operator commands live and should absorb useful OpenClaw
   patterns.
4. Produce a **repeatable farming methodology**: extract
   patterns/algorithms/strategies → map → graft/merge into existing Hermes
   commands and references — **without** duplicating OpenClaw-specific config
   paths where Hermes has its own runtime.

**Success looks like:** a documented gap matrix, a pattern catalog, prioritized
graft targets, and a phased merge plan that reuses existing absorption
infrastructure (`hermes-skill-absorption-map.md`, thin-skill installer,
universal invocation protocol) rather than inventing parallel skill trees.

---

## Current State (from `main` audit)

| Dimension | **SOURCE: `openclaw-skills`** | **TARGET: `hermes-harness/commands`** |
| --------- | ----------------------------- | -------------------------------------- |
| **Count** | 11 `SKILL.md` (9 ops + master + `codex-openclaw-agent`) | ~10 command cards + spawn/orama/delegate core |
| **Model** | Overlay cards extending `cc-openclaw` upstream; JSON envelope | Thin slash-command shells → `scripts/*.sh` / PT `hermes_harness.py` |
| **Strengths** | Lifecycle pipelines (status→change→stow→restart), secret hygiene, agent scaffolding templates, `json-response.sh`, universal protocol | PT-backed pipeline, LAN co-orchestration, partner dispatch, hardware policy gate, thin Hermes install |
| **Scripts** | `json-response.sh`, `openclaw-mcp-stdio-clean.sh`, `codex-openclaw-agent/scripts/*` | `hermes_spawn.sh`, `resolve_perp_harness.sh`, `install_hermes_thin_skills.py`, coord/LAN suite |
| **Existing bridge** | `universal-skill-protocol.md` already lists Hermes discovery path | `hermes-skill-absorption-map.md`, `openclaw-to-hermes-migration.md` |

**Key insight:** OpenClaw skills are **config/lifecycle operators** for a gateway
home; Hermes commands are **runtime orchestration operators** for AIAgent
instances. Grafting is **pattern transfer**, not file copy — e.g. adopt
OpenClaw's `status→verify→act` discipline inside `hermes-spawn` /
`pt-orama-*` gates, not `openclaw-stow` verbatim on Windows Hermes.

---

## Patterns to Mirror (codebase grounding)

| Category | Source | Pattern |
| -------- | ------ | ------- |
| **Naming** | `openclaw-skills/skills/openclaw-status/SKILL.md` | `{domain}-{verb}` skill IDs; overlay `extends:` upstream |
| **Invocation** | `openclaw-skills/references/universal-skill-protocol.md` | `{skill_id, args, agent_id, home}` — Hermes maps legacy `openclaw_home` → `home` when ingesting OpenClaw envelopes |
| **Shell I/O** | `openclaw-skills/scripts/json-response.sh` | `set -euo pipefail`; stdout=JSON only; stderr=logs |
| **Lifecycle** | `openclaw-status` → `openclaw-restart` → `openclaw-stow` | Always audit before mutate; canonical restart sequence |
| **Secrets** | `openclaw-add-secret` | Never in envelope; Keychain + 3-file propagation |
| **Hermes bridge** | `hermes-harness/scripts/resolve_perp_harness.sh` | Fail-closed PT root resolution before spawn |
| **Absorption** | `hermes-harness/references/hermes-skill-absorption-map.md` | Redirect stubs → canonical supersets; archive pointers |
| **Thin install** | `hermes-harness/scripts/install_hermes_thin_skills.py` | ≤60-line Hermes stubs pointing at `commands/*/SKILL.md` |
| **Tests** | `tests/test_hermes_spawn.py` | `pytest.mark.integration`; subprocess lifecycle in temp dirs |

---

## Phase 0 — Isolated Worktree (no code changes yet)

**Goal:** Compare without disturbing PR #268/#270 work.

```bash
cd /agent/repos/orama-system
git fetch origin main
git worktree add .worktrees/orama-hermes-graft-audit \
  -b cursor/hermes-openclaw-graft-audit-f559 origin/main
cd .worktrees/orama-hermes-graft-audit
git submodule update --init \
  bin/orama-system/skills/openclaw-skills/cc-openclaw  # if comparing upstream overlays
```

**Deliverable:** `docs/plans/2026-08-03-hermes-openclaw-graft-audit-plan.md` (this
file) + future `…-graft-audit.md` inventory artifact when Phase 1 completes.

---

## Phase 1 — Inventory & Diff Matrix (read-only)

### 1A. OpenClaw pattern harvest sheet

For each of **The Nine Skills** + `codex-openclaw-agent`, extract:

| Field | What to capture |
| ----- | --------------- |
| **Trigger** | When the skill fires |
| **Preconditions** | status checks, dry-run gates |
| **Algorithm** | ordered steps (numbered) |
| **Artifacts** | files/dirs touched |
| **Output contract** | JSON shape / follow-ups |
| **Harness notes** | `agent_compatibility` list |
| **Hermes analogue?** | existing command, partial, or gap |

### 1B. Hermes command capability sheet

For each `hermes-harness/commands/*`:

| Command | Runtime | PT dependency | OpenClaw overlap | Gap |
| ------- | ------- | ------------- | ---------------- | --- |
| `hermes-spawn` | `hermes_spawn.sh` | `hermes_harness.py` | partial (start/stop/status) | no pre-flight status audit |
| `hermes-orama` | PT pipeline | full 5-stage | none direct | no envelope/result JSON |
| `hermes-delegate` | ThreadPool executor | `spawn_hermes_agent` | parallel fan-out | no bounded result schema |
| `pt-orama-council/review/delegate` | partner scripts | Codex/AGY | council ≈ multi-agent | no OpenClaw-style verify chain |
| `windows-hermes-setup` | PS1 + install | PATH/canaries | ≈ bootstrap | different from `openclaw-new-agent` |
| `lan-peer-self-talk` | probe/assign | discovery JSON | Mac↔Win only | no OpenClaw gateway equivalent |

### 1C. Produce a **Graft Matrix** (single table)

Rows = OpenClaw patterns. Columns = Hermes target (command / script /
reference). Cells = `ADOPT` | `ADAPT` | `SKIP` | `NEW`.

**Example rows:**

| OpenClaw pattern | Hermes target | Action |
| ---------------- | ------------- | ------ |
| `openclaw-status` pre-flight audit | New `hermes-status` command or extend `hermes-spawn status` | **ADAPT** |
| Universal JSON envelope | All `commands/*` + `hermes_spawn.sh` stdout | **ADOPT** |
| `openclaw-restart` 5-step sequence | `coord_pulse.sh` / spawn recovery | **ADAPT** (no launchd on Win) |
| `openclaw-add-secret` 3-file sync | Hermes env + PT `.env.local` policy | **ADAPT** (no Keychain on Win) |
| `openclaw-dream-setup` memory cron | `pt-orama-lesson-mining` + GossipBus | **MERGE** |
| Agent directive templates | `install_hermes_profiles.py` + `bin/agents/*/SOUL.md` | **ALREADY ABSORBED** — verify parity |
| `codex-openclaw-agent` bind scripts | `dispatch_codex_partner.py` pattern | **ADAPT** for Hermes-native bind |

---

## Phase 1.5 — Reality checkpoint (2026-08-03 research)

**GBrain:** orama code index refreshed (905 pages). Memory corpus searchable.
**EXA + FireCrawl:** NousResearch delegation docs + `delegate_tool.py` scraped.
**PT `.agent/memory`:** PR222 Hermes staging, coord_pulse, portable-brain lessons.

Canonical taxonomy: `bin/orama-system/skills/hermes-harness/references/hermes-dispatch-taxonomy.md`

### Dispatch truth table

| orama name today | Actual lane | Native Hermes equivalent |
| ---------------- | ----------- | ------------------------ |
| `hermes-delegate` | **L-PT** ThreadPool + `spawn_hermes_agent` | `delegate_task` (not wired) |
| `hermes-orama` / `hermes_harness.py` | **L-PT** sequential `AIAgent.chat` | N/A (script, not in-session) |
| `hermes-spawn` | **L-PT** PT harness PID lifecycle | N/A |
| `coord_pulse.ps1` | **L-Fleet** cursor-agent one-shot | N/A |
| `subagent/win-coder/…` git branches | **L-Fleet** inbox coordination | N/A |
| `bin/agents/REGISTRY.yml` roles | **Staging** profile materialization | Profiles ≠ runtime children |
| Interactive Hermes `delegate_task` | **L-H1** | Canonical Nous behavior |

### Windows Hermes commands (session-evidence)

Verified in fleet results + `coord_pulse.ps1` (not hypothetical):

- `install.ps1`, `install-hermes-harness.ps1 -RunDoctor`
- `install_coord_pulse.ps1`, `coord_pulse.ps1 -DryRun`
- `hermes backup`, `hermes doctor`, `hermes profile list`
- `hermes_spawn.sh` start/stop/status (PID file, not `AIAgent.chat` probe)
- `cursor-agent --print --model composer-2.5` via coord_pulse enqueue

### Plan corrections recalled (Win / Hermes staging)

| Incident | Fix |
| -------- | --- |
| PR #222 body clobber (aguara replaced Phase B scope) | Append-only restore from ladder + review-gate docs |
| discover.py Win platform role | `RUNNING_ON_WINDOWS` + LM Studio model list |
| coord_pulse `$Args` collision | `-LanArgs` (matches `start.ps1`) |
| `.env.local` vs Task Scheduler | User-level env for `ORAMA_SYSTEM_PATH` / `PERPETUA_TOOLS_PATH` |
| SKILL.md all-`1.` procedure lists | LINT-010; Hermes reads raw markdown |

### Graft wave reorder (mandatory)

1. **Wave 0** — taxonomy doc + SKILL lane tags + registry `dispatch_lane` field
2. **Wave 1** — JSON envelope on shell commands (all lanes)
3. **SKIP** `recursive-spawn-protocol` → `hermes-delegate` until rename
4. **NEW** optional `hermes-native-delegate` card (L-H1 docs only)

### `bin/agents/` staging amendments

Add to each `REGISTRY.yml` role (or `agent.md` header):

| Role group | `dispatch_lane` | `native_hermes_delegate` |
| ---------- | --------------- | ------------------------ |
| context → crystallizer pipeline | `L-PT` | `false` |
| orchestrator | `L-Fleet` (Win default) | `false` |
| coder / win-researcher / autoresearcher | `L-Fleet` | `false` |
| hermes-monitor | `L-H1` when in interactive Hermes | `true` (future skills only) |

---

## Phase 2 — Farming Methodology (how to extract, not just list)

### 2A. Pattern taxonomy

Classify every harvested item into one bucket:

1. **Protocol** — envelopes, error shapes, chaining rules
   (`universal-skill-protocol.md`)
2. **Lifecycle** — ordered gates (status → dry-run → mutate → verify)
3. **Algorithm** — deterministic step lists (cron install, secret propagation)
4. **Technique** — idempotent scripts, marker regions, lock/PID patterns
5. **Skill card** — markdown operator surface (thin command)
6. **Script** — executable helper (belongs in `scripts/`, not SKILL body)

### 2B. Farming workflow (per pattern)

```text
1. READ  openclaw skill + upstream cc-openclaw baseline (if overlay)
2. EXTRACT numbered algorithm + I/O contract into a scratch card
3. MAP   to hermes-harness target via absorption map rules
4. CLASSIFY ADOPT | ADAPT | SKIP (OpenClaw-only paths → SKIP)
5. DRAFT minimal diff: command card + script + reference cross-link
6. VERIFY against hermes-universal-invocation-protocol.md envelope
7. REGISTER in hermes-skill-absorption-map.md (additive row)
8. TEST  pytest integration for any new shell script behavior
```

### 2C. Anti-patterns (do not farm)

- Copying `openclaw_home`, `stow`, `launchctl`, or `jobs.json` handling into
  Hermes Win paths
- Duplicating skills already marked **absorbed** in
  `hermes-skill-absorption-map.md`
- Creating parallel trees under `~/.hermes/skills/` without
  `install_hermes_thin_skills.py`
- Cross-repo symlinks (per orama policy — thin stubs + GitHub URLs only)

---

## Phase 3 — Grafting Strategy (merge into existing superset)

### Wave 0 — Dispatch taxonomy + path doctrine (DONE on graft branch)

**Goal:** Stop conflating L-H1 / L-PT / L-Fleet before any protocol or lifecycle grafts.

| Deliverable | Status |
| ----------- | ------ |
| `references/hermes-dispatch-taxonomy.md` | **Done** — three lanes, command catalog, graft rules |
| `references/openclaw-workspace-path-doctrine.md` | **Done** — ban `$OPENCLAW_ROOT` in committed prose |
| `references/openclaw-pattern-graft-registry.md` | **Done** — Wave 0 graft matrix |
| `commands/hermes-delegate` / `hermes-orama` / `hermes-spawn` SKILL wording | **Done** — L-PT lane tags; `hermes-delegate` ≠ `delegate_task` |
| `hermes-harness/SKILL.md` dispatch section | **Done** |
| `scripts/resolve_perp_harness.sh` fallback | **Done** — git crawl from ORAMA mother + `$HOME`; not `$OPENCLAW_HOME` |
| `references/workspace-path-resolution.md` | **Done** — git crawl rows; no layout literals |
| `bin/agents/REGISTRY.yml` | **Done** — `dispatch_lane` + `native_hermes_delegate` per role |
| `references/hermes-skill-absorption-map.md` | **Done** — additive Wave 0 row |
| Harness `references/results/*.md` `$OPENCLAW_ROOT` scrub | **Done** — historical fleet cards |
| `references/hermes-portable-brain-map.md` | **Done** — path doctrine pointer |

**Explicit SKIP (Wave 0):** graft OpenClaw `recursive-spawn-protocol` into `hermes-delegate`
until rename (e.g. `hermes-pt-parallel`). `hermes-delegate` stays L-PT documentation only.

**Path doctrine (committed prose):**

| Use | Do not use |
| --- | ---------- |
| `$REPO_ROOT`, `$ORAMA_SYSTEM_PATH`, `$PERPETUA_TOOLS_ROOT` | `$OPENCLAW_ROOT` |
| Git crawl: mother-of-orama + `$HOME` | Hardcoded workstation or layout paths in repo |
| `$HOME` for user-level runtime | `$OPENCLAW_HOME` for cross-repo discovery |

Canonical: `bin/orama-system/skills/hermes-harness/references/openclaw-workspace-path-doctrine.md`

### Plan-only reconciliation gate (2026-08-06)

This section closes the cross-repository design questions before Wave 1 or Wave
2 code begins. It is a planning contract, not an implementation claim.

#### Ownership boundary

| Surface | Owner | MVP responsibility |
| --- | --- | --- |
| Hermes command cards, shell adapters, result validation, and tests | `orama-system` | Define and emit the canonical envelope; preserve text output until opt-in migration is complete. |
| Hermes runtime, process execution, queues, and durable state | `Perpetua-Tools` | Consume the envelope and provide runtime facts through an adapter when a concrete runtime target exists. |
| Cross-repo protocol and compatibility table | `orama-system` canonical reference | Specify the contract once; PT consumes it and does not create a competing schema. |

The current PT checkout contains Hermes wrappers and coordination infrastructure,
but no tracked `hermes_harness.py` or authoritative `SPECS.md` matching the
plan's assumed runtime target. Wave 1/2 implementation must begin with a PT
target inventory and stop if no owning runtime file can be named. No guessed
path, new duplicate runtime, or cross-repo symlink is allowed.

#### One canonical result envelope

`hermes-universal-invocation-protocol.md` is the single source of truth. The
canonical result keeps the existing protocol's required fields and adds only
portable command metadata:

```json
{
  "status": "ok",
  "skill_id": "hermes-spawn",
  "agent_id": "hermes",
  "executor_id": "hermes",
  "command": "hermes-spawn",
  "action": "status",
  "data": {},
  "files_modified": [],
  "follow_up_actions": [],
  "warnings": [],
  "error": null
}
```

Rules:

1. `status` is authoritative: `ok`, `needs_input`, `partial`, `error`, or
   `blocked`. The legacy `ok: true|false` boolean is compatibility output only
   and must not be used by new callers.
2. `files_modified` and `follow_up_actions` are always arrays. They remain empty
   for read-only status checks.
3. `warnings` contains non-fatal information. A caller should distrust the
   result only when `status` is not `ok` or `error` is non-null.
4. `error` is either `null` or `{ "code": "...", "message": "..." }`. Messages
   state the problem, cause, and next safe action without secrets or workstation
   paths.
5. `data` is command-specific. Health reports put subsystem results under
   `data.subsystems`; invocation results may use `data.result`.

#### Compatibility mapping for the four existing shapes

| Existing shape | Reconciliation |
| --- | --- |
| Hermes protocol `{status, files_modified, follow_up_actions}` | Canonical baseline; add optional metadata and `error: null` on success. |
| OpenClaw `{status, data}` / `{status, message}` | Map `data` to `data`; map `message` to `error.message`; derive an error code from the command when absent. |
| Draft `{ok, command, action, data, warnings, error}` | Replace `ok` with canonical `status`; retain the other fields as optional metadata. |
| Canary `{canaries: [{status: PASS\|FAIL\|UNAVAILABLE\|SKIPPED}]}` | Keep the canary vocabulary inside `data.canaries`; map required FAIL/UNAVAILABLE to top-level `error`/`blocked`, optional failures to `partial`, and SKIPPED to a warning plus `follow_up_actions` when required. |

Canary records keep `name`, `status`, `detail`, and `required`. They do not
become a second top-level protocol. This lets old canary consumers continue to
read their list while new consumers use one result envelope.

#### Canonical health surface

Wave 2 uses one command: `hermes-status --json`. It is read-only and owns the
health rollup. A separate `hermes-doctor` command is deferred unless an existing
Hermes launcher requires that exact name; if needed, it must be a thin alias to
the same implementation, not a second health engine.

Each subsystem reports `ok`, `degraded`, or `not_yet_implemented` under
`data.subsystems`: PT root, spawn session, partner canaries, and profiles. The
top-level result is `ok` only when every implemented subsystem is `ok`; it is
`partial` when only optional checks are unavailable; it is `blocked` or `error`
when a required precondition or health check prevents safe mutation. During the
incremental rollout, `not_yet_implemented` does not by itself fail the report,
but it must remain visible with a follow-up action.

#### Execution gates after this plan-only pass

Wave 1 may start only after:

- a PT runtime owner and exact target file are named, or the PT portion is
  explicitly marked adapter-pending;
- all four mappings above have fixture tests;
- stdout migration is `--json` opt-in, with text output preserved;
- the verified `hermes-delegate` timeout/deadlock case and empty-PID display case
  have regression tests;
- Windows PowerShell output is either covered by a matching adapter or explicitly
  excluded with a documented reason.

Wave 2 may start only after Wave 1's envelope fixtures pass and the health
surface has bounded, parallel canary checks. `verify_partner_canaries.py` must
not be assumed parallel; its implementation and worst-case timeout must be
measured before `hermes-status` reuses it.

Appendix C remains deliberately deferred to the next control-plane increment:
task API, fleet manager, scheduler, observability transport, server-side
verifier gate, recursive workers, and HITL approval. This MVP exposes the
contract those consumers will use; it does not pretend to implement them.

### Wave 1 — Protocol harmonization (low risk, high leverage)

**Files:**

| File | Action | Why |
| ---- | ------ | --- |
| `hermes-harness/references/hermes-universal-invocation-protocol.md` | UPDATE | Align L3 envelope with OpenClaw `{skill_id, args, agent_id, home}` shape |
| `hermes-harness/scripts/json-response.sh` | CREATE (port from openclaw) | Shared JSON stdout for all Hermes shell commands |
| `commands/hermes-spawn`, `hermes-delegate`, `hermes-orama` | UPDATE | Emit normalized JSON on success/error |

**Mirror:** `openclaw-skills/scripts/json-response.sh`,
`universal-skill-protocol.md` result schema.

### Wave 2 — Lifecycle commands (OpenClaw ops → Hermes ops)

| New/adapted command | Inspired by | Hermes behavior |
| ------------------- | ----------- | --------------- |
| `hermes-status` (NEW) | `openclaw-status` | PT root resolved, spawn sessions, partner canaries, profile list |
| `hermes-doctor` (NEW or extend `verify_partner_canaries.py`) | `openclaw-status` + ECC doctor | Single JSON health report |
| Extend `hermes-spawn start` | `openclaw-restart` pre-checks | Require `hermes-status` pass or `--force` |

**Mirror:** `commands/hermes-spawn/SKILL.md` + `scripts/hermes_spawn.sh` lock/PID
patterns.

### Wave 3 — Orchestration grafts (algorithms, not config)

| OpenClaw source | Hermes merge target |
| --------------- | ------------------- |
| `openclaw-dream-setup` token budgets + cron shape | `pt-orama-lesson-mining` + `references/update-all-agents-comms.md` |
| `openclaw-add-script` scaffold rules | New `hermes-add-script` or section in `skillify` references |
| `recursive-spawn-protocol.md` | **SKIP** → `hermes-delegate` until L-PT rename; optional future `hermes-native-delegate` (L-H1 only) |
| `codex-openclaw-agent` bind flow | `dispatch_codex_partner.py` + `pt-orama-delegate` preflight |

### Wave 4 — Command consolidation (reduce duplication)

- Inline Python in `hermes-delegate/SKILL.md` → extract `scripts/hermes_delegate.py`
  (mirror `hermes_spawn.sh` extraction)
- ~~Deduplicate PT root resolver: single `resolve_perp_harness.sh` sourced everywhere~~
  — **Done, pulled forward from Wave 4 (2026-08-05).** This was not just a DRY
  cleanup: the embedded resolver in `hermes-delegate/SKILL.md` returned the
  *first* marker-valid checkout on an ambiguous crawl instead of erroring, and
  silently fell through to crawl discovery when an explicit `PERPETUA_TOOLS_*`
  override was invalid — both violate the fail-closed contract
  `resolve_perp_harness.sh` implements and `tests/test_resolve_perp_harness.py`
  enforces. `hermes-delegate` now sources the canonical resolver instead of
  reimplementing it, closing a real correctness gap, not a style one.
- Update `install_hermes_thin_skills.py` manifest when new commands land

### Wave 5 — Documentation & absorption ledger

- Append rows to `hermes-skill-absorption-map.md` (additive only)
- Add `references/openclaw-pattern-graft-registry.md` — living map of ADOPT/ADAPT
  decisions
- Cross-link from `openclaw-skills/SKILL.md` → Hermes equivalents where absorbed

---

## Phase 4 — Comparison Worktree Outputs

Before any merge to `main`, the audit worktree should produce:

1. **`docs/plans/…-graft-audit.md`** — full Graft Matrix
2. **`.claude/plans/hermes-openclaw-graft.plan.md`** — executable task breakdown
   (if using PRD flow later)
3. **Gap scorecard** — % of Nine Skills + `codex-openclaw-agent` patterns with Hermes ADOPT/ADAPT coverage
4. **No code on `main`** until Wave 1 is approved

---

## Files Likely to Change (post-confirmation)

| File | Action |
| ---- | ------ |
| `hermes-harness/references/openclaw-pattern-graft-registry.md` | UPDATE (additive — created in Wave 0, per the Wave 0 table above) |
| `hermes-harness/references/hermes-universal-invocation-protocol.md` | UPDATE |
| `hermes-harness/scripts/json-response.sh` | CREATE |
| `hermes-harness/commands/hermes-status/SKILL.md` | CREATE |
| `hermes-harness/scripts/hermes_status.sh` | CREATE |
| `hermes-harness/scripts/hermes_delegate.py` | CREATE (extract) |
| `hermes-harness/references/hermes-skill-absorption-map.md` | UPDATE (additive) |
| `tests/test_hermes_status.py` | CREATE |
| `hermes-harness/scripts/install_hermes_thin_skills.py` | UPDATE |

---

## Validation

```bash
# Audit worktree — inventory only
find bin/orama-system/skills/openclaw-skills -name SKILL.md | wc -l
find bin/orama-system/skills/hermes-harness/commands -name SKILL.md | wc -l

# After each wave
python3 -m pytest tests/test_hermes_spawn.py tests/test_hermes_status.py -q
python3 bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py --verify
bash scripts/ci/run_agent_security_scans.sh  # skill-scanner collisions
npx markdownlint-cli2 "bin/orama-system/skills/hermes-harness/**/*.md"
```

---

## Risks

| Risk | Likelihood | Mitigation |
| ---- | ---------- | ---------- |
| Confusing OpenClaw gateway ops with Hermes runtime ops | High | Graft Matrix `SKIP` column; platform tags on every command |
| Duplicating already-absorbed content | Medium | Start from `hermes-skill-absorption-map.md`; diff before write |
| PT `hermes_harness.py` boundary creep | Medium | Keep spawn/pipeline in PT; orama owns command cards + shell |
| Skill-scanner name collisions | Medium | `{skill-prefix}-*.md` naming (checklist lesson) |
| `cc-openclaw` submodule uninitialized | Medium | Phase 0 init; document upstream-only patterns separately |
| Win/Mac path divergence | High | Separate PS1 vs bash script pairs; shared JSON contract only |
| `resolve_perp_harness.sh`'s marker-file trust (2026-08-05 review) — any directory with `.git` + `orchestrator/fastapi_app.py`, or a `.paths` entry, is trusted as the PT root without validating it's actually the real repo (e.g. git remote origin) | Medium | Deferred: would need retrofitting all 9 existing fixture-based tests in `tests/test_resolve_perp_harness.py` (they use marker files, not real git repos with remotes) to add a remote-URL check safely. Tracked here, not silently dropped. |

---

## Recommended Execution Order

1. **Phase 0** — worktree + audit doc (this file)
2. **Phase 1** — Graft Matrix (read-only)
3. **Phase 1.5** — taxonomy + lane tags (this file §1.5 + `hermes-dispatch-taxonomy.md`)
4. **Wave 0** — lane tags on skills + REGISTRY; no `hermes-delegate` / `delegate_task` conflation
5. **Wave 1** — JSON protocol harmonization (smallest shippable graft)
6. **Wave 2** — `hermes-status` / doctor gate
7. **Waves 3–5** — deeper merges prioritized by Graft Matrix scores

---

## Acceptance Criteria

- [ ] Isolated worktree from `main` with audit artifact committed
- [ ] Graft Matrix covers all Nine OpenClaw skills + `codex-openclaw-agent`
- [ ] Every `ADOPT`/`ADAPT` row has a concrete Hermes command/script target
- [ ] No OpenClaw-only paths copied verbatim into Hermes Win flows
- [ ] Absorption map updated additively for each merged pattern
- [ ] Integration tests for new shell entrypoints
- [ ] `install_hermes_thin_skills.py --verify` passes after new commands

---

## Appendix A — OpenClaw Skills Tree Summary (`main`)

```text
openclaw-skills/
├── SKILL.md                          # Master skill (The Nine Skills index + ops rules)
├── cc-openclaw/                        # Upstream git submodule
├── codex-openclaw-agent/               # Orama extension: dedicated Codex sub-agent
├── references/                         # Shared cross-harness contracts
├── scripts/                            # Shared helpers (json-response.sh, etc.)
├── skills/                             # The Nine Skills (Orama overlays)
│   ├── openclaw-new-agent/SKILL.md
│   ├── openclaw-add-channel/SKILL.md
│   ├── openclaw-add-cron/SKILL.md
│   ├── openclaw-dream-setup/SKILL.md
│   ├── openclaw-add-script/SKILL.md
│   ├── openclaw-add-secret/SKILL.md
│   ├── openclaw-status/SKILL.md
│   ├── openclaw-restart/SKILL.md
│   └── openclaw-stow/SKILL.md
└── templates/                          # Agent directive scaffolds
```

**Dispatch stack (PT-Orama weave):**

```text
orama-system (L3) → Perpetua-Tools dispatcher (L2) → openclaw-skills/{skill_id} → OpenClaw home (L1)
```

---

## Appendix B — Hermes Harness Command Inventory (`main`)

| Command | Purpose |
| ------- | ------- |
| `hermes-spawn` | `start\|stop\|status` for background Hermes session |
| `hermes-orama` | Full Orama 5-stage pipeline via PT |
| `hermes-delegate` | 2–5 parallel executor workers |
| `pt-orama-council` | 5-model council coordination |
| `pt-orama-review` | Findings-first review |
| `pt-orama-delegate` | Bounded specialist subtask |
| `pt-hardware-policy` | Model↔hardware affinity gate |
| `lan-peer-self-talk` | Mac↔Win LAN probe |
| `windows-hermes-setup` | Windows PATH, ECC doctor, thin-skill install |
| `pt-orama-lesson-mining` | *(optional)* session insights → memory |

**Key scripts:** `resolve_perp_harness.sh`, `hermes_spawn.sh`,
`install_hermes_thin_skills.py`, `verify_partner_canaries.py`,
`dispatch_codex_partner.py`, LAN/coord suite (24 files total under `scripts/`).

---

## Appendix C — Known Gaps vs Full Orchestration Harness

| Present | Missing / deferred |
| ------- | ------------------ |
| Thin command cards + universal JSON envelope (partial) | No unified **task API** |
| Single-session spawn + parallel delegate | No **fleet manager** |
| Mac↔Win pulse + job queues | No **central scheduler** |
| Partner dispatch (Codex/AGY) | **L1 portal dispatch** blocked on P5 |
| GossipBus + inbox drops | No built-in OTel/Periscope transport in spawn/delegate |
| Hardware policy gate at edge | Pipeline model defaults not wired through PT ModelRegistry |
| Verifier stage in pipeline | No server-side verifier gate blocking crystallization |
| V1 `depth=0` | No recursive worker trees or HITL approval flows |

---

## Status

| Milestone | State |
| --------- | ----- |
| Phase 0 worktree | **Done** — ephemeral local worktree on `cursor/hermes-openclaw-graft-audit-f559` (path is workstation-specific, not tracked here). Note (2026-08-06 CEO review): a separate, now-stale worktree for this same branch still exists on disk at the original 2026-08-03 commit — PR #271 already merged this branch's Phase-0/1 work into `main`; the stale worktree is an orphaned local artifact, not evidence of unmerged work. Safe to prune (`git worktree remove`) once confirmed unneeded. |
| This plan document | **Done** — saved 2026-08-03; corrected 2026-08-05/06 across two review passes (internal contradictions, then this file's own stale Status row below) |
| Phase 1 Graft Matrix | **Pending** — read-only audit |
| Wave 0 | **Done** — dispatch taxonomy, path doctrine, lane tags (see Wave 0 table above) |
| Plan-only Wave 1-2 reconciliation | **Done** — ownership, canonical envelope, compatibility mappings, and execution gates recorded above; no code executed |
| T-ENG-1 (protocol SoT + fixtures) | **Done** — saved uncommitted on branch; see [Progress (2026-08-06)](#progress-2026-08-06--save-only-commit-deferred) |
| Wave 1-2 implementation | **Done** — four logical local commits (T-ENG-1, plan docs, Wave 1, Wave 2); 38/38 tests pass; **push deferred** |
| Wave 4 (partial) | **Done** — PT-root-resolver dedup (`resolve_perp_harness.sh` canonicalization) landed 2026-08-05, pulled forward ahead of Wave 1-2 as a correctness fix, not a sequencing violation |
| Waves 3, 5 | **Deferred** — reassess scope/priority after Wave 1-2 ships (see design doc Next Steps) |

---

## /autoplan Phase 1: CEO Review (2026-08-06)

Mode: **SELECTIVE EXPANSION** (autoplan default for feature-enhancement-on-existing-system plans). Premise gate (D1) confirmed by user: accept premises as stated, with explicit refinement to prioritize Wave 1-2 ahead of Waves 3-5 (captured in the design doc referenced in Status above).

### CEO Dual Voices

**CODEX SAYS (CEO — strategy challenge):**

The plan assumes the problem is "Hermes needs OpenClaw's operational rigor" instead of proving the higher-order problem: "Hermes needs to become a reliable orchestration product." Appendix C admits the actual missing platform primitives are a task API, fleet manager, scheduler, observability transport, verifier gate, recursive workers, and HITL flows — none of which this plan attacks. JSON envelope harmonization (Wave 1) is called "low risk, high leverage" but standardized stdout is infrastructure hygiene, not leverage, unless there's a consumer (scheduler, dashboard, verifier, retry engine) that doesn't exist yet. The plan optimizes internal taxonomy (Wave 0) before external utility, defers native delegation while polishing shell wrappers, and its Risk table + Acceptance Criteria are entirely inward-facing (repo shape, not user/adoption impact). Reframe: stop asking "which OpenClaw patterns should Hermes absorb" and ask "what is the smallest Hermes control plane that makes multi-agent work trustworthy" — OpenClaw grafting becomes a compatibility layer, not the roadmap.

**CLAUDE SUBAGENT (CEO — strategic independence):**

Grounded in the actual worktree/git state (not just the doc): confirmed a separate, stale comparison worktree for this branch, frozen at the original 2026-08-03 commit (`8909b691`) — PR #271 already merged this branch's work into `main`, so the stale worktree is orphaned, not evidence of unmerged work (now noted in Status above). Confirmed the plan's own Status table was self-contradictory — said "Wave 1+ Pending" while the plan body documented Wave 4 work as already done — surviving a dedicated 2026-08-05 inconsistency-fix commit (now fixed above). Echoes Codex's strategic point independently: Appendix C's real gaps (task API, fleet manager, verifier gate) are parked in an appendix with no wave/owner while a "Large" complexity effort goes into pattern harmonization instead. Flags a real architectural risk this org has been burned by before (dual Win-PS1/Mac-bash implementations drifting — same class of bug as the attribution-guard fragmentation this repo's own CLAUDE.md calls out as an invariant to avoid) with only a one-line mitigation. Flags the deferred `resolve_perp_harness.sh` remote-URL trust gap (Risks table) as plausibly a half-day additive-test fix, not the multi-week retrofit its current framing implies.

**CEO DUAL VOICES — CONSENSUS TABLE:**

```
═══════════════════════════════════════════════════════════════════════
  Dimension                              Claude    Codex     Consensus
  ─────────────────────────────────────  ────────  ────────  ─────────
  1. Premises valid?                     Partial   No        DISAGREE
  2. Right problem to solve?             No        No        CONFIRMED (both say: pattern-graft
                                                               is the wrong altitude vs Appendix C gaps)
  3. Scope calibration correct?          No        No        CONFIRMED (Wave 0/1 taxonomy work over-
                                                               indexed vs platform primitives)
  4. Alternatives sufficiently explored? No        No        CONFIRMED (neither "fix delegate rename
                                                               first" nor "attack Appendix C directly"
                                                               scored against chosen path)
  5. Competitive/market risks covered?   No        No        CONFIRMED (Risk table is inward-facing;
                                                               no adoption/migration/lock-in risk)
  6. 6-month trajectory sound?           No        Partial   DISAGREE (Claude: concrete evidence of
                                                               drift already happening; Codex: more
                                                               about strategic altitude than trajectory)
═══════════════════════════════════════════════════════════════════════
CONFIRMED = both agree. DISAGREE = models differ in framing (not contradiction — see below).
4 of 6 dimensions CONFIRMED between independent voices — strong convergent signal.
```

### USER CHALLENGE (surfaced at Final Gate — NOT auto-decided)

Both models, working independently (no shared context — Codex saw only the plan file; the
Claude subagent saw the plan file plus the live git/worktree state), converged on the same
strategic objection: **grafting OpenClaw patterns into Hermes commands (the plan's entire
premise, including the user's own Wave 1-2 prioritization) may be optimizing the wrong layer.**
Both point at this plan's own Appendix C (task API, fleet manager, scheduler, verifier gate,
recursive workers, HITL — all explicitly named as missing) as the higher-leverage target.
This is classified as a **User Challenge**, not a taste decision, per autoplan's Decision
Classification: both models recommend changing direction on something the user explicitly
specified (Wave 1-2 first). It is deferred to the Phase 4 Final Approval Gate for your
decision — not auto-decided here.

### Sections 1-10 (SELECTIVE EXPANSION mode, HOLD-SCOPE analysis + cherry-pick scan)

**Complexity check:** Plan touches ~9 files across Wave 1-2 scope (per "Files Likely to
Change" table) — within the 8-file smell threshold but close. No new classes/services;
all changes are to existing thin-wrapper commands, scripts, and reference docs.

**Section 1 (Architecture):** Examined the command→script→PT-pipeline dependency chain.
```
  openclaw-skills/scripts/json-response.sh (pattern source)
         │ (adapt, not copy — per Constraints)
         ▼
  hermes-universal-invocation-protocol.md (envelope shape, UPDATE)
         │
         ├──▶ hermes-spawn/SKILL.md ──▶ hermes_spawn.sh (stdout: plain → JSON)
         ├──▶ hermes-delegate/SKILL.md ──▶ [PT] hermes_harness.py (stdout: plain → JSON)
         └──▶ hermes-orama/SKILL.md ──▶ [PT] 5-stage pipeline (stdout: plain → JSON)
```
Coupling: new coupling is `hermes-status`/`hermes-doctor` (Wave 2) to four existing
subsystems (PT root resolution, spawn PID state, partner canaries, profile list) —
justified (that's the point of a health-check surface), but per Codex/Claude findings
above, none of these four are confirmed to already expose structured state — auto-decided
(P1, completeness): Eng phase must verify per-subsystem instrumentation before committing
effort estimate (already captured as a design-doc Next Step). Single point of failure:
none new — `hermes-status` reads existing state, doesn't gate it. Rollback: pure revert,
no data migration, no feature flag needed for Wave 1 IF the `--json` opt-in flag from the
design doc's Migration Note ships (auto-decided: adopt the flag, P1 completeness > shipping
a hard breaking change with only a grep-based "no consumers" check).

**Section 2 (Error & Rescue Map):**

```text
  METHOD/CODEPATH             | WHAT CAN GO WRONG          | EXCEPTION CLASS
  --------------------------- | -------------------------- | ------------------
  hermes-spawn (JSON output)  | PT root unresolved         | PT_ROOT_UNRESOLVED
                              | Spawn script crash         | SPAWN_FAILED
  hermes-status (new)         | Canary unreachable         | CANARY_TIMEOUT
                              | Profile list read fails    | PROFILE_READ_ERROR
                              | Partial subsystem state    | (see not_yet_implemented,
                              |  during incremental Wave 2 |  design doc)

  EXCEPTION CLASS         | RESCUED? | RESCUE ACTION                    | USER SEES
  ----------------------- | -------- | -------------------------------- | -------------------
  PT_ROOT_UNRESOLVED      | Y        | fail closed (existing behavior)  | JSON error envelope
  SPAWN_FAILED            | Y        | existing PID-file cleanup path   | JSON error envelope
  CANARY_TIMEOUT          | N ← GAP  | —                                | must degrade, not 500-equivalent
  PROFILE_READ_ERROR      | N ← GAP  | —                                | must degrade, not crash whole report
```

2 GAPs identified — both auto-decided (P1 completeness): `hermes-status`/`hermes-doctor`
must catch per-subsystem failures and report `degraded`/`not_yet_implemented` rather than
letting one subsystem's exception crash the whole health report. This is already captured
in the design doc's draft schema (top-level `ok` rollup rule) — logged as confirmed
requirement, not a new gap needing separate remediation.

**Section 3 (Security & Threat Model):** Attack surface: none new (no new network-exposed
endpoints; these are local CLI commands invoked by an operator or Hermes agent, same trust
boundary as existing `hermes-spawn`). Input validation: `hermes-status`/`hermes-doctor` take
no user input beyond existing invocation args. Secrets: explicitly out of scope for Wave 1-2
(deferred to Wave 3, per design doc). Injection: N/A (no template/SQL/prompt-injection surface
introduced by a JSON-formatting change). One real finding (auto-decided, P1): the
`resolve_perp_harness.sh` marker-file trust gap (any `.git` + marker file trusted as PT root
without a remote-URL check) is a genuine threat-model gap in a script this plan's Wave 1-2
work depends on — both Codex and the Claude subagent independently suggested it's cheaper
to fix additively than the plan's Risk table implies (one new fixture with a real remote,
not retrofitting the existing 9). Logged as a TODO (see below), not blocking Wave 1-2 (P6
bias toward action — the existing fail-closed-on-ambiguity behavior already mitigates the
worst case; the gap is "trusts a single unambiguous match without checking its remote,"
not "fails open on ambiguity").

**Section 4 (Data Flow & Interaction Edge Cases):** Only new "interaction" is CLI invocation
of `hermes-status`. Edge cases: called during partial Wave 2 rollout (not_yet_implemented
state, handled per Section 2), called when PT unreachable (existing fail-closed path,
reused), called concurrently by multiple operators (read-only status query, no write
contention). No gaps found beyond Section 2's GAPs.

**Section 5 (Code Quality):** DRY: Wave 1-2 explicitly reuses the `json-response.sh`
*pattern* (adapted, not copied verbatim per design doc's Clarity fix) — no violation.
Naming: `hermes-status` vs `hermes-spawn status` naming decision explicitly deferred to
this Eng phase (see below) rather than guessed. No over-engineering: the four-subsystem
health rollup is the minimum needed for the stated Wave 2 goal, not gold-plating.

**Section 6 (Test Review):**
```
  NEW CODEPATHS: JSON envelope emission (3 commands) x 2 (success/error) = 6 paths
  NEW COMMAND: hermes-status/doctor health rollup, 4 subsystems x 3 states (ok/degraded/
               not_yet_implemented) = up to 12 reportable combinations
  NEW ERROR/RESCUE PATHS: CANARY_TIMEOUT, PROFILE_READ_ERROR (Section 2 GAPs, now closed
               by the not_yet_implemented/degraded design)
```
Test coverage plan (auto-decided, P1 completeness — full coverage, not a sampling):
- Unit: envelope shape validation (schema assertion) for each of the 6 paths above.
- Integration: `hermes-status` against a live-but-degraded PT root (existing
  `tests/test_resolve_perp_harness.py` fixture pattern extends naturally here).
- 2am-Friday test: `hermes-status` called when PT root is ambiguous (2+ candidates) —
  must report `degraded` with the ambiguity error, not crash or hang.
- Hostile-QA test: call `hermes-status` mid-Wave-2-rollout (3 of 4 subsystems shipped) —
  must NOT report top-level `ok: false` for the unshipped 4th (this is exactly the
  `not_yet_implemented` design doc fix — now also a required test, not just a schema note).

**Section 7 (Performance):** No DB, no N+1 risk. `hermes-status` aggregates 4 subsystem
reads — worst case is 4 sequential canary timeouts; auto-decided (P5 explicit): run the 4
subsystem checks in parallel (existing pattern: `verify_partner_canaries.py` likely already
does concurrent canary checks — confirm and reuse in Eng phase, don't reinvent).

**Section 8 (Observability):** This IS the deliverable (a health-check surface), so
observability review is largely "does hermes-status itself satisfy the observability bar
for other commands." Auto-decided (P1): `hermes-spawn`/`hermes-delegate`/`hermes-orama`'s
new JSON error envelope must include enough context (which subsystem, what was attempted)
to reconstruct a failure 3 weeks later from logs alone — already captured in the draft
schema's `error.code`/`error.message` fields.

**Section 9 (Deployment & Rollout):** No DB migration. Feature-flag question already
resolved in the design doc (Migration Note: `--json` opt-in, default-safe fallback).
Rollout order: ship `--json` opt-in first, confirm no breakage, THEN flip default in a
follow-up — auto-decided (P6 bias toward action, but P5 explicit-over-clever: don't skip
the opt-in step just to move faster, since the whole point is avoiding an undiscovered
breaking change).

**Section 10 (Long-Term Trajectory):** Reversibility: 4/5 (a git revert undoes the code;
the JSON envelope shape becomes a soft contract once callers depend on it — hence the
opt-in-first sequencing). Technical debt: minimal if the `--json` flag has a stated removal
date once adoption is confirmed (auto-decided: add this as a TODO, don't leave the flag
permanent by default). The 1-year question: this section is where the CEO consensus
findings above are most relevant — a new engineer in 12 months reading a plan that shipped
Wave 1-2 (JSON envelopes) while Appendix C's task-API/scheduler/verifier-gate gaps remain
unaddressed may reasonably ask "why did we polish the wrapper instead of building the
missing engine?" — this is exactly the User Challenge surfaced above, not resolved by
Section 10 alone.

Section 11 (Design & UX): **SKIPPED — no UI scope detected** (Phase 0 grep: 2 stray
"layout" matches, not real UI terms; confirmed with user before this review began).

### NOT in scope (this Wave 1-2 pass)
- Secret hygiene graft (Wave 3) — explicitly deferred, not dropped (design doc).
- `hermes-delegate`/`delegate_task` rename — explicitly SKIPPED by the plan's own Wave 0
  decision; Claude subagent's Finding 7 (do the rename now, before more wave work references
  the old name) is logged as a TASTE DECISION for the final gate, not auto-decided, since
  reasonable people could disagree on urgency.
- `resolve_perp_harness.sh` remote-URL trust hardening — logged as TODO (P2), not blocking.
- Appendix C platform primitives (task API, fleet manager, scheduler, verifier gate,
  recursive workers, HITL) — this is the substance of the User Challenge above; NOT
  silently deferred, explicitly surfaced for the user's decision.

### What already exists
- `install_hermes_thin_skills.py` thin-wrapper install/verify pipeline — reused as-is,
  not rebuilt.
- `resolve_perp_harness.sh` fail-closed PT-root resolution — reused; its known gap
  (remote-URL trust) is logged as a TODO, not rebuilt from scratch.
- `verify_partner_canaries.py` — likely already does canary health checks; Eng phase
  should confirm reuse rather than reimplementing inside `hermes-status`.
- `openclaw-skills/scripts/json-response.sh` — the pattern source for the envelope shape
  (adapted, per design doc's Clarity fix, not copied verbatim).

### Dream state delta

```text
  CURRENT STATE                 THIS PLAN (Wave 1-2)          12-MONTH IDEAL (per Appendix C
                                                                + CEO consensus findings)
  Inconsistent Hermes  --->     Consistent JSON       --->    Unified task API, fleet
  command stdout,               envelope + health             manager, scheduler,
  no health gate                gate (this pass)              verifier gate, HITL flows
```

This plan's Wave 1-2 moves toward the ideal (a health gate and consistent envelope are
real prerequisites for a scheduler/verifier gate to consume), but does not reach it — the
CEO consensus above questions whether it's the highest-leverage next step vs. attacking
Appendix C's gaps more directly. Surfaced at Final Gate.

### Error & Rescue Registry
See Section 2 table above — 2 GAPs identified, both closed by the design doc's
degraded/not_yet_implemented rollup design (confirmed requirement, not open gap).

### Failure Modes Registry

| CODEPATH                  | FAILURE MODE          | RESCUED? | TEST? | USER SEES?      | LOGGED? |
| ------------------------- | --------------------- | -------- | ----- | --------------- | ------- |
| hermes-status subsystem   | Canary timeout         | Y (design)| Y (planned)| degraded state | Y |
| hermes-status subsystem   | Not-yet-shipped (Wave 2 partial) | Y (design)| Y (planned) | not_yet_implemented | Y |
| resolve_perp_harness.sh   | Ambiguous crawl match  | Y (existing)| Y (existing, 13/13)| ERROR + candidate list | Y |
| resolve_perp_harness.sh   | Untrusted remote (no URL check) | N ← GAP | N | silently trusts | Partial (deferred TODO) |

No CRITICAL GAPs (RESCUED=N AND TEST=N AND USER SEES=Silent) — the one open GAP
(remote-URL trust) does log its failure mode, just doesn't verify the remote.

### TODOS.md — proposed (auto-decided per P2/P3, logged individually)
1. **T-CEO-1 (P2, human ~half-day / CC ~20min)** — Add a remote-URL check to
   `resolve_perp_harness.sh` as an ADDITIVE new test fixture (real git remote), not a
   retrofit of the existing 9 fixture-based tests. Why: closes the marker-file trust gap
   both Codex and the Claude subagent flagged independently, at the smaller cost the
   original Risk table's framing didn't consider.
2. **T-CEO-2 (P3, human ~2h / CC ~10min)** — Prune the stale comparison worktree
   once confirmed its branch's work is fully captured in `main` via PR #271.
3. **T-CEO-3 (P3, taste — see Final Gate)** — `hermes-delegate`/`delegate_task` rename,
   timing TBD by user.

### Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---| ----- | -------- | -------------- | --------- | --------- | -------- |
| 1 | CEO | Fixed stale Status table (Wave 1+ marked Pending despite Wave 4 partial landing) | Mechanical | P5 explicit | Verified factually stale via direct file read | — |
| 2 | CEO | Adopt `--json` opt-in flag before flipping default JSON output | Mechanical | P1 completeness | Avoids undiscovered-caller breaking change | Hard cutover without flag |
| 3 | CEO | `hermes-status` health rollup needs per-subsystem degraded/not_yet_implemented states | Mechanical | P1 completeness | Section 2 GAPs; incremental Wave 2 rollout must not read as broken | Binary ok/broken rollup |
| 4 | CEO | Run 4 subsystem health checks in parallel, not sequential | Mechanical | P5 explicit | Avoids 4x latency; likely matches existing canary-check pattern | Sequential checks |
| 5 | CEO | `resolve_perp_harness.sh` remote-URL trust gap → additive TODO, not blocking | Mechanical | P6 bias to action | Existing fail-closed-on-ambiguity already mitigates worst case | Blocking Wave 1-2 on this fix |
| 6 | CEO | `hermes-delegate` rename timing | **TASTE** | — | Reasonable people disagree on urgency vs. Wave 1-2 focus | — surfaced at gate |
| 7 | CEO | Pattern-graft vs. attack Appendix C platform gaps directly | **USER CHALLENGE** | — | Both Codex + Claude subagent independently recommend reframing | — surfaced at gate |

### CEO Phase Completion Summary
```
+====================================================================+
|            MEGA PLAN REVIEW — COMPLETION SUMMARY (CEO)             |
+====================================================================+
| Mode selected        | SELECTIVE EXPANSION                          |
| System Audit         | git log/diff/stash reviewed; stale worktree  |
|                       | + stale Status table found and fixed         |
| Step 0               | Premise gate confirmed (D1); Wave 1-2 priority|
| Section 1  (Arch)    | 1 finding (envelope/flag sequencing) — decided|
| Section 2  (Errors)  | 2 GAPs mapped, both closed by design          |
| Section 3  (Security)| 1 finding (PT-root remote trust) — TODO       |
| Section 4  (Data/UX) | 0 unhandled edge cases beyond Sec 2            |
| Section 5  (Quality) | 0 issues found                                |
| Section 6  (Tests)   | Diagram produced, test plan specified          |
| Section 7  (Perf)    | 1 finding (parallelize subsystem checks)       |
| Section 8  (Observ)  | 0 gaps beyond existing draft schema             |
| Section 9  (Deploy)  | 0 risks beyond Migration Note (already fixed)  |
| Section 10 (Future)  | Reversibility: 4/5, debt items: 1 (flag removal)|
| Section 11 (Design)  | SKIPPED (no UI scope)                          |
+--------------------------------------------------------------------+
| NOT in scope         | written (4 items)                             |
| What already exists  | written (4 items)                             |
| Dream state delta    | written                                        |
| Error/rescue registry| 2 methods, 0 CRITICAL GAPS                     |
| Failure modes        | 4 total, 0 CRITICAL GAPS                       |
| TODOS.md updates     | 3 proposed                                     |
| Scope proposals      | 0 proposed (HOLD-scope analysis; no cherry-pick|
|                       | ceremony run — plan scope already narrowed by  |
|                       | design doc to Wave 1-2)                        |
| CEO plan             | design doc (informal office-hours) written     |
| Outside voice         | ran (Codex + Claude subagent)                  |
| Diagrams produced     | 3 (architecture, error flow, dream-state delta)|
| Unresolved decisions | 2 (1 taste, 1 USER CHALLENGE — both at gate)    |
+====================================================================+
```

**Phase 1 complete.** Codex: 8 strategic concerns. Claude subagent: 13 findings (5
critical/high). Consensus: 4/6 confirmed, 2 dimension framings differ (not contradictions).
Passing to Phase 2 (Design — SKIPPED, no UI scope) → Phase 3 (Eng Review).

---

## Phase 2: Design Review — SKIPPED

No UI scope detected (Phase 0 grep: 2 stray "layout" matches, not real UI terms). This is
a CLI/skill-graft plan with no user-facing screens, forms, or visual surfaces.

## /autoplan Phase 3: Eng Review (2026-08-06)

Scope challenge (Step 0): Wave 1-2 touches ~9 files, no new classes/services — below the
complexity-smell threshold; no scope-reduction gate triggered. Focus: Wave 1-2 (JSON
envelope harmonization + hermes-status/doctor), per design doc priority.

### Eng Dual Voices

**CODEX SAYS (eng — architecture challenge):** Would NOT approve Wave 1-2 as written.
The plan still doesn't resolve the "wrong layer" objection from CEO phase — execution
prioritizes JSON envelopes/status wrappers while Appendix C's real gaps stay parked behind
a gate, which is "not an architectural decision, it's a parked contradiction." Wave 1's
scope is understated: `hermes-delegate`/`hermes-orama` route into PT runtime behavior, and
the "Files Likely to Change" list has zero PT-side contract changes — if PT's process
prints mixed logs/results, wrapper-level JSON "either loses information, double-encodes,
or lies about success." The `resolve_perp_harness.sh` trust gap "should not be deferred if
Wave 2 depends on it" — `hermes-status` can certify the wrong PT checkout. Flags
`hermes-status` risks duplicating/contradicting existing `hermes-spawn status` (spawn
session state should be a reusable function, not reimplemented by a new wrapper).
Validation command only names spawn/status tests, not delegate/orama. **Independently
found the exact same `hermes_spawn.sh` empty-PID bug** the Claude subagent found (see below)
by reading the same 3 lines of code.

**CLAUDE SUBAGENT (eng — independent review):** Read the actual code, not just the plan
prose. **F6 (CRITICAL, verified):** `hermes-delegate`'s per-worker timeout is dead code —
`concurrent.futures.as_completed(future_by_task)` is called with no `timeout` argument, so
by definition it only yields already-completed futures; the subsequent
`fut.result(timeout=WORKER_TIMEOUT_SEC)` can never raise `TimeoutError`. If
`spawn_hermes_agent` hangs, the entire command hangs forever — no JSON, no error, nothing.
**F1 (HIGH):** four incompatible envelope schemas already coexist on disk (universal
protocol's `status` enum, `json-response.sh`'s flat shape, the design doc's `ok`/`data`
draft, and `verify_partner_canaries.py`'s `PASS/FAIL/UNAVAILABLE/SKIPPED` vocabulary) —
"JSON harmonization" is not a mechanical port, it's an unreconciled four-way schema
conflict. **F2 (HIGH):** `hermes-orama` execs PT's `hermes_harness.py` directly — JSON
harmonization for this command requires either a cross-repo PT change or buffering away
real-time pipeline progress (multi-minute pipelines currently stream; buffering means
silence until completion). **F3 (MEDIUM-HIGH):** `hermes-status`'s "profile list"
subsystem is raw third-party CLI text (confirmed: `install_hermes_profiles.py` has no
`list` action; `hermes profile list` is the upstream Nous binary, piped straight to
console with zero parsing anywhere in this repo). **F4 (HIGH):** `verify_partner_canaries.py`
runs canary checks SEQUENTIALLY (confirmed: no threading/asyncio in `main()`) — directly
contradicting the CEO phase's own Section 7 auto-decision to "reuse" an assumed-parallel
pattern; worst case ~9 minutes for one canary pass, which would block every gated
`hermes-spawn start` in a degraded environment. **F7 (MEDIUM, verified — same bug Codex
found independently):** `hermes_spawn.sh` clears `child_pid` before echoing it in the
success message — every successful start already prints an empty PID; once wrapped in a
JSON envelope, `data.pid` will be null on every success. **F8 (MEDIUM):** `hermes-spawn
status` uses the same exit code for "no session running" (normal) and "stale/broken
session" (real problem) — any caller branching on exit code alone conflates them.

**ENG DUAL VOICES — CONSENSUS TABLE:**

```
═══════════════════════════════════════════════════════════════════════
  Dimension                              Claude    Codex     Consensus
  ─────────────────────────────────────  ────────  ────────  ─────────
  1. Architecture sound?                 No        No        CONFIRMED (4-way schema conflict +
                                                               PT cross-repo boundary unaddressed)
  2. Test coverage sufficient?           No        No        CONFIRMED (existing envelope test
                                                               untouched by plan; delegate/orama
                                                               untested for the new shape)
  3. Performance risks addressed?        No        No        CONFIRMED (sequential canary checks
                                                               contradict CEO's own auto-decision)
  4. Security threats covered?           Partial   No        DISAGREE (Claude: incremental blast-
                                                               radius widening, logged; Codex:
                                                               should not be deferred at all)
  5. Error paths handled?                No        No        CONFIRMED (hermes-delegate deadlock;
                                                               empty-PID bug — both independently
                                                               found the SAME empty-PID bug)
  6. Deployment risk manageable?         Partial   No        DISAGREE (Claude: opt-in flag from
                                                               design doc mitigates; Codex: PT-side
                                                               contract drift risk remains open)
═══════════════════════════════════════════════════════════════════════
CONFIRMED = both agree. DISAGREE = models differ (real tension, not framing gap this time).
4 of 6 CONFIRMED. Both independently found the identical hermes_spawn.sh empty-PID bug —
strongest possible cross-model verification signal (same bug, zero shared context).
```

### Section 1: Architecture

Confirmed via direct code inspection (not just plan prose) — the JSON-envelope work
depends on reconciling FOUR existing incompatible shapes, not porting one script:

```
  hermes-universal-invocation-protocol.md   {status: ok|needs_input|partial|error|blocked,
                                              files_modified: [], follow_up_actions: []}
  openclaw-skills/scripts/json-response.sh  {status: ok, data: ...} / {status: error, message}
  design doc draft schema                   {ok: true/false, command, action, data, warnings,
                                              error: {code, message}}
  verify_partner_canaries.py --json         {canaries: [{name, status: PASS|FAIL|UNAVAILABLE|
                                              SKIPPED, detail, required}]}
```
Auto-decided (P5 explicit over clever, P1 completeness): pick ONE canonical shape and
make `hermes-universal-invocation-protocol.md` the single source of truth for it —
explicitly map the canary `PASS/FAIL/UNAVAILABLE/SKIPPED` vocabulary and the old `status`
enum onto it in writing before any Wave 1 code lands. This is now a required Wave 1
pre-step, not an implementation detail — logged as T-ENG-1 below.

`hermes-orama`'s cross-repo PT boundary (F2/Codex's "Files Likely to Change has zero
PT-side contract changes") is marked a **TASTE DECISION** for the gate: either (a) scope
`hermes-orama` out of Wave 1's JSON requirement and ship NDJSON/streaming-preserving output
in a follow-up, or (b) accept buffered output and lose real-time pipeline visibility. Both
models flagged this; neither prescribed which to pick — genuinely a product tradeoff.

### Section 2: Code Quality

`hermes-delegate`'s `as_completed()`/`fut.result(timeout=...)` pattern (F6) is flagged by
both the Claude subagent and Codex's independent architecture read as a textbook Python
concurrency footgun likely to recur in later-wave parallel-dispatch work — worth a repo-wide
grep for the same anti-pattern elsewhere before Wave 3+ ships more of it (auto-decided,
P5: fix now, note the pattern for future review).

### Section 3: Test Review

```
NEW CODEPATHS (Wave 1-2):                              COVERAGE
  JSON envelope emission (spawn/delegate/orama)          [GAP] existing test hard-codes
                                                          OLD schema (tests/test_hermes_
                                                          invoke_envelope.py) — not in the
                                                          plan's file list at all
  hermes-delegate per-worker timeout                     [GAP] [CRITICAL] no test exists for
                                                          the as_completed/timeout deadlock —
                                                          its absence is why F6 shipped unnoticed
  hermes_spawn.sh PID reporting                          [GAP] no test asserts the emitted pid
                                                          is non-empty on success
  hermes-status 4-subsystem health rollup                [GAP] no timeout-bound test for all-
                                                          canaries-degraded case; no malformed-
                                                          external-CLI-output test for profile list
COVERAGE: 0/4 new-surface items have a proposed test in the plan as written.
```
Auto-decided (P1 completeness — full test plan, not partial):
- Add `tests/test_hermes_invoke_envelope.py` to Wave 1's file list explicitly; update in
  lockstep with whatever schema T-ENG-1 settles on.
- Add a regression test for F6: a worker that sleeps forever; assert the overall command
  returns within `WORKER_TIMEOUT_SEC + epsilon` with an `error` entry for that task — this
  is the REGRESSION RULE (mandatory, no AskUserQuestion): F6 breaks existing behavior users
  may already depend on (a hung worker currently hangs forever with zero signal; a fix
  changes that to bounded + reported, which is correct, but any caller expecting the old
  silent-hang behavior — unlikely, but the rule doesn't permit skipping the test either way).
- Add a test asserting `hermes_spawn.sh`'s success message contains a non-empty PID (F7).
- Add a timeout-bound integration test for `hermes-status` under all-canaries-degraded
  conditions (exercises F4 directly).
- Add a fixture-based test feeding malformed/empty `hermes profile list` output through
  whatever parser gets written for that subsystem (exercises F3).

### Section 4: Performance

F4 (sequential canary checks, ~9min worst case) directly falsifies the CEO phase's Section
7 auto-decision ("likely already does concurrent canary checks"). Corrected auto-decision
(P1 completeness, supersedes the CEO-phase decision): parallelizing
`verify_partner_canaries.py`'s checks is now an explicit, costed Wave 2 task (not a free
reuse), and it blocks the "gate `hermes-spawn start` on `hermes-status` pass" design —
gating a spawn on a potentially 9-minute synchronous health check is a regression in
operator experience, not an improvement. Logged as T-ENG-2.

`resolve_pt_root()`'s uncached `$HOME` crawl (F5) becomes a hot path once `hermes-status`
polls it repeatedly — auto-decided (P5 explicit): cache the resolved PT root for the
session duration instead of re-crawling on every health check. Logged as T-ENG-3.

### Required Outputs

**Architecture diagram (Wave 1-2 dependency graph, corrected post-review):**
```
  json-response.sh pattern ──▶ [RECONCILE 4 SCHEMAS FIRST — T-ENG-1] ──▶ ONE canonical envelope
                                                                              │
       ┌──────────────────────────────────┬───────────────────────────────┼─────────────────┐
       ▼                                  ▼                                 ▼                 ▼
  hermes-spawn (fix F7, F8         hermes-delegate (fix F6         hermes-orama         verify_partner_
  first; then wrap in envelope)     CRITICAL first; then wrap)     (TASTE DECISION:      canaries.py
                                                                    stream vs buffer      (parallelize
                                                                    — gate)               first — T-ENG-2)
                                                                         │
                                                                         ▼
                                                          hermes-status/doctor (4-subsystem
                                                          rollup; depends on ALL of the above
                                                          being fixed/decided first, plus
                                                          resolve_pt_root caching — T-ENG-3)
```
This corrects the CEO-phase architecture diagram's implicit ordering (which showed
`hermes-status` as roughly parallel work) — Eng review shows it's actually LAST in the
dependency chain: every subsystem it aggregates needs its own fix first.

**Failure Modes Registry (updated):**
```
  CODEPATH                    | FAILURE MODE                  | RESCUED? | TEST? | USER SEES?        | LOGGED?
  ------------------------------|--------------------------------|----------|-------|--------------------|--------
  hermes-delegate (F6)          | Worker hangs forever           | N ← CRITICAL GAP | N | Nothing — silent hang | N
  hermes_spawn.sh (F7)          | Success msg prints empty PID   | N ← GAP  | N     | Malformed pid field | N
  hermes-spawn status (F8)      | "no session" vs "broken" conflated | N ← GAP | N | Same exit code for both | N
  verify_partner_canaries.py(F4)| Sequential checks, ~9min worst | Y (works, just slow) | N | Long hang, no progress | N
  resolve_pt_root (F5)          | Uncached $HOME crawl on hot path | Y (works, just slow) | N | Latency, not correctness | N
```
**1 CRITICAL GAP** (F6: RESCUED=N, TEST=N, USER SEES=Silent) — the plan's Wave 1-2 as
originally scoped would ship a JSON-envelope wrapper AROUND a command that can still hang
forever with zero output, defeating the entire point of the envelope work for that
codepath.

### NOT in scope (Eng phase additions)
- PT-side (`hermes_harness.py`) contract changes for `hermes-orama` streaming — cross-repo,
  out of this repo's Wave 1-2 scope; the TASTE DECISION above determines whether Wave 1
  descopes `hermes-orama` entirely instead.
- Fixing the upstream Nous `hermes profile list` CLI to support `--json` — not this repo's
  code to change; `hermes-status`'s profile-list subsystem must work around it or mark
  `not_yet_implemented`.

### What already exists (Eng phase additions)
- `verify_partner_canaries.py --json` — already has a structured (if incompatible) output
  mode; reuse the mapping, don't rebuild canary-checking logic.
- `tests/test_hermes_invoke_envelope.py` — already tests envelope validation against the
  OLD schema; extend it, don't write a parallel test file.

### TODOS.md — proposed (Eng phase, auto-decided per P1/P5, logged individually)
4. **T-ENG-1 (P1, human ~4h / CC ~30min, BLOCKS Wave 1)** — Reconcile the 4 incompatible
   envelope schemas into one canonical shape in `hermes-universal-invocation-protocol.md`
   before any Wave 1 code change. Why: F1 — without this, "port json-response.sh" and "the
   design doc's draft schema" are two different, contradictory targets.
5. **T-ENG-2 (P1, human ~2h / CC ~15min, BLOCKS the `hermes-spawn start` gate design)** —
   Parallelize `verify_partner_canaries.py`'s sequential checks. Why: F4 — a synchronous
   9-minute-worst-case health check cannot gate spawn starts without regressing operator
   experience.
6. **T-ENG-3 (P2, human ~1h / CC ~10min)** — Cache `resolve_pt_root()`'s result for session
   duration instead of re-crawling `$HOME` on every `hermes-status` poll. Why: F5.
7. **T-ENG-4 (P0/CRITICAL, human ~2h / CC ~15min, BLOCKS Wave 1 — fix before wrapping in
   JSON)** — Fix `hermes-delegate`'s `as_completed()` call to pass an overall `timeout=`
   and catch `TimeoutError` around the whole iteration, not per-`.result()` call. Why: F6 —
   verified, reproducible, silent-hang-forever bug; both Codex and Claude subagent
   independently confirmed by reading the code.
8. **T-ENG-5 (P1, human ~15min / CC ~5min, BLOCKS Wave 1 — trivial, do it now)** — Fix
   `hermes_spawn.sh`'s cleared-before-echo `child_pid` bug. Why: F7 — verified by both
   Codex and Claude subagent independently; a one-line fix (capture PID before clearing).
9. **T-ENG-6 (P2, human ~1h / CC ~10min)** — Give `hermes-spawn status` a distinct signal
   (exit code or JSON `state` field) for "no session" vs "stale/broken session." Why: F8.
10. **T-ENG-7 (P3)** — LM Studio log-tail exclusion from `hermes-doctor`'s default JSON
   payload (opt-in flag only). Why: F13, info-disclosure via aggregated/shared reports.

### Decision Audit Trail (Eng phase additions)

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|-----------------|-----------|-----------|----------|
| 8 | Eng | Reconcile 4 envelope schemas before any Wave 1 code (T-ENG-1) | Mechanical | P1/P5 | Verified 4-way conflict via direct code read, not assumed | Porting json-response.sh as-is |
| 9 | Eng | `hermes-orama` stream-vs-buffer JSON decision | **TASTE** | — | Real product tradeoff, both models flagged, neither prescribed | — surfaced at gate |
| 10 | Eng | Parallelize canary checks before gating spawn on health (T-ENG-2), supersedes CEO Section 7's "assume parallel" decision | Mechanical | P1 | CEO-phase assumption falsified by direct code read | Trusting the CEO-phase assumption |
| 11 | Eng | Fix hermes-delegate timeout deadlock before JSON-wrapping (T-ENG-4) | Mechanical | P1/P5 | CRITICAL verified bug, cross-model confirmed | Wrapping the bug in JSON as-is |
| 12 | Eng | Fix hermes_spawn.sh empty-PID bug (T-ENG-5) | Mechanical | P5 | Verified, trivial, cross-model confirmed independently | — |
| 13 | Eng | Codex's "would not approve Wave 1-2 as written" bottom line | **reinforces USER CHALLENGE #7** | — | Independent second model reaches the same "wrong layer" conclusion from a different angle (code-level, not strategy-level) | — surfaced at gate |

### Eng Phase Completion Summary
```
+====================================================================+
|            MEGA PLAN REVIEW — COMPLETION SUMMARY (ENG)             |
+====================================================================+
| Section 1  (Arch)    | 2 findings (4-schema conflict, PT boundary) |
| Section 2  (Quality) | 1 finding (concurrency footgun, note for later)|
| Section 3  (Tests)   | 4 GAPs, all closed with proposed tests       |
| Section 4  (Perf)    | 2 findings, 1 supersedes a CEO-phase decision|
| Architecture diagram  | produced (corrected dependency ordering)     |
| Failure modes         | 5 total, 1 CRITICAL GAP (F6)                 |
| TODOS.md updates      | 7 proposed (2 P0/P1 BLOCKING Wave 1)         |
| Outside voice          | ran (Codex + Claude subagent)                |
| Cross-model verify     | IDENTICAL bug (empty PID) found independently|
| Unresolved decisions   | 2 (1 taste — stream/buffer; 1 reinforces the |
|                        | CEO-phase User Challenge, both at Final Gate)|
+====================================================================+
```

**Phase 3 complete.** Codex: 6 findings (would not approve as written). Claude subagent:
16 findings (1 CRITICAL, 4 HIGH). Consensus: 4/6 confirmed, 2 genuine disagreements (not
framing gaps). Both models independently found the identical `hermes_spawn.sh` empty-PID
bug — the strongest possible cross-model verification signal this session. Passing to
Phase 3.5 (DX Review).

## /autoplan Phase 3.5: DX Review (2026-08-06)

DX scope confirmed in Phase 0 (strong signal: 65+ matches for "openclaw"/"agent"/
"command"/"SKILL.md" — this is a developer/operator-facing CLI surface). Persona:
Hermes/orama operator invoking `hermes-spawn`/`hermes-delegate`/`hermes-orama`.

**Codex DX voice: [codex-unavailable]** — the call errored (MCP transport failure,
exit code 1, no usable response) rather than timing out or hitting an auth wall.
Tagged per the degradation matrix; proceeding subagent-only for this phase
(source: `subagent-only`).

**CLAUDE SUBAGENT (DX — independent review):** Verified directly against the actual
command-card files (not just the plan), and against `openclaw-status/SKILL.md` as the
explicit comparison baseline the plan itself says it wants to mirror. Two CRITICAL
findings: **D4** — `hermes-delegate`'s name collides, in the operator's mental model,
with Hermes's own native `delegate_task` capability; disambiguation today is 100% prose
(warnings scattered across 4 different docs) with zero runtime mechanism preventing the
mistake. The plan defers this as a "taste decision" (T-CEO-3) — DX review disagrees with
that classification: a command name colliding with a different capability, for the same
user, in the same product, is a naming defect, not a style preference, and the cost of
the eventual rename only grows as more waves reference the current name. **D9** —
independently re-verified F6 (the `hermes-delegate` silent-deadlock bug) directly against
the code; this is now the THIRD independent voice (2 in Eng phase, 1 here) to find the
identical bug by reading the same 6 lines of Python. Also found: no zero-to-first-call
onboarding doc (D1, HIGH — TTHW effectively unbounded), required credential env vars for
`hermes-spawn`/`hermes-orama` named nowhere in this repo (D2, HIGH), the documented JSON
envelope protocol doesn't match any command's actual current output — not even
`hermes-delegate`'s own JSON, which uses a fourth, different ad-hoc shape (D7, HIGH — this
independently reproduces the Eng phase's F1 four-schema finding from a docs-vs-reality
angle instead of a code-reconciliation angle), only 1 of 7 distinct error paths includes a
docs link (D8, HIGH), zero copy-paste example invocations exist for any of the 3 commands
(D11, HIGH), and the two escape hatches Wave 1-2 is about to build opinions around
(task-count override, JSON-output toggle) don't have an existing convention to extend —
Wave 1 would be establishing the pattern from scratch, risking a 4th inconsistent grammar
on top of the 3 that already exist across the commands' input argument shapes (D5/D14).

### DX Scorecard

| Dimension | Score | Note |
|---|---|---|
| Getting started (TTHW) | 2/10 | No onboarding doc; env vars for credentials undocumented in-repo (D1, D2) |
| API/CLI naming | 3/10 | `hermes-delegate` name collision is CRITICAL (D4); 3 incompatible arg grammars (D5) |
| Error messages | 4/10 | 1 genuinely good error (PT-root resolution) not applied elsewhere (D8) |
| Docs findability | 3/10 | Zero copy-paste examples; registry table is implementation- not task-oriented (D11, D12) |
| Upgrade/deprecation path | 5/10 | `--json` opt-in flag design (already adopted in CEO phase) covers this if applied consistently |
| Escape hatches | 6/10 | Most defaults ARE overridable (4 env vars found); the 2 that aren't are exactly what Wave 1-2 touches (D6, D14) |
| Consistency | 3/10 | Same issue as naming — 3 commands, 3 different grammars, no stated rationale |
| Overall | **3.7/10** | Pre-Wave-1-2 baseline; this is what the JSON/status work is being layered onto |

### Developer Journey Map (9-stage)

```
1. Discover           → hermes-harness/SKILL.md (600+ lines, mixed concerns)     [FRICTION]
2. Understand scope   → no task-oriented index, only implementation taxonomy    [FRICTION: D12]
3. Find credentials   → not named in this repo; must open PT's hermes_harness.py [FRICTION: D2]
4. First invocation    → no copy-paste example exists for any command            [FRICTION: D11]
5. First success       → hermes-spawn prints "pid " (empty) — looks broken       [FRICTION: D10/F7]
6. First error         → 6 of 7 error paths give no fix or docs link             [FRICTION: D8]
7. Try hermes-delegate → name suggests native delegation; isn't                 [FRICTION: CRITICAL D4]
8. Something hangs     → silent forever, zero signal (worker deadlock)          [FRICTION: CRITICAL D9/F6]
9. Give up or escalate → no smoke test scoped to exactly these 3 commands       [FRICTION: D13]
```
Every one of the 9 stages has at least one friction point — this is the "before" state
Wave 1-2 is being layered onto, not a hypothetical.

### Developer Empathy Narrative

"I'm an operator who just cloned this repo. I want to run one Hermes task. I find
`hermes-harness/SKILL.md` and it's 600+ lines mixing install steps, PATH setup, Windows
provisioning, and LAN coordination protocol with the three commands I actually want. I
find `hermes-spawn` and try `start "do the thing"` — it prints '✅ Hermes started (pid ,
session default)' with no PID. Did it work? I check `hermes-spawn status` — that works,
so I guess it's fine, but I don't trust the first message anymore. Now I want to run 3
tasks in parallel and I reach for `hermes-delegate` because the name matches what I want
— nothing warns me at the command line that this isn't native delegation, only a
paragraph buried in a doc I didn't read. One of my 3 tasks hangs. Nothing happens. No
error, no timeout, no partial results. I wait. I wait more. Eventually I Ctrl-C and have
no idea if it did anything at all."

### TTHW Assessment

Current: **unbounded** (no onboarding doc; operator must self-assemble the path across
4+ files, 1 cross-repo). Target: **under 5 minutes** per DX benchmark. Gap: a single
quickstart doc (T-DX-1 below) plus fixing D10/F7 (empty PID) closes most of the gap to
target — these are both cheap relative to Wave 1's existing scope and directly improve
the FIRST thing an operator sees.

### DX Implementation Checklist
- [ ] `hermes-harness/references/quickstart.md` — clone PT, set 1 env var, first
      `hermes-spawn status`, first `hermes-spawn start`, expected output (T-DX-1)
- [ ] Apply `openclaw-status`'s section template (Purpose/When to Use/Inputs/Procedure/
      Output Contract/Gotchas/See Also) to `hermes-spawn`, `hermes-delegate`,
      `hermes-orama` SKILL.md files (T-DX-2)
- [ ] Retrofit all 7 error paths to the `resolve_perp_harness_script` house style
      (problem + cause + fix + docs link) — same work item as Eng phase's Section 3
      test-gap closure, do together (T-DX-3, folds into T-ENG-1's envelope work)
- [ ] One copy-paste example block per command (literal call → literal output →
      next-step-on-error) (T-DX-4)
- [ ] `--json`/`HERMES_JSON=1` convention adopted uniformly across all 3 commands in the
      SAME Wave 1 change, not command-by-command (T-DX-5, reinforces CEO phase's
      `--json` opt-in decision)

### TODOS.md — proposed (DX phase, auto-decided per P1/P5 except where noted)
11. **T-DX-1 (P1, human ~2h / CC ~15min)** — Write `hermes-harness/references/
    quickstart.md`. Why: D1, TTHW currently unbounded.
12. **T-DX-2 (P2, human ~3h / CC ~20min)** — Apply `openclaw-status`'s section template
    to all 3 command cards. Why: D3, D11 — the plan already names this template as the
    pattern to mirror but hasn't applied it to the commands it's grafting onto.
13. **T-DX-3 (P1, folds into T-ENG-1)** — Retrofit error messages to the house style.
    Why: D8.
14. **T-DX-4 (P2, human ~1h / CC ~10min)** — Add copy-paste example blocks. Why: D11.
15. **T-DX-5 (P1, folds into T-ENG-1/Wave 1)** — Adopt one `--json` convention across all
    3 commands simultaneously. Why: D14.

### Decision Audit Trail (DX phase additions)

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|-----------------|-----------|-----------|----------|
| 14 | DX | `hermes-delegate` rename urgency — DX voice reclassifies T-CEO-3 from taste to defect | **TASTE (elevated)** | — | 3rd independent voice (CEO Claude subagent, DX Claude subagent) now calls this a naming defect, not a preference; still surfaced at gate since it's a rename with real migration cost, not auto-fixable | — |
| 15 | DX | Bundle error-message retrofit + `--json` convention into Wave 1's T-ENG-1, not separate follow-up work | Mechanical | P4 DRY | Same files, same PR, avoids two touch-passes on identical lines | Separate DX-only PR after Wave 1 ships |
| 16 | DX | Codex DX voice unavailable this phase (MCP transport error, not timeout/auth) | Mechanical | — | Degradation matrix: proceed subagent-only, tag `[codex-unavailable]` | Retrying indefinitely |

### DX Phase Completion Summary
```
+====================================================================+
|            MEGA PLAN REVIEW — COMPLETION SUMMARY (DX)              |
+====================================================================+
| Product type          | Internal CLI/operator tooling (Hermes harness)|
| Initial DX score       | 3.7/10 (pre-Wave-1-2 baseline)                |
| TTHW current/target    | Unbounded / <5 min                            |
| Developer journey map  | produced (9 stages, friction at every stage)  |
| Empathy narrative      | written                                       |
| DX Implementation Checklist | 5 items                                  |
| Outside voice          | Claude subagent only (Codex unavailable)      |
| Cross-model verify     | 3rd independent confirmation of F6 deadlock   |
| Unresolved decisions   | 1 (hermes-delegate rename — elevated priority,|
|                        | still surfaced at gate, not auto-decided)     |
+====================================================================+
```

**Phase 3.5 complete.** DX overall: 3.7/10. TTHW: unbounded → target <5 min. Codex:
unavailable (MCP transport error). Claude subagent: 14 findings (2 CRITICAL, 4 HIGH).
Third independent confirmation of the `hermes-delegate` deadlock bug (F6/D9). Passing to
Phase 4 (Final Gate).

## Phase 4: Final Approval Gate (2026-08-06)

**Pre-gate check (user-directed):** before deciding, checked PT's GossipBus claim board
(`scripts/agent_coordination.py agents` / `list` / `queue list`) for concurrent work —
no open claims there. Then discovered independently, via `git log`, that this check
under-covered the real signal: **a concurrent agent (registered this session as
"Relay Cursor Agent", `bin/agents/relay-cursor/`) had been committing directly to THIS
branch, in this same working directory, while this review was in progress.** 5 new
commits appeared between this review's Eng phase and this gate (`ec8678b3` through
`f54c3d7a`) — including two `feat(hermes)` commits implementing Wave 1 and Wave 2.

**Verification performed before trusting any of this (per this session's own
"verify before replaying past agent work" discipline):** read the actual diffs, not just
commit messages, and ran the actual test suite rather than trusting the commit message's
claimed count.

```
$ python3 -m pytest tests/test_hermes_delegate.py tests/test_hermes_spawn.py \
    tests/test_hermes_status.py tests/test_resolve_perp_harness.py \
    tests/test_hermes_invoke_envelope.py -q
38 passed in 3.30s
```
Confirmed genuine, correct fixes by reading the code directly:
- **T-ENG-4 (F6 deadlock):** FIXED — `hermes_delegate.py` now uses
  `concurrent.futures.wait(pending, timeout=remaining, return_when=FIRST_COMPLETED)`
  against a real `deadline`, cancels stragglers, reports them as `error` rows. Correct.
- **T-ENG-5 (F7 empty PID):** FIXED — `hermes_spawn.sh` line 285 now captures
  `local started_pid="$child_pid"` before line 287 clears `child_pid`. Correct.
- **T-ENG-2 (F4 sequential canaries):** FIXED — `verify_partner_canaries.py` now runs
  checks via `ThreadPoolExecutor(max_workers=min(len(check_specs), 4))`. Correct.
- **T-ENG-3 (F5 uncached PT-root crawl):** FIXED — `resolve_perp_harness.sh` added
  `_RESOLVED_PT_ROOT_CACHE`. Correct.
- **T-ENG-1 (F1 four-schema conflict):** RESOLVED — chose the EXISTING
  `hermes-universal-invocation-protocol.md` `status` enum as the canonical shape (the
  more conservative choice vs. introducing a 5th shape) and mapped canary
  `PASS/FAIL/UNAVAILABLE/SKIPPED` and the subsystem rollup onto it; the previously-stale
  `tests/test_hermes_invoke_envelope.py` (Eng finding F9) was updated in lockstep.
  Also additively addressed part of the **User Challenge**: `hermes-status --json`
  now exposes the Appendix C platform gaps (task API, fleet manager, scheduler,
  verifier gate, recursive workers, HITL) as explicit `not_yet_implemented` subsystem
  rows in the live health report — keeping the strategic question visible in the running
  system, not just in this plan doc.
- **T-ENG-6 (F8 status conflation):** SUBSTANTIALLY ADDRESSED — in `--json` mode,
  "no session" (`running:false`, not an error) and "broken" (`malformed_pid`/`stale_pid`
  error codes) are now distinguishable; plain-text mode still shares exit code 1 (legacy
  behavior, lower-priority since `--json` is the interface new callers will use).
- `hermes-orama` streaming (the TASTE DECISION from Eng phase): explicitly **scoped out**
  by the concurrent agent's own progress note ("unchanged this pass (per locked
  decision)") — consistent with this review's own framing of it as an open tradeoff, not
  silently resolved either way.

**Push status:** all 5 new commits are local-only; push explicitly deferred by the
concurrent agent's own commit message, consistent with this session's standing
"don't push until told" instruction. No conflict with session policy.

**Decision:** Given the above, most of what would have been "mandatory blockers before
Wave 1-2 ships" are already fixed and tested. **Option A stands** (proceed with Wave 1-2)
— it has, in effect, already happened, correctly, concurrently with this review. The
**User Challenge (pattern-graft vs. Appendix C platform primitives) remains open and
unresolved by design** — the concurrent agent's `not_yet_implemented` stub rows keep it
visible rather than resolving it either way; revisit after operator feedback on Wave 1-2.

**Taste decisions still genuinely open:** `hermes-delegate` rename timing (T-CEO-3,
elevated by DX to a defect, not a preference) and `hermes-orama` stream-vs-buffer
(explicitly deferred by the concurrent implementation, not decided).

### Implementation Tasks (aggregated across CEO + Eng + DX phases, status verified 2026-08-06)

- [x] **T-ENG-4 (P0/CRITICAL)** — `hermes-delegate` deadlock fix. **DONE**, verified
  (code read + test run). Files: `hermes_delegate.py`.
- [x] **T-ENG-5 (P1)** — `hermes_spawn.sh` empty-PID fix. **DONE**, verified.
- [x] **T-ENG-1 (P1)** — Envelope schema reconciliation. **DONE**, verified (kept
  existing `status` enum as canonical; test file updated in lockstep).
- [x] **T-ENG-2 (P1)** — Parallelize canary checks. **DONE**, verified.
- [x] **T-ENG-3 (P2)** — Cache `resolve_pt_root()`. **DONE**, verified.
- [x] **T-ENG-6 (P2)** — Status conflation. **SUBSTANTIALLY DONE** (JSON mode fixed;
  plain-text mode unchanged, lower priority).
- [ ] **T-DX-1 (P1, human ~2h / CC ~15min)** — Write
  `hermes-harness/references/quickstart.md`. **STILL PENDING** — confirmed no file
  matching `*quickstart*` exists under `hermes-harness/` as of this gate.
  - Surfaced by: DX D1 (TTHW currently unbounded)
- [ ] **T-DX-2 (P2, human ~3h / CC ~20min)** — Apply `openclaw-status`'s section
  template to the 3 command SKILL.md files. **STILL PENDING.**
  - Surfaced by: DX D3, D11
- [ ] **T-DX-4 (P2, human ~1h / CC ~10min)** — Copy-paste example block per command.
  **STILL PENDING.**
  - Surfaced by: DX D11
- [ ] **T-CEO-1 (P2, human ~half-day / CC ~20min)** — Additive remote-URL trust check
  for `resolve_perp_harness.sh`. **STILL PENDING** — confirmed no `remote`/`origin`
  check exists in the script as of this gate.
  - Surfaced by: CEO Section 3, reinforced by Codex Eng review
- [ ] **T-CEO-2 (P3, human ~2h / CC ~10min)** — Prune the stale
  grant-mvp worktree (ephemeral `/tmp` checkout) once confirmed fully captured in `main`.
- [ ] **T-CEO-3 (P3, taste — rename timing not resolved by this gate)** —
  `hermes-delegate`/`delegate_task` naming-collision fix, elevated from taste to a
  DX-flagged defect (3 independent voices), timing still the user's call.

_15 tasks total: **6 DONE/verified this gate** (2 CRITICAL/P0-P1 bug fixes + 4 P1-P2
correctness/perf fixes, all independently verified by reading code and running tests,
not by trusting a commit message), 6 P2 items still pending (docs/DX polish + 1 security
hardening item), 1 P3 cleanup, 1 P3 taste decision, plus the User Challenge kept
explicitly open. None dropped silently — every finding from all 3 phases maps to exactly
one task above or to the logged User Challenge._

### Cross-Phase Themes

**Theme: the empty-PID bug (F7/D10).** Found independently by 3 different voices across
2 different phases with zero shared context between them — Claude subagent (Eng phase,
reading code), Codex (Eng phase, reading code independently), and Claude subagent again
(DX phase, reading code independently a third time). This is the single highest-confidence
finding in the entire review — not because of severity, but because of independent
replication.

**Theme: the `hermes-delegate` deadlock (F6/D9).** Same pattern — found independently 3
times (Claude subagent + Codex in Eng phase, Claude subagent again in DX phase). Combined
with its CRITICAL severity (silent, unbounded hang with zero operator signal), this is the
single most load-bearing fix in the entire task list.

**Theme: "pattern-graft vs. platform primitives."** Raised independently by Codex in BOTH
the CEO phase (strategic framing) and the Eng phase (code-level: "would not approve as
written"), and by the Claude subagent in the CEO phase (evidence-grounded). Three
independent instances of the same underlying objection, from 2 models across 2 phases —
the strongest cross-phase signal in this review, now logged as the open User Challenge.

### Review Scores
- CEO: SELECTIVE EXPANSION mode; 4/6 dual-voice dimensions confirmed; 1 User Challenge, 1
  taste decision surfaced
- CEO Voices: Codex (8 strategic concerns), Claude subagent (13 findings, 5 crit/high),
  Consensus 4/6 confirmed
- Design: SKIPPED (no UI scope)
- Eng: 1 CRITICAL gap (hermes-delegate deadlock), 4/6 dual-voice dimensions confirmed
- Eng Voices: Codex (6 findings, "would not approve as written"), Claude subagent (16
  findings, 1 CRITICAL/4 HIGH), Consensus 4/6 confirmed
- DX: 3.7/10 overall, TTHW unbounded → target <5min
- DX Voices: Codex unavailable (MCP transport error), Claude subagent (14 findings, 2
  CRITICAL/4 HIGH), Consensus N/A (single voice)

### Deferred to TODOS.md
- Appendix C platform primitives (task API, fleet manager, scheduler, verifier gate,
  recursive workers, HITL flows) — the User Challenge itself; explicitly named, not
  silently dropped, revisit after Wave 1-2 ships.
- `hermes-orama` stream-vs-buffer JSON decision (TASTE, unresolved).
- `hermes-delegate` rename timing (TASTE, unresolved, elevated priority per DX).

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` (via /autoplan) | Scope & strategy | 1 | issues_open | 1 User Challenge, 1 taste decision, 6 auto-decided |
| Codex Review | `/codex review` (via /autoplan dual voices) | Independent 2nd opinion | 3 (CEO+Eng+DX) | issues_open | 8+6 findings across CEO/Eng; DX unavailable |
| Eng Review | `/plan-eng-review` (via /autoplan) | Architecture & tests (required) | 1 | issues_open | 1 CRITICAL gap, 16 findings (Claude), 6 findings (Codex) |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | SKIPPED | No UI scope detected |
| DX Review | `/plan-devex-review` (via /autoplan) | Developer experience gaps | 1 | issues_open | score 3.7/10, 14 findings, 2 CRITICAL |

- **CODEX:** Ran in CEO and Eng phases (8 strategic concerns; 6 architecture findings,
  "would not approve Wave 1-2 as written"); errored in DX phase (MCP transport failure,
  tagged `[codex-unavailable]`, degraded to Claude-subagent-only for that phase.
- **CROSS-MODEL:** Both Codex and the Claude subagent independently converged on the same
  strategic objection (pattern-graft vs. Appendix C platform primitives) across 2 separate
  phases, and independently found the identical `hermes_spawn.sh` empty-PID bug by reading
  the same lines of code with zero shared context — the strongest cross-model verification
  signal in this review.
- **VERDICT:** CEO + ENG + DX REVIEWED — 1 CRITICAL gap (F6) was confirmed FIXED and
  test-verified at this gate (concurrent implementation, `e17aad66`/`252e339f`, 38/38
  tests passing), along with 5 of 6 other Eng-phase blocking items. 1 User Challenge
  remains open by design (not a defect — an explicit strategic question). Design review
  not applicable (no UI scope). Eng review required gate: **CLEAR** — all P0/CRITICAL and
  P1 correctness items verified fixed; remaining P2 items (docs/DX polish, 1 security
  hardening) do not block, tracked as TODOs.

**UNRESOLVED DECISIONS:**
- User Challenge: pattern-graft (Wave 1-2 as scoped) vs. Appendix C platform primitives
  (task API, fleet manager, scheduler, verifier gate) — user decision: proceed with Wave
  1-2 (now shipped locally, unpushed), revisit Appendix C reframe as a live question —
  the concurrent implementation's `not_yet_implemented` stub rows in `hermes-status --json`
  keep this visible in the running system rather than resolving it either way.
- Taste: `hermes-orama` JSON stream-vs-buffer (explicitly scoped out this pass, not
  decided).
+ `hermes-delegate` rename timing (taste, elevated priority per DX review, not resolved).
