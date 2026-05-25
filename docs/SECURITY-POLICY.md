# Security Policy — orama-system + Perpetua-Tools

> **Canonical security posture** for the OpenClaw orchestration stack.  
> **Last updated:** 2026-05-25  
> **Source review:** [`OpenClaw/v1/2026-05-23-security-markdown.md`](../../OpenClaw/v1/2026-05-23-security-markdown.md)

---

## Scope

This policy covers **orama-system** (portal, ultrathink API, hygiene CI) and **Perpetua-Tools** (job control plane, workers, RAG memory, MCP packages). AlphaClaw MCP code lives in the Perpetua-Tools tree.

---

## Implemented (fixes 1–3) — 2026-05-25

| # | Finding | Implementation |
|---|---------|----------------|
| **1** | Committed Google API key-shaped literal | `config/mac-orchestrator.json` uses `${env:OPENCLAW_MODELS_PROVIDERS_GEMINI_FALLBACK_APIKEY}`; rotate any key ever committed |
| **2** | No secret scanning in CI | `scripts/review/repo_hygiene.py` → `scan_tracked_secrets()`; `tests/test_repo_hygiene.py` |
| **3** | Unauthenticated LAN control plane | Shared bearer: `ORAMA_CONTROL_PLANE_TOKEN`; `utils/control_plane_auth.py` (orama); `orchestrator/control_plane_auth.py` (PT); portal + API middleware; PT job routes protected |
| **3b** | Wildcard CORS / `0.0.0.0` default | Portal: `cors_allow_origins()` + `default_bind_host()` loopback-first; PT FastAPI CORS allowlist |
| **3c** | Raw memory persistence | `orchestrator/redaction.py` + `memory_governance.py`; GossipBus `emit()` redacts before SQLite/LanceDB |

**Perpetua-Tools sync note (2026-05-25):** Fixes **3** and **3c** in the table above are implemented on **remote** `Perpetua-Tools` `main` (control-plane auth, memory redaction). A stale local `main` checkout may not include those commits yet — see [79-commit audit — Appendix A](../../OpenClaw/v1/2026-05-23-security-markdown.md#appendix-a--79-commit-security-audit-2026-05-25) before assuming PT routes are protected on disk.

**Operator checklist**

1. Set `ORAMA_CONTROL_PLANE_TOKEN` in `.env.local` (orama + PT share via `.state/control_plane_token` when PT starts).
2. For LAN exposure: set `PORTAL_BIND_LAN=1` / `PT_BIND_LAN=1` **and** keep bearer auth enforced (`ORAMA_INSECURE_DEV=0` or token set).
3. Run `bash scripts/git/install-local-hooks.sh` before commits in each repo clone.
4. Run `python3 scripts/review/repo_hygiene.py` (orama) before push.
5. Multi-file code exploration: **code-review-graph MCP first** (`detect_changes_tool`, `get_review_context_tool`), then gbrain, then scoped Read — see `bin/orama-system/skills/code-review/SKILL.md` (no pre-commit hook; required workflow).

---

## Queued — next session (fixes 4–6) — document only, not implemented

| # | Finding | Planned work |
|---|---------|--------------|
| **4** | MCP file/log read without path boundary | Path allowlist under approved repo roots; reject absolute paths; redact logs |
| **5** | Remote LM Studio / Win coder URL policy | Central URL parser; default loopback + RFC1918; `ALLOW_PUBLIC_MODEL_ENDPOINTS` opt-in |
| **6** | Least-privilege MCP profiles | Split read-only vs process-spawning tools; env-gated dangerous CLI workers |

Do **not** treat 4–6 as shipped until a follow-up PR updates this section.

---

## Related docs

- **79-commit audit + PR review (Appendix A):** [`OpenClaw/v1/2026-05-23-security-markdown.md`](../../OpenClaw/v1/2026-05-23-security-markdown.md) — implementation status table and finding cross-ref
- Remediation plan: [`docs/plans/2026-05-23-security-remediation-plan.md`](plans/2026-05-23-security-remediation-plan.md)
- v2 preconditions: [`docs/v2/23-security-preconditions.md`](v2/23-security-preconditions.md)
- Debug notes: [`docs/2026-05-24-security-review-debug-and-fix-notes.md`](2026-05-24-security-review-debug-and-fix-notes.md)
- Git identity: [`docs/wiki/08-git-hygiene-and-branching.md`](wiki/08-git-hygiene-and-branching.md)
