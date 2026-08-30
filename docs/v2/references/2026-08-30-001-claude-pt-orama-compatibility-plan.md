# Claude, Perpetua, and Oramasys Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish Telos-owned endpoint-policy parity, Phylax-owned runtime
checks, and a fail-closed Claude provider-integration adapter without creating
a generic contracts package.

**Architecture:** Telos publishes the semantic endpoint-policy v1 specification
and deterministic test vectors. PT keeps its generic untrusted-egress behavior;
Claude consumes the same contract through a TypeScript adapter while retaining
an explicit trusted-LAN provider mode. Phylax later publishes generic
runtime-check envelopes, and Claude adds an optional versioned, fail-closed
client only after those owner APIs exist.

**Tech Stack:** Markdown specifications, JSON conformance vectors, Python
pytest, TypeScript, native `node:test`, Node fetch/undici, existing PT
requests/httpx transport, GitHub Actions.

**Spec:** `docs/v2/references/claude-desktop-llm-perpetua-oramasys-compatibility-2026-08-30.md`

## Global Constraints

- Keep one canonical TypeScript implementation under
  `oramasys/Claude-Desktop-LLM/src/`.
- Keep Claude provider-native observability authoritative; JSONL is secondary,
  redacted evidence only; do not add OpenTelemetry/OTLP dependencies.
- Endpoint policy is Telos-owned; generic runtime checks are Phylax-owned.
- Preserve local loopback model access and explicitly approved trusted-LAN
  provider access; do not broaden PT generic egress.
- Use no generic `oramasys/contracts` package or repository.
- Fail closed on unknown versions, denied address classes, resolver failures,
  unexpected peers, malformed envelopes, and unavailable owner services.
- Every policy change requires deterministic fakes; required tests must not
  depend on live DNS, public networks, or a running model server.
- Do not delete legacy policy code until identical conformance evidence exists.

---

## Repository and File Map

- **Telos:** Create `spec/endpoint-policy/v1/endpoint-policy-v1.json` for
  canonical mode and decision vectors, and
  `spec/endpoint-policy/v1/README.md` for normative semantics and versioning.
- **Perpetua-Tools:** Modify `src/utils/ssrf_fetch_policy.py` and
  `src/utils/ssrf_pinned_adapter.py`; add
  `tests/test_ssrf_policy_vectors.py` for offline vector conformance.
- **Claude-Desktop-LLM:** Modify `src/policy/endpoint-policy.ts`; add
  `tests/endpoint-policy-vectors.test.ts` for TypeScript vectors.
- **Phylax:** Create `spec/runtime-check/v1/runtime-check-v1.json` and
  `README.md` for the owner-defined generic runtime-check envelope.
- **Claude-Desktop-LLM integration:** Add
  `src/integration/runtime-check-client.ts` and
  `tests/runtime-check-client.test.ts` for version, redaction, and failure
  behavior.

## Task 1: Publish the Telos Endpoint-Policy v1 Contract

**Repository and branch:** Create `oramasys/telos` from its default branch,
then create `2026-08-30-001-endpoint-policy-v1`.

**Files:**
- Create: `spec/endpoint-policy/v1/README.md`
- Create: `spec/endpoint-policy/v1/endpoint-policy-v1.json`

**Produces:** A language-neutral `EndpointPolicyVectorV1` corpus with
`mode`, `url`, `configured_hosts`, `remote_opt_in`, `dns_answers`,
`peer_address`, `redirects`, and expected `decision`.

- [ ] **Step 1: Write the normative mode table**

  Define exactly these modes: `untrusted_egress`, `provider_local`,
  `provider_trusted_lan`, and `provider_public_remote`. State that
  `untrusted_egress` never accepts private addresses, while
  `provider_trusted_lan` accepts only an explicit approved LAN range and
  exact host allowlist.

- [ ] **Step 2: Add the first failing cross-language vector corpus**

  Create vectors equivalent to:

  ```json
  {
    "id": "mixed-a-aaaa-answer-denied",
    "mode": "provider_public_remote",
    "url": "https://model.example/v1/models",
    "remote_opt_in": true,
    "configured_hosts": ["model.example"],
    "dns_answers": ["203.0.113.7", "10.0.0.8"],
    "peer_address": "203.0.113.7",
    "expected_decision": "dns_answer_denied"
  }
  ```

  Also include direct loopback, DNS-to-loopback, mapped IPv6 loopback, CGNAT,
  IMDS, link-local, trusted-LAN allowed, public remote allowed, peer mismatch,
  and redirect-to-denied vectors.

- [ ] **Step 3: Define the stable decision-code set**

  Require exactly:
  `url_invalid`, `scheme_disallowed`, `userinfo_present`,
  `hostname_missing`, `dns_resolution_failed`, `dns_answer_denied`,
  `host_not_allowlisted`, `remote_opt_in_required`,
  `remote_https_required`, `peer_address_denied`, `redirect_limit`, and
  `allowed`.

- [ ] **Step 4: Validate vector JSON and commit**

  Run: `python -m json.tool spec/endpoint-policy/v1/endpoint-policy-v1.json`

  Commit:

  ```bash
  git add spec/endpoint-policy/v1
  git commit -m "feat(telos): publish endpoint policy v1 vectors"
  ```

## Task 2: Make Perpetua-Tools Conform Without Broadening Egress

**Repository and branch:** `diazMelgarejo/Perpetua-Tools`, branch
`2026-08-30-001-telos-endpoint-vectors` from current `main`.

**Files:**
- Modify: `src/utils/ssrf_fetch_policy.py`
- Modify: `src/utils/ssrf_pinned_adapter.py`
- Create: `tests/test_ssrf_policy_vectors.py`

**Consumes:** Telos `endpoint-policy-v1.json`.

**Produces:** A PT vector runner proving that `untrusted_egress` retains the
existing deny-private behavior and validates every resolution result.

- [ ] **Step 1: Write failing vector tests**

  Add a parametrized pytest loader that injects DNS answers and peer address.
  Assert that a mixed public/private answer returns `dns_answer_denied`, not
  `allowed`.

  ```python
  @pytest.mark.parametrize("vector", load_vectors())
  def test_untrusted_egress_vectors(vector):
      assert evaluate_vector(vector).decision == vector["expected_decision"]
  ```

- [ ] **Step 2: Run the test before implementation**

  Run: `pytest tests/test_ssrf_policy_vectors.py -q`

  Expected: FAIL because the vector evaluator does not exist.

- [ ] **Step 3: Add the minimal PT evaluator seam**

  Keep `_is_denied_ip` as the address-class SSOT. Add a pure evaluator that
  accepts injected A/AAAA answers and calls `validate_resolved` for every
  answer. Do not add a LAN exception to `untrusted_egress`.

- [ ] **Step 4: Verify PT policy and transport**

  Run:

  ```bash
  pytest tests/test_ssrf_policy_vectors.py -q
  pytest -q tests -k "ssrf"
  ```

  Expected: all vector and existing SSRF tests pass.

- [ ] **Step 5: Commit**

  ```bash
  git add src/utils/ssrf_fetch_policy.py src/utils/ssrf_pinned_adapter.py \
    tests/test_ssrf_policy_vectors.py
  git commit -m "test(pt): enforce Telos endpoint policy v1 vectors"
  ```

## Task 3: Refactor Claude Endpoint Policy to the Same Contract

**Repository and branch:** `oramasys/Claude-Desktop-LLM`, branch
`2026-08-30-001-telos-provider-policy-v1` from current `main`.

**Files:**
- Modify: `src/config.ts`
- Modify: `src/policy/endpoint-policy.ts`
- Modify: `tests/endpoint-policy.test.ts`
- Create: `tests/endpoint-policy-vectors.test.ts`
- Modify: `README.md`

**Consumes:** Telos v1 mode definitions, decision codes, and vectors.

**Produces:** A TypeScript policy adapter that validates all DNS answers,
rechecks the connected peer, and distinguishes trusted-LAN provider routing
from generic egress.

- [ ] **Step 1: Write failing all-address and peer tests**

  Add deterministic resolver and connector fakes. The public-provider mode must
  reject a hostname with `["203.0.113.7", "10.0.0.8"]`, and trusted-LAN mode
  must reject a peer outside the approved resolved set.

  ```ts
  assert.equal(result.code, "dns_answer_denied");
  assert.equal(result.code, "peer_address_denied");
  ```

- [ ] **Step 2: Run targeted tests to prove the gap**

  Run:

  ```bash
  npm test -- tests/endpoint-policy.test.ts tests/endpoint-policy-vectors.test.ts
  ```

  Expected: FAIL because the current policy accepts one resolved address and
  does not expose peer verification.

- [ ] **Step 3: Implement policy modes and injected resolution**

  Replace single-address resolution with a resolver returning every unique
  A/AAAA answer. Normalize IPv4-mapped IPv6 before classification. Introduce a
  typed policy mode selected only by provider configuration; do not expose an
  arbitrary tool-call mode selector.

  Define the transport boundary as:

  ```ts
  type EndpointDecision = {
    code: EndpointDecisionCode;
    pinnedIp?: string;
    allowedPeers: readonly string[];
  };
  ```

- [ ] **Step 4: Recheck the actual connected peer**

  Extend the Undici connection boundary so the completed socket peer is compared
  against `allowedPeers` and the selected mode before request use. A mismatch
  must end the request with `peer_address_denied`.

- [ ] **Step 5: Run full Claude verification and commit**

  Run:

  ```bash
  npm run build
  npm test
  ```

  Commit:

  ```bash
  git add src/config.ts src/policy/endpoint-policy.ts tests README.md
  git commit -m "feat(claude): conform provider endpoints to Telos v1"
  ```

## Task 4: Publish Phylax Runtime-Check v1

**Repository and branch:** Create `oramasys/phylax` if it does not exist,
then create `2026-08-30-001-runtime-check-v1`.

**Files:**
- Create: `spec/runtime-check/v1/runtime-check-v1.json`
- Create: `README.md`
- Create: `tests/validate_runtime_check_vectors.py`

**Produces:** A generic, owner-defined runtime-check envelope. Endpoint-policy
rules are referenced by Telos policy version; they are not reimplemented.

- [ ] **Step 1: Write failing schema/vector tests**

  Require every result to contain `version`, `check_id`, `owner`,
  `status`, `reason_code`, and redacted `evidence_refs`. Reject unknown
  owners, versions, statuses, and raw prompt/model-response fields.

- [ ] **Step 2: Implement the minimal JSON validator**

  Permit only `pass`, `fail`, and `unavailable`. Require
  `unavailable` for an unreachable owner service; never infer `pass`.

- [ ] **Step 3: Verify and commit**

  Run: `pytest tests/validate_runtime_check_vectors.py -q`

  Commit:

  ```bash
  git add README.md spec/runtime-check/v1 tests/validate_runtime_check_vectors.py
  git commit -m "feat(phylax): publish runtime check v1 envelope"
  ```

## Task 5: Add a Fail-Closed Claude Owner-API Client

**Repository and branch:** Continue the Task 3 Claude branch after Telos and
Phylax v1 are published.

**Files:**
- Create: `src/integration/runtime-check-client.ts`
- Modify: `src/config.ts`
- Modify: `src/server/create-server.ts`
- Create: `tests/runtime-check-client.test.ts`
- Modify: `.env.example`
- Modify: `README.md`

**Consumes:** Phylax runtime-check v1 and owner-specific Telos version metadata.

**Produces:** An optional client that requests only allowed route/check facts.
Claude retains direct local provider operation when no client is configured.

- [ ] **Step 1: Write failure-first client tests**

  Cover unavailable service, unsupported version, malformed result, a denied
  decision, and a valid redacted pass. Assert each failure produces
  `unavailable` or deny behavior, never an implicit approval.

- [ ] **Step 2: Run the test before implementation**

  Run: `npm test -- tests/runtime-check-client.test.ts`

  Expected: FAIL because the client module is absent.

- [ ] **Step 3: Implement a narrow read-only interface**

  Use this exact TypeScript shape:

  ```ts
  export interface RuntimeCheckResultV1 {
    version: "v1";
    checkId: string;
    owner: "telos" | "phylax";
    status: "pass" | "fail" | "unavailable";
    reasonCode: string;
    evidenceRefs: string[];
  }
  ```

  Reject a response that contains raw prompt, response, authorization, endpoint
  secret, or unrecognized fields required for approval.

- [ ] **Step 4: Wire configuration without changing default behavior**

  The default remains no remote owner service and direct local provider
  operation. When configured, an unavailable or invalid owner service denies
  only the optional governed route; it does not silently select another remote
  provider.

- [ ] **Step 5: Verify and commit**

  Run:

  ```bash
  npm run build
  npm test
  ```

  Commit:

  ```bash
  git add src/integration src/config.ts src/server/create-server.ts tests \
    .env.example README.md
  git commit -m "feat(claude): add fail-closed owner runtime-check client"
  ```

## Task 6: Differential Release Gate and Documentation Closure

**Repositories and branches:** Use the Task 2 and Task 5 branches. Open
separate PRs; do not combine PT, Telos, Phylax, and Claude implementation into
one review.

**Files:**
- Modify: `docs/v2/references/claude-desktop-llm-perpetua-oramasys-compatibility-2026-08-30.md`
- Modify: each affected repository README with its owner-specific contract link.

**Consumes:** Passing PT and Claude vector suites plus Phylax client tests.

**Produces:** Recorded compatibility evidence and a safe retirement decision.

- [ ] **Step 1: Run the shared vector corpus in both languages**

  Run the PT vector command and the Claude vector command against the same
  committed Telos JSON SHA. Record the SHA and command output in each PR.

- [ ] **Step 2: Compare decisions by vector ID**

  Fail the gate if any identical mode/input tuple produces different
  `expected_decision` values. Treat a missing vector as a failure, not a
  skipped case.

- [ ] **Step 3: Run repository-wide verification**

  Run:

  ```bash
  # Perpetua-Tools
  pytest -q

  # Claude-Desktop-LLM
  npm run build
  npm test
  ```

- [ ] **Step 4: Update the architecture reference with exact evidence**

  Replace only the implementation-status section with PR URLs, immutable
  commit SHAs, vector-corpus SHA, and verification commands. Do not claim a
  live integration is complete until Task 5 is merged and exercised.

- [ ] **Step 5: Commit documentation evidence**

  ```bash
  git add docs/v2/references
  git commit -m "docs(v2): record endpoint-policy compatibility evidence"
  ```

## Merge Order

1. Merge Telos endpoint-policy v1 vectors.
2. Merge PT vector conformance without permission broadening.
3. Merge Claude TypeScript policy conformance.
4. Merge Phylax runtime-check v1 envelope.
5. Merge Claude's optional owner-API client.
6. Merge the differential-evidence documentation update.

No implementation PR may claim end-to-end compatibility before the preceding
owner contract is merged and its exact vector version is pinned.
