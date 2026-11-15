# 09. Policy Fail-Closed + Consolidated Verification Checklist

**TL;DR:** Hardware-bound routing must fail closed when policy authority is unavailable, and every priority block must end with a concrete checklist run.

---

## Root Cause

- Policy and env-key drift (`PERPETUATOOLSROOT`, `PERPETUA_TOOLS_ROOT`, `PERPETUA_TOOLS_PATH`) allowed ambiguous behavior across API and discovery paths.
- Verification commands in docs drifted from real scripts, so “green” claims were hard to trust.
- Large migrations landed without a single end-to-end checklist report, which hid partial compliance.

## Fix

1. Enforced explicit-provider fail-closed behavior (`POLICY_UNAVAILABLE`) when resolver is in degraded no-policy mode.
2. Standardized root resolution helpers and legacy fallback order in runtime/discovery paths.
3. Added/updated checklist tools and commands so documented verification commands are executable in-repo.
4. Required post-priority-block checklist execution and status reporting (pass/warn/fail).

## Verification

Run after each priority block:

```bash
python -m pytest tests/test_api_server.py scripts/tests/test_discover.py -q --tb=short
python3 scripts/hardware_policy_cli.py --check-openclaw
grep -rn "discover.py --all" docs/ || true
grep -rn "hardware_policy_cli.py validate" docs/ || true
```

Optional full suite:

```bash
python -m pytest tests/ -q
```

## Rules

1. For hardware-bound model/provider hints, policy-unavailable states must return `POLICY_UNAVAILABLE` (never silently continue).
2. Canonical env key is `PERPETUATOOLSROOT`/`PERPETUA_TOOLS_ROOT`; legacy key is compatibility-only.
3. Every major priority block must include a checklist run and explicit status summary.
4. If checklist items remain warnings (e.g., historical docs), call them out explicitly and do not label fully green.

## Related

- [Session log entry](../LESSONS.md#2026-05-04--codex--priority-execution-p1-p6-checklist-and-fail-closed-hardening)
- [Wiki index](README.md)


---

## Addendum (2026-11-15) - One validated snapshot: unavailable security config is not permission

A qualification-gate loader caught `OSError`/`ValueError` and returned `None`, which the gate
treated as "no catalog configured" and ALLOWED dispatch. A reviewer reproduced all four catalog
candidates being dispatched after a loader failure raised *between* route assembly and the gate:
production read the policy twice, and the second read failing silently disabled the gate.

**Rules (fail-secure):**

1. Load ONE validated snapshot before route assembly. On failure, refuse dispatch (503) -
   unavailable security configuration must not become permission (OWASP fail-secure principle).
2. Hand the SAME snapshot object to every consumer (route assembly and the gate) through an
   additive keyword-only parameter. Two independent reads of one security document are a TOCTOU
   window even when both usually succeed. Legacy callers that pass no snapshot keep their
   previous behavior; the enforcement boundary lives in the handler.
3. Gate-denied candidates skip their availability probe entirely - record the blocked entry and
   continue. A denied candidate reaching its backend probe is a real leak (a denied Ollama-backed
   cloud candidate hit a one-shot cloud probe this way).
4. Request schemas must not carry gate-exemption fields (`dispatch_mode`): an internal exemption
   must not be caller-reachable.
5. Registry reachability flags (live-derived `online`) are probe inputs, not qualification
   verdicts - only the catalog row's explicit `online` flag is a dispatch kill switch, or the
   probe-failure fallback is silently defeated.

Regression shape: failing-first tests for each loader-failure mode (FileNotFoundError,
ValueError), a probe-spy asserting zero calls for denied candidates, and an object-identity
assertion that route assembly received the handler's snapshot with a zero registry re-read count.
PT #514 round 2; 137 passed / 0 failed across the eight affected suites.
