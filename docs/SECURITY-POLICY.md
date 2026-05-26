# Security Policy — orama-system + Perpetua-Tools

> **Canonical security posture** for the OpenClaw orchestration stack.  
> **Last updated:** 2026-05-26  
> **Source review:** [`OpenClaw/v1/2026-05-23-security-markdown.md`](../../OpenClaw/v1/2026-05-23-security-markdown.md)

---

## Scope

This policy covers **orama-system** (portal, ultrathink API, hygiene CI) and **Perpetua-Tools** (job control plane, workers, RAG memory, MCP packages). AlphaClaw MCP code lives in the Perpetua-Tools tree.

---

## Implemented (fixes 1–6) — 2026-05-25

| # | Finding | Implementation |
|---|---------|----------------|
| **1** | Committed Google API key-shaped literal | `config/mac-orchestrator.json` uses `${env:OPENCLAW_MODELS_PROVIDERS_GEMINI_FALLBACK_APIKEY}`; rotate any key ever committed |
| **2** | No secret scanning in CI | `scripts/review/repo_hygiene.py` → `scan_tracked_secrets()`; `tests/test_repo_hygiene.py` |
| **3** | Unauthenticated LAN control plane | Shared bearer: `ORAMA_CONTROL_PLANE_TOKEN`; `utils/control_plane_auth.py` (orama); `orchestrator/control_plane_auth.py` (PT); portal + API middleware; PT job routes protected |
| **3b** | Wildcard CORS / `0.0.0.0` default | Portal: `cors_allow_origins()` + `default_bind_host()` loopback-first; PT FastAPI CORS allowlist |
| **3c** | Raw memory persistence | `orchestrator/redaction.py` + `memory_governance.py`; GossipBus `emit()` redacts before SQLite/LanceDB |
| **4** | MCP file/log read without path boundary | PT: `packages/local-agents/src/path-boundary.cjs` + `alphaclaw-mcp` log redaction; orama: `utils/mcp_path_boundary.py`; env roots `MCP_APPROVED_ROOTS`, `ALPHACLAW_ROOT`, `PERPETUA_TOOLS_ROOT`, `ORAMA_SYSTEM_ROOT` |
| **5** | Remote LM Studio / Win coder URL policy | `utils/model_endpoint_url.py` (orama + PT); default loopback + RFC1918; `ALLOW_PUBLIC_MODEL_ENDPOINTS=1` opt-in; wired in PT `supervisor.py` + `worker_registry.py`, orama `api_server.py` |
| **6** | Least-privilege MCP profiles | PT: `alphaclaw-mcp` profile gate + `PT_ALLOW_DANGEROUS_CLI_WORKERS`; orama: `cursor-mcp.stack.readonly.json` + `sync-cursor-mcp.sh --profile` |

**Perpetua-Tools sync note (2026-05-25):** Fixes **3** and **3c** in the table above are implemented on **remote** `Perpetua-Tools` `main` (control-plane auth, memory redaction). A stale local `main` checkout may not include those commits yet — see [79-commit audit — Appendix A](../../OpenClaw/v1/2026-05-23-security-markdown.md#appendix-a--79-commit-security-audit-2026-05-25) before assuming PT routes are protected on disk.

**Operator checklist**

1. Set `ORAMA_CONTROL_PLANE_TOKEN` in `.env.local` (orama + PT share via `.state/control_plane_token` when PT starts).
2. For LAN exposure: set `PORTAL_BIND_LAN=1` / `PT_BIND_LAN=1` **and** keep bearer auth enforced (`ORAMA_INSECURE_DEV=0` or token set).
3. Run `bash scripts/git/install-local-hooks.sh` before commits in each repo clone.
4. Run `python3 scripts/review/repo_hygiene.py` (orama) before push.
5. Multi-file code exploration: **code-review-graph MCP first** (`detect_changes_tool`, `get_review_context_tool`), then gbrain, then scoped Read — see `bin/orama-system/skills/code-review/SKILL.md` (no pre-commit hook; required workflow).

---

## Immediate TODO list — validated findings from scheduled review (2026-05-26)

These items are additive to the implemented fix table above. Some findings
overlap precise planned work in
[`docs/plans/2026-05-23-security-remediation-plan.md`](plans/2026-05-23-security-remediation-plan.md);
those planned workstreams come first so agents continue the existing patch
shape instead of inventing a parallel remediation.

### A. Already planned / duplicate workstreams to reopen first

| Workstream | Existing plan anchor | Covers findings | Next action |
|------------|----------------------|-----------------|-------------|
| **A1 — Control-plane auth, loopback, and LAN-bind hardening** | Remediation plan Phase 1 (`start.sh`: LAN bind requires token; portal route auth audit) and Phase 2 (shared bearer auth on PT + orama routes) | Critical/High/Medium portal takeover surfaces: spawn-agent execution, secret overwrite, swarm launch, lifecycle stop/restart, job detail exposure, copied example token, loopback dashboard token bootstrap, Windows all-interface launcher | Re-open Fix 3/3b as incomplete until every mutating/read-sensitive route is covered, no bearer is embedded in HTML, copied templates do not contain usable tokens, and all launchers use loopback-by-default with explicit `*_BIND_LAN=1` plus strong token. |
| **A2 — Model endpoint discovery and egress policy** | Remediation plan Phase 3 (`Endpoint URL validator`, local-only/default-private endpoint policy) | LAN discovery endpoint hijack and status-probe bearer leakage to model endpoints | Pin/approve discovered model hosts before persistence, strip control-plane `Authorization` from LM Studio/Ollama probes, and keep public/non-approved model endpoints opt-in only. |
| **A3 — Least-privilege MCP / worker profiles** | Implemented Fix 6 plus operator reference in this policy | Readonly Cursor MCP profile still preserving elevated `ai-cli-mcp` in active project config | Make readonly profile pruning verifiable against the merged on-disk config, not only dry-run stack output; keep dangerous CLI workers behind explicit elevated opt-in. |

### B. Severity-ranked remediation queue

| Priority | Severity | Finding | Primary location | Highest-leverage remediation |
|----------|----------|---------|------------------|------------------------------|
| 1 | Critical | Unauthenticated portal endpoint dispatches full-auto CLI agents with attacker-controlled tasks | `portal_server.py` | Require control-plane auth on `/api/spawn-agent`, disable HTTP access to full-auto CLI dispatch unless explicitly elevated, and add regression tests for unauthenticated denial. |
| 2 | High | Loopback dashboard auth exemption leaks the control-plane bearer through local reverse proxies | `utils/control_plane_auth.py` | Remove bearer-in-HTML bootstrap and do not infer operator trust solely from `request.client.host`; use an explicit authenticated browser/session bootstrap. |
| 3 | High | Windows launcher exposes control-plane services on all interfaces by default | `platform/windows/start.ps1` | Mirror `start.sh` loopback-first bind resolution and require explicit `*_BIND_LAN=1` plus strong token before any LAN bind. |
| 4 | High | Unauthenticated portal clients can overwrite persisted integration secrets | `portal_server.py` | Gate `/api/configure-tool` behind authenticated operator auth and audit every secret write. |
| 5 | High | Unauthenticated portal clients can launch multi-agent supervisor jobs with attacker-controlled prompts | `portal_server.py` | Replace request-body `approved=true` with server-side authenticated approval and PT-side auth rejection for unauthenticated job creation. |
| 6 | High | LAN discovery trusts unauthenticated LM Studio responders and persists attacker endpoints | `scripts/discover.py` | Require explicit operator approval or trusted host pinning before persisting newly discovered model endpoints. |
| 7 | High | Portal status probes leak the control-plane bearer token to untrusted model endpoints | `portal_server.py` | Split trusted PT/orama clients from untrusted model-probe clients and explicitly strip `Authorization` for LM Studio/Ollama/discovery-derived hosts. |
| 8 | High | Unescaped model names from LAN model probes execute script in the portal dashboard | `portal_server.py` | Escape all remotely supplied model/status strings before HTML interpolation or render structured JSON via safe text nodes. |
| 9 | High | Example control-plane token plus copied LAN bind gives same-LAN clients authenticated portal access | `.env.example` | Ship no usable example control-plane token; keep active template values loopback-safe and require generated/operator-provided strong tokens. |
| 10 | High | Worktree bootstrap writes attacker-controlled slugs into a source-able shell file without quoting | `scripts/worktree-bootstrap.sh` | Enforce a narrow slug allowlist and write generated shell environment values with safe quoting. |
| 11 | Medium | Unauthenticated lifecycle endpoints let remote clients kill or restart the orchestration stack | `portal_server.py` | Require authenticated operator auth and CSRF/origin protections for stop/restart or remove HTTP lifecycle controls from LAN-facing routes. |
| 12 | Medium | Job detail proxy exposes unredacted prompts and worker results to unauthenticated clients | `portal_server.py` | Authenticate job APIs and return a redacted job DTO instead of raw PT `result.json`/prompt payloads. |
| 13 | Medium | Readonly Cursor MCP profile still launches the elevated ai-cli worker from the tracked project config | `.cursor/mcp.json` | Make tracked/default Cursor MCP config readonly-safe and have `sync-cursor-mcp.sh --profile readonly` prune managed elevated servers. |

### C. Immediate acceptance checks for agents

- [ ] Unauthenticated `POST /api/spawn-agent`, `/api/configure-tool`,
  `/api/swarm/launch`, `/api/stop`, `/api/restart/*`, and job detail routes
  return 401 when auth is enforced.
- [ ] `GET /` with auth enforced never returns the raw control-plane token in
  HTML, even when the upstream peer is loopback.
- [ ] `start.sh` and `platform/windows/start.ps1` both bind to loopback unless
  the corresponding `*_BIND_LAN=1` flag is set and a strong token is present.
- [ ] Status/model probes never send the control-plane bearer to LM Studio,
  Ollama, discovered LAN hosts, or public model endpoints.
- [ ] Legacy dashboard/status HTML escapes model names, URLs, routing labels,
  activity text, and all other remote probe strings.
- [ ] `scripts/worktree-bootstrap.sh` rejects slugs outside a safe
  alphanumeric/dot/dash/underscore pattern and shell-quotes generated env files.
- [ ] Readonly MCP profile tests validate the final merged `.cursor/mcp.json`
  state, not only dry-run stack contents.

---

### Fix 6 — operator reference (implemented)

**Perpetua-Tools — AlphaClaw MCP**

| Profile | Env | Effect |
|---------|-----|--------|
| readonly (default) | `ALPHACLAW_MCP_PROFILE=readonly` | 10 read-only tools only |
| elevated | `ALPHACLAW_MCP_PROFILE=elevated` | all 14 tools |
| granular | `ALPHACLAW_MCP_ENABLE_PROCESS_TOOLS=1` | adds build_ui, run_tests |
| granular | `ALPHACLAW_MCP_ENABLE_MUTATING_TOOLS=1` | adds login, propose_edit |

Examples: `Perpetua-Tools/packages/alphaclaw-mcp/examples/mcp.readonly.json`, `mcp.elevated.json`.

**Perpetua-Tools — subprocess workers:** `PT_ALLOW_DANGEROUS_CLI_WORKERS=1` required for codex/gemini/agy job backends.

**orama-system — Cursor stack:** default `sync-cursor-mcp.sh --profile readonly` (CRG only); elevated adds `ai-cli-mcp` via `cursor-mcp.stack.json` or `ORAMA_MCP_ENABLE_AI_CLI=1`.

---

## Related docs

- **79-commit audit + PR review (Appendix A):** [`OpenClaw/v1/2026-05-23-security-markdown.md`](../../OpenClaw/v1/2026-05-23-security-markdown.md) — implementation status table and finding cross-ref
- Remediation plan: [`docs/plans/2026-05-23-security-remediation-plan.md`](plans/2026-05-23-security-remediation-plan.md)
- v2 preconditions: [`docs/v2/23-security-preconditions.md`](v2/23-security-preconditions.md)
- Debug notes: [`docs/2026-05-24-security-review-debug-and-fix-notes.md`](2026-05-24-security-review-debug-and-fix-notes.md)
- Git identity: [`docs/wiki/08-git-hygiene-and-branching.md`](wiki/08-git-hygiene-and-branching.md)
