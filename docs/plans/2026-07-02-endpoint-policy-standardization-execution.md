# Endpoint-Policy Standardization — Verified Execution Record & Forward Plan

> **Date:** 2026-07-02 · **Produced by:** Win orchestrator (Fable 5) + Sonnet 5 audit fleet
> **Method:** oramasys 5-stage (Context Immersion → Visionary Architecture → Ruthless
> Refinement → Masterful Execution → Crystallize) — this doc is the Stage-5 artifact.
> **Supersedes-with-corrections:** the external "Cross-Repository Endpoint Policy
> Standardization" deliverable (2026-07-02, Fable-5 folder), whose two core deductions
> are refuted below with authenticated evidence.
> **Scope:** Perpetua-Tools (PT), orama-system, AlphaClaw `feature/MacOS-post-install`.

---

## 0. Corrections to the input plan (ground truth vs deduction)

The external deliverable marked its pillars "UNVERIFIED — deduced" (GitHub was
robots-gated to it). Authenticated `gh` + local-clone inspection refutes both:

| External deduction | Verified reality |
|---|---|
| CI exit-2 = cross-repo contract **drift**; fix = land a new shared `packages/endpoint-policy/` first | CI exit-2 = **missing file**. Merge `e47de40` (branch side `033737c`) deleted `scripts/security/check_endpoint_policy_contract.py` + `.agent/endpoint-policy-contract.yml` + the AGENTS.md section while the workflow survived conflict resolution. `python: can't open file` → exit 2. |
| PRs PT#177 / orama#127 "likely still open — hardened validator not yet merged" | **Both MERGED 2026-06-28.** The hardened validator is landed and parity-checked. |
| Shared-package extraction is the immediate fix | The repos already implement a different architecture: **byte/AST-parity mirror + CI peer contract** (same pattern as the attribution guards). See § 3 decision. |

**CI status:** restored files pushed (commit `dea6b20`, includes checkout@v5 /
setup-python@v6 bumps). "Endpoint Policy Peer Contract" is **green** on main, along
with Test Suite, CI-Test&Build, CodeQL.

## 1. Context Immersion — audited landed state (Sonnet fleet, 4 auditors)

**PT validator (`src/utils/model_endpoint_url.py`):** sound. All six regression
vectors **tested** (35/35 pass): bare-host `localhost:port`, `notaport`, `99999`,
`169.254.169.254`, IPv4-mapped-IPv6 bypass, skip-invalid list parsing.
IPv4-mapped-IPv6 unwrap present. FastAPI maps `ModelEndpointPolicyError` → HTTP 400.

**PT repo-wide invariant: VIOLATED (confirmed by live repro).** Unguarded
`urlparse().port/.hostname` outside the policy layer — `agent_launcher.py` (×5),
`fastapi_app.py` `_candidate_base_url`, `autoresearch_bridge.py`. Repro:
`OLLAMA_MAC_ENDPOINT=http://localhost:notaport` → bare `ValueError` at import.
→ **Fixed this session** (see § 4).

**orama validator (`src/utils/model_endpoint_url.py`):** logic-identical to PT,
61 tests + fuzz suite pass, parity checker PASS. **But** orama's
`src/utils/endpoint_policy_core.py` was an unrelated **fork** (ModelEndpointPolicyError/
host_allowed/validate_base_url) squatting the contract-designated path where PT owns
TransportIdentity semantics — the exact "second parser" AGENTS.md forbids, invisible
to the string-grep checker. Only consumer: its own fuzz test. → **Removed this
session**, fuzz test repointed at the mirror (see § 4).

**AlphaClaw (`feature/MacOS-post-install`):** two confirmed findings, delegated to
the Mac co-orchestrator lane (peer-drop `win-finding-alphaclaw-bind-and-macos-gap.md`):
- HIGH: own Express server binds `0.0.0.0` unconditionally
  (`lib/server/init/server-lifecycle.js:16`) — correct for Docker, wrong for the
  bare-metal macOS install the branch targets; gateway child is correctly loopback.
- MEDIUM: the branch contains **no implementation** — only a planning doc; promised
  `lib/platform.js` / `sanitizeOpenclawConfig` don't exist.
- OK: openclaw dep ≥ 2026.2.14 (CVE-2026-26324 IPv4-mapped-IPv6 patch included);
  I1 zero-config and I4 discovery order pass.

**CI sweep:** all other workflows green in both repos (12-run window). Deprecated
`actions/checkout@v4` / `setup-python@v5` remain in 1 orama + 4 PT workflow files
(deadline pressure starts Sept 2026) — low, batched for a later chore commit.

## 2. First-run invariants (I1–I5) — status

- **I1 zero-config:** PT/orama start with loopback defaults; AlphaClaw seeds `.env`.
  PASS (AlphaClaw's empty `SETUP_PASSWORD` + 0.0.0.0 bind noted as the exception).
- **I2 consistent defaults:** ports 8000/8001/8002/3000 documented; LAN discovery now
  honors `MAC_IP` env override (subnet move 192.168.254.x → 192.168.8.x healed this
  session; `scripts/discover.py` hardcodes `SUBNET` — gap, see § 5 roadmap).
- **I3 single source of truth:** satisfied via **mirror + parity gate**, not a shared
  package (decision below). Fork removal closes the one live violation.
- **I4 predictable discovery:** env → config → default holds in all three repos.
- **I5 fail-closed typed errors:** holds at the policy layer; PT call-site fixes
  extend it repo-wide; orama has no request-time endpoint intake route (module-import
  validation only — acceptable, documented).

## 3. Architecture decision — shared package vs mirror+parity

**Decision (Win orchestrator, 2026-07-02): keep mirror + parity-gate; defer the
`packages/endpoint-policy/` extraction to PyPI-publish time.**

Rationale: the external plan's sequencing ("land shared package first, CI goes green
once vectors agree") was designed to fix a CI failure that turned out to be a deleted
file, not drift. The landed mirror+parity architecture is working (green CI, AST
parity checker, 96 combined tests). Extracting a pip package now adds a
git-install dependency + licensing surface (Apache-2.0 subpackage in an AGPL host)
without removing any live risk. The extraction remains the right long-term move —
trigger it when either repo publishes to PyPI, using the external plan's package
design (kept as the reference spec).

Residual gap accepted + recorded: `verify_model_endpoint_policy_parity.py` covers only
three functions of `model_endpoint_url.py`; the contract checker greps strings.
Roadmap item R2 extends coverage.

## 4. Masterful Execution — landed this session

| # | Repo | Change | Verification |
|---|---|---|---|
| 1 | orama | Restore contract checker + yml + AGENTS.md section (merge-casualty) | checker exit 0; CI green on `dea6b20` (raced with Mac co-orchestrator — identical fix, theirs landed, mine dropped) |
| 2 | PT | Wrap all unguarded `urlparse` call sites (agent_launcher ×5, fastapi_app, autoresearch_bridge); extend `check_endpoint_policy_core.py` coverage; regression tests | endpoint suites + new `test_endpoint_env_hardening.py` + parity checker (Sonnet agent, results in LESSONS) |
| 3 | orama | Delete `endpoint_policy_core.py` fork; repoint fuzz test at mirror | `pytest -k "endpoint or policy"` + contract checker exit 0 |
| 4 | both | LAN re-discovery: `MAC_IP=192.168.8.51` (.env.local), coordination + findings peer-dropped to Mac | drops ok:true; portal 8002 healthy |

## 5. Roadmap (ranked)

- **R1 (Mac lane, dropped):** AlphaClaw bind-host fix + actually implement the macOS
  post-install deliverables the branch promises.
- **R2:** extend parity gate to whole-module AST hash of `model_endpoint_url.py` and
  add an import-graph check that no new `endpoint_policy_core` fork reappears.
- **R3:** structured error taxonomy (`ERR_INVALID_URL` / `ERR_SSRF_BLOCKED` / …) on
  `ModelEndpointPolicyError` in BOTH mirrors in one lockstep commit (contract requires
  simultaneous sync); migrate tests off message matching.
- **R4:** trailing-dot host canonicalization (`localhost.`) in both mirrors, lockstep.
- **R5:** actions v5/v6 bumps in the 5 remaining workflow files (before 2026-09).
- **R6:** `discover.py` subnet derivation from active adapters (drop hardcoded
  `SUBNET`), honoring env override first — the 2026-07-02 subnet move proved the gap.
- **R7 (publish-time):** extract `packages/endpoint-policy/` per the reference spec;
  reconcile orama license metadata (README Apache-2.0 vs sidebar MIT) beforehand.

## 6. Assumptions ledger

- Verified live: CI logs (authenticated), PR states, both validators' source + tests,
  fork consumer graph, AlphaClaw branch tree, LAN endpoints.
- Delegated trust: Sonnet auditor claims that were also adversarially verified or
  deterministically reproduced (all § 1 claims fall in this class).
- Not re-verified: openclaw@2026.3.13 internal SSRF guard behavior (upstream-patched
  per advisory; treated as vendor-fixed).
