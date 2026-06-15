# Agentic Security Controls

> **Status:** implementation guidance extracted from the former security-harness plan
> **Strategy:** [`31-security-harness-excellence-plan.md`](31-security-harness-excellence-plan.md)
> **Prior mixed source:** [`33-security-harness-source-material.md`](33-security-harness-source-material.md)

---

## 1. Authentication and LAN-bind hardening

### Problem

A local developer default can become a LAN exposure when the service binds beyond loopback. The safest default is fail-closed control-plane auth, with explicit and narrow insecure-dev affordances.

### Recommendation

- Enforce auth by default when no token is configured.
- Permit unauthenticated dev only when an explicit insecure-dev flag is set and the actual bind address is loopback.
- Refuse startup for insecure LAN bind unless a second, noisy override exists.
- Emit startup state: auth mode, bind host, token source, and insecure override state.
- Add route-level tests for every mutating or sensitive endpoint.

### Acceptance

`pytest tests/security/test_control_plane_auth.py` should prove no-token defaults are not open on LAN and unauthenticated sensitive routes return 401 when auth is enforced.

---

## 2. Cookie/session hardening

### Problem

Bearer-in-cookie support is convenient for a browser portal but widens CSRF/session-confusion risk if cookie issuance is scattered or attributes are not tested.

### Recommendation

- Centralize cookie issuance in one helper.
- Prefer Authorization headers for API clients.
- If cookies remain, test `HttpOnly`, `SameSite=Strict`, path scoping, expiry, and `Secure` behavior by environment.
- Add CSRF/origin checks for cookie-authenticated state-changing requests.

---

## 3. Rate, token, and concurrency budgets

### Problem

IP-only rate limits are insufficient for localhost/LAN agent systems. A single authenticated principal can still exhaust local model capacity with long prompts, tool loops, or parallel workers.

### Recommendation

Track and enforce budgets by authenticated principal/session/model/tool class:

- requests per minute
- input tokens per minute
- output tokens per minute
- concurrent jobs
- wall-clock deadline
- max tool calls per request
- max spawned subagents per task

Return structured 429/budget errors with the exhausted dimension.

---

## 4. Tool-executor mediator

### Problem

Tool-call syntax, model refusals, and prompt rules are not security boundaries. The boundary must sit between the model and filesystem/network/process capabilities.

### Recommendation

Before executing any tool, the mediator should evaluate:

- principal/session identity
- requested tool and method
- file path and repo/worktree scope
- network destination
- environment variables and credential scope
- risk class and human-approval requirement
- dry-run / write mode

Deny by default. Log every decision.

---

## 5. Sandboxing and egress ladder

Do not block early security wins on a microVM migration. Implement an isolation ladder:

| Level | Control | Purpose |
|---|---|---|
| L0 | explicit dangerous-tool prompts | baseline operator visibility |
| L1 | mediator path/egress/env policy | fastest high-value control |
| L2 | subprocess user separation and read-only mounts where practical | reduce accidental host mutation |
| L3 | macOS Seatbelt profiles for local dev | local M2 isolation path |
| L4 | container with restricted mounts and no default network | transitional isolation |
| L5 | Firecracker/Kata microVM | production/autonomous high-risk isolation |

Docker alone is not a complete isolation story because it shares the host kernel. MITRE ATT&CK documents container escape as a technique class under T1611: https://attack.mitre.org/techniques/T1611/.

---

## 6. Prompt-injection scanner

### References

gstack is a useful pattern source for layered defenses: local classifier, transcript check, canary leak detection, and combiner logic are described in its repo/design docs: https://github.com/garrytan/gstack and https://github.com/garrytan/gstack/blob/main/docs/designs/ML_PROMPT_INJECTION_KILLER.md. TestSavantAI describes prompt-injection classifier models on Hugging Face: https://huggingface.co/testsavantai/prompt-injection-defender-large-v0.

### Recommendation

- Apply datamarking/trust-boundary envelopes to all external tool/RAG/web output.
- Strip hidden/ARIA/invisible content before model exposure where applicable.
- Use local classification as a signal, not as a single point of failure.
- Add canary tokens to detect leakage into tool args, URLs, files, and responses.
- Require bypass fixtures and false-positive fixtures before blocking in production.

---

## 7. Memory ACL and provenance

### Problem

Memory risk is not only who can read/write. It is also why a fact became retrievable, what evidence supports it, and under what task scope it may influence an agent. OWASP Agentic Applications identifies memory and context poisoning as a top agentic risk: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/. OWASP LLM 2025 includes vector and embedding weaknesses as LLM08: https://genai.owasp.org/llm-top-10/.

### Required memory fields

- source URI/path
- repo SHA or external source timestamp
- author/principal
- ingestion principal/session
- trust tier
- checksum
- evidence links
- allowed task scopes
- expiry/staleness policy
- scanner result

### Retrieval policy

- Do not let the LLM decide memory access.
- Deny untrusted memory in security-sensitive tasks unless explicitly requested.
- Separate facts from suggestions.
- Require citations for memory-derived claims.
- Quarantine newly ingested memory until scanned.

---

## 8. Supply chain

### Recommendation

- Install from lockfiles in CI.
- Run dependency audit tooling against the lockfile.
- Verify model-file hashes before load where model files are managed locally.
- Generate SBOM/ML-BOM artifacts where practical. CycloneDX supports ML-BOM workstreams: https://cyclonedx.org/capabilities/mlbom/.
- Use SLSA/in-toto/cosign for release artifacts when there is a release pipeline to protect.

Do not make signing theater. Signing is useful only if verification is enforced before use.

---

## 9. Observability and replay

### Recommendation

- Emit spans/events for `invoke_agent`, `execute_tool`, model calls, retrievals, and egress attempts.
- Include token usage, finish reasons, principal, session, tool/resource, and policy decision.
- Store replayable traces for high-risk or multi-agent tasks.
- Alert on runaway token usage, egress anomalies, repeated tool denial, and cascade failures.

OpenTelemetry maintains GenAI semantic conventions for AI spans/attributes: https://opentelemetry.io/docs/specs/semconv/gen-ai/.

---

## 10. SWARM-style system objective audit

The durable insight from multi-agent risk literature is that individually plausible agents can still produce system-level drift. The local implementation should use an objective contract:

- original user goal
- non-goals
- forbidden actions
- allowed repos/files/tools
- required evidence
- human approval gates
- max tool calls/subagents
- rollback plan

Fail finalization if the network solves a different goal, relies on uncited evidence, has two or more agents reinforcing the same unverified assumption, touches files outside scope, or exceeds budget.
