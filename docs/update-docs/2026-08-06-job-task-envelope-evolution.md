# Job / Task Envelope Evolution — Perpetua-Tools + orama-system

> Research report (2026-08-06). Sources: gbrain, Perpetua-Tools `.agent` memory, all LESSONS
> surfaces, and cross-repo SPECS/design docs.

## Related plan

Hermes OpenClaw graft audit plan (cross-linked): [`docs/plans/2026-08-03-hermes-openclaw-graft-audit-plan.md`](../plans/2026-08-03-hermes-openclaw-graft-audit-plan.md)

## Cross-repo references

<!-- AUTO-GENERATED cross-repo links -->

| Path | GitHub |
| ------ | -------- |
| `orama-system/docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md` | [blob](https://github.com/diazMelgarejo/orama-system/blob/main/docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md) |
| `orama-system/docs/2026-05-08-v1-supervisor-brainstorm.md` | [blob](https://github.com/diazMelgarejo/orama-system/blob/main/docs/2026-05-08-v1-supervisor-brainstorm.md) |
| `orama-system/docs/v2/14-supervisor-and-anthropic-patterns.md` | [blob](https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/14-supervisor-and-anthropic-patterns.md) |
| `orama-system/bin/agents/orchestrator/task_schema.py` | [blob](https://github.com/diazMelgarejo/orama-system/blob/main/bin/agents/orchestrator/task_schema.py) |
| `orama-system/bin/agents/dispatcher.py` | [blob](https://github.com/diazMelgarejo/orama-system/blob/main/bin/agents/dispatcher.py) |
| `orama-system/docs/LESSONS.md` | [blob](https://github.com/diazMelgarejo/orama-system/blob/main/docs/LESSONS.md) |
| `orama-system/docs/superpowers/specs/2026-05-14-rc1-orchestration-master-plan.md` | [blob](https://github.com/diazMelgarejo/orama-system/blob/main/docs/superpowers/specs/2026-05-14-rc1-orchestration-master-plan.md) |
| `orama-system/docs/plans/2026-08-03-hermes-openclaw-graft-audit-plan.md` | [blob](https://github.com/diazMelgarejo/orama-system/blob/main/docs/plans/2026-08-03-hermes-openclaw-graft-audit-plan.md) |
| `Perpetua-Tools/orchestrator/supervisor.py` | [blob](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/supervisor.py) |
| `Perpetua-Tools/orchestrator/contracts.py` | [blob](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/contracts.py) |
| `Perpetua-Tools/tests/test_contracts.py` | [blob](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/tests/test_contracts.py) |
| `Perpetua-Tools/tests/test_job_spec.py` | [blob](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/tests/test_job_spec.py) |
| `Perpetua-Tools/docs/LESSONS.md` | [blob](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/LESSONS.md) |
| `Perpetua-Tools/docs/adapter-interface-contract.md` | [blob](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/adapter-interface-contract.md) |
| `Perpetua-Tools/orchestrator/openclaw_skill_resolver.py` | [blob](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/openclaw_skill_resolver.py) |
| `Perpetua-Tools/.agent/memory/semantic/LESSONS.md` | [blob](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/.agent/memory/semantic/LESSONS.md) |
| `Perpetua-Tools/.agent/memory/semantic/lessons.jsonl` | [blob](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/.agent/memory/semantic/lessons.jsonl) |
| `OpenClaw/v1/07-steps+combined.md` | (path exists locally; not in orama-system or Perpetua-Tools GitHub — no blob URL rule) |
| `OpenClaw/v1/06-steps.md` | (path exists locally; not in orama-system or Perpetua-Tools GitHub — no blob URL rule) |

<!-- /AUTO-GENERATED -->

## Executive summary

**Yes — an absorption plan explicitly drove the MVP envelope/schema.** The canonical source is
[`orama-system/docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md`](https://github.com/diazMelgarejo/orama-system/blob/main/docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md)
(synthesized from `OpenClaw/v1/07-steps+combined.md` — local only; not in orama/PT GitHub).

The MVP is **two related envelope layers**, not one:

| Layer                        | Type(s)                                                                                          | Role                                       | Primary code                                                                                            |
| ---------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------ | ------------------------------------------------------------------------------------------------------- |
| Control-plane job envelope   | `JobSpec` + `JobStatus`                                                                          | Submit/cancel/replay jobs to PT supervisor | [`supervisor.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/supervisor.py) |
| Worker / cross-repo contract | `TaskEnvelope`, `WorkerResult`, `WorkerAssignment`, `OrchestrationSession`, `VerificationResult` | orama plans -> PT workers                  | [`contracts.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/contracts.py)   |

There is **no `JobEnvelope` or `TaskEnvelope` in the supervisor HTTP path today** — runtime
dispatch uses **`JobSpec`**. `TaskEnvelope` exists as the documented worker wire contract and is
tested in [`tests/test_contracts.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/tests/test_contracts.py),
but production dispatch (`OramaToPTBridge`) builds `JobSpec` directly, not `TaskEnvelope`.

Evolution: **OpenClaw v1 drafts -> 2026-05-08 supervisor brainstorm (JobSpec) -> 2026-05-14
absorption plan (five shared types + JobSpec extension) -> shipped code -> later
SkillEnvelope/Hermes envelopes (separate concerns).**

## Original specs

| Doc | Path | Date | What the envelope looked like |
| ----- | ------ | ------ | ------------------------------- |
| V1 supervisor brainstorm | [`orama-system/docs/2026-05-08-v1-supervisor-brainstorm.md`](https://github.com/diazMelgarejo/orama-system/blob/main/docs/2026-05-08-v1-supervisor-brainstorm.md) | 2026-05-08 | Structured handoff envelope = `JobState` enum (`queued -> running -> waiting_input -> succeeded -> failed -> cancelled`) + `JobSpec` dataclass (`job_id`, `intent`, `backend_hint`, `prompt`, `constraints`, `metadata`, `created_at`). Pattern #2: workers return `status + summary + artifact_pointer`. |
| OpenClaw v1 combined source | `OpenClaw/v1/07-steps+combined.md` (local only; not in orama/PT GitHub) | pre-2026-05-14 | Early unified schema: `OrchestrationSession`, `TaskEnvelope` (role, specialization, intent, prompt, depth=0), `WorkerAssignment`, `WorkerResult`, `VerificationResult`. Originally placed contracts in orama. |
| Unified Absorption Plan (canonical) | [`orama-system/docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md`](https://github.com/diazMelgarejo/orama-system/blob/main/docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md) | 2026-05-14 (marked canonical 2026-06-14) | §3 five shared types (PT-owned). §5.1 extends `JobSpec` with `role`, `specialization`, `session_id`, `parent_orchestrator_id`, `artifact_policy`, `depth`. Corrects ownership: contracts live in PT, orama imports. |
| V1 shipped record | [`Perpetua-Tools/docs/LESSONS.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/LESSONS.md) §2026-05-08 | 2026-05-08 | Documents shipped `OrchestrationSupervisor` + `JobSpec` + `JobStatus`, jsonl persistence, `/v1/jobs` API. |
| Adapter contract pointer | [`Perpetua-Tools/docs/adapter-interface-contract.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/adapter-interface-contract.md) | cites absorption plan | Points architecture authority to absorption plan; lists five shared types in `contracts.py`. |
| V2 planning (not shipped) | [`orama-system/docs/v2/14-supervisor-and-anthropic-patterns.md`](https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/14-supervisor-and-anthropic-patterns.md) | post-2026-05-08 | Proposes V2 `JobState` dataclass + SQLite replacing V1 `JobSpec`; explicitly says do not break V1 API. |
| orama planning types (not PT contracts) | [`orama-system/bin/agents/orchestrator/task_schema.py`](https://github.com/diazMelgarejo/orama-system/blob/main/bin/agents/orchestrator/task_schema.py) | post-absorption | `TaskPlan`, `StageSpec`, `WorkerSpec` — orama-side planning only; defers runtime types to PT. |

Brainstorm quote (origin of "handoff envelope"):

> "Structured handoff envelope with explicit lifecycle states | PT — `JobState` enum | Replace
> today's `{"ok": bool, "output": str, "elapsed": float}` with
> `queued -> running -> waiting_input -> succeeded -> failed -> cancelled`."
> — [`orama-system/docs/2026-05-08-v1-supervisor-brainstorm.md`](https://github.com/diazMelgarejo/orama-system/blob/main/docs/2026-05-08-v1-supervisor-brainstorm.md)
> §2, pattern #5

Absorption plan quote (worker contract):

> "Workers are one generic primitive... TaskEnvelope in, WorkerResult out... `depth` is always 0
> — workers do not enqueue sub-workers."
> — [`orama-system/docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md`](https://github.com/diazMelgarejo/orama-system/blob/main/docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md)
> §4.1

## Evolution timeline (with evidence)

- Pre-May 2026 — OpenClaw v1 design drafts. `OpenClaw/v1/06-steps.md` and
  `v1/07-steps+combined.md` (local only; not in orama/PT GitHub) describe `JobState`
  (SQLite-oriented) and the five-type schema including `TaskEnvelope`. Combined doc originally
  said contracts live in orama (`models/contracts.py`).
- 2026-05-08 — Supervisor brainstorm (reference, not execution plan).
  [`orama-system/docs/2026-05-08-v1-supervisor-brainstorm.md`](https://github.com/diazMelgarejo/orama-system/blob/main/docs/2026-05-08-v1-supervisor-brainstorm.md)
  names the gap as missing `submit_job -> get_status -> cancel/replay` and proposes `JobState` +
  `JobSpec` as the durable envelope. Status doc: "Brainstorm + plan only. Not implementation."
- 2026-05-08 — V1 supervisor shipped. Implemented as `JobSpec` (Pydantic) + `JobStatus` (enum) —
  `JobState` renamed to `JobStatus`. File-based jsonl, no DB. Documented in PT
  [`docs/LESSONS.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/LESSONS.md)
  §2026-05-08 and orama
  [`docs/LESSONS.md`](https://github.com/diazMelgarejo/orama-system/blob/main/docs/LESSONS.md)
  §2026-05-08. Code cites brainstorm §4.
- 2026-05-14 — Unified Absorption Plan canonicalized.
  [`orama-system/docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md`](https://github.com/diazMelgarejo/orama-system/blob/main/docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md)
  supersedes prior PLAN/PLAN2 docs; source = `OpenClaw/v1/07-steps+combined.md`. Key corrections
  applied before adoption: contracts PT-owned
  ([`orchestrator/contracts.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/contracts.py)),
  not orama; Pydantic v2 `@field_validator` instead of `@validator`; `LM_STUDIO_WIN_ENDPOINTS` env
  naming.
- 2026-05-14 — Shared contracts implemented.
  [`Perpetua-Tools/orchestrator/contracts.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/contracts.py)
  implements all five types per §3.
  [`tests/test_contracts.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/tests/test_contracts.py)
  dated 2026-05-14. `JobSpec` in
  [`supervisor.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/supervisor.py)
  extended per §5.1.
  [`tests/test_job_spec.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/tests/test_job_spec.py)
  explicitly references "§ 5.1 of the unified absorption plan."
- 2026-05-14+ — Cross-repo bridge.
  [`orama-system/bin/agents/dispatcher.py`](https://github.com/diazMelgarejo/orama-system/blob/main/bin/agents/dispatcher.py)
  (`OramaToPTBridge`) builds `JobSpec` and submits to `OrchestrationSupervisor`. Crystallization
  gate enforced per absorption plan §6.
- 2026-06-14 — RC-1 orchestration milestone.
  [`orama-system/docs/superpowers/specs/2026-05-14-rc1-orchestration-master-plan.md`](https://github.com/diazMelgarejo/orama-system/blob/main/docs/superpowers/specs/2026-05-14-rc1-orchestration-master-plan.md)
  marked RESOLVED; supervisor/orchestration built out.
- Later — Parallel "envelope" concepts (different domains): `SkillEnvelope` in
  [`Perpetua-Tools/orchestrator/openclaw_skill_resolver.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/openclaw_skill_resolver.py)
  (OpenClaw skill routing); Hermes dispatch envelope (orama-owned, L0/L2/L3 layers); LAN peer JSON
  envelope `{type, source, ts, data}` (transport, not job schema).
- Planned V2 (not MVP).
  [`docs/v2/14-supervisor-and-anthropic-patterns.md`](https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/14-supervisor-and-anthropic-patterns.md)
  proposes DB-backed `JobState` replacing V1 `JobSpec` — planning only.

## Absorption plan link

YES — explicitly and directly.

| Evidence | Relevance |
| ---------- | ----------- |
| Absorption plan header: "Canonical spec for orama-system + Perpetua-Tools v1. Supersedes all prior PLAN / PLAN2 docs." | Names itself as the v1 schema authority |
| §3 defines `TaskEnvelope`, `WorkerResult`, etc. | Invented the worker MVP data structure |
| §5.1 defines `JobSpec` extension | Extended the supervisor envelope for worker roles |
| §6 `OramaToPTBridge` | Bridge from orama plan -> PT `JobSpec`s |
| `contracts.py` line 7: `See: orama-system/docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md §§ 3–5` | Code points back to plan |
| `supervisor.py` JobSpec docstring cites "§ 5.1 of the unified absorption plan" | Runtime type annotated with plan section |
| orama `docs/LESSONS.md` line 25: Architecture authority: absorption plan | Cross-repo LESSONS index |

Correction the plan applied to the original combined spec: contracts moved from orama to PT (§0
Error 1) — the MVP schema owner is Perpetua-Tools, not orama.

## LESSONS clues (envelope / absorption / MVP)

### Perpetua-Tools `.agent/memory/semantic/LESSONS.md` + `lessons.jsonl`

| ID | One-line relevance |
| ---- | ------------------- |
| `lesson_3086671b02f6` | Core worker contract: `TaskEnvelope` in, `WorkerResult` out, `depth=0` enforced. Mined from absorption plan §3–§5. |
| `lesson_b5d28f5d6e08` | Fail-closed gateway rule from absorption plan §1.5. |
| `lesson_dd15b50b7f7d` | Strangler-fig / bridge pattern from absorption plan §6. |
| `lesson_f6de10a70a81` | Hermes dispatch envelope layers (separate from job/TaskEnvelope). |
| `lesson_c9fb1689c1aa` | OpenClaw->Hermes graft: taxonomy before JSON envelope. |
| `lesson_legacy_e0fb9321d79f` | LAN P2P shared JSON envelope `{type, source, ts, data}`. |
| `lesson_8560a9654f72` / `lesson_07e0aca4e41a` | G7 portal SSE envelope fields (orama MVP, not job schema). |

Sources:
[`Perpetua-Tools/.agent/memory/semantic/LESSONS.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/.agent/memory/semantic/LESSONS.md),
[`lessons.jsonl`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/.agent/memory/semantic/lessons.jsonl).

### Perpetua-Tools `docs/LESSONS.md`

| Section | One-line relevance |
| --------- | ------------------- |
| §2026-05-08 V1 supervisor shipped | Records `JobSpec` + `JobStatus` as shipped MVP; cites V2 spec for DB future. |
| §2026-06-28 Hermes dispatch | Hermes envelope authority is orama; PT owns hardware runtime only. |
| LAN peer channel | Transport envelope pattern, not orchestrator job schema. |

Source: [`Perpetua-Tools/docs/LESSONS.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/LESSONS.md).

### orama-system `docs/LESSONS.md`

| Section | One-line relevance |
| --------- | ------------------- |
| Architecture authority row | Points all architecture questions to absorption plan. |
| §2026-05-08 V1 supervisor shipped | Mirrors PT lesson on supervisor MVP. |
| §2026-06-28 Hermes envelope | L3/L2/L0 dispatch envelope (orthogonal to TaskEnvelope). |

Source: [`orama-system/docs/LESSONS.md`](https://github.com/diazMelgarejo/orama-system/blob/main/docs/LESSONS.md).

## Current MVP — code + mapping to design

### Control plane (what `/v1/jobs` uses)

Path: [`Perpetua-Tools/orchestrator/supervisor.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/supervisor.py)

- `JobSpec` (BaseModel) — immutable job descriptor; §5.1 fields: `role`, `specialization`,
  `session_id`, `parent_orchestrator_id`, `artifact_policy`, `depth`, plus `task_type`.
- `JobStatus` (str, Enum) — `queued`, `running`, `waiting_input`, `succeeded`, `failed`,
  `cancelled`.
Maps to: 2026-05-08 brainstorm `JobState` + `JobSpec`, extended by absorption plan §5.1.

### Worker / session contract (cross-repo)

Path: [`Perpetua-Tools/orchestrator/contracts.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/contracts.py)

- `TaskEnvelope` (§3.2), `WorkerAssignment` (§3.3), `WorkerResult`/`VerificationResult`
  (§3.4–3.5), `OrchestrationSession` (§3.1). Tests:
  [`tests/test_contracts.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/tests/test_contracts.py),
  [`tests/test_job_spec.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/tests/test_job_spec.py).

### orama -> PT dispatch (runtime bridge)

Path:
[`orama-system/bin/agents/dispatcher.py`](https://github.com/diazMelgarejo/orama-system/blob/main/bin/agents/dispatcher.py)
— `_build_spec()` imports PT `JobSpec`, not `TaskEnvelope`.

### orama planning layer (separate from PT contracts)

Path:
[`orama-system/bin/agents/orchestrator/task_schema.py`](https://github.com/diazMelgarejo/orama-system/blob/main/bin/agents/orchestrator/task_schema.py)
— `TaskPlan` / `WorkerSpec`; explicitly not PT shared types.

### Skill routing envelope (additive, not in original absorption plan)

Path:
[`Perpetua-Tools/orchestrator/openclaw_skill_resolver.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/openclaw_skill_resolver.py)
— `SkillEnvelope` when `JobSpec.task_type` is set; supervisor `_try_skill_envelope()`.

## Gaps / open questions

1. `JobEnvelope` does not exist — only `JobSpec` (supervisor) and `TaskEnvelope` (worker
   contract).
2. `TaskEnvelope` is spec + tests, not wired on hot dispatch path — `OramaToPTBridge` builds
   `JobSpec` directly.
3. Two naming lineages for job state — V1 `JobSpec`/`JobStatus`; V2 spec proposes `JobState`
   dataclass (not shipped).
4. `task_schema.py` lives in orama, not PT.
5. Multiple "envelope" meanings — job lifecycle (`JobSpec`), worker primitive (`TaskEnvelope`),
   skill dispatch (`SkillEnvelope`), Hermes protocol, LAN transport.
6. gbrain search for envelope terms returned no results on PT/orama (indexing gap); `gbrain query`
   did surface absorption plan + supervisor files.
7. Original PT-only spec under `docs/superpowers/specs/` not found in PT; orchestration master
   plan lives in orama.
