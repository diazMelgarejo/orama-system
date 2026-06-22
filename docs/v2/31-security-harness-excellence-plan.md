# Security Harness Excellence Plan

> **Status:** v2 strategy rewrite — single canonical entrypoint
> **Scope:** `orama-system` + Perpetua-Tools + AlphaClaw adapter boundary
> **Source preservation:** prior mixed plan is preserved verbatim at [`33-security-harness-source-material.md`](33-security-harness-source-material.md)
> **Control details:** [`32-agentic-security-controls.md`](32-agentic-security-controls.md)
> **Runtime/model details:** [`34-local-model-runtime-profile.md`](34-local-model-runtime-profile.md)

---

## Document map

This is the single canonical security-harness excellence plan. The follow-on documents are numbered in reading order:

- `31-security-harness-excellence-plan.md` — strategy, threat model, standards traceability, roadmap, and acceptance gates.
- [`32-agentic-security-controls.md`](32-agentic-security-controls.md) — implementation recommendations for auth, cookies, budgets, tools, sandboxing, memory, supply chain, observability, and system-level audits.
- [`33-security-harness-source-material.md`](33-security-harness-source-material.md) — verbatim preserved source material from the former mixed plan.
- [`34-local-model-runtime-profile.md`](34-local-model-runtime-profile.md) — local model/Ollama/MLX/Qwen runtime guidance with caveats.

---

## 0. Evidence and source reliability model

This plan deliberately separates **verified local evidence**, **proposed controls**, and **external reference material**. Standards mappings are traceability aids, not proof of security. A control is accepted only when it has an executable check, adversarial test, or operational artifact.

| Tier | Meaning | Examples | How to use |
|---|---|---|---|
| Tier 1 | Primary / canonical source | repo code, official project docs, OWASP, MITRE, CSA, vendor docs, CVE/NVD | May support requirements and acceptance criteria |
| Tier 2 | Reproducible technical evidence | benchmark scripts, published papers, CI logs, static-analysis artifacts | May support implementation choices if reproduction notes are present |
| Tier 3 | Commentary / scouting | blogs, forums, videos, social posts | May suggest ideas; must not be treated as authoritative |

External standards are living references. OWASP describes the Agentic Applications Top 10 as a peer-reviewed framework for autonomous and agentic AI systems, not as a pass/fail certification program: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/. MITRE describes ATLAS as a living knowledge base of adversary tactics and techniques against AI-enabled systems: https://atlas.mitre.org/.

---

## 1. Executive strategy

Make every agent action **attributable, bounded, replayable, and deny-by-default**. Treat all model output, memory, tool output, repository content, and imported skills as untrusted until a local policy grants authority.

The previous framing — “exceed gstack + GBrain + Hermes and pass agentic standards” — is useful as ambition but too broad as an engineering target. The measurable target is now:

> orama-system and Perpetua-Tools should enforce policy-mediated agent action across authentication, identity, tools, filesystem, network egress, memory, observability, and supply chain, with executable tests for each security gate.

---

## 2. Local system model

### 2.1 Assets

- Source repositories and worktrees
- User prompts, task briefs, and transcripts
- Control-plane bearer tokens and local runtime secrets
- MCP tools and subprocess-capable workers
- Local model endpoints, Ollama/LM Studio state, and model files
- RAG/vector memory and durable logs
- Perpetua-Tools adapter state and AlphaClaw bridge traffic

### 2.2 Principals

- Human operator
- orama orchestrator
- subagents and worker agents
- Perpetua-Tools adapter / gateway
- AlphaClaw MCP boundary
- local model server
- external model or API providers when explicitly configured

### 2.3 Trust boundaries

- Browser/API caller → orama control plane
- orama orchestrator → tool executor
- tool executor → filesystem and shell
- orama → Perpetua-Tools → AlphaClaw
- memory ingest → retrieval → model context
- model endpoint discovery → persisted endpoint config
- external docs/web/tool output → prompt context

### 2.4 Representative kill chain

1. Prompt injection enters through a web page, repo file, tool output, imported skill, or memory record.
2. The model treats untrusted text as operational instruction.
3. A tool call reads or writes outside intended scope.
4. Secrets or sensitive local state are exposed through model/tool output or egress.
5. Poisoned content is persisted in memory.
6. A later agent retrieves and trusts the poisoned memory.
7. Multiple subagents reinforce the same false assumption and finalize a wrong or unsafe result.

---

## 3. Threat model

| Threat | Description | Primary controls |
|---|---|---|
| T1 LAN control-plane exposure | Unauthenticated or weakly authenticated local-network caller reaches control endpoints | fail-closed auth, loopback-first bind, token/session bootstrap, route tests |
| T2 Prompt injection to tool misuse | Untrusted content causes unsafe command/file/network action | content scanner, datamarking, tool mediator, path/egress policy |
| T3 Memory poisoning | Untrusted or stale memory influences future decisions | memory provenance, ACLs, quarantine, retrieval logging |
| T4 Credential exposure | Tool/model process inherits broad secrets or forwards bearer tokens | env scrub, scoped credentials, egress mediator, no bearer to probes |
| T5 Unbounded consumption | Model/tool loops saturate local hardware | rate limits, token budgets, concurrency caps, deadlines |
| T6 Supply-chain compromise | Unpinned deps, unverified model files, compromised tool/plugin | lockfiles, audit, ML-BOM, hashes, signing where practical |
| T7 Inter-agent cascade | Local agent goals pass but system goal drifts | objective contract, trace replay, SWARM-style system audit |
> **Local IDs, not OWASP T-codes.** Every `PT-` ID below is **local to this
> table** — it is not part of the OWASP MAS Guide's T1–T47 namespace, despite
> the shared "T" letter and overlapping numbers 1–7. Prefixed `PT-` (2026-06-18)
> specifically to remove a prior textual collision with OWASP's IDs. See
> [`39-maestro-owasp-genai-reference.md`](39-maestro-owasp-genai-reference.md)
> §6 for the approximate cross-reference table mapping each `PT-01`-style local
> ID to its closest OWASP T-code and OWASP Agentic ASI Top 10 code.

| Threat (local ID, not an OWASP T-code) | Description | Primary controls |
|---|---|---|
| PT-01 LAN control-plane exposure | Unauthenticated or weakly authenticated local-network caller reaches control endpoints | fail-closed auth, loopback-first bind, token/session bootstrap, route tests |
| PT-02 Prompt injection to tool misuse | Untrusted content causes unsafe command/file/network action | content scanner, datamarking, tool mediator, path/egress policy |
| PT-03 Memory poisoning | Untrusted or stale memory influences future decisions | memory provenance, ACLs, quarantine, retrieval logging |
| PT-04 Credential exposure | Tool/model process inherits broad secrets or forwards bearer tokens | env scrub, scoped credentials, egress mediator, no bearer to probes |
| PT-05 Unbounded consumption | Model/tool loops saturate local hardware | rate limits, token budgets, concurrency caps, deadlines |
| PT-06 Supply-chain compromise | Unpinned deps, unverified model files, compromised tool/plugin | lockfiles, audit, ML-BOM, hashes, signing where practical |
| PT-07 Inter-agent cascade | Local agent goals pass but system goal drifts | objective contract, trace replay, SWARM-style system audit |

---

## 4. Standards traceability

Use standards to check coverage, not to claim compliance.

| Standard / framework | Primary use in this plan | Source |
|---|---|---|
| OWASP Top 10 for Agentic Applications 2026 | Agent risks: goal hijack, tool misuse, identity abuse, supply chain, code execution, memory poisoning, inter-agent communication, cascades, trust exploitation, rogue agents | https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ |
| OWASP Top 10 for LLM Applications 2025 | Model/app risks: prompt injection, sensitive information disclosure, supply chain, data/model poisoning, output handling, excessive agency, prompt leakage, vector weaknesses, misinformation, unbounded consumption | https://genai.owasp.org/llm-top-10/ |
| MITRE ATLAS | AI-specific adversary tactics, techniques, mitigations, and case studies; use as a living TTP vocabulary | https://atlas.mitre.org/ and https://github.com/mitre-atlas/atlas-data |
| CSA MAESTRO | Layered threat modeling for agentic AI systems; useful for cross-layer failure analysis | https://cloudsecurityalliance.org/blog/2025/02/06/agentic-ai-threat-modeling-framework-maestro |
| OWASP MAS Threat Modelling Guide v1.0 + AIVSS | T1–T47 threat-ID namespace, MCP-specific threats (T39–T47), quantitative 0–10 scoring rubric | See [`39-maestro-owasp-genai-reference.md`](39-maestro-owasp-genai-reference.md) §3, §7 |
| Morris II research | Evidence that self-replicating adversarial prompts can propagate through GenAI application workflows | https://arxiv.org/html/2403.02817v2 |

---

## 5. Benchmark references, reframed

### 5.1 gstack

gstack remains useful as a pattern source for layered prompt-injection defense, not as an orchestration-security benchmark. The project advertises local prompt-injection scanning, transcript review, canary-token leak detection, and combiner logic: https://github.com/garrytan/gstack and https://github.com/garrytan/gstack/blob/main/docs/designs/ML_PROMPT_INJECTION_KILLER.md.

**Adopt as ideas:** datamarking, hidden-content stripping, local classifier, transcript classifier, canary leak detection, ensemble combiner.

**Do not overclaim:** any classifier stack needs local calibration, bypass testing, false-positive budgets, and an explicit fallback path.

### 5.2 GBrain

GBrain is a useful memory-design comparison point because it centers persistent retrieval for agents and uses Postgres/pgvector patterns: https://github.com/garrytan/gbrain. Treat any product/benchmark claims as Tier 3 unless reproduced locally.

**Adopt as ideas:** repo-scoped memory trust, provenance, retrieval tools, and least-privilege access modes.

**Implementation recommendation:** orama memory controls must record source, trust tier, checksum, repo SHA, author/principal, task scope, expiry, and retrieval audit data.

### 5.3 Hermes

Hermes is useful for tool-call format and hosted-agent patterns. The Hermes 3 technical report describes JSON-schema tool definitions inside `<tools>`, calls in `<tool_call>`, responses in `<tool_response>`, and RAG citations using `<co>` tags: https://arxiv.org/pdf/2408.11857. Hermes Agent docs describe trajectory/tool schema mechanics: https://hermes-agent.nousresearch.com/docs/developer-guide/trajectory-format.

**Adopt as ideas:** explicit tool schemas, transcript/trajectory replay, session scoping, and progressive disclosure of tool schemas.

**Do not overclaim:** tool-call syntax is not a security boundary. Tool security belongs in the mediator and sandbox.

---

## 6. Roadmap

### Stage 0 — stop direct exposure and make evidence reproducible

1. Fail closed on control-plane auth by default.
2. Add regression tests for auth defaults, LAN bind, and unauthenticated route denial.
3. Add rate/token/concurrency budgets for model/tool fan-out endpoints.
4. Centralize and test cookie issuance, or remove cookie auth if not needed.
5. Generate dependency lockfiles and run dependency audits.
6. Preserve security-review commands, repo SHAs, and scan artifacts.

### Stage 1 — policy-mediated tools and identity

1. Introduce a tool-executor mediator.
2. Give each agent/run a scoped identity.
3. Enforce path, method, network, and secret-inheritance policy before tool execution.
4. Emit audit records for every tool call.

### Stage 2 — memory trust and prompt-injection controls

1. Add memory provenance and ACL schema.
2. Quarantine untrusted memory until scanned.
3. Apply datamarking and trust-boundary envelopes to tool/RAG outputs.
4. Add local scanner/canary tests with bypass and false-positive fixtures.

### Stage 3 — sandbox and egress isolation

1. Start with env scrub, path allowlists, read-only mounts where practical, and deny-by-default egress proxy.
2. Add macOS Seatbelt profiles for local dev if the tool launcher can enforce them reliably.
3. Treat Firecracker/Kata as production-grade target isolation, not as a prerequisite for earlier controls.

### Stage 4 — observability, replay, and system-level audit

1. Trace agent runs, tool calls, token usage, and egress attempts.
2. Add replay harnesses for agent action sequences.
3. Add SWARM-style objective-contract audit before high-risk or multi-agent finalization.

---

## 7. Acceptance gates

Every gate must include an exact command, expected result, artifact path, and rollback note. Initial gates:

| Gate | Command target | Expected result |
|---|---|---|
| AC-AUTH | `pytest tests/test_control_plane_auth.py` | existing auth tests run from the current test tree; extend this file or add a future `tests/security/` suite for no-token/LAN-bind cases |
| AC-RATE | future `pytest tests/security/test_rate_limits.py` | create this test suite with model/tool endpoint 429 or budget-error coverage before marking the gate complete |
| AC-COOKIE | future `pytest tests/security/test_control_plane_cookie.py` | create this test suite if cookie auth remains; verify centralized issuance and secure dev/prod attributes |
| AC-TOOLS | future `pytest tests/security/test_tool_mediator.py` | create this test suite when the mediator lands; denied paths/egress/tools must fail before subprocess launch |
| AC-MEM | future `pytest tests/security/test_memory_acl.py` | create this test suite when memory ACLs land; deny/read-only/read-write modes must be enforced at retrieval and write time |
| AC-SCAN | future `pytest tests/security/test_prompt_injection_scanner.py` | create this test suite when the scanner lands; canary leakage must block and benign fixtures must stay below the false-positive threshold |
| AC-TRACE | future `pytest tests/security/test_agent_trace.py` | create this test suite when tracing lands; every tool call must include principal/session/tool/resource/policy decision/timestamp |
| AC-SUPPLY | `pip-audit -r requirements.lock` plus CI lockfile install | dependency audit result is stored; CI installs from hashes/lockfile |

---

## 8. Security PR stacking recommendation

Do not ship docs, auth behavior changes, dependency locks, and sandboxing in one mega-PR. Recommended stack:

1. Docs split and evidence model.
2. Auth fail-closed and route tests.
3. Rate/token/concurrency budgets.
4. Cookie/session hardening.
5. Dependency lock/audit workflow.
6. Tool mediator skeleton.
7. Memory ACL/provenance.
8. Sandboxing/egress hardening.

Follow the repository security PR stacking policy in [`../../SECURITY.md`](../../SECURITY.md).

---

## 9. Quarterly standards refresh

At least quarterly:

1. Re-check OWASP Agentic Applications, OWASP LLM, MITRE ATLAS, and CSA MAESTRO sources.
2. Diff the standards traceability table.
3. Update acceptance gates if new threats affect local controls.
4. Record the refresh date and commands/source URLs in a docs PR.

---

## 10. One-line summary


---

## 7. Acceptance gates

Every gate must include an exact command, expected result, artifact path, and rollback note. Initial gates:

| Gate | Command target | Expected result | Artifact path | Rollback note |
|---|---|---|---|---|
| AC-AUTH | `pytest tests/test_control_plane_auth.py` | existing auth tests run from the current test tree; extend this file or add a future `tests/security/` suite for no-token/LAN-bind cases | CI test-run log (pytest output) | `git revert` the auth-posture commit; `ORAMA_INSECURE=1` is the explicit, narrow dev-only bypass — never a silent default |
| AC-RATE | future `pytest tests/security/test_rate_limits.py` | create this test suite with model/tool endpoint 429 or budget-error coverage before marking the gate complete | CI test-run log; once created, the new test file itself | remove/disable the limiter middleware registration |
| AC-COOKIE | future `pytest tests/security/test_control_plane_cookie.py` | create this test suite if cookie auth remains; verify centralized issuance and secure dev/prod attributes | CI test-run log; once created, the new test file itself | revert to bearer-only auth, dropping cookie issuance entirely |
| AC-TOOLS | future `pytest tests/security/test_tool_mediator.py` | create this test suite when the mediator lands; denied paths/egress/tools must fail before subprocess launch | CI test-run log; once created, the new test file itself | disable the mediator and fall back to the pre-mediator allow-list, if any |
| AC-MEM | future `pytest tests/security/test_memory_acl.py` | create this test suite when memory ACLs land; deny/read-only/read-write modes must be enforced at retrieval and write time | CI test-run log; once created, the new test file itself | revert to the pre-ACL memory-governance commit (classify_and_redact only) |
| AC-SCAN | future `pytest tests/security/test_prompt_injection_scanner.py` | create this test suite when the scanner lands; canary leakage must block and benign fixtures must stay below the false-positive threshold | CI test-run log; once created, the new test file itself | set the scanner's kill switch env var to disable, then revert the commit |
| AC-TRACE | future `pytest tests/security/test_agent_trace.py` | create this test suite when tracing lands; every tool call must include principal/session/tool/resource/policy decision/timestamp | CI test-run log; once created, the new test file itself | revert to pre-tracing logging; no data-loss risk since tracing is additive |
| AC-SUPPLY | `uv export --frozen --no-hashes -o requirements-export.txt && uvx pip-audit -r requirements-export.txt` plus CI lockfile install | dependency audit result is stored; CI installs from hashes/lockfile | `requirements-export.txt` (gitignored, regenerated each run) + audit output saved under `docs/security-artifacts/` | `uv lock --revert` or pin to the last-known-good `uv.lock` commit SHA |

---

## 8. Security PR stacking recommendation

Do not ship docs, auth behavior changes, dependency locks, and sandboxing in one mega-PR. Recommended stack:

1. Docs split and evidence model.
2. Auth fail-closed and route tests.
3. Rate/token/concurrency budgets.
4. Cookie/session hardening.
5. Dependency lock/audit workflow.
6. Tool mediator skeleton.
7. Memory ACL/provenance.
8. Sandboxing/egress hardening.

Follow the repository security PR stacking policy in [`../../SECURITY.md`](../../SECURITY.md).

---

## 9. Quarterly standards refresh

At least quarterly:

1. Re-check OWASP Agentic Applications, OWASP LLM, MITRE ATLAS, CSA MAESTRO, OWASP AIVSS, and the OWASP MAS Threat Modelling Guide sources — see [`39-maestro-owasp-genai-reference.md`](39-maestro-owasp-genai-reference.md) for AIVSS's pre-1.0 status and what to watch for in a v1.0 release.
2. Diff the standards traceability table.
3. Update acceptance gates if new threats affect local controls.
4. Record the refresh date and commands/source URLs in a docs PR.

---

## 10. One-line summary

Security excellence means policy-mediated agency: every agent action is attributable, bounded, replayable, and deny-by-default, with standards used for traceability and tests used for proof.
