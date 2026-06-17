# 38 — Helicone Proxy-Caching Pattern: Hash-Based LRU in `_dispatch`

> **Canonical home:** `orama-system/docs/v2/38-helicone-proxy-caching-pattern.md`
> **Status:** Proposed — approve before any implementation
> **Locks decision:** D21

---

## 1. Context

Helicone is a proxy caching layer for LLM APIs. Its core contribution is
**deterministic hash-based caching**: the full canonical request (model + messages +
sampling params) is hashed; on a cache hit the stored response is returned without
calling the model; misses are forwarded to the provider and the response is stored.

The v2 distillation plan (Group B, item [2]) says: emulate Helicone's proxy-caching
pattern as a **hash-based LRU inside PT's `_dispatch`** — never a separate service,
never a proxy process.

`MultiLLMRouter` (D17, `30-`) is the decorator that wraps `_dispatch`. The Helicone
cache lives **inside that decorator** — it is not a separate layer.

---

## 2. Decision (D21)

**What to build:** A cache substrate inside `MultiLLMRouter` (not a separate class)
that:
1. Computes a deterministic cache key from the canonical request.
2. On hit: returns the stored response, emitting a `cache_hit` trace span (D18).
3. On miss: calls through to `_dispatch`, stores the response, emits `cache_miss`.
4. Enforces TTL, a global LRU size cap, a kill-switch, and a purge API.

**What it is NOT:**
- Not a Helicone installation, proxy process, or SDK wrapper.
- Not a Redis cache — in-process Python `dict` with LRU eviction in v2.
- Not a separate class or service — lives inside `MultiLLMRouter`.
- Not shared across processes — per-process, in-memory only in v2.
- **Not implementable before D17 is approved.** D21 lives entirely inside `MultiLLMRouter`
  (the D17 decorator). D17 must be approved and its binding rules satisfied before D21
  implementation begins.

This document specifies only the caching layer. The full `MultiLLMRouter` is
specified in D17 (`30-multi-llm-router-caching-batching-decorator.md`).

---

## 3. Cache key correctness

The key must be:
- **Deterministic**: same logical request → same key, always.
- **Complete**: includes model, messages (after redaction), all sampling params.
- **Isolated**: namespaced per provider to prevent cross-provider collisions.
- **Redacted**: PII/secret-stripped before hashing — raw prompt never in the key.

Key construction pipeline (order is mandatory):

```
1. Redact PII/secrets from messages  →  redacted_messages
2. Canonicalize redacted_messages    →  sorted keys, normalised whitespace
3. Build canonical dict              →  {provider, model, tenant_id, session_id,
                                         messages: redacted_messages, ...params}
4. JSON-serialise (sorted keys)      →  canonical_json
5. HMAC-SHA256(canonical_json, salt) →  cache_key   (salt = per-deployment secret from env)
```

> **Namespace requirement (D17 §3.2):** `tenant_id` and `session_id` are required fields
> in step 3. A Fable 5 result must never be served for an Opus 4.8 key, and one session's
> cache must never be visible to another. The key namespace is: model / tenant / session /
> backend — all four must be in the canonical dict.

> **Pipeline failure = MISS (binding):** If any step in the key construction pipeline
> raises an exception (redaction failure, serialization error, HMAC error), the result
> is a **cache MISS**. The exception MUST NOT propagate to the caller; the real `_dispatch`
> is called as normal. The failed key computation MUST NOT write to the cache. Log the
> exception type only — never log the failed intermediate state (it may contain prompt content).

**Temperature is NOT a caching gate.** Removed from prior drafts: temperature==0
is not a reliable determinism signal across providers. Cache correctness is enforced
by the key construction above (same inputs → same key → same response is valid to
serve), not by inspecting temperature.

---

## 4. Cache substrate

```python
# Inside MultiLLMRouter — not a public class
@dataclass
class _CacheEntry:
    response: dict
    ts: float        # insertion timestamp
    ttl: float       # seconds

class _LRUCache:
    def __init__(self, maxsize: int, default_ttl: float): ...
    def get(self, key: str) -> dict | None: ...       # None = miss or expired
    def put(self, key: str, value: dict, ttl: float | None = None) -> None: ...
    def purge(self, pattern: str | None = None) -> int: ...   # returns evicted count
    def kill(self) -> None: ...                        # runtime kill-switch: purge ALL entries
                                                        # AND disable atomically; re-enabling
                                                        # requires process restart (not a toggle)
```

Config (from `config/models.yml` or env):

| Key | Default | Notes |
|-----|---------|-------|
| `cache.maxsize` | 512 entries | LRU eviction when exceeded |
| `cache.default_ttl` | 3600 s | Per-entry TTL |
| `cache.enabled` | `true` | Kill-switch: set `false` to disable without restart |
| `cache.hmac_salt` | from env `ORAMA_CACHE_SALT` | Required; no default; startup fails if absent. **This config key is an env-only pointer — the salt value itself MUST NOT appear in `models.yml` or any tracked config file.** |

---

## 5. What is cached vs. not cached

| Cacheable | Not cacheable |
|-----------|---------------|
| Successful responses (2xx) | Errors, rate-limit responses |
| Any model/provider | Streaming responses (v2; v2.1 adds stream caching) |
| Any temperature | Responses where provider returned a retry hint |

---

## 6. Trace integration (D18)

Every cache access emits a trace span:

```jsonl
{"trace_id": "...", "parent_id": "...", "span": "cache", "result": "hit|miss|skip", "key_prefix": "<first 8 hex chars of key>", "ttl_remaining": N}
```

`key_prefix` is defined as **exactly the first 8 hexadecimal characters** of the HMAC-SHA256
key (binding, not advisory). The full key MUST never appear in logs — it is derived from
redacted prompts but still contains structural information about the request.

---

## 7. Alternatives rejected

| Alternative | Why rejected |
|-------------|-------------|
| Use Redis | Not in PT dep graph; per-process dict is sufficient for v2 workload |
| Separate caching service / proxy | Violates "emulation not importation"; adds process boundary |
| Cache only temperature==0 calls | Temperature is not a determinism gate — removed |
| Cache responses in orama (L3) | Caching is runtime state — belongs in PT (L2) per architecture |
| Shared cache across processes | Requires Redis or file locking — deferred to v2.1 |

---

## 8. Consequences

**Positive:**
- Repeat prompts (common in distillation loops) return instantly with zero model cost.
- Kill-switch allows runtime disable without restart.
- Trace integration (D18) makes cache hit rate visible in session distillation.

**Negative / constraints:**
- In-process: cache dies on restart. Cross-session reuse requires v2.1 persistence.
- `ORAMA_CACHE_SALT` must be set at startup — startup hard-fails if absent (intentional).
- No stream caching in v2; streaming calls always go to model.

---

## 9. Open questions

- **Q1:** Should cache hits count against the cost budget (D20)? Recommend: no —
  hits are free; only misses (actual model calls) count.
- **Q2:** Should `purge(pattern)` match on key prefix or on model ID? Recommend:
  key prefix in v2 (simpler); model-ID-aware purge in v2.1 when model retires.

---

## 10. Locked decision

**D21 — Helicone proxy-caching is an in-process LRU cache inside `MultiLLMRouter`, key = HMAC-SHA256(redacted+canonicalized request) (2026-06-17)**

PT emulates Helicone's proxy-caching as an `_LRUCache` substrate inside `MultiLLMRouter`.
Key = HMAC-SHA256 of redacted+canonicalized request (salt from env); namespace includes
model/tenant/session/backend (D17 §3.2). Cache only successes. In-memory LRU (512 entries,
1 h TTL, runtime kill-switch = purge+disable atomically, restart required to re-enable).
Temperature not a caching gate. key_prefix = first 8 hex chars only. Trace spans on every
cache access. `ORAMA_CACHE_SALT` required at startup.

**Clarification on "fail-open":** a cache MISS (including pipeline failures) falls through
to the real `_dispatch` — this is intended behavior, not a security bypass. The cost gate
from D17 (`self._cost_guard.gate(spec)`) remains **fail-closed** and is NOT bypassed by a
cache miss. "Fail-open on miss" means only: missing cache entries never block dispatch.
Gate doc: this file. **Prerequisite: D17 must be approved before D21 implementation.**

---

## 11. Cross-references

- D17: `30-multi-llm-router-caching-batching-decorator.md` — `MultiLLMRouter` is the host; **D17 must be approved before D21 implementation**; D17 §3.7 specifies route-provenance stripping (`:607` only — `routed_to_windows`/`windows_endpoint` stripped before store; `:567` skill-envelope leg is non-cacheable)
- D18: `35-langfuse-trace-tree-pattern.md` — trace spans from cache accesses feed distillation
- D20: `37-manifest-cost-tiering-pattern.md` — cache hits bypass model call but NOT the cost gate (cost gate is in D17 decorator, before cache check on miss; cache hits short-circuit before `gate()` on the read path per D17 §2)
- `Perpetua-Tools/orchestrator/supervisor.py:534` — `_dispatch` seam wrapped by `MultiLLMRouter`; route-provenance keys at `:607` only (not `:567`)
- `docs/distill-fable-5/implementation-plan.md` — Group B [2]
