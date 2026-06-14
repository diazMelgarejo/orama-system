> ✅ **RESOLVED 2026-06-14** — RAG v1 backport shipped — this is the ship record.

# RAG v1 Backport — What Shipped (2026-05-22)

> **Status:** Released on `diazMelgarejo/Perpetua-Tools` branch `feat/rag-backport-v1` (PR #28)
> **Reference plan:** `docs/superpowers/plans/2026-05-21-rag-memory-v1-plan.md`
> **External reviews applied:** `docs/2026-05-21-001--Critique-RAG-ChatGPT-codex-GPT-5.5.md`
>                                `docs/2026-05-21-002--RAG-Gstack-Review--Antigravity-Gemini-3.5-Flash-Preview.md`

---

## Shipped to diazMelgarejo/Perpetua-Tools

| File | Description |
|------|-------------|
| `orchestrator/gossip_bus.py` | GossipBus — aiosqlite FTS5 event log with `_pending_embeds` GC guard |
| `orchestrator/memory_embed.py` | Ollama bge-m3 httpx helper + `probe_embed_dim()` |
| `orchestrator/memory_store.py` | LanceDB `EmbeddingStore(dim=...)` + `get_lance_store()` |
| `orchestrator/memory_rrf.py` | Pure RRF k=60 merge function |
| `tests/test_gossip_bus.py` | 16 tests — FTS5, GC guard, embed_status, sanitizer |
| `tests/test_memory_rrf.py` | 6 tests — RRF merge, dedup, top-n |
| `tests/test_memory_store.py` | 7 tests — LanceDB, dim env var, singleton isolation |
| `orchestrator/fastapi_app.py` | `_bg_startup_tasks` GC guard on routing-bg task |
| `pyproject.toml` | `aiosqlite>=0.19` core; `lancedb+pyarrow` as `[rag]` optional extras |
| `docs/2026-05-22-rag-backport-v1-release-notes.md` | Full release notes |

**Tests (items 1–4):** 345 passed, 2 skipped, 0 regressions.

---

## All 3 bug-class gaps applied (from Gemini 3.5 Flash review)

| Gap | Severity | Fix |
|-----|----------|-----|
| Gap 1 — dim hardcode | HARD BUG | `probe_embed_dim()` + `EmbeddingStore(dim=...)` + `EMBED_DIM` env var |
| Gap 2 — FTS5 silent failure | UX BUG | `_sanitize_fts_query()` strips FTS5 operators before MATCH |
| Gap 3 — GC test tautology | TEST BUG | Real `asyncio.sleep` behavioral test verifies `_pending_embeds` lifecycle |

---

## v1 Backport Candidates — updated status

From `docs/superpowers/plans/2026-05-21-rag-memory-v1-plan.md`:

| # | Item | Priority | Status |
|---|------|----------|--------|
| 1 | RRF merge | High | ✅ **Shipped** — `orchestrator/memory_rrf.py` |
| 2 | FTS5 + `_sanitize_fts_query()` | High | ✅ **Shipped** — `orchestrator/gossip_bus.py` |
| 3 | `_pending_embeds` GC guard | High | ✅ **Shipped** — `gossip_bus.py` + `fastapi_app.py` |
| 4 | LanceDB `EmbeddingStore` + dim probe | Medium | ✅ **Shipped** — `orchestrator/memory_store.py` + `memory_embed.py` |
| 5 | GbrainSearchTool | Conditional | ✅ **Shipped (2026-05-27)** — `orchestrator/gbrain_search.py`: async fn, subprocess CLI, graceful `[]` on any failure (no `@tool` needed in v1) |
| 6 | MemoryNode | Low/defer | ✅ **Shipped (2026-05-27)** — `orchestrator/memory_node.py`: `retrieve_context()` async callable, FTS5+LanceDB+optional gbrain+RRF; no v2 graph required |
| 7 | dispatch_node wiring | Low/defer | ✅ **Shipped (2026-05-27)** — `supervisor._inject_memory_context()` prepends `[MEMORY CONTEXT]` block to `spec.prompt` before routing |

---

## Architecture invariant re-confirmed (2026-05-22)

> **`diazMelgarejo/*` repos = v1-legacy = implement code here.**
> **`oramasys/*` repos = v2-planning = NEVER write code. Plan only via `/docs/v2/`.**
>
> The RAG v1 plan targets `oramasys/perpetua-core` module paths. The v1 backport
> adapts all paths to `orchestrator/` in Perpetua-Tools. This is intentional.
> Override of this separation rule requires explicit `AskUserQuestion` confirmation.

---

## Items 5–7 shipped details (2026-05-27)

Branch: `diazMelgarejo/Perpetua-Tools` `2026-05-27-006-rag-items-5-7`

| File | Description |
|------|-------------|
| `orchestrator/gbrain_search.py` | `gbrain_search()` async fn — subprocess `gbrain search --json`, `_normalise_hits()`, env-configurable timeout, `[]` on any failure |
| `orchestrator/memory_node.py` | `retrieve_context()` — FTS5 + LanceDB + optional gbrain + RRF; module-level bus/store singletons; `reset_singletons()` test helper |
| `orchestrator/supervisor.py` | `_inject_memory_context()` method + step 0 in `_dispatch()` — opt-out via `metadata["use_memory"]=False` |
| `tests/test_gbrain_search.py` | 14 tests — normalise, binary missing, empty query, list/dict response, bad JSON, timeout, nonzero exit |
| `tests/test_memory_node.py` | 7 tests — empty query, FTS-only, RRF merge, gbrain blend, all-fail degradation, top_n |
| `tests/test_supervisor_smoke.py` | +4 tests — inject prepends block, no hits unchanged, disabled by metadata, degrades on exception |

**Tests (items 5–7):** 25 new tests, all passing. Total suite: 400 passed (excl. pre-existing Python 3.9 / aiosqlite env failures).

**Env vars added:**
- `GBRAIN_MEMORY_ENABLED=1` — enables gbrain in every `retrieve_context` call (default off)
- `GBRAIN_SEARCH_TIMEOUT_SECONDS` — gbrain subprocess timeout in seconds (default 5)
- `MEMORY_NODE_TOP_N` — max hits returned by `retrieve_context` (default 5)

---

## Next sprint (v2.1)

Per `docs/v2/20-rag-and-memory-design.md`:
- `EmbeddingCircuitBreaker` — process-local breaker, opens after N failures, auto-closes
- Observability: state metrics, open/close counters, cooldown events
- Migration sequence: v1 → v2.1 rollback point documented

See also: `docs/superpowers/plans/2026-05-21-rag-memory-v1-plan.md` §"Follow-on"
