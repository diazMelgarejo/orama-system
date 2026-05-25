# 23 — Security Preconditions (v2 gate)

> **Status:** Active gate — v2 scaffold work must not proceed on a shared LAN until rows marked **done** below are true in production configs.  
> **Review source:** [`OpenClaw/v1/2026-05-23-security-markdown.md`](../../../OpenClaw/v1/2026-05-23-security-markdown.md)  
> **Canonical policy:** [`../SECURITY-POLICY.md`](../SECURITY-POLICY.md)

---

## Fix map (1–6)

| Fix | Title | v2 milestone blocker? | Status (2026-05-25) |
|-----|-------|----------------------|---------------------|
| 1 | Remove committed API key literals | Yes | **done** — env placeholders + hygiene scanner |
| 2 | Secret scanning in CI/hygiene | Yes | **done** — `repo_hygiene.py` + tests |
| 3 | Control-plane auth + loopback bind + CORS allowlist | Yes | **done** — bearer middleware (orama + PT) |
| 3c | Memory redaction before persist | Yes (RAG) | **done** — PT `memory_governance` + GossipBus |
| 4 | MCP path boundary + log redaction | Yes (MCP modules) | **queued** — next session |
| 5 | Endpoint URL egress policy | Yes (distributed) | **done** — `utils/model_endpoint_url.py` (orama + PT) |
| 6 | Least-privilege MCP / worker profiles | Recommended | **queued** — next session |

---

## v2 features blocked until preconditions pass

| v2 doc | Blocked until |
|--------|----------------|
| [`20-rag-and-memory-design.md`](20-rag-and-memory-design.md) | Fix 3c + auth on any memory search API |
| [`04-build-order.md`](04-build-order.md) Phase 4+ HTTP surfaces | Fix 3 on all mutation routes |
| [`02-modules/rag-and-memory.md`](02-modules/rag-and-memory.md) | Fix 3c + retention/erase design (v2.5) |
| MCP / multi-agent modules | Fixes 4 and 6 |

---

## Acceptance criteria (operator)

- [ ] `ORAMA_CONTROL_PLANE_TOKEN` set; portal `GET /api/status` without bearer returns 401
- [ ] PT `POST /v1/jobs` without bearer returns 401
- [ ] `python3 scripts/review/repo_hygiene.py` exits 0 on both repos
- [ ] No `AIza…` literals in tracked config (scanner clean)
- [ ] Defaults bind to `localhost` unless `*_BIND_LAN=1` is explicit

Fixes **4–6** remain open; do not check those boxes until implemented.
