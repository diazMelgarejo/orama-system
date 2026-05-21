# 19 — gstack Optional Integration (v2 Forward Plan)

> **Status:** Planning doc — v1 implementation is in `docs/superpowers/plans/2026-05-21-gstack-optional-submodule-plan.md`.
> This document records the v2 canonical design for `oramasys/*`.
> **No code changes to `oramasys/*` until this plan is reviewed.**

---

## What is gstack?

gstack is an optional developer toolkit that ships:
- **gbrain** — hybrid pgvector + FTS semantic search over indexed knowledge
- **gstack skills** — `/investigate`, `/qa`, `/context-save`, `/context-restore`, etc.
- **Continuous checkpoint** — auto-commit Claude Code sessions to git

gstack is maintained by garrytan and is independently versioned from orama-system.

In v1, gstack is registered as an optional git submodule (`tools/gstack/`). In v2,
it remains optional and idempotent — it is NEVER a hard dependency of any oramasys/* package.

---

## v2 Integration Design

### Detection contract (stable across v1 → v2)

The detection API defined in v1 (`scripts/tool_status.py`) becomes the canonical
contract. v2 perpetua-core may call it via a new `perpetua_core.sidecar.gstack` module:

```python
# perpetua_core/sidecar/gstack.py  (v2.1 addition)

def is_available() -> bool:
    """Return True if gbrain is callable on this machine. Never raises."""
    ...

def gbrain_query(query: str, limit: int = 5) -> list[dict]:
    """Call gbrain CLI. Returns [] if unavailable. Never raises."""
    ...
```

This replaces the `GbrainSearchTool` subprocess wrapper from v1 — same semantics,
extracted into a proper sidecar module with its own unit tests.

### v2 graph integration

In v2, the `GbrainSearchTool` is registered as a first-class `@tool` in the graph's
tool registry. Agents call it explicitly when they need semantic recall, rather than
it being injected automatically by ContextNode.

This preserves D4 (dependency-minimal kernel) — gstack/gbrain is an opt-in tool
that agents can invoke, not infrastructure that runs on every job.

```python
# perpetua_core/graph/plugins/tool.py — existing @tool registry
# v2.1: register GbrainSearch at import time (only if available)

if gstack.is_available():
    @tool
    def gbrain_search(query: str, limit: int = 5) -> list[dict]:
        return gstack.gbrain_query(query, limit)
```

### Portal integration (v2.1+)

The portal `GET /api/tools/status` endpoint from v1 is promoted to a first-class
API in oramasys. The portal UI shows a gstack installation widget:

```
┌─ Optional Tools ──────────────────────────────────────┐
│ gstack / gbrain                                        │
│ Status: ✓ detected (path)  Version: v1.2.3             │
│ Semantic RAG: enabled                                  │
│                                          [Re-check]    │
└────────────────────────────────────────────────────────┘
```

When not installed:

```
┌─ Optional Tools ──────────────────────────────────────┐
│ gstack / gbrain                                        │
│ Status: ✗ not detected                                 │
│ Semantic RAG: keyword-only mode                        │
│                          [Install via CLI] [Learn more]│
└────────────────────────────────────────────────────────┘
```

The "Install via CLI" button shows the command `bash install-gstack.sh` in a modal.
It does NOT auto-install — the user must run the command manually.

---

## gstack as OCI Sidecar (v2.5 target)

For distributed deployments (v2.5+), gstack runs as an OCI sidecar:

```yaml
# docker-compose.yml (v2.5 sketch)
services:
  oramasys:
    image: ghcr.io/oramasys/oramasys:latest
    environment:
      GBRAIN_MCP_URL: "http://gstack:4242"

  gstack:  # optional — comment out to disable
    image: ghcr.io/garrytan/gstack:latest
    ports: ["4242:4242"]
    profiles: ["gstack"]  # not started by default
```

When `GBRAIN_MCP_URL` is set, perpetua-core routes `GbrainSearchTool` calls to the
MCP HTTP endpoint instead of the CLI subprocess. Zero code change in the tool — the
sidecar module handles the transport.

---

## Invariants (must hold across all versions)

| Invariant | v1 | v2 |
|-----------|----|----|
| System starts without gstack | ✅ | ✅ |
| `GbrainSearchTool` returns `[]` when unavailable | ✅ | ✅ |
| No pip install required for gstack | ✅ | ✅ |
| Detection is idempotent and fail-safe | ✅ | ✅ |
| gstack import never in perpetua-core top-level | ✅ | ✅ |

---

## OQ resolutions

| OQ | Topic | Resolution |
|----|-------|------------|
| (new) OQ22 | gstack hard dep? | Never. Optional sidecar in all versions. |
| (new) OQ23 | gbrain vs. LanceDB for agent RAG | gbrain = semantic search over docs + gstack memory (developer-maintained). LanceDB = agent-local RAG over GossipBus + docs (agent-owned). Both coexist, different corpora. |
| (new) OQ24 | gstack version pinning | `tools/gstack` submodule pinned to a specific commit. Operator updates manually. No auto-update. |

---

## See also

- `18-rag-and-memory-design.md` — LanceDB vector store and MemoryNode design
- `docs/superpowers/plans/2026-05-21-gstack-optional-submodule-plan.md` — v1 implementation plan
- `docs/plans/2026-05-19-gbrain-crg-embedding-integration.md` — unified bge-m3 embedding plan
