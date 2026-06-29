# L1 Local Dispatch — Weekend Build Execution Plan

> **Status:** INGREDIENTS ONLY — **do not wire portal routes until P5 swarm HITL is on `main`**  
> **Date:** 2026-06-29  
> **Draft input:** [`2026-06-29-intra-machine-l1-comms-draft.md`](2026-06-29-intra-machine-l1-comms-draft.md)  
> **Prerequisite:** [`2026-06-28-security-pr3-p5-swarm-approval-execution-plan.md`](2026-06-28-security-pr3-p5-swarm-approval-execution-plan.md) merged  
> **Wedge:** Option C — `/api/l1/preview` + `/api/l1/launch` in `portal_server.py`, shared P5 HMAC helpers, thin `l1_dispatch.py` CLI

---

## Product (weekend build UX)

One surface, same mental model as P5 swarm — applied to **single-host L1**:

```text
Paste objective
    → Preview (which executor: Hermes | Codex | cursor-agent | PT job)
    → Approve (HMAC token when required)
    → Watch status (session_id + child PIDs + PT job ids)
    → Stop (children first)  |  Stop All / Emergency (full NUCLEAR stack)
```

**Portal:** `L1Composer` panel beside Swarm (reuse command-center layout, token storage pattern from P5 T5).  
**CLI:** `l1_dispatch.py preview|launch|status|stop` — Hermes harness scripts call localhost:8002.

**Reject v1:** Redis, NATS, remote cursor RPC, new daemon port.

---

## Locked decisions (D1–D4)

| ID | Question | Decision |
|----|----------|----------|
| **D1** | Preview mandatory? | **Yes** for fan-out (2+ jobs), ALL multi-executor launches, and any action classified HITL (Class 3/4). **Fast-path:** single read-only Codex review (`executor_id=codex`, `transport.profile=read_only`) may use bearer-only like today's `dispatch_codex_partner.py` / harness `codex exec`. |
| **D2** | PT queue canonical? | **`POST /v1/jobs`** for PT-owned workers (swarm parity). `/user-input` remains legacy poll path for orchestrate loop — not L1 primary. |
| **D3** | `win_job_queue` relation? | **Parallel track:** LAN Mac orchestrator + post-hoc completion. L1 launch does not replace file inbox. After local executor finishes, harness may `win_job_queue.py complete` + optional peer drop. |
| **D4** | Kill scope? | **Tiered:** `POST /api/l1/stop` or portal **Stop** → SIGTERM registered child PIDs only. **`POST /api/stop`** full stack (PT+orama+portal) only on explicit **Stop All / Emergency** control (operator confirms). |

---

## Architecture

```text
                    ┌─────────────────────────────────────┐
                    │  portal :8002                        │
                    │  POST /api/l1/preview  (sign P5)     │
                    │  POST /api/l1/launch   (verify P5)   │
                    │  GET  /api/l1/status/{session_id}    │
                    │  POST /api/l1/stop     (children)      │
                    └──────────────┬──────────────────────┘
                                   │
         ActionValidator (PT) ◄────┼────► l1_child_registry (orama)
                                   │
         ┌─────────┬───────────┬───┴────┬──────────────┐
         ▼         ▼           ▼        ▼              ▼
    codex      cursor-agent  hermes   PT /v1/jobs   (audit)
    dispatch_  subprocess    CLI      trusted       win_job_queue
    codex_     wrapper       harness               lan_peer drop
    partner.py
```

### Executor routing table

| `executor_id` | Spawn | Preview required |
|---------------|-------|------------------|
| `codex` | `dispatch_codex_partner.py` | Fast-path if `read_only` |
| `cursor` | `cursor-agent --print` wrapper (subprocess, no RPC) | Yes unless single read-only profile |
| `hermes` | Hermes CLI / harness skill runner | Per D1 |
| `pt-worker` | `POST {PT_URL}/v1/jobs` | Yes when multi or HITL class |

### HITL piggyback

- Reuse `sign_operator_payload` / `verify_operator_payload` from P5 (`control_plane_auth.py`).
- Canonical payload adds: `executor_id`, `assignments_hash`, `envelope_hash`, `fanout_count`.
- Import PT `ActionValidator` before spawn; map `tool=spawn_l1_job` + envelope fields to Class 3/4.

### Killswitch piggyback

- `l1_child_registry.register(session_id, pid, executor_id)` on launch.
- `/api/l1/stop` → terminate children, mark session `stopped`.
- Emergency **only** → existing `/api/stop` NUCLEAR (unchanged semantics, new UI label).

---

## Ingredients (safe before P5 merge)

| Artifact | Path | Status |
|----------|------|--------|
| Envelope schema | `docs/schemas/l1-dispatch-envelope.schema.json` | **draft** |
| CLI skeleton | `bin/orama-system/skills/hermes-harness/scripts/l1_dispatch.py` | **stub** (gates on P5) |
| Child registry | `src/orama_system/l1_child_registry.py` | **module** + unit tests |
| Ladder G draft | section below → merge into `graceful-degradation.md` post-P5 | **text only** |
| This plan | `docs/plans/2026-06-29-intra-machine-l1-comms-execution-plan.md` | **active** |

---

## Post-P5 implementation tasks

| Step | Task | Verify |
|------|------|--------|
| **L1-T0** | Confirm P5: `approval_token` on swarm preview; launch rejects bare `approved` | grep `main` |
| **L1-T1** | `_build_l1_preview(envelope)` → assignments + signed token | `tests/test_l1_preview.py` |
| **L1-T2** | `POST /api/l1/preview` + `POST /api/l1/launch` thin wrappers | auth + HMAC tests |
| **L1-T3** | Wire `ActionValidator` gate on launch | Class 3/4 block → 403 |
| **L1-T4** | Executor spawners (codex/cursor/hermes/pt) + registry | integration test subprocess mock |
| **L1-T5** | `GET /api/l1/status`, `POST /api/l1/stop` | children killed < 5s |
| **L1-T6** | `l1_dispatch.py` full HTTP client (un-gate stub) | manual e2e |
| **L1-T7** | React `L1Composer.tsx` | vitest + manual |
| **L1-T8** | Ladder G row in `graceful-degradation.md` | doc |
| **L1-T9** | Extend `test_portal_mutating_route_auth.py`, lifecycle CSRF | CI |

---

## Ladder G (draft — paste into graceful-degradation.md after L1-T8)

```markdown
### Ladder G — Local L1 dispatch (same host)

| Tier | Path | When |
|------|------|------|
| G0 | File inbox + `win_job_queue` | LAN handoff, audit trail |
| G1 | `l1_dispatch.py preview` (CLI) | Harness scripts, no UI |
| G2 | Portal L1 preview/launch | Operator same-machine spawn |
| G3 | Emergency Stop All | Full `/api/stop` — not default Stop |
```

---

## Out of scope (v1)

- Redis / message broker
- Remote cursor-agent over LAN
- Automatic cursor-agent daemon
- Replacing `coord_pulse` / file inbox LAN cycle

---

## Sequencing

```text
P5 merge on main  ──►  /autoplan this plan  ──►  branch cursor/security-l1-dispatch-*
                              │
                              ▼
                    L1-T1..T9 (portal + CLI + UI)
                              │
                              ▼
                    Unblock win-coder-l1-comms-autoplan-backlog
```

---

## Acceptance criteria

- [ ] Paste objective → preview shows executor + routing rationale
- [ ] Launch without token on HITL-class → 422/403
- [ ] Fast-path read-only Codex works with bearer only
- [ ] Stop kills children; Stop All runs full `/api/stop`
- [ ] LAN inbox + `win_job_queue` unchanged
- [ ] No new ports; no Redis
