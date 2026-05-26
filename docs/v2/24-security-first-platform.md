# 24 — Security-First Platform Requirements

> **Status:** Active design gate — security is a platform feature, not a
> retrofit checklist.  
> **Canonical policy:** [`../SECURITY-POLICY.md`](../SECURITY-POLICY.md)  
> **Immediate queue:** [`../SECURITY-POLICY.md#immediate-todo-list--validated-findings-from-scheduled-review-2026-05-26`](../SECURITY-POLICY.md#immediate-todo-list--validated-findings-from-scheduled-review-2026-05-26)

---

## 1. Prime directive

v2 must treat security controls as product primitives that ship with the kernel
and glass-window APIs:

- **Secure by default:** loopback bind, no public default passwords, no bearer
  token in HTML, no public model egress unless explicitly approved.
- **Server-side authorization:** every control-plane read/write is authorized on
  trusted server-side code, never by hidden UI state, client-side flags, or
  request-body "approved" booleans.
- **Capability-first execution:** subprocess workers, MCP tools, model probes,
  file access, and lifecycle controls are discrete capabilities with explicit
  grants, audit events, and tests.
- **Append-only evidence:** security findings, lessons, and audit trails are
  preserved and annotated, not overwritten.

This aligns the platform with NIST SSDF's guidance to integrate secure
development practices into the SDLC, reduce released vulnerabilities, mitigate
undetected vulnerability impact, and prevent recurrence through root-cause
fixes ([NIST SP 800-218 SSDF](https://www.nist.gov/publications/secure-software-development-framework-ssdf-version-11-recommendations-mitigating-risk)).

---

## 2. Public reference baseline

Use these as the common citation vocabulary for design reviews, PRs, and agent
plans:

| Source | Use in v2 |
|--------|-----------|
| [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/) | Technical verification requirements for authentication, access control, secrets, configuration, logging, and error handling. |
| [OWASP Top 10:2021](https://owasp.org/Top10/2021/) | Risk vocabulary for broken access control, insecure design, vulnerable components, SSRF, and logging/monitoring failures. |
| [NIST SSDF SP 800-218](https://www.nist.gov/publications/secure-software-development-framework-ssdf-version-11-recommendations-mitigating-risk) | SDLC integration, security requirements, threat/risk modeling, vulnerability response. |
| [CISA Secure by Design / Secure by Default](https://www.cisa.gov/sites/default/files/2023-04/principles_approaches_for_security-by-design-default_508_0.pdf) | Secure defaults, customer burden reduction, and elimination of universal default passwords. |
| [CISA default-password alert](https://www.cisa.gov/resources-tools/resources/secure-design-alert-how-manufacturers-can-protect-customers-eliminating-default-passwords) | Instance-unique or operator-set credentials during installation instead of copied static tokens. |
| [OpenSSF Scorecard](https://openssf.org/projects/scorecard/) | OSS repository hygiene: branch protection, CI tests, token permissions, dependency updates, SAST, security policy. |
| [OpenSSF Security Insights](https://security-insights.openssf.org/) | Machine-processable public security posture metadata beyond `SECURITY.md` and SBOMs. |
| [SLSA](https://slsa.dev/) | Build integrity, provenance, dependency transparency, and artifact verification. |
| [GitHub Actions security hardening](https://github.com/github/docs/blob/main/content/actions/reference/security/secure-use.md) | Least-privilege workflow tokens, careful privileged triggers, and untrusted-input handling in CI. |

---

## 3. Security features baked into the v2 platform

| Platform feature | Requirement | Why |
|------------------|-------------|-----|
| Control-plane auth | Auth middleware is a kernel-adjacent primitive shared by `oramasys` and PT adapters; every non-health route declares `public`, `read`, `mutate`, `lifecycle`, or `dangerous-worker` capability. | OWASP Top 10 A01 says access control failures cause unauthorized data disclosure/modification and business-function abuse; ASVS V4 requires server-side access control and least privilege. |
| Browser operator session | The browser never receives the raw control-plane bearer. UI auth uses explicit login/bootstrap and session-scoped credentials; loopback peer IP alone is not identity. | Prevents local reverse proxies and XSS from converting UI load into API takeover. |
| Secure networking defaults | All services bind to loopback by default; LAN bind requires explicit flag, strong token, and startup warning/fail-closed checks. | CISA secure-by-default guidance says secure configuration should be the default baseline and not a customer burden. |
| Secret onboarding | No usable shared example tokens. First start generates an instance-unique token or requires operator-set credentials. Secrets never appear in source, build artifacts, argv, URLs, logs, or HTML. | CISA recommends eliminating universal default passwords; ASVS V13.3 requires secret-management solutions and no source/build-artifact secrets. |
| Model endpoint egress | Model probe and dispatch endpoints use a positive allowlist, host pinning/approval, RFC1918 defaults, no redirect following for discovery, and no control-plane auth headers on untrusted origins. | OWASP Top 10 A10 SSRF recommends positive allowlists and deny-by-default network controls for server-side fetches. |
| HTML/dashboard rendering | Remote probe values are data: render through escaping/text nodes only. No `innerHTML` for untrusted model names, URLs, routing labels, or activity strings. | OWASP ASVS provides requirements for protecting technical controls against XSS/injection classes. |
| MCP and file access | MCP profiles are readonly by default, path-boundary enforced, and merged config is tested after sync. Dangerous process tools require explicit elevated profile. | Least privilege and path boundary turn data-egress tools into intentional capabilities. |
| Subprocess workers | CLI agents and lifecycle controls are disabled by default or require `dangerous-worker` capability, authenticated actor ID, and pre-spawn audit event. | Reduces RCE blast radius and preserves human accountability before irreversible actions. |
| Append-only audit | `GossipBus`, security logs, and finding memory are append-only. Redaction happens before persistence; stale/remediated items are annotated, not deleted. | ASVS V16 calls for security-event logging and safe error handling; append-only records support incident response and regression prevention. |
| Supply chain | CI uses minimal token permissions, avoids privileged untrusted PR execution, records build provenance, and tracks security posture metadata. | OpenSSF Scorecard and GitHub hardening emphasize token permissions/branch protection; SLSA emphasizes provenance and artifact verification. |

---

## 4. Required design gates for every v2 module

Every module spec under `docs/v2/02-modules/` must answer these questions before
implementation starts:

1. **Who is the attacker?** Include local process, same-LAN client, malicious web
   page, compromised model endpoint, prompt-injected agent, and supply-chain
   actor where applicable.
2. **What input crosses the trust boundary?** Route body, path param, model
   endpoint JSON, file path, shell argv, workflow context, webhook payload, etc.
3. **Which capability is required?** `public`, `read`, `mutate`, `lifecycle`,
   `file-read`, `file-write`, `model-egress`, `dangerous-worker`, `admin`.
4. **What is the fail-closed behavior?** Missing auth, unknown endpoint, failed
   policy load, unsupported profile, stale config, and non-TTY override must all
   have explicit behavior.
5. **What is logged and redacted?** Security events must log actor, capability,
   decision, route/tool, and correlation ID while omitting secrets, prompts when
   not needed, raw transcripts, tokens, and chain-of-thought.
6. **What CI gate proves it?** Each security requirement needs a unit/integration
   test or lint gate, not only documentation.

---

## 5. Platform-level security backlog

These are first-class feature workstreams, not cleanup tickets:

| Stream | Deliverable | Blocks |
|--------|-------------|--------|
| S-AuthZ | Shared capability middleware + route manifest for `oramasys` and PT adapters. | Any new HTTP control-plane route. |
| S-Session | Browser-safe operator session bootstrap with no raw bearer in HTML. | Portal/dashboard promotion. |
| S-Network | One bind resolver used by bash, PowerShell, Python, and docs. | LAN bind on any platform. |
| S-Egress | Endpoint approval store and probe client that strips privileged headers. | Model discovery, LM Studio/Ollama probes, remote model dispatch. |
| S-Render | Safe renderer contract for all dashboard/status surfaces. | Any HTML/status fragment rendering. |
| S-MCP | Profile sync that prunes elevated managed servers in readonly mode and tests final merged config. | Cursor/OpenClaw MCP default profile. |
| S-Audit | Append-only security event schema with redaction and correlation IDs. | Worker dispatch, lifecycle controls, HITL, memory. |
| S-SupplyChain | Scorecard/SLSA-oriented CI gates: least-privilege tokens, protected branches, dependency inventory, provenance plan. | Public release artifacts. |

---

## 6. Release gate

No v2 milestone may be marked complete unless:

- `23-security-preconditions.md` acceptance criteria pass.
- Every new HTTP/MCP/subprocess/file/network feature has a completed section
  from §4.
- Security-related tests fail before the control exists and pass after it is
  implemented.
- Public docs include the relevant citation(s) from §2 when introducing a new
  security control or exception.
- Residual risk is tracked additively in `docs/SECURITY-POLICY.md` or the
  allowed flagged-vulnerability memory family.
