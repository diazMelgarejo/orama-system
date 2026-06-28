# OramaSys v2 — Security Execution Plan (Part 2)

## 🔗 Crosslink to Core Roadmap

This document is the **execution companion (Part 2)** to:

👉 `docs/v2/plans/security-v2-roadmap.md`

It translates the v2 architecture + SSRF spec + CI contract into an **operational Cursor Agent execution bundle**.

---

# 🚨 PURPOSE

This file defines the **real-world implementation artifacts** required to:

- fully close CodeRabbit findings
- finalize PRs across orama-system + Perpetua-Tools
- enforce SSRF + auth + rendering invariants
- deploy CI-level security enforcement

---

# 🧠 ORAMASYS EXECUTION MODEL (FINAL PHASE)

## Core Principle

> Security is enforced at 3 layers:

1. Policy Layer (endpoint_policy_core)
2. Runtime Layer (portal + auth + workers)
3. CI Enforcement Layer (GitHub Actions contract tests)

---

# 📦 1. CURSOR AGENT EXECUTION PACKAGE

## Objective
Automate deterministic remediation of PR findings.

### Tasks

### 1. Auth Hardening
- Locate `control_plane_auth.py`
- Replace file writes with `_secure_write_token()`
- Enforce `0600` permissions at creation time

### 2. Portal Security
- Escape all external inputs in `portal_server.py`
- Apply `html.escape()` to:
  - event labels
  - messages
  - model metadata

### 3. SSRF Enforcement
- Ensure ALL URL validation goes through:
  ```
  endpoint_policy_core.validate_base_url()
  ```
- Block raw `urlparse()` usage outside policy module

### 4. Windows Script Validation
- Confirm `start.ps1` has NO `??` operator issue (false positive)
- Do not modify unless verified in full file context

### 5. SECURITY.md Update
- Mark CSRF/origin protections as:
  - MANDATORY
- Mark session-cookie UX as:
  - OPTIONAL

---

# ⚙️ 2. CI SECURITY GATE (GITHUB ACTIONS)

## Objective
Prevent regression of SSRF + auth + token leakage.

### Enforcement Rules

CI MUST FAIL if:

- `urlparse(` is detected in production code
- `ORAMA_CONTROL_PLANE_TOKEN` appears in rendered HTML
- unauthenticated control-plane routes exist
- SSRF bypass patterns are introduced

### Pipeline Stages

1. Install dependencies
2. Run pytest suite
3. Scan for insecure patterns
4. Validate SSRF invariants

### Pattern checks

```bash
! grep -R "urlparse(" src
! grep -R "ORAMA_CONTROL_PLANE_TOKEN" .
```

---

# 🩹 3. PATCH BUNDLE (APPLIED FIXES)

## Control Plane Auth Fix

```python
import os

def _secure_write_token(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(value)
```

---

## Portal XSS Fix

- Escape all external inputs:

```python
from html import escape

label = escape(label)
msg = escape(msg)
```

---

## SECURITY.md Fix

- CSRF/origin = MANDATORY
- session UX = OPTIONAL

---

# 🧪 4. VALIDATION CHECKLIST

## Must Pass Before Merge

- [ ] No unauthenticated spawn-agent routes
- [ ] No token leakage in HTML or logs
- [ ] SSRF policy enforced via endpoint_policy_core
- [ ] All portal inputs escaped
- [ ] control_plane_auth uses secure file creation
- [ ] Windows script false positive confirmed

---

# 🧱 5. CROSS-REPO CONSISTENCY RULE

Applies to:
- orama-system
- Perpetua-Tools

### Invariants

- Same SSRF rules
- Same auth model
- Same endpoint validation
- No divergence allowed in security logic

---

# 🚀 6. EXECUTION ORDER (IMPORTANT)

1. Apply auth hardening
2. Apply portal sanitization
3. Validate SSRF policy usage
4. Run CI security gate
5. Merge stacked PRs

---

# 🧠 FINAL SYSTEM STATE

> All external inputs must pass deterministic policy validation before execution, storage, or rendering.

---

# 🔗 BACKLINK

See main architecture:
👉 `docs/v2/plans/security-v2-roadmap.md`
