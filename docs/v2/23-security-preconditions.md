# 23 — Security Preconditions (v2 gate)

> **Status:** Active gate — v2 scaffold work must not proceed on a shared LAN until rows marked **done** below are true in production configs, and new v2 surfaces must satisfy the security-first platform requirements.  
> **Review source:** [`OpenClaw/v1/2026-05-23-security-markdown.md`](../../../OpenClaw/v1/2026-05-23-security-markdown.md)  
> **Canonical policy:** [`../SECURITY-POLICY.md`](../SECURITY-POLICY.md)
> **Design baseline:** [`24-security-first-platform.md`](24-security-first-platform.md)

---

## Fix map (1–6)

| Fix | Title | v2 milestone blocker? | Status (2026-05-26) |
|-----|-------|----------------------|---------------------|
| 1 | Remove committed API key literals | Yes | **done** — env placeholders + hygiene scanner |
| 2 | Secret scanning in CI/hygiene | Yes | **done** — `repo_hygiene.py` + tests |
| 3 | Control-plane auth + loopback bind + CORS allowlist | Yes | **re-opened as active gate** — scheduled review found remaining route/bootstrap/launcher gaps; see immediate queue |
| 3c | Memory redaction before persist | Yes (RAG) | **done** — PT `memory_governance` + GossipBus |
| 4 | MCP path boundary + log redaction | Yes (MCP modules) | **done** — PT `path-boundary.cjs` + orama `mcp_path_boundary.py` |
| 5 | Endpoint URL egress policy | Yes (distributed) | **re-opened as active gate** — model discovery/probe authorization leakage must be fixed in v2 design |
| 6 | Least-privilege MCP / worker profiles | Recommended | **re-opened as active gate** — readonly merged config must prove elevated servers are pruned |

---

## v2 features blocked until preconditions pass

| v2 doc | Blocked until |
|--------|----------------|
| [`20-rag-and-memory-design.md`](20-rag-and-memory-design.md) | Fix 3c + auth on any memory search API |
| [`04-build-order.md`](04-build-order.md) Phase 4+ HTTP surfaces | Fix 3 on all mutation routes |
| [`02-modules/rag-and-memory.md`](02-modules/rag-and-memory.md) | Fix 3c + retention/erase design (v2.5) |
| MCP / multi-agent modules | Fixes 4–6 (path boundary, URL policy, least-privilege MCP) |
| Any new module under [`02-modules/`](02-modules/) | Completed design-gate answers from [`24-security-first-platform.md`](24-security-first-platform.md#4-required-design-gates-for-every-v2-module) |

---

## Acceptance criteria (operator)

- [ ] `ORAMA_CONTROL_PLANE_TOKEN` set; portal `GET /api/status` without bearer returns 401
- [ ] PT `POST /v1/jobs` without bearer returns 401
- [ ] `python3 scripts/review/repo_hygiene.py` exits 0 on both repos
- [ ] No `AIza…` literals in tracked config (scanner clean)
- [ ] Defaults bind to `localhost` unless `*_BIND_LAN=1` is explicit
- [ ] `GET /` and dashboard routes never expose a raw control-plane bearer in
  HTML/JS/JSON bootstraps
- [ ] Model probes and discovery requests never include control-plane
  `Authorization` headers and only persist approved/pinned endpoints
- [ ] Readonly MCP profile tests inspect the final merged runtime config and
  fail if elevated managed workers remain enabled
- [ ] Every new route/tool/worker declares a capability and has auth-denial
  tests unless it is explicitly `public`

The original fixes remain valuable, but rows **3**, **5**, and **6** are active
v2 design gates again until the 2026-05-26 immediate queue in
[`../SECURITY-POLICY.md`](../SECURITY-POLICY.md#immediate-todo-list--validated-findings-from-scheduled-review-2026-05-26)
is resolved or explicitly annotated as remediated.
