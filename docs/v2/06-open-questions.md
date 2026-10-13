# 06 — Open Questions

> **Repository standard:** everything executable lives under `/src`; no root-level
> `scripts`/`tests`/`tools`/`examples`; data output and produced binaries stay `.gitignore`d, never
> committed with secrets, personal paths, or SecOps material. Additive — see
> [`46-repository-standard.md`](46-repository-standard.md).
Items deliberately deferred. Each has a target checkpoint for resolution.

---

## Active open questions

| # | Question | Context | Status |
| --- | ---------- | --------- | ------------ |
| — | *None* | All baseline v2 questions (OQ1–OQ30) resolved as of 2026-10-03, except OQ10, which is **APPROVED** and scheduled for v2.2 planning (canonical row: [`08-technical-architecture-review.md`](08-technical-architecture-review.md)). Future open questions are scoped to module-specific RFCs. | **All Settled** (OQ10: v2.2 planning, APPROVED) |

---

## Resolved (logged for posterity)

| # | Question | Resolution | Date |
| --- | ---------- | ------------ | ------ |
| OQ1 | **Pydantic AI as framework vs LangGraph/LangChain** | **Resolved 2026-10-03:** No runtime replacement of MiniGraph kernel. Maximize Pydantic AI coverage across application and tool layers (typed dependency injection, `@tool` schema extraction, structured outputs, agent signatures) while pursuing 100% drop-in compatibility with LangGraph/LangChain (StateGraph protocol, checkpoint/thread identity, message wrappers) as a standing target. It is work in progress, not yet finished and not a delivered guarantee; the target is never dropped or qualified. MiniGraph nodes natively host both Pydantic AI agents and LangGraph runnables. | 2026-10-03 |
| OQ2 | **GGUF hardware spec extension** | **Resolved 2026-10-03:** Do not wait for community RFC pending since Oct 2024. Implement and publish `agate` as the de facto bridge specification mapping GGUF model IDs to hardware policy. When the upstream GGUF RFC eventually lands, `agate` will serve as the reference compiler targeting native GGUF `system_requirements` metadata keys. | 2026-10-03 |
| OQ3 | **`agate` naming on PyPI** | **Resolved 2026-10-03:** Live PyPI check confirmed package name `agate` is TAKEN (v1.14.2, data analysis library by Christopher Groskopf). The Python package distribution name must use namespace prefix: `oramasys-agate` (or `agate-spec`), while the GitHub repository remains `oramasys/agate`. | 2026-10-03 |
| OQ5 | **Agent identity attestation (MAESTRO Layer 3)** | **Resolved 2026-10-03:** Honor-system agent IDs (`metadata["agent_id"]`) remain sufficient for LAN-local deployment until external exposure. Upon external exposure, implement lightweight cryptographic signing by hashing the local node's control plane secret with `metadata["agent_id"]` to generate an HMAC verification signature without heavy PKI. | 2026-10-03 |
| OQ6 | **Perpetua-Tools repository** | **Resolved 2026-10-03:** Done. Perpetua-Tools repository is cloned locally at `perplexity-api/Perpetua-Tools`, CI blockers and typo fixes resolved, PR pair #418 (PT) and #376 (Orama) actively maintained in lockstep with 100% test pass rate. | 2026-10-03 |
| OQ9 | **`quickstart.py` scope & TTHW** | **Resolved 2026-10-03:** Target Time-To-Hello-World (TTHW) ≤ 10 min. `quickstart.py` lives in `oramasys/oramasys` (unifying both repos). Must demonstrate: (a) 3-node graph, (b) hardware routing via agate/hardware policy, (c) HITL pause + resume via Interrupt. Standalone runnable with `uvicorn oramasys.orama.api.server:app --reload` + client script. | 2026-10-03 |
| OQ29 | **GossipBus mesh transport — LAN GossipMesh vs BLE** | **Resolved 2026-10-03:** Mesh gossip is the frugal event fan-out layer ([`43-gossipbus-mesh-transport.md`](43-gossipbus-mesh-transport.md)). Retain exact same JSON envelope standard across all tiers. Design the BLE envelope specification now for bitchat-class offline mesh (proximity cells, ≤512 byte framed JSON envelope payload) so v2.1 LAN HTTP/WS and v3 offline BLE share identical schema and deduplication semantics. | 2026-10-03 |
| OQ30 | **Mesh sync strategy — Cursor-based tail pull vs CRDT** | **Resolved 2026-10-03:** Adopt cursor-based tail pull (`since_id` / `since_ts`). CRDT/merge is rejected as unwarranted complexity for LAN and bounded mesh. Tail cursors match append-only GossipBus storage, hot-write batching (≤50 events or 500ms), and `(particle_id, event_id)` receiver deduplication. | 2026-10-03 |
| D1 | Clean-slate vs. evolve-in-place | Clean-slate rewrite | 2026-04-30 |
| D2 | Repo names | `perpetua-core` + `oramasys` | 2026-04-30 |
| D3 | v2 sequencing | v1.0 RC first | 2026-04-30 |
| D4 | Architecture model | Microkernel | 2026-04-30 |
| D5 | Plugin API | Internal v2.0, public v2.1 | 2026-04-30 |
| D6 | Spec layout | Master + per-module | 2026-04-30 |
| D7 | Schema lib | Pydantic v2 (Pydantic AI = framework, not schema lib) | 2026-04-30 |
| D8 | Kernel tier | **Revised 2026-04-30**: ~70-line pure kernel + `graph/plugins/`. Canonical implementation: `oramasys/perpetua-core` commit `2f717f5`, 65-line engine + 6 plugins, 32 tests | 2026-04-30 / impl 2026-05-01 |
| D9 | Build approach | GPT Phase 1-4, lift proven pieces | 2026-04-30 |
| D10 | License | MIT | 2026-04-30 |
| D11 | 3rd new repo | `oramasys/agate` (Hardware Policy Specification) | 2026-05-01 |
| D12 | GitHub org | Real GitHub org `oramasys` (user to create at github.com/organizations/new) | 2026-05-01 |
| D13 | TDD policy | Enshrined in `docs/v2/README.md` and `04-build-order.md`. tdd.md is the source of truth. | 2026-05-01 |
| OQ10 | **Capability-Based Routing** — Should the `model_hardware_policy.yml` move from model-ID mapping to hardware capability rules (e.g. `VRAM >= 12GB`)? | **Approved (v2.2 planning).** The `model_hardware_policy.yml` schema will support a `requirements` block (e.g., `vram_min_gb: 12`). Canonical row with all details: [`08-technical-architecture-review.md`](08-technical-architecture-review.md). | v2.2 planning, APPROVED |
| OQ11 | GossipBus async | **Resolved:** `aiosqlite` used from day one in `oramasys/perpetua-core` — no sync SQLite; background writer concern resolved by async-native design | 2026-05-01 |
| OQ4 | GitHub org `oramasys` creation | Org created; all 3 v2 repos live at `github.com/oramasys/*` | 2026-05-01 |
| OQ7 | Python version for new repos | Python 3.11+ from day one; `requires-python = ">=3.11"` in all 3 `pyproject.toml` files | 2026-05-01 |
| OQ8 | `optimize_for` field name | `optimize_for: OptHint = "quality"` IS on `PerpetuaState` in canonical (matches Grok synthesis + policy routing key structure) | 2026-05-01 |
| (OQ13) | PerpetuaState dataclass vs BaseModel | `BaseModel` with `ConfigDict` in canonical; `scratchpad: dict[str,Any]` | 2026-05-01 |
| (OQ14) | `perpetua-core` org transfer | Canonical was always under `oramasys` org; no transfer needed | 2026-05-01 |
| (OQ16) | Engine integration vs. plugins | 65-line pure engine + `graph/plugins/` is canonical; D8 revision implemented | 2026-05-01 |
| D14 | LM Studio proxy gotcha / mirror enforcement | `_MIRROR_BACKENDS` + `windows_only:` hard enforcement in `model_hardware_policy.yml`; `devices.yml` corrected; `_TIER_HOSTS["mac"]` = ollama-only. See `17-hardware-policy-enforcement.md` for full chain. | 2026-05-17 |
| D15 | `orchestrator/agent_launcher.py` naming collision | Renamed to `orchestrator/backend_resolver.py` — pure policy function split from 859-line operational CLI. Interface: `resolve_backend_for_spec(registry, spec) -> Backend`. | 2026-05-18 |
| D16 | **P5 Sybil defense — witness dedup method** | `/24` prefix dedup for now (2-3 operator-controlled nodes; no untrusted peers). Upgrade to MaxMind GeoLite2 ASN lookup when v2.1 adds untrusted peers. See detail below. | 2026-07-13 |
| OQ12 | **Kernel recursion limit** — Should `MiniGraph.ainvoke` enforce a `max_steps` safety guard? | **Resolved 2026-05-17 (RC-1):** `max_steps` guard implemented in `engine.ainvoke`; raises `RuntimeError` on overflow. `tests/graph/test_engine_max_steps.py` (Task 5). | ✅ Done |
| OQ17 | **Typed Message wrapper** — Should `perpetua_core/message.py` add a typed wrapper for messages instead of plain `dict`? | **Resolved 2026-05-17 (RC-1):** `Message(BaseModel)` shipped in `perpetua_core/message.py` (43 lines); `tests/test_message.py` (Task 12). | ✅ Done |
| OQ18 | **agate `NEVER` verdict integration** — The v1 `_MIRROR_BACKENDS` + `windows_only:` pattern implements a `NEVER` verdict (dispatch = hardware damage risk). How does the agate schema expose this? Options: (a) explicit `NEVER`/`PREFER`/`ALLOW` string verdicts in the YAML (cleanest, user-facing); (b) derived from `windows_only:`/`mac_only:`/`shared:` list membership (current v1, implicit); (c) separate `enforcement:` key distinguishing hard vs. soft routing. | v1 uses list-membership inference. agate schema should make this explicit — consumers (LangGraph, CrewAI, custom runtimes) need to distinguish "won't run well here" from "will OOM/crash here." The `NEVER` verdict must be unambiguous. | agate v0.1 schema design |
| OQ19 | **Selector mirror exclusion in v2 perpetua-core** — `selector.py` in v1 carries `_MIRROR_BACKENDS` and `_TIER_HOSTS` as module-level constants. Should v2 derive these from config? | **Resolved 2026-05-17 (RC-1):** `selector.py` ships with `_MIRROR_BACKENDS` frozenset enforcing D14 mirror-exclusion policy; `_TIER_HOSTS["mac"]` = ollama-only. `test_discovery_selector.py` covers 12 cases (Task 4). | ✅ Done |
| OQ20 | **Board-job source-line schema — optional or hard-required?** — `Perpetua-Tools` `_queue_add()` now accepts optional `source_ref`/`expected_base_sha` (validated when provided, see [`48-board-job-source-line-schema.md`](48-board-job-source-line-schema.md)). Should v2 make these mandatory on every producer, and require every claimant to verify HEAD against `expected_base_sha` before starting work? | **Scoped resolution:** v1 remains optional/provisional; the deferred v2.1 Orchestrator Controller requires both fields for every new task and claimant. Legacy queued rows need explicit migration/handoff disposition, not silent compliance. See [`68-orchestrator-controller-satellite.md`](68-orchestrator-controller-satellite.md). | v2.1 controller gate |

---

## D16 detail — ASN Lookup Decision (P5 Sybil Defense)

Per the recommendation: **Use /24 prefix dedup for now.**

Rationale:

- Current deployment: 2-3 operator-controlled nodes (Mac, Windows, maybe cloud)
- No untrusted peers — Sybil attack is not a realistic threat at this scale
- Zero additional dependencies — /24 prefix check is 2 lines of Python
- Upgrade path documented: MaxMind GeoLite2 when scaling to untrusted peers in v2.1

```python
# /24 prefix dedup (2 lines, zero deps)
ip_prefix = ipaddress.ip_address(ip).packed[:3]  # first 3 octets
prefix_id = ip_prefix.hex()  # use as witness dedup key
```

When v2.1 adds untrusted peers, upgrade to:

```python
# MaxMind GeoLite2 (requires maxminddb package + DB download)
import maxminddb
with maxminddb.open_database('GeoLite2-ASN.mmdb') as reader:
    asn = reader.get(ip)['autonomous_system_number']
```
