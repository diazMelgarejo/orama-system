# P5 + P6 — Swarm HITL approval and discovery persistence gates

> **Status:** Phase C implemented (#224); Phase D deferred to v2 launch  
> **Parent:** [`SECURITY.md`](../../SECURITY.md) findings #6 (P6), P5 swarm approval  
> **Threat model:** [`docs/v2/45-single-operator-lan-threat-model-descope.md`](../v2/45-single-operator-lan-threat-model-descope.md)  
> **Migration ladder:** [`docs/v2/50-mesh-security-migration-ladder.md`](../v2/50-mesh-security-migration-ladder.md) (Phases A–D)

## P6 — Discovery persistence gate (highest exploitability)

**Problem:** `scripts/discover.py` auto-persists the first LAN `:1234` responder → `last_discovery.json`, `.env.lmstudio`, `openclaw.json` — no authenticity check.

**Elegant fix (3 layers):**

| Layer | Change | File |
|-------|--------|------|
| Prevent | `discover.py --persist` requires `ORAMA_APPROVE_DISCOVERY=1` or interactive `y/N` | `scripts/discover.py` |
| Runtime | Allowlist: only persist IPs matching `last_known_good` in `.local/lan-topology-archive.json` or operator `.env.local` | new `scripts/mesh/discovery_trust.py` |
| Verify | pytest: rogue responder not persisted without approval; `repo_hygiene` unchanged | `tests/test_discover_persist_gate.py` |

**PT bridge:** `orchestrator/lan_discovery.py` already prefers env + `last_discovery.json` — no PT code change if orama gate is authoritative.

## P5 — Server-side swarm approval (client `approved: true` is not HITL)

**Problem:** `POST /api/swarm/launch` trusts client `approved: true`.

**Elegant fix:**

1. `POST /api/swarm/preview` → returns `preview_id` + task fingerprint + hardware policy snapshot (existing partial flow).
2. Server signs `approval_token = HMAC-SHA256(ORAMA_SWARM_APPROVAL_SECRET, preview_id || fingerprint)` with TTL 5m.
3. `POST /api/swarm/launch` requires `{preview_id, approval_token}` — rejects replay/stale preview.
4. React console: two-step UI (preview → explicit confirm); token never stored in localStorage.

**Files:** `portal_server.py`, `web/src/` swarm flow, `tests/test_swarm_approval_hmac.py`, `SECURITY.md` checklist.

## After P5 + P6 (priority order)

1. **`ORAMA_INSECURE_DEV` + LAN bind** — refuse LAN unless loopback or auth enforced (`start.sh` / `control_plane_auth.py`).
2. **Mandatory `GOSSIP_SHARED_SECRET` when `PT_BIND_LAN=1`** — close default-open gossip (`fastapi_app.py`).
3. **CSRF/origin on all mutating portal routes** — extend `verify_lifecycle_origin()` pattern.
4. **Deprecate `src/perpetua_tools/orchestrator.py`** entrypoint or add same auth middleware as `fastapi_app.py`.

## Landing order for mesh continuity

See [`docs/v2/50-mesh-security-migration-ladder.md`](../v2/50-mesh-security-migration-ladder.md) for full Phase A–D operator steps.

**Safe pre-v2 merge order:**

1. Merge #223 (Phase A) → operator backup + gossip on **all** nodes.
2. Merge #224 + PT #287 (Phase C) → distribute `GOSSIP_SHARED_SECRET` OOB.
3. Verify mesh on all nodes.
4. Merge #222 (Phase B IP expunge).
5. **v2 launch:** Phase D strict cutover (`ORAMA_SWARM_STRICT=1`, remove legacy defaults).

Merging #223 + #224 + PT #287 **before** #222 is safe when Phase A is complete on every node.
