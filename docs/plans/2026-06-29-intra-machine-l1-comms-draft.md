# Draft — Intra-machine L1 comms (Hermes Harness ↔ PT/orama subagents)

> **Status:** DRAFT — office-hours brainstorm input (not approved for implementation)  
> **Date:** 2026-06-29  
> **Method:** oramasys-method AFRP Type C · precedes `/autoplan`  
> **Prerequisite (hard gate):** [`2026-06-28-security-pr3-p5-swarm-approval-execution-plan.md`](2026-06-28-security-pr3-p5-swarm-approval-execution-plan.md) must **land on `main`** before any L1 dispatch work  
> **Related:** `hermes-universal-invocation-protocol.md`, `graceful-degradation.md` Ladder C/F, PR3 P5 swarm HITL

---

## Problem statement

On a **single Windows (or Mac) host**, multiple L1 executors can run at once:

- Hermes CLI / harness scripts  
- `cursor-agent` (Cursor subagents)  
- `codex exec` / `dispatch_codex_partner.py`  
- PT-spawned workers (orchestrate, autoresearch bridge, future swarm jobs)

Today there is **no unified local dispatch bus**. Operators and portals use **HTTP between localhost services**, **file inboxes**, **subprocess spawn**, and **in-process queues** — but L1 agents do not share a single envelope, approval gate, or kill path.

**Goal:** Reuse existing scripts and services; **do not** add a second control plane or message broker. Piggyback **killswitch** and **HITL** doctrine already landing in portal + `ActionValidator` + swarm P5.

---

## What already works (reuse map)

| Layer | Asset | Port / path | Role today |
|-------|-------|-------------|------------|
| L2 runtime | Perpetua-Tools FastAPI | `:8000` | `POST /user-input`, `GET /user-input/next`, `POST /v1/jobs`, orchestrate |
| L3 methodology | orama `api_server` | `:8001` | `POST /oramasys` (stateless reasoning) |
| Operator shell | `portal_server` | `:8002` | Proxies `/api/user-input`, swarm preview/launch, peer-file, lifecycle stop/restart |
| Wire contract | Hermes universal envelope | docs | `skill_id`, `agent_id`, `executor_id`, optional `transport` |
| Partner spawn | `dispatch_codex_partner.py` | script | Subprocess Codex with runtime path resolution |
| LAN work (same pattern) | `lan_peer_assign.py` + inbox | `~/.openclaw/state/lan_peer/` | Durable assignment cards |
| Win sequential | `win_job_queue.py` | `win_job_queue.json` | One active job per role |
| Live signal | `lan_peer_channel.py` | WS + SSE | Heartbeats, not assignment transport |
| HITL (PT) | `action_validator.py` | library | Class 3/4 gates before tool execution |
| HITL (portal) | swarm preview → launch | `/api/swarm/*` | P5: HMAC `preview_id` + `approval_token` (planned on `main`) |
| Killswitch | `POST /api/stop` | portal | Stop all services; CSRF/origin guards (PR3 stack) |
| Degradation SSOT | `graceful-degradation.md` | doc | Ladders A–F; no parallel expensive tiers |

**Explicit non-goals (v1.1 plan §9):** Redis distributed PT, remote agent RPC over LAN, new message broker.

---

## Proposed wedge: L1 Local Dispatch Facade (no new daemon)

A **thin facade** in orama-system (portal or `bin/orama-system/skills/hermes-harness/scripts/`) that:

1. Accepts a **Hermes universal envelope** (L3 + L2 extensions).  
2. Writes a **preview record** (same shape as swarm preview assignments).  
3. On operator approval (HMAC token or portal UI), **routes to exactly one** local executor:
   - `executor_id=codex` → `dispatch_codex_partner.py`  
   - `executor_id=hermes` → Hermes CLI / harness skill runner  
   - `executor_id=cursor` → `cursor-agent --print …` (documented wrapper, not RPC)  
   - `executor_id=pt-worker` → `POST {PT_URL}/user-input` or `POST /v1/jobs`  
4. Records outcome in **existing** audit surfaces (OTel spans if present, `win_job_queue` complete, or PT job status).

### ASCII — same-machine flow

```
Operator / Portal / Harness
        │
        ▼
 POST /api/l1/preview   ──► assignments + preview_id + approval_token (reuse P5 pattern)
        │
        ▼ (HITL: operator approves in UI or CLI presents token)
 POST /api/l1/launch    ──► ActionValidator.validate(envelope)
        │                      │
        │                      ├─ reject → 403 + gate_class
        │                      └─ approve → spawn ONE subprocess / PT queue push
        ▼
 Local executor (cursor-agent | codex | hermes | PT poll)
```

### Killswitch piggyback

| Event | Existing hook | L1 extension |
|-------|---------------|--------------|
| Operator panic stop | `POST /api/stop` | Facade registers PIDs/session_ids; stop kills child processes |
| Irreversible tool | `ActionValidator.IRREVERSIBLE` | Map `tool=spawn_l1_job` with `transport.profile=destructive` → Class 4 |
| Scope mutation | `REQUIRES_HITL` | `modify_model_registry`, `restart_backend`, `push_to_remote` block launch |
| Swarm-style jobs | P5 HMAC tokens | **Same token verifier** for `/api/l1/launch` and `/api/swarm/launch` |

### Relationship to LAN co-orchestration

- **Cross-host:** keep file inbox + `win_job_queue` (proven).  
- **Same-host:** L1 facade is **fast path** for spawn; file inbox remains **audit trail** and Mac↔Win handoff.  
- **Never** remote cursor-agent RPC (unchanged doctrine).

---

## Alternatives considered

| # | Approach | Pros | Cons | Verdict |
|---|----------|------|------|---------|
| A | New Redis/NATS bus | Real pub/sub | v1 OOS; violates frugality | **Reject** |
| B | PT `/user-input` only | Minimal | No envelope, no preview/HITL parity with swarm | **Defer** as transport only |
| C | Portal L1 preview/launch (reuse P5) | HITL + killswitch aligned; one UI | Touch `portal_server.py` | **Recommend v1** |
| D | File-only queue (extend inbox) | Auditable | Too slow for interactive same-machine | **Keep for LAN + audit** |
| E | Cursor subagents only | Zero new API | No PT/orama integration; no HITL centralization | **Complement, not replace** |

---

## v1 scope (smallest shippable)

1. **Spec** — `l1-dispatch-envelope.json` schema = Hermes envelope + `transport.partner` + optional `queue_role`.  
2. **Script** — `l1_dispatch.py preview|launch|status` CLI mirroring swarm API (calls localhost:8002).  
3. **Portal** — `/api/l1/preview` + `/api/l1/launch` thin wrappers sharing P5 token helpers.  
4. **Validator hook** — call PT `ActionValidator` (or shared copy in orama) before spawn.  
5. **Tests** — extend `test_portal_mutating_route_auth.py`, `test_portal_lifecycle_csrf.py`.  
6. **Docs** — one ladder row in `graceful-degradation.md` Ladder G (local L1 dispatch).

**Out of v1:** cross-peer L1 RPC, automatic cursor-agent daemon, Redis, frugality_router chokepoint (separate P1 track).

---

## Open questions — RESOLVED (2026-06-29)

| ID | Decision |
|----|----------|
| **D1** | Preview **mandatory** for fan-out (2+), multi-executor, and HITL-class actions. **Fast-path:** single read-only Codex (`transport.profile=read_only`) may use bearer-only like harness `codex exec`. |
| **D2** | **`POST /v1/jobs`** canonical for PT workers (swarm parity). `/user-input` stays legacy orchestrate poll. |
| **D3** | **`win_job_queue`** parallel LAN track + post-hoc `complete`; L1 facade does not replace file inbox. |
| **D4** | **Tiered stop:** `/api/l1/stop` kills registered children only; full **`POST /api/stop`** NUCLEAR only on **Stop All / Emergency**. |

**Execution plan (ingredients phase):** [`2026-06-29-intra-machine-l1-comms-execution-plan.md`](2026-06-29-intra-machine-l1-comms-execution-plan.md)

---

## Open questions (archived — see table above)

1. ~~Should **preview** be mandatory…~~ → D1  
2. ~~Is **PT `/v1/jobs`** or **`/user-input`**…~~ → D2  
3. ~~How does **win_job_queue** relate…~~ → D3  
4. ~~**Kill scope**…~~ → D4  
5. **Cursor subagents** — register as `executor_id=cursor` profiles in envelope (**yes**, v1)

---

## Success criteria

- One envelope dispatches to Hermes, Codex, cursor-agent, or PT worker on **same host** without new ports.  
- Launch without valid approval token **fails closed** (P5 parity).  
- `POST /api/stop` terminates in-flight L1 children within N seconds.  
- No regression to LAN peer-file inbox or `win_job_queue` sequential discipline.

---

## Sequencing (steered 2026-06-29)

```text
PR3 P5 swarm HITL (merge first)
        │
        ▼
L1 comms draft → /autoplan → implement (reuses _sign_swarm_preview / _verify_swarm_launch)
        │
        ▼
PR4 P6 discovery approval (stack plan; independent of L1)
```

**Do not start** `/api/l1/*`, `l1_dispatch.py`, or Ladder G until P5 acceptance criteria are green on `main`. L1 piggybacks the same HMAC helpers — building L1 first would fork the HITL contract.

---

## Next steps (after P5 lands)

1. Confirm P5 merged: `approval_token` on preview, launch rejects bare `approved: true`  
2. Resolve open questions D1–D4 (office-hours or inline)  
3. `/autoplan` on this file (CEO → Eng; Design only if portal UI panels)  
4. Branch `cursor/security-l1-dispatch-*` **from post-P5 `main`**  
5. Lesson + PT `.agent` memory after first green same-host e2e
