# Oramasys Vision

> **Scope:** Organization, fleet, mesh, and v2 program — all `oramasys/*` and `perpetua-core` repos, plus v1 interop (`orama-system`, `Perpetua-Tools`) until v2 parity ships.  
> **Supersedes:** Ad-hoc v1 vision fragments, experimental multi-agent prose without policy gates, and any per-repo priority lists that conflict with this file.  
> **Does not replace:** Per-agent `SOUL.md`, `GOALS.md`, `MEMORY.md`, or per-task `GOAL.md` — see [file-scope taxonomy](docs/v2/README.md).

**Canonical spec tree:** [`docs/v2/README.md`](docs/v2/README.md)  
**Methodology:** [`bin/orama-system/skills/oramasys-method/SKILL.md`](bin/orama-system/skills/oramasys-method/SKILL.md)

---

## Product thesis

**Oramasys is a secure, hardware-aware, local-first multi-agent orchestration system:** a small ruthless kernel (`perpetua-core`), a glass-window composition layer (`oramasys`), and orbit plugins that ship at their own pace — running on the operator's devices, in the operator's channels, under the operator's rules.

Agents execute through a **fixed five-stage pipeline** (Context → Architect → Refiner → Executor → Verifier → Crystallizer), gated by **AFRP** at ingress and **Warden** at policy boundaries. Nothing commits, pushes, deploys, or sends without human approval on guarded paths.

---

## Priority stack (current)

Ordered. Lower items wait.

1. **Security and safe defaults** — auth, bind, egress, capability manifests, redacted audit ([`docs/v2/24-security-first-platform.md`](docs/v2/24-security-first-platform.md), [`docs/v2/23-security-preconditions.md`](docs/v2/23-security-preconditions.md)).
2. **Portable memory invariant (D25)** — tracked policy names categories only; concrete forbidden identity, device, path, and topology fragments live in local-only registries ([`docs/v2/47-portable-memory-local-topology-invariant.md`](docs/v2/47-portable-memory-local-topology-invariant.md)).
3. **v1 finish-now on `main`** — identity audit Phase 3 (PT sync), Phase 4 (remove legacy lists), mesh operator verify + #222 merge ladder, Hermes Win smoke, TLS test hygiene — per [`docs/next/2026-07-27-phase-0-master-plan.md`](docs/next/2026-07-27-phase-0-master-plan.md).
4. **Kernel lean + one-way imports** — `perpetua-core` never imports `oramasys` (D4, D8).
5. **v2 parity tests (Phase 4)** — wire `LLMClient` to dispatch; lift proven v1 pieces ([`docs/v2/04-build-order.md`](docs/v2/04-build-order.md)).
6. **Orbit plugins** — `oramaclaw`, `agate`, GossipBus mesh, Langfuse traces — **plugins only**, not kernel entanglements (D22, docs 40–43).
7. **New features** — only after 1–5 are green for the affected surface.

---

## Architectural rules

### Kernel and layering

- **Microkernel (D4):** ~70-line graph engine + `graph/plugins/` on demand ([`docs/v2/01-kernel-spec.md`](docs/v2/01-kernel-spec.md)).
- **One-way import:** `oramasys` → `perpetua_core` only. Upward import = layering bug.
- **Repository standard (D24):** executable code under `/src`; no root-level `scripts`/`tests`/`tools`/`examples`; never commit secrets, personal paths, or topology literals ([`docs/v2/46-repository-standard.md`](docs/v2/46-repository-standard.md)).

### Five-stage pipeline (non-negotiable core)

```
AFRP gate → Cass (S1) → Aria (S2) → Sena (S3) → Rourke (S4) → Vera (S4.5) → Crystal (S5)
```

- No new stages without human approval.
- No manager-of-managers / nested planner trees as default architecture — flat pipeline + explicit delegation ([`docs/v2/02-modules/multi-agent-network.md`](docs/v2/02-modules/multi-agent-network.md) deferred as v2 module, not kernel bloat).

### Hardware affinity (agate)

- Dispatch respects **PREFER / ALLOW / NEVER** ([`docs/v2/07-agate-vision.md`](docs/v2/07-agate-vision.md), D14).
- **Fail closed** if required hardware unavailable — no silent cloud fallback without policy.
- Mirror backends are mirror-only; never default execution path.

### Memory and files (org vs agent)

| Level | Files | Authority |
|-------|-------|-----------|
| **Organization** | This `VISION.md` | Human edits only |
| **Agent** | `SOUL.md`, `GOALS.md`, `MEMORY.md` | Agent maintains; human approves soul/goals changes |
| **Task** | `GOAL.md` | Ephemeral; one job |

Promotion rule: only learnings that **strengthen the goal-to-action loop**, **reduce context bloat**, or **improve security posture** graduate into agent `MEMORY.md`. Scope-widening or policy-weakening notes are discarded.

### Integrative merge (all repos)

When harmonizing branches or plans: **synthesize, never amputate** ([`bin/orama-system/skills/oramasys-method/references/integrative-merge.md`](bin/orama-system/skills/oramasys-method/references/integrative-merge.md)). Archive; do not delete working intent.

---

## Triage gut-checks (Vera + autotriage)

Every PR, issue pickup, or agent-proposed change must pass **all three**:

1. **Goal-to-action:** Does this strengthen persistent, traceable execution — or add stateless one-off behavior?
2. **Kernel lean:** Could this ship as an orbit/bundle plugin instead of core?
3. **Threat model:** Does this respect single-operator LAN assumptions and hardware policy ([`docs/v2/45-single-operator-lan-threat-model-descope.md`](docs/v2/45-single-operator-lan-threat-model-descope.md))?

Fail any → `BLOCKED` or `NEEDS_HUMAN`. No Rourke execution without Vera pass.

---

## What we will not merge (rationale-backed)

| Rejection | Because |
|-----------|---------|
| Manager-of-managers agent hierarchies as default | Breaks flat 5-stage pipeline; context bloat; breaks deterministic verification |
| Raw DB / filesystem writes bypassing CIDF | CIDF mandates `direct_form_input → scripting → API`; bypasses audit layer |
| Hardcoded LAN IPs, device names, or workstation paths in tracked repos | Violates D25 portable-memory invariant and breaks CI on other machines |
| Multi-fix drive-by PRs | Review cost is per-PR; bundling hides blast radius from autotriage |
| BFT/Sybil P2P patterns on single-operator LAN | D23 — no real witness quorum; false security theater |
| Kernel imports from `oramasys` or UI/portal layers | Layering violation |
| RAG / vector DB / swarm parallelism **inside kernel** | Deferred modules per v2 anti-scope ([`docs/v2/README.md`](docs/v2/README.md)) |
| Autonomous edits to `VISION.md`, `SOUL.md`, `USER.md`, `AGENTS.md` | Identity and org intent are human-guarded (VisionaireLabs pattern) |
| Deleting v1 working code without v2 parity test | D1 — v1 ships until v2 supersedes with evidence |

---

## Autonomous-OK vs needs-human

### Autonomous-OK (implement + test + propose PR)

- Bug fixes with clear repro and scoped blast radius
- Tests and docs that **add** coverage without changing security posture
- Refactors that preserve public API and pass existing gates
- Plugin/orbit code that does not widen kernel surface

### Needs-human (always)

- `VISION.md`, security policy, capability manifests, auth/TLS
- Commit, push, merge, deploy, release, dependency major bumps
- SOUL / GOALS / identity policy changes
- New kernel stages, new default network egress, new MCP tool classes
- Anything failing Vera gut-checks above

---

## v2 repo topology (target home)

| Repo | Role |
|------|------|
| `perpetua-core/` | Kernel: state, LLM client, hardware policy, MiniGraph, GossipBus |
| `oramasys/` | Graph DSL, FastAPI glass window, app nodes |
| `oramasys/agate/` | Hardware policy spec + gateway (side-car) |

**v1 interop until parity:** `diazMelgarejo/orama-system` + `diazMelgarejo/Perpetua-Tools` remain production; v2 repos absorb proven pieces per [`docs/v2/04-build-order.md`](docs/v2/04-build-order.md) and [`docs/plans/2026-07-22-cross-repo-out-of-scope-closure.md`](docs/plans/2026-07-22-cross-repo-out-of-scope-closure.md).

---

## Multi-agent network (Mode 3 today → v2 module tomorrow)

**Today (v1):** Seven-stage registry in [`bin/orama-system/config/agent_registry.json`](bin/orama-system/config/agent_registry.json); Perpetua governance ring (Atlas, Warden, Lumen, Beacon, Scout); external specialists via Relay only after Warden `ALLOW`. Operational blueprint: `OpenClaw/references/raft-Output-grounded-06.md`.

**Tomorrow (v2):** Full swarm parallelism ships as **non-kernel module** ([`docs/v2/02-modules/multi-agent-network.md`](docs/v2/02-modules/multi-agent-network.md)), not kernel creep.

**Raft / shared room:** When using [Raft](https://raft.build) as collaboration surface — channels, held drafts, agent inbox ([blog](https://raft.build/resources/blog/is-having-agents-in-the-room-meant-to-be-chaotic/)) — harness files (`SOUL.md`, etc.) stay on the Computer workspace; Raft provides the room, not the file schema.

---

## Open work this vision absorbs (tie-off list)

| Track | Status | Doc |
|-------|--------|-----|
| Identity audit Phases 3–4 | PT sync + list removal pending | `docs/plans/2026-07-24-unified-identity-audit-integrated-plan.md` |
| Peer-mesh TLS + pluggable auth | v1 bearer-over-HTTP fixed; TLS mesh open | `docs/v2/49-peer-mesh-auth-tls-v2-plan.md` |
| oramaclaw Gate M1+ | In progress | `docs/v2/40-oramaclaw-lifecycle-plugin.md` |
| Security-first platform gates | Active blocker for new HTTP/MCP | `docs/v2/24-security-first-platform.md` |
| Deferred v1 plans → v2 | Ledger closed, items named | `docs/plans/2026-07-22-cross-repo-out-of-scope-closure.md` |
| Fleet mesh / G7 MVP | Open | `docs/next/fleet-mesh/README.md` |

---

## Agent session contract

1. Read **`VISION.md`** (this file) first — org alignment.
2. Read agent **`SOUL.md`**, **`GOALS.md`**, **`MEMORY.md`** — persona and standing ownership.
3. Read task **`GOAL.md`** when dispatched on a specific job.
4. Run **AFRP** → stage pipeline → **CIDF** before writes.
5. Route executor output to **Vera**; never self-grade.
6. Crystallize only lessons that pass the promotion rule above.

---

## Related documents

- v2 master index: [`docs/v2/README.md`](docs/v2/README.md)
- Locked decisions D1–D25: [`docs/v2/00-context-and-decisions.md`](docs/v2/00-context-and-decisions.md)
- Oramasys mastery plan: [`docs/v2/29-oramasys-mastery-implementation-plan.md`](docs/v2/29-oramasys-mastery-implementation-plan.md)
- Multi-agent protocol: [`bin/orama-system/references/multi-agent-collaboration-protocol.md`](bin/orama-system/references/multi-agent-collaboration-protocol.md)
- Grounded agent-network blueprint (OpenClaw `references/`): `raft-Output-grounded-06.md`

---

*This file is the ideological and architectural north star for the oramasys organization. Agents may propose diffs; humans merge changes to this file.*
