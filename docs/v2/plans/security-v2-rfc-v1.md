# OramaSys v2 — Formal Security RFC Publication Set (v1)

## 📌 Status
This document is an **addendum to the OramaSys v2 security roadmap**:

- `docs/v2/plans/security-v2-roadmap.md`
- `docs/v2/plans/security-v2-roadmap-part2.md`

It formalizes the **security guarantees, invariants, and enforcement architecture** into a versioned RFC specification.

---

# 🧠 RFC-001 — SSRF & Endpoint Security Contract

## 1. Scope

This RFC applies to:
- all URL parsing
- all external network requests
- all agent-to-agent communication
- all runtime model endpoint resolution

---

## 2. Core Security Model

### 2.1 Deterministic Boundary Principle

All external inputs MUST pass through:

```
endpoint_policy_core.validate_base_url()
```

No exceptions.

---

### 2.2 Forbidden Operations

The following are STRICTLY forbidden in production paths:

- raw `urlparse()` usage for security decisions
- implicit URL normalization via stdlib
- silent scheme stripping or rewriting
- uncontrolled host resolution

---

## 3. SSRF Threat Model

This RFC explicitly protects against:

- cloud metadata SSRF (169.254.169.254)
- RFC1918 private network bypass
- IPv6 mapped IPv4 bypass
- DNS rebinding attacks
- malformed URL parser exploits

---

## 4. Transport Identity Integrity

### Critical Invariant

> URL scheme is part of the security identity.

### Rules:

- `http` and `https` MUST be preserved end-to-end
- reconstruction layers MUST NOT hardcode schemes
- missing scheme only then defaults to safe fallback

Any deviation is a **critical violation**.

---

## 5. Authentication Security Contract

- tokens MUST be written using secure file primitives
- file permission MUST be `0600` at creation
- token material MUST NEVER appear in:
  - logs
  - HTML
  - telemetry

---

## 6. Rendering Security Contract

- all external inputs MUST be HTML escaped
- UI rendering MUST NOT trust upstream metadata

---

## 7. Cross-Repo Consistency Rule

This RFC applies equally to:
- Perpetua-Tools
- Orama-System

Any divergence is considered a **system integrity failure**.

---

## 8. CI Enforcement Binding

This RFC is enforced by:

- `.github/workflows/security-invariant-enforcer.yml`
- `.github/workflows/invariant-monitor-bot.yml` (see Part 2)

CI MUST fail if:
- SSRF bypass detected
- auth leakage detected
- scheme downgrade detected
- unsafe parsing detected

---

## 9. Formal Invariants

### Invariant A — SSRF Safety
No unsafe URL may reach execution layer.

### Invariant B — Auth Safety
No token may leak across system boundaries.

### Invariant C — Transport Integrity
No scheme mutation without explicit policy decision.

### Invariant D — Rendering Safety
No raw external input may reach UI layer.

---

## 10. Versioning

- RFC Version: v1.0
- System Version: OramaSys v2

---

## 🧩 Conclusion

This RFC defines the **authoritative security contract layer** for OramaSys.

It supersedes ad-hoc validation logic and establishes CI-enforced deterministic security behavior across all repositories.
