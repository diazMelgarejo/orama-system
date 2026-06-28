# OramaSys v2 — Security Architecture & Execution Plan

## 0. Executive Summary

This document defines the **v2 security roadmap** for OramaSys built on top of Perpetua-Core.

It formalizes a shared security model across:
- orama-system
- Perpetua-Tools
- future agent/runtime services

Core principle:

> All external inputs that can influence execution (URLs, tokens, hosts, endpoints) must pass through a single deterministic security boundary before reaching application logic.

---

## 1. Shared Security Core (First-Class Package)

### Goal
Convert endpoint validation into a **versioned, reusable library**:

```
endpoint_policy_core (pip-installable package)
```

### Responsibilities

- Canonical URL parsing and normalization
- SSRF-safe host classification
  - loopback
  - RFC1918 private ranges
  - link-local filtering
  - IPv4-mapped IPv6 normalization
- Scheme enforcement (`http`, `https` only)
- Credential stripping detection
- Port parsing safety normalization
- Guaranteed exception contract:

> All invalid inputs MUST raise `ModelEndpointPolicyError`

### Design Constraints

- No raw `ValueError` or `TypeError` escapes allowed
- No stdlib parsing exceptions may propagate upward
- Deterministic behavior across Python versions

---

## 2. SSRF Defense Specification v2.0 (Formal Contract)

### Objective
Define a **strict security contract** for all network-bound inputs.

### Threat Model

Covers:
- SSRF via metadata endpoints (169.254.169.254)
- DNS rebinding attacks
- IPv6 mapped bypasses
- malformed URL injection
- port overflow / parsing exceptions

---

### v2.0 Rules

#### Rule 1 — Input Normalization Boundary
All inputs MUST pass through:

```
validate_base_url()
```

or equivalent policy function.

---

#### Rule 2 — Exception Contract
Only allowed exception type:

```
ModelEndpointPolicyError
```

All others are implementation bugs.

---

#### Rule 3 — Host Classification Hierarchy
Order of evaluation:

1. localhost / loopback
2. RFC1918 private networks
3. IPv4-mapped IPv6 normalization
4. link-local rejection
5. public allowlist opt-in

---

#### Rule 4 — Parser Safety
Any stdlib parsing failure (e.g. urlparse.port ValueError) MUST be caught and normalized.

---

#### Rule 5 — API Layer Responsibility
API layers (FastAPI / CLI / agents):

- MUST NOT parse URLs directly
- MUST only translate policy exceptions → transport errors (HTTP 400, CLI error)

---

## 3. Cross-Repo Architecture (Perpetua ↔ Orama)

### Problem
Duplicate validators created drift risk.

### Solution
Introduce shared dependency:

```
endpoint_policy_core
```

Used by:
- Perpetua-Tools
- orama-system
- future agent runtime

---

## 4. CodeRabbit Findings Classification (v2 Strategy)

### Category A — Parser leakage bugs
Example:
- malformed ports
- ValueError escape from stdlib

Fix: enforce boundary normalization

---

### Category B — SSRF bypass vectors
Example:
- 169.254.169.254 metadata IP
- IPv6 mapped IPv4 bypass

Fix: host classification hardening

---

### Category C — API boundary inconsistencies
Example:
- FastAPI returning 500 instead of 400

Fix: unify exception mapping at policy boundary

---

### Category D — Resource safety leaks
Example:
- unclosed HTTP clients

Fix: enforce lifecycle management in tests and runtime

---

## 5. Execution Plan (Phased Rollout)

### Phase 1 — Core Extraction
- Implement `endpoint_policy_core`
- Freeze validation logic as canonical

---

### Phase 2 — Repo Migration
- Replace duplicated validators
- Align Perpetua + Orama implementations

---

### Phase 3 — SSRF v2.0 Enforcement
- Apply contract rules across all ingress points
- Enforce exception taxonomy

---

### Phase 4 — Fuzz & Property Testing
- Randomized input validation tests
- Adversarial URL generation tests
- Parser resilience validation

---

### Phase 5 — CI Enforcement
- Fail CI on:
  - non-policy exceptions
  - SSRF regression cases
  - schema drift

---

## 6. Future v2 Enhancements

### 6.1 Published Package
Publish as:

```
pip install oramasys-endpoint-policy
```

or later unified under:

```
perpetua-security-core
```

---

### 6.2 SSRF Defense Spec v2.0 Formalization
- Convert this document into a versioned RFC
- Add compliance test suite
- Define backward compatibility guarantees

---

### 6.3 Security Boundary Contract Tests

A shared test suite enforcing:

- identical behavior across repos
- identical exception taxonomy
- identical SSRF handling rules

---

## 7. Final System Invariant

> No external input can reach execution layer without passing through a deterministic, testable, versioned security boundary.

---

## 8. Upgrade Path Options (v2 Expansion)

### Option 1 — SSRF v2 Specification RFC
Formalize this document into a **versioned security RFC**:
- versioned threat model
- compliance ruleset
- backward compatibility guarantees
- reference test vectors

Outcome:
A publishable security standard for OramaSys ecosystem.

---

### Option 2 — pip-installable Security Package
Scaffold and publish:

```
oramasys-endpoint-policy
```

Includes:
- `endpoint_policy_core`
- validation API
- fuzz harness
- versioned contract

Outcome:
Reusable dependency across all Orama/Perpetua systems.

---

### Option 3 — Cross-Repo Contract Test Harness
Introduce CI-enforced parity suite:

- identical validator behavior across repos
- shared SSRF regression tests
- enforced exception taxonomy alignment
- drift detection between versions

Outcome:
Prevents divergence across multi-repo agent ecosystem.

---

## Status

- v1: implemented (current PR work)
- v2: formalization + packaging + CI enforcement
- v3: distributed agent-wide enforcement (future)
