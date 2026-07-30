# 50 — Mesh Security Migration Ladder (Phases A–D)

> **Repository standard:** additive — see [`46-repository-standard.md`](46-repository-standard.md).  
> **Status:** Active — Phases A–C ship pre-v2; **Phase D is a v2 launch gate** (not a pre-v2 merge blocker).  
> **Parent:** [`23-security-preconditions.md`](23-security-preconditions.md), [`24-security-first-platform.md`](24-security-first-platform.md), [`32-agentic-security-controls.md`](32-agentic-security-controls.md) §10, [`45-single-operator-lan-threat-model-descope.md`](45-single-operator-lan-threat-model-descope.md), [`47-portable-memory-local-topology-invariant.md`](47-portable-memory-local-topology-invariant.md)  
> **Implementation plans:** [`docs/plans/2026-07-26-p5-p6-lan-discovery-swarm-approval-plan.md`](../plans/2026-07-26-p5-p6-lan-discovery-swarm-approval-plan.md), [`docs/plans/2026-07-26-hermes-openclaw-staging-review-gate.md`](../plans/2026-07-26-hermes-openclaw-staging-review-gate.md)

---

## Purpose

Hermes staging security hardening (PR #222) removes committed LAN topology from git. P5/P6 runtime gates (PR #224) and Perpetua-Tools gossip mandate (PT #287) close the highest-exploitability LAN paths **without** breaking a single-operator fleet that already depends on those endpoints.

This ladder defines four phases. **Phases A–C are safe to land before v2.** **Phase D is deferred to initial v2 launch** — it removes grandfathering defaults and makes strict HITL/discovery gates the only path.

---

## Phase summary

| Phase | Name | When | PRs / artifacts | Operator action required |
|-------|------|------|-----------------|--------------------------|
| **A** | Mesh continuity prep | **Before** IP expunge | #223 (`lan_topology_archive.py`, `ensure_local_mesh_secrets.py`) | Backup + gossip secret on **every** fleet node |
| **B** | IP hygiene + supply-chain gates | After A on all nodes | #222 (LINT-013, pre-commit, `verify_trusted_install`, agent-security CI) | Re-run `install.sh`; set `LM_STUDIO_*_ENDPOINTS` in `.env.local` |
| **C** | Runtime gates (grandfathered) | After A; may land **before** B | #224 (P5/P6), PT #287 (`GOSSIP_SHARED_SECRET` on LAN) | Distribute `GOSSIP_SHARED_SECRET` OOB to all peers; ack new discovery peers |
| **D** | Strict cutover | **v2 launch only** | Code + config flag flip (see §Phase D) | Fleet-wide coordinated cutover; no silent rollback |

```text
  A (prep) ──► C (runtime gates) ──► B (IP expunge)     ← safe pre-v2 merge order
                    │                      │
                    └──────────┬───────────┘
                               ▼
                         D (strict)  ← v2 launch gate only
```

**Merge-order answer (Q1):** Merging **#223 + #224 + PT #287 before #222 is safe** provided Phase A operator steps completed on every node before #222 merges. #224 does not remove committed IPs; it adds fail-closed runtime checks that require `GOSSIP_SHARED_SECRET` when binding LAN. Skipping Phase A on any node will cause discovery/gossip/`start.sh` failures after #224 or #222 land.

---

## Phase A — Mesh continuity prep

**Goal:** Preserve fleet endpoint knowledge in local-only stores before git stops carrying RFC1918 literals.

### Security-first requirements

1. **No new secrets in git** — `.local/`, repo-local `.env.local`, and `mesh-secrets.json` stay gitignored ([`47-portable-memory-local-topology-invariant.md`](47-portable-memory-local-topology-invariant.md)). Workspace-level files outside any repo are **not** covered by `.gitignore` — use explicit filesystem and credential-store access controls. Treat all fleet-local secret files as sensitive; agents must not echo values in PRs or logs. `ensure_local_mesh_secrets.py` writes without printing secrets.
2. **Backup from trusted ref** — archive reads committed topology from `origin/main` (or explicit `--ref`), not from unreviewed working trees.
3. **Idempotent apply** — re-running archive/ensure scripts must not rotate secrets unless `--force`.
4. **Cross-repo parity** — `PERPETUA_TOOLS_PATH` hosts get the same `.env.local` merge when set.

### Operator steps (every fleet node)

```bash
cd "${REPO_ROOT:-.}"
git fetch origin main

# 1. Snapshot committed endpoints → .local/lan-topology-archive.json + .env.local
python3 scripts/mesh/lan_topology_archive.py --backup --ref origin/main

# 2. Generate GOSSIP_SHARED_SECRET locally (value never printed)
python3 scripts/mesh/ensure_local_mesh_secrets.py

# 3. Confirm env placeholders resolve (no committed IPs required yet)
grep -E 'LM_STUDIO_|GOSSIP_' .env.local   # names only — do not log values
```

Repeat on Windows RTX nodes via the same Python entrypoints (PowerShell `python`).

### Acceptance

- [ ] `.local/lan-topology-archive.json` exists and lists known Mac/Win endpoints
- [ ] `.env.local` contains `LM_STUDIO_WIN_*_ENDPOINTS` and `GOSSIP_SHARED_SECRET`
- [ ] `python3 scripts/mesh/lan_topology_archive.py --check` exits 0
- [ ] `repo_hygiene.py` still passes (archive is outside git scan for literals)

---

## Phase B — IP hygiene + supply-chain gates

**Goal:** Enforce portable-memory invariant in CI; block re-introduction of committed LAN topology; harden Hermes/OpenClaw install trust.

### Security-first requirements

| Control | Prevent | Runtime | Verify |
|---------|---------|---------|--------|
| LINT-013 | `repo_hygiene` on config/docs | `${env:LM_STUDIO_*}` placeholders in `agent_registry.json` | `tests/test_repo_hygiene.py` |
| Pre-commit | `no_committed_lan_topology.py` | blocks RFC1918 in `config/`, `bin/*/config/` | local hook + CI |
| Trusted install | `ORAMA_SKIP_HERMES_SYNC` default | `verify_trusted_install.py` before profile sync | `tests/test_verify_trusted_install.py` |
| Overlay allowlist | path regex in sync script | writes only under allowlisted workspace roots | dry-run + tests |
| Agent-security CI | workflow on PR | Tier-A scanners (gitleaks, skill-scanner, etc.) | `.github/workflows/agent-security.yml` |

### Operator steps (after merge, every node)

Clean-tree sync — see [`safe-cross-host-sync-reference-card.md`](../../bin/orama-system/skills/git-history-surgery/references/safe-cross-host-sync-reference-card.md) § Quick sync.

```bash
git fetch origin --prune
test -z "$(git status --porcelain --untracked-files=all)" || { echo "error: dirty worktree"; exit 1; }
git switch main
git pull --ff-only origin main
./install.sh --ensure-local-cache    # merges archive → .env.local if missing keys

# Windows Hermes hosts
# install-hermes-harness.ps1  (uses verify_trusted_install gate)
```

### Acceptance

- [ ] `python3 scripts/review/repo_hygiene.py` exits 0
- [ ] `python3 scripts/hooks/no_committed_lan_topology.py` exits 0
- [ ] No private/link-local literals in tracked `config/` or `bin/*/config/` JSON/YAML (same scan as LINT-013 / pre-commit hook)
- [ ] `discover.py` / portal still reach Win LM Studio via `.env.local` endpoints
- [ ] Hermes profile install succeeds on trusted `main` or with explicit `ORAMA_TRUST_HERMES_SYNC=1`

---

## Phase C — Runtime gates (grandfathered)

**Goal:** Close P5 (swarm HITL bypass) and P6 (rogue discovery persist) with **backward-compatible defaults** so existing single-operator fleets keep working during pre-v2 operation.

**PRs:** orama #224, Perpetua-Tools #287.

### Security-first requirements

| Finding | Prevent | Runtime (grandfathered) | Verify |
|---------|---------|-------------------------|--------|
| **P6** discovery hijack | `discovery_trust.py` filter before persist | Known peers from archive + `known-peers.json`; new peers need `ORAMA_APPROVE_DISCOVERY=1` or `--ack-peer` | `tests/test_discovery_trust.py` |
| **P5** swarm bypass | HMAC `preview_id` + `approval_token` | `ORAMA_SWARM_LEGACY_APPROVE=1` (default) accepts old `approved: true` | `tests/test_swarm_approval.py` |
| Gossip default-open | `start.sh` refuses LAN without secret | `GOSSIP_SHARED_SECRET` required when LAN bind | PT `_require_gossip_auth` on `PT_BIND_LAN=1` |
| INSECURE+LAN | `start.sh` / `control_plane_auth.py` | `ORAMA_INSECURE_DEV` cannot disable auth on LAN bind | `tests/test_control_plane_auth.py` |
| CSRF | middleware on mutating routes | origin check on portal auth paths | portal mutating-route tests |

### Operator steps (every fleet node, after #224 + PT #287)

```bash
# 1. Same secret on ALL peers (dedicated air-gapped transfer — e.g. TailsOS-hardened USB
#    or operator-approved secure channel; never git/email/Slack/agent comms)
#    Copy GOSSIP_SHARED_SECRET from primary Mac to Win nodes' .env.local

# 2. Restart mesh
./start.sh    # or platform equivalent

# 3. When a NEW peer appears on the subnet:
ORAMA_APPROVE_DISCOVERY=1 python3 scripts/discover.py --persist
# or: discover.py --ack-peer <ip> --nonce <n> --signature <sig>

# 4. Swarm: legacy path still works (grandfathered)
#    Portal two-step preview→launch with tokens is optional until Phase D
```

### Acceptance

- [ ] `start.sh` succeeds on LAN with matching `GOSSIP_SHARED_SECRET` on all nodes
- [ ] PT `POST /v1/gossip/*` returns 401 without secret when `PT_BIND_LAN=1`
- [ ] Rogue `:1234` responder on subnet is **not** auto-persisted without ack
- [ ] Swarm launch with bearer + `approved: true` still works (grandfather mode)
- [ ] Swarm launch with invalid/missing token fails when `ORAMA_SWARM_LEGACY_APPROVE=0`

---

## Phase D — Strict cutover (v2 launch gate)

> **Deferred:** Phase D is **not** required for pre-v2 merges of #222–#224 or PT #287. It is a **coordinated v2 launch requirement** documented here so operators and implementers share one cutover contract.

**Goal:** Remove grandfathering defaults; make server-side HITL and discovery trust **mandatory**; align with [`24-security-first-platform.md`](24-security-first-platform.md) §6 release gate and [`23-security-preconditions.md`](23-security-preconditions.md) acceptance criteria.

### What changes at cutover

| Surface | Phase C (grandfathered) | Phase D (strict) |
|---------|-------------------------|------------------|
| Swarm launch | `ORAMA_SWARM_LEGACY_APPROVE=1` accepts `approved: true` | `ORAMA_SWARM_STRICT=1`; `preview_id` + `approval_token` **required** |
| Discovery persist | Known peers auto-trusted; one-shot `ORAMA_APPROVE_DISCOVERY` | No env one-shot; **only** HMAC `--ack-peer` or interactive operator UI |
| Gossip / mesh | Secret required on LAN | Same + rotate policy documented; stale peers purged from `known-peers.json` |
| Default env | Legacy flags default **on** | Legacy flags default **off**; strict is opt-out impossible on production profiles |
| Code defaults | `grandfather_legacy()` returns true by default | `strict_mode()` default true in v2 kernel config profile |

### Security-first requirements (Phase D)

1. **Fail closed** — missing `preview_id`/`approval_token`, unknown discovery peer, or missing gossip secret → hard deny (no silent fallback).
2. **No client-trusted booleans** — `approved: true` in JSON body is ignored; only server-issued HMAC tokens count ([`32-agentic-security-controls.md`](32-agentic-security-controls.md) §10).
3. **Fleet-wide coordination** — all nodes flip strict flags in the same maintenance window; document rollback as temporary `ORAMA_SWARM_LEGACY_APPROVE=1` on loopback-only dev hosts only.
4. **Audit evidence** — append-only log in `.local/` for discovery acks and swarm approvals (redacted; no secrets in stdout).
5. **CI proof** — tests run with `ORAMA_SWARM_STRICT=1` as the default fixture profile before v2 tag.
6. **Threat-model check** — re-run Q1–Q3 from [`45-single-operator-lan-threat-model-descope.md`](45-single-operator-lan-threat-model-descope.md); strict mode is justified when trust boundary or exposure changes, not merely at calendar v2.

### Operator cutover checklist (v2 launch day)

Execute on **every** fleet node in order:

```bash
# 0. Preconditions (must all pass)
python3 scripts/review/repo_hygiene.py
python3 scripts/mesh/lan_topology_archive.py --check
pytest tests/test_discovery_trust.py tests/test_swarm_approval.py tests/test_control_plane_auth.py

# 1. Confirm gossip secret parity (all peers)
#    If rotating: run ensure_local_mesh_secrets.py --force on primary, redistribute OOB, then peers

# 2. Enable strict mode in .env.local (v2 profile — never commit this file)
cat >> .env.local <<'EOF'
ORAMA_SWARM_STRICT=1
ORAMA_SWARM_LEGACY_APPROVE=0
EOF

# 3. Remove one-shot discovery bypass from shell profiles / systemd env
#    Unset ORAMA_APPROVE_DISCOVERY everywhere

# 4. Restart all mesh services
./start.sh

# 5. Smoke tests
#    a) discover.py against known peer → persists without ack
#    b) discover.py against unknown IP → blocked; ack flow works
#    c) POST /api/swarm/preview → copy preview_id + approval_token
#    d) POST /api/swarm/launch with tokens → 200
#    e) POST /api/swarm/launch with approved:true only → 422/403

# 6. Portal UI: confirm two-step swarm composer is the only launch path
```

### Code changes required for Phase D (v2 implementation ticket)

These are **not** part of pre-v2 PR #222–#224; track as v2 kernel work:

- [ ] Flip `grandfather_legacy()` default to `false` when `ORAMA_V2_STRICT_PROFILE=1`
- [ ] Remove `ORAMA_APPROVE_DISCOVERY` env bypass in `discovery_trust.peer_trusted()`
- [ ] Portal React: remove legacy single-step launch; store tokens only in memory for session
- [ ] `start.sh`: warn if legacy flags detected when v2 profile active
- [ ] Document `ORAMA_SWARM_APPROVAL_SECRET` as instance-unique (CISA secure-by-default)
- [ ] Add Phase D section to [`23-security-preconditions.md`](23-security-preconditions.md) acceptance checklist

### Phase D acceptance (v2 release gate)

- [ ] All Phase A–C acceptance items still pass
- [ ] Default test profile uses `ORAMA_SWARM_STRICT=1`
- [ ] No production fleet node runs with `ORAMA_SWARM_LEGACY_APPROVE=1`
- [ ] Discovery persist without HMAC ack fails on all nodes
- [ ] [`24-security-first-platform.md`](24-security-first-platform.md) §6 release gate signed off
- [ ] Operator runbook executed once on Mac + each Win node; results logged in append-only fleet journal

---

## Recommended merge sequence

```text
1. Merge #223 (Phase A scripts)           → operator: backup + gossip on ALL nodes
2. Merge #224 + PT #287 (Phase C)       → operator: distribute GOSSIP_SHARED_SECRET OOB
3. Verify mesh (discover, gossip, swarm) on all nodes
4. Merge #222 (Phase B IP expunge)        → operator: install.sh --ensure-local-cache
5. v2 launch                              → Phase D strict cutover (this doc §Phase D)
```

**Do not merge #222 before Phase A on every node** — committed IPs will be gone and mesh will not self-heal without `.local/lan-topology-archive.json`.

---

## Environment variable reference

| Variable | Phase | Purpose |
|----------|-------|---------|
| `LM_STUDIO_WIN_*_ENDPOINTS` | A/B | Local-only model endpoint URLs |
| `GOSSIP_SHARED_SECRET` | A/C/D | Shared mesh auth; required on LAN bind |
| `ORAMA_APPROVE_DISCOVERY=1` | C only | One-shot new peer approve (**removed in D**) |
| `ORAMA_SWARM_LEGACY_APPROVE=1` | C default | Grandfather `approved: true` (**off in D**) |
| `ORAMA_SWARM_STRICT=1` | D | Require HMAC swarm tokens |
| `ORAMA_SWARM_APPROVAL_SECRET` | C/D | Instance-unique swarm HMAC key (preferred over shared gossip) |
| `ORAMA_TRUST_HERMES_SYNC=1` | B | Explicit override for non-main Hermes sync |
| `ORAMA_SKIP_HERMES_SYNC=1` | B | Skip Hermes materialization entirely |

---

## References

- Hermes staging review gate: [`docs/plans/2026-07-26-hermes-openclaw-staging-review-gate.md`](../plans/2026-07-26-hermes-openclaw-staging-review-gate.md)
- P5/P6 implementation plan: [`docs/plans/2026-07-26-p5-p6-lan-discovery-swarm-approval-plan.md`](../plans/2026-07-26-p5-p6-lan-discovery-swarm-approval-plan.md)
- GossipBus mesh: [`43-gossipbus-mesh-transport.md`](43-gossipbus-mesh-transport.md)
- Peer-mesh TLS (post-D): [`49-peer-mesh-auth-tls-v2-plan.md`](49-peer-mesh-auth-tls-v2-plan.md)
