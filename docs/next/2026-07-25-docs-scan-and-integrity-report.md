# Cross-Repo Docs Scan & Integrity Report — 2026-07-25

**Purpose:** Single re-verified snapshot of both repos on `origin/main`, plus a
full `docs/` scan separating **finish now on v1** from **deliberately deferred
to v2 `oramasys/*`**.

**Canonical trackers (keep in sync with this report):**

| Repo | Tracker |
| --- | --- |
| orama-system | [`2026-07-25-pending-work-tracker.md`](2026-07-25-pending-work-tracker.md) |
| Perpetua-Tools | [`2026-07-25-pending-work-tracker.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/next/2026-07-25-pending-work-tracker.md) |

**Related:** [`2026-07-22-cross-repo-out-of-scope-closure.md`](../plans/2026-07-22-cross-repo-out-of-scope-closure.md) (v2 deferral ledger) · [`docs/v2/README.md`](../v2/README.md) (oramasys org scope)

---

## 1. Sync & integrity (both repos)

Verified **2026-07-25**: `git fetch` + `git pull --ff-only` on `main`; shallow
fresh-clone tree-twin against local checkout.

| Repo | `main` HEAD | vs `origin/main` | Tracked-tree integrity |
| --- | --- | --- | --- |
| **Perpetua-Tools** | `acb878db` | Up to date | **Clean** — only intentional local overlay: `config/devices.yml`, `config/models.yml`, `vendor/ecc-tools` submodule pointer |
| **orama-system** | `5b05f545` | Up to date | **Clean** — no local diffs |

**No merge-mangle signal:** fresh `git clone --depth 1` tree-twin matches
`main` for tracked source. Local-only diffs are gitignored runtime (`.env`,
`.logs`, `__pycache__`, etc.).

**Smoke tests (PT):** `tests/test_env_paths.py` (5/5) pass after tilde-path fix.
One regression: `tests/test_alphaclaw_tls_proxy.py::
test_proxy_bounds_stalled_client_connections` — investigate before next TLS touch.

**Recently landed on `main` (tracker-relevant):**

| Change | Repo | Merge / commit |
| --- | --- | --- |
| AlphaClaw TLS proxy scaffold | PT | PR **#276** → `f120239e` |
| Windows ACL for TLS cert store | PT | PR **#278** → `e331aaf1` |
| Identity audit Phases 1–2 | orama | PR **#220** → `0cce8110` |
| `ALPHACLAW_INSTALL_DIR` tilde fix + wiki | PT | `acb878db` |
| Wiki mirror (tilde forensic) | orama | `5b05f545` |

---

## 2. Finish now on `diazMelgarejo/*` (v1 stack)

### Priority A — actionable on current `main`

| Item | Repo | Status on `main` | Next step |
| --- | --- | --- | --- |
| **Identity audit Phase 3** | PT | orama has `audit_engine` + policy; **PT lacks sync** | Dedicated PT PR: `sync-attribution-guard-scripts.sh`, wire `repo_hygiene` / wrappers — see [`docs/plans/2026-07-24-unified-identity-audit-integrated-plan.md`](../plans/2026-07-24-unified-identity-audit-integrated-plan.md) |
| **Identity audit Phase 4** | both | Not started | Remove 3 legacy hardcoded identity lists after Phase 3 green |
| **TLS proxy hardening (optional)** | PT | Core + Windows ACL **merged**; opt-in via `ALPHACLAW_TLS_ENABLED` | Admin-pinned fingerprints, rotation policy, mTLS, auto-enable |
| **TLS stalled-client test** | PT | 1 failing test | Fix `test_proxy_bounds_stalled_client_connections` |
| **Tri-repo item #1 live smoke** | PT | Unit tests green; live `SETUP_PASSWORD` smoke not re-run | Needs live AlphaClaw — [`Perpetua-Tools tri-repo plan`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/2026-05-31-tri-repo-alignment-completion-plan.md) |
| **AutoResearch adoption** | PT | Canonical plan; bridge exists | [`autoresearch-orchestrator-adoption.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/plans/autoresearch-orchestrator-adoption.md) — dry-run first |
| **Fleet mesh / G7** | orama (+ PT) | G7 pre-v2 backlog closed; Phase 7 portal hub MVP open | [`docs/next/fleet-mesh/README.md`](fleet-mesh/README.md) → G7 analysis + [`docs/superpowers/plans/2026-07-14-g7-authenticated-sse-mvp.md`](../superpowers/plans/2026-07-14-g7-authenticated-sse-mvp.md) |
| **Peer-mesh TLS + pluggable auth** | orama | Bearer-over-HTTP guard done; rest not started | [`docs/v2/49-peer-mesh-auth-tls-v2-plan.md`](../v2/49-peer-mesh-auth-tls-v2-plan.md) |
| **Security remediation 4–6** | orama | Fixes 1–3 done | [`docs/plans/2026-05-23-security-remediation-plan.md`](../plans/2026-05-23-security-remediation-plan.md) |
| **gbrain CRG Phase 2** | orama | Phase 0–1 + graph built | [`docs/plans/2026-05-19-gbrain-crg-embedding-integration.md`](../plans/2026-05-19-gbrain-crg-embedding-integration.md) |
| **Hermes Windows walkthrough** | orama | Needs live Win host | [`docs/plans/2026-06-24-hermes-windows-hardware-policy-walkthrough.md`](../plans/2026-06-24-hermes-windows-hardware-policy-walkthrough.md) |
| **L6 JSON schemas** | orama | L2–L5 done; L6 planned | [`docs/plans/2026-06-24-optimization-priorities.md`](../plans/2026-06-24-optimization-priorities.md) |
| **ecc-tools submodule drift** | PT | Local modified, uncommitted | Reconcile submodule pointer |

### Priority B — open docs, lower urgency

| Doc | Notes |
| --- | --- |
| PT `docs/plans/2026-07-14-final-remedy-primary-plan.md` | Branch-scoped — verify relevance |
| PT `docs/plans/2026-07-12-pr206-multi-agent-remediation-completion-plan.md` | PR #206 merged — archive candidate |
| PT `docs/plans/2026-05-31-gate2-implementation-plan.md` | Overlaps tri-repo plan |
| PT `docs/phase-0-specifications/*` | Fix #3 pending user confirmation |
| PT `docs/next/2026-07-19-heartbeat-daemon-design.md` | Design only |

### Priority C — reference only

- PT/orama `docs/next/2026-07-17-*` reflections
- `docs/wiki/*` — lessons, not backlog
- `vendor/*/docs` — out of scope

---

## 3. Deliberately deferred to v2 `oramasys/*`

**Governing directive (2026-07-22):** unimplemented or ambiguous parts → v2
oramasys repos **after** migration. Canonical ledger:
[`docs/plans/2026-07-22-cross-repo-out-of-scope-closure.md`](../plans/2026-07-22-cross-repo-out-of-scope-closure.md).

### Closure-ledger deferrals

| Bucket | Examples |
| --- | --- |
| L6 schemas | `topology.schema.json`, `devices.schema.json`, `skills.schema.json` |
| Periscope L4 | 52 open items |
| Skill upgrade PR3–PR5 | Medium/elevated/high-risk tiers |
| Tri-repo gates #2, #3, #8 | Retire `lib/mcp`, orama→PT adapter, Gate 3/4 E2E |
| Coordination consolidation Part 2/3 | Part 2 gated on nonexistent "Phase 0F" |
| 29-document phase-0 audit | Large companion audit not re-run |
| Housecleaning judgment calls | Kimi guidance, D23 placement, STM benchmark, etc. |

### `docs/v2/` deferrals (`perpetua-core`, `oramasys`, `agate`)

From [`docs/v2/README.md`](../v2/README.md) anti-scope + module roadmap:

| Deferred | Target |
| --- | --- |
| RAG / vector memory | v2.0+ stub |
| Multi-agent swarm parallelism | v2.0+ |
| Self-improving evaluator | v2.5 |
| MAESTRO + SWARM enforcement | v2.5 |
| Public Plugin API | v2.1 |
| Redis coordination | v2.0+ (superseded by GossipMesh doc 43) |
| MCP-optional transport | v2.0+ |
| GossipBus mesh (BLE, CRDT) | v2.1+ — [`43-gossipbus-mesh-transport.md`](../v2/43-gossipbus-mesh-transport.md) |
| Master alignment v2 migration | [`18-master-alignment-v2-migration-plan.md`](../v2/18-master-alignment-v2-migration-plan.md) — PLAN stage only |
| Open questions OQ1, OQ2, OQ5, OQ9, OQ20, OQ29, OQ30 | See [`06-open-questions.md`](../v2/06-open-questions.md) |

### Fleet mesh deferred layers

[`docs/next/fleet-mesh/README.md`](fleet-mesh/README.md): Phases 8–10+
(recovery, topology learning, Byzantine/GossipMesh); LAN trust hardening /
multisite / durable replay → v2.1 / v2.5.

---

## 4. Recommended ordering

```text
1. Identity audit Phase 3 PT sync PR     ← highest cross-repo gap
2. Fix TLS stalled-client test
3. Identity audit Phase 4 (after 3 green)
4. Peer-mesh TLS/auth (orama) OR G7 portal MVP — pick one lane
5. Live AlphaClaw smoke (tri-repo #1) when stack is up
```

---

## 5. Navigation map

| Question | Start here |
| --- | --- |
| What's unfinished on v1? | Both `2026-07-25-pending-work-tracker.md` files |
| What was closed vs deferred? | [`2026-07-22-cross-repo-out-of-scope-closure.md`](../plans/2026-07-22-cross-repo-out-of-scope-closure.md) |
| What belongs in v2 org repos? | [`docs/v2/README.md`](../v2/README.md) + [`06-open-questions.md`](../v2/06-open-questions.md) |
| Fleet / mesh / G7? | [`docs/next/fleet-mesh/README.md`](fleet-mesh/README.md) |
| Tri-repo gates? | [PT tri-repo plan](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/2026-05-31-tri-repo-alignment-completion-plan.md) |
| Tilde `~/` junk root cause? | [PT wiki/12](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/wiki/12-literal-tilde-alphaclaw-install-dir.md) · [orama wiki/18](../wiki/18-literal-tilde-alphaclaw-install-dir.md) |

---

## How to use this file

Re-run integrity checks (`git fetch`, `pull --ff-only`, fresh-clone tree-twin)
before trusting HEAD SHAs. Update this report and both pending-work trackers in
the **same commit** as any status change they describe.
