# Security Policy - orama-system + Perpetua-Tools

> **Canonical security posture** for the OpenClaw orchestration stack.
> **Last updated:** 2026-06-18
> **Source review:** `OpenClaw/v1/2026-05-23-security-markdown.md` in the private operator workspace.

---

## Scope

This policy covers **orama-system** (portal, ultrathink API, hygiene CI) and **Perpetua-Tools** (job control plane, workers, RAG memory, MCP packages). AlphaClaw MCP code lives in the Perpetua-Tools tree.

Root security entrypoints:

- orama-system: [`SECURITY.md`](SECURITY.md)
- Perpetua-Tools: [`SECURITY.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/SECURITY.md)

MAESTRO/OWASP GenAI v2 foundation:

- [`docs/v2/31-security-harness-excellence-plan.md`](docs/v2/31-security-harness-excellence-plan.md)
- [`docs/v2/32-agentic-security-controls.md`](docs/v2/32-agentic-security-controls.md)
- [`docs/v2/39-maestro-owasp-genai-reference.md`](docs/v2/39-maestro-owasp-genai-reference.md)

Local repo-owned threat IDs use the `PT-01`, `PT-02`, ... `PT-09` format.
Do not insert an extra `T` after the repo prefix or use similar local IDs that
visually collide with OWASP Agentic/MCP `T1`-style identifiers.

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

**Perpetua-Tools sync note (2026-05-25):** Fixes **3** and **3c** in the table above are implemented on **remote** `Perpetua-Tools` `main` (control-plane auth, memory redaction). A stale local `main` checkout may not include those commits yet — see the private operator-workspace 79-commit audit appendix before assuming PT routes are protected on disk.

**Operator checklist**

1. Set `ORAMA_CONTROL_PLANE_TOKEN` in `.env.local` (orama + PT share via `.state/control_plane_token` when PT starts).
2. For LAN exposure: set `PORTAL_BIND_LAN=1` / `PT_BIND_LAN=1` **and** keep bearer auth enforced (`ORAMA_INSECURE_DEV=0` or token set).
3. Run `bash scripts/git/install-local-hooks.sh` before commits in each repo clone.
4. Run `python3 scripts/review/repo_hygiene.py .` in both repos before push.
5. Multi-file code exploration: **code-review-graph MCP first** (`detect_changes_tool`, `get_review_context_tool`), then gbrain, then scoped Read — see `bin/orama-system/skills/code-review/SKILL.md` (no pre-commit hook; required workflow).

---

## Defense-in-Depth Operating Baseline — 2026-06-17

Security fixes must land as layered controls, not as single-point patches. For
each sensitive surface, require a preventive control, a runtime guard, a
verification gate, and an operator recovery path.

| Surface | Prevent | Runtime guard | Verify |
|---------|---------|---------------|--------|
| Credentials | `.env*` ignored except `.env.example`; no literals in tracked config | OS keychain or process env only; rotate any exposed key | `repo_hygiene.py`, provider secret scanning, billing/usage alerts |
| Control plane | Loopback default; LAN bind requires explicit opt-in | Strong bearer auth on mutating/read-sensitive routes | unauthenticated route tests + no bearer in HTML/logs |
| MCP and workers | readonly default profiles; dangerous workers opt-in only | path boundary roots + log redaction + no tracked bearer headers | profile tests verify final merged config, not only dry-run output |
| Model discovery | trusted host pinning before persistence | strip `Authorization` from LM Studio/Ollama/public probes | tests assert control-plane tokens never reach model endpoints |
| Memory and artifacts | redact before persistence; runtime dirs ignored | store only sanitized prompts/results; private tickets for raw artifacts | hygiene blocks databases, traces, screenshots, logs, and `/tasks/` |
| Dependencies | lockfiles are security surfaces; override vulnerable transitives at package-manager root | builds/tests must pass after lock refresh | Dependabot alerts close on the exact target lockfile |

Cross-repo changes must keep this file and
[`Perpetua-Tools/SECURITY.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/SECURITY.md)
in policy sync. If a rule applies to both repos, update both in the same branch
or explain why the repo-specific surface differs.

---

## Immediate TODO list — validated findings from scheduled review (2026-05-26)

These items are additive to the implemented fix table above. Some findings
overlap precise planned work in
[`docs/plans/2026-05-23-security-remediation-plan.md`](docs/plans/2026-05-23-security-remediation-plan.md);
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

## Security PR stacking and merge strategy (mandatory)

All agents working on security remediation must use a stacked PR strategy so
reviewers can merge fixes in risk order without losing dependency context.

### Required order of operations

1. **Look back first.** Before opening new work, list open PRs and remote
   branches that are not merged into `origin/main`; classify them against the
   immediate TODO list above.
2. **Existing security work wins.** If an existing branch precisely implements a
   planned security fix, revive/rebase that branch before creating a new branch
   for the same finding. Do not duplicate the patch line.
3. **Stack by priority.** Build the stack in the same order as this policy:
   planned duplicate workstreams first, then severity-ranked findings from
   Critical to High to Medium.
4. **Base rule.**
   - `PR1` must branch from current `origin/main`.
   - `PR2` must be rebased on top of `PR1`'s branch before opening.
   - `PR(N+1)` must be rebased on top of `PR(N)` before opening.
5. **One logical fix per PR.** Keep each PR scoped to one finding or one precise
   planned workstream (for example auth/bind, model egress, MCP profile
   pruning). Shared tests may live in the earliest PR that needs them.
6. **Ask before rewriting.** Rebasing or force-updating any existing remote
   branch is a history rewrite. AskUserQuestions first unless the user has
   explicitly authorized that branch rewrite in the current turn.
7. **No security record deletion.** If a PR supersedes another branch or marks a
   finding remediated, annotate the finding/plan additively. Do not delete prior
   finding records.

### Stacked PR base example

```text
origin/main
  └─ security/01-control-plane-auth-bind      → PR1 base: main
      └─ security/02-model-egress-probes      → PR2 base: security/01-control-plane-auth-bind
          └─ security/03-mcp-readonly-profile → PR3 base: security/02-model-egress-probes
```

### Current branch survey (2026-05-26)

No open PRs were present in `orama-system`, `Perpetua-Tools`, or `AlphaClaw`
when this directive was added. Remote branches not merged into `origin/main`
that appear security-relevant and should be considered before opening new work:

| Repo | Branch | Relevance to priority queue |
|------|--------|-----------------------------|
| `orama-system` | `origin/cursor/application-security-review-601e` | Current security policy/docs branch; merge before follow-up implementation branches so future agents inherit this strategy. |
| `orama-system` | `origin/cursor/security-pr-review-4254` | Prior security review report; inspect for already-planned findings before duplicating review/docs work. |
| `orama-system` | `origin/cursor/disable-cursor-coauthor-all-repos-6421` and `origin/cursor/allow-cursor-agent-identity-76c9` | Git attribution/agent identity guardrails; merge before attribution-policy follow-ups. |
| `orama-system` | `origin/feat/worktree-doctrine` and `origin/feat/multi-agent-ordinal-safety` | Worktree/parallel-agent safety; inspect before fixing worktree bootstrap and branch-stack workflows. |
| `Perpetua-Tools` | `origin/2026-05-25-security-fixes-1-3` | Existing security fixes for control-plane auth, redaction, and memory governance; highest priority to inspect/revive before duplicate PT auth/redaction work. |
| `Perpetua-Tools` | `origin/cursor/critical-correctness-bugs-08b6`, `origin/cursor/critical-correctness-bugs-bfdd`, `origin/cursor/critical-correctness-bugs-c247`, `origin/cursor/critical-correctness-bugs-9b3e` | Hardware affinity and mirror-routing correctness; inspect before model-egress and endpoint policy changes. |
| `Perpetua-Tools` | `origin/chore-env-precommit-hook` | Env assignment hygiene; inspect before adding secret/config hygiene gates. |
| `AlphaClaw` | `origin/cursor/application-security-review-601e` | Current agent append-only directives branch; merge before follow-up AlphaClaw policy work. |

If a GitHub PR creation tool is unavailable, agents must still push the
prepared branch and report the intended PR base/head chain explicitly.

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

## Credential and Artifact Hygiene

The enforceable contract, byte-aligned with Perpetua-Tools' `SECURITY.md`:

- **No secrets in source** — API keys, OAuth tokens, private keys, service-account
  files, and credentials are never committed. Commit `.env.example`; never `.env`.
  Enforced by `scripts/review/repo_hygiene.py` `SECRET_PATTERNS` (OpenAI `sk-`,
  Anthropic `sk-ant-`, GitHub `ghp_`/`github_pat_`, Google `AIza`, AWS `AKIA`,
  Telegram bot tokens, `BEGIN … PRIVATE KEY`) in pre-commit + CI.
- **Secure storage** — runtime secrets live in the OS keychain via the
  `openclaw-add-secret` skill, never in source, settings JSON, package metadata,
  logs, or UI captures. The gateway Bearer token is never propagated into tracked files.
- **Local environments** — secrets load from git-ignored `.env`; `.env.example` (empty
  values) is the only env file committed.
- **Artifact protection** — logs, databases, recordings, browser traces, screenshots,
  hook logs (`.claude/hooks/.logs/`), and UI-capture artifacts are git-ignored; redact
  before attaching to a private ticket.
- **No workstation paths** — tracked files use repo-relative references
  (`"$(git rev-parse --show-toplevel)"`, `~`, `$REPO_ROOT`); `repo_hygiene.py` blocks
  literal `/Users/<name>/…` so they cannot doxx the owner in a public repo.
- **Dependency integrity** — lockfiles and workspace package-manager settings are
  security policy surfaces. Vulnerable transitive dependencies must be fixed in
  the lockfile that Dependabot names, not only by adding unrelated direct deps.

## Defense-in-Depth Credential Policy

### Gemini / Google API Keys

Gemini keys are high-risk billing and data-access credentials. They must follow
the current [Gemini API key guidance](https://ai.google.dev/gemini-api/docs/api-key)
checked on 2026-06-17:

- Prefer Gemini **auth keys** or explicitly restricted keys. Unrestricted
  standard keys are not acceptable for new setup.
- Restrict keys to the Gemini API where applicable. Apply request-origin
  restrictions such as IP, website, or app restrictions when the deployment
  shape allows it.
- Read keys from environment variables, not source or tracked config. Supported
  local names are `GEMINI_API_KEY`, `GOOGLE_API_KEY`, and
  `GOOGLE_GENERATIVE_AI_API_KEY`. If two Gemini accounts are required, use a
  secondary variable such as `GEMINI_API_KEY_2`; do not invent typo aliases.
- Never expose Gemini keys in production browser or mobile client code. Use a
  backend proxy or server-side worker for production calls.
- Enable billing and usage alerts for every project that owns an active key.
- Treat the 2026 Gemini transition deadlines as operational risk: unrestricted
  standard keys are rejected starting 2026-06-19, and all standard-key usage
  should migrate to auth keys before September 2026.

### MCP, Control Plane, and Bearer Tokens

- Control-plane tokens, OmniRoute tokens, MCP bearer headers, and local gateway
  tokens are runtime secrets. They may live in git-ignored local config, OS
  keychain/editor secret storage, or process environment only.
- Do not copy bearer headers into tracked `mcp.json`, examples, screenshots,
  issue bodies, logs, or rendered portal output.
- Model-status and discovery probes must not forward the control-plane bearer
  to LM Studio, Ollama, discovered LAN endpoints, or public model endpoints.
- LAN binding remains loopback-first. Any LAN bind requires explicit operator
  opt-in and strong authenticated control-plane protection.

### Local Runtime Surfaces

- `.env`, `.env.local`, `.env.lmstudio`, `/tasks/`, `/runtime/`, `/state/`,
  `/sessions/`, logs, captures, traces, databases, and screenshots are runtime
  surfaces only and must remain ignored.
- `.env.example` documents variable names with empty or placeholder values only.
- Tracked docs and config must use repo-relative paths, `~`, or environment
  variables; never literal personal workstation paths.
- Hidden bidirectional Unicode controls and mojibake are blocked because they
  can hide malicious diffs or corrupt policy text.

### Enforcement Layers

1. `.gitignore` blocks local secret, runtime, and artifact paths before staging.
2. `scripts/review/repo_hygiene.py` scans tracked files for secret-shaped
   literals, private artifacts, workstation paths, hidden Unicode controls, and
   generated runtime files.
3. Local hooks installed by `scripts/git/install-local-hooks.sh` run the hygiene
   gate before commits.
4. CI must run the same hygiene gate so bypassing local hooks cannot land
   secrets.
5. GitHub secret scanning and provider-side leak detection are backstops, not
   primary controls.

## Leak Response

If a secret is committed or exposed:

1. Generate and deploy a replacement credential first.
2. Verify the replacement works.
3. Disable or revoke the exposed credential; do not wait for history cleanup.
4. Audit provider usage, billing, and logs for unauthorized access.
5. Remove the secret from active code and config.
6. If a private file was tracked, remove it from the index with
   `git rm --cached`.
7. Treat Git history cleanup as secondary and coordinate it explicitly because
   history rewrites disrupt other agents and clones.

---

## Related docs

- **79-commit audit + PR review (Appendix A):** `OpenClaw/v1/2026-05-23-security-markdown.md` in the private operator workspace — implementation status table and finding cross-ref
- Remediation plan: [`docs/plans/2026-05-23-security-remediation-plan.md`](docs/plans/2026-05-23-security-remediation-plan.md)
- v2 preconditions: [`docs/v2/23-security-preconditions.md`](docs/v2/23-security-preconditions.md)
- Debug notes: [`docs/2026-05-24-security-review-debug-and-fix-notes.md`](docs/2026-05-24-security-review-debug-and-fix-notes.md)
- Git identity: [`docs/wiki/08-git-hygiene-and-branching.md`](docs/wiki/08-git-hygiene-and-branching.md)
