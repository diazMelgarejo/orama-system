# PLAN: BigModel free-first Cline and PT qualification

<!-- wandb-inference-working-config -->
## W&B inference, not the Cline CLI

When this guidance mentions Cline and the call is W&B inference,
use the OpenAI client and Weave setup in
[../../bin/orama-system/skills/cline-openclaw-agent/references/wandb-inference-working-config.md](../../bin/orama-system/skills/cline-openclaw-agent/references/wandb-inference-working-config.md).
The Cline CLI returns `invalid model ID` for the model that client
completes. Do not send a CoreWeave team/project string. Shell-source
the operator W&B env file before reading `DEEPSEEK_V4_FLASH_WANDB`.

Date: 2026-11-13
Status: proposed implementation plan; no runtime changes activated by this patch.
Policy ID: bigmodel-free-first-2026-11-13-v1

## 1. Scope and immutable baselines

- Orama PR #493: c8d22852db685d10997d3ede793ad1bf05f0080a.
- PT PR #497: f38634a65188feec55737af95aab4d1a0f0baf55.
- These are operator-selected source snapshots, not independently certified releases.
- PR #493 is a queue-fencing documentation package. Preserve it unchanged.
- PR #497 is a discovery-endpoint lesson targeting a non-main memory branch.
- GitHub reported PT #497 mergeable_state=dirty during this review. This does not
  justify rebasing, resolving conflicts, force-pushing, or changing its base.
- Use separate local worktrees at the exact commits for application checks.
- The supplied patches add plans only. They do not enable fallback or spend money.
- Preserve historical lessons, probe outcomes, identity guards, endpoint contracts,
  hardware policy and operator-held queue decisions.

The pinned PR #493 tip contains:

- bin/orama-system/scripts/cline-provider-profiles/bigmodel-glm52.json.tmpl
- bin/orama-system/scripts/cline-provider-profiles/switch_cline_provider.py
- bin/orama-system/scripts/cline-provider-profiles/switch-cline-provider.sh

The inspected template selects glm-5.3-flash, timeout=30000, and
reasoning={"enabled":true}. It does not express this free-first policy.
The inspected Python switcher provides backups and atomic replacement, but is
not a request-level fallback engine.

In the consolidated series, this plan is applied after the three 2026-11-12
provider-research commits. Those commits rename the template to
bigmodel-glm53-flash.json.tmpl and extend the switcher and tests. They still
do not implement request-level free-first fallback, so this plan's
implementation steps remain open. Target the renamed template path.

## 2. Primary-source evidence and corrections

Sources were retrieved on 2026-11-13. Recheck them before promotion.

- Pricing: <https://docs.bigmodel.cn/cn/guide/start/pricing>
- Active catalog: <https://docs.bigmodel.cn/cn/guide/start/model-overview>
- Primary: <https://docs.bigmodel.cn/cn/guide/models/free/glm-4.7-flash>
- Legacy warning: <https://docs.bigmodel.cn/cn/guide/models/free/glm-z1-flash>
- GLM-4.5: <https://docs.bigmodel.cn/cn/guide/models/text/glm-4.5>
- API: <https://docs.bigmodel.cn/api-reference/模型-api/对话补全>
- Cline: <https://docs.cline.bot/cline-cli/overview>

The pricing page lists GLM-4.7-Flash input, output and cache-hit tokens as free.
Cache storage is only temporarily free; no guaranteed end date was established.
GLM-4-Flash-250414 has free input/output; cache hits are listed as unsupported.
GLM-4.5-Flash is called free in the active catalog and its family documentation;
its exact current cache/account terms require confirmation before promotion.
GLM-Z1-Flash retains a historical free pricing row, but its model page says the
Z1 series is offline. Exclude it; a price row does not establish availability.

GLM-5.3-Flash is paid: CNY 0.8 input, 2.8 output, 0.23 cache-hit per million
Tokens in the retrieved table. Cache storage is temporarily free, not inference.
No promotion automatically changes its classification to free.

Free model pricing does not prove unlimited concurrency, account eligibility,
no identity checks, no balance prerequisite, or availability for this key.
Do not assert 'no balance required' until an applicable official rule or a
controlled zero-balance account test establishes the narrower observation.

The supplied HTTP 429/code 1113 means insufficient balance or no usable package.
Record billing_or_entitlement_blocked, not ordinary traffic throttling.
It does not demonstrate generation, model-ID validation, or successful Cline use.
Passing queue tests does not change inference qualification.

## 3. Ordered model policy

This is a proposed text/coding preference order, not a benchmark claim that one
model is universally best. 'Exhaust all free' means all eligible, explicitly
allowlisted models for this task, not every model or every possible retry.

| Order | Exact model ID | State before qualification | Role |
|---|---|---|---|
| 1 | glm-4.7-flash | Source-supported; execution unqualified | Primary coding/text |
| 2 | glm-4.5-flash | Free catalog candidate; terms/tool tests pending | Secondary text |
| 3 | glm-4-flash-250414 | Free catalog candidate; capability tests pending | Basic text |
| 4 | glm-5.3-flash | Paid, account previously blocked | Paid last resort |

Never use glm-z1-flash, FlashX variants, glm-4.7, or generic aliases as a free
replacement. Similar names do not imply identical prices or deployments.

For vision, maintain an independent task-specific candidate list. Catalog-listed
free vision models include glm-4.6v-flash, glm-4.1v-thinking-flash and glm-4v-flash.
They are not automatically extra text/coding fallbacks. Qualify their tools,
context, pricing and modality first. Do not silently drop images to use text.

Eligible means active, price-verified, policy-compatible, within context/output
limits, and qualified for required tools/modality on the exact execution lane.
Do not silently truncate a 200K task for a smaller-context fallback.
A skipped ineligible candidate needs an evidence-backed reason, not an attempt.
Unknown terms or capability are not 'free exhausted': block or qualify first.

## 4. Paid boundary and budgets

Default mode is free_only. The complete free candidate list may end in a safe
failure. A reliability target never overrides the financial boundary.

After eligible free candidates have terminal recorded outcomes, return
free_candidates_exhausted. Only then may a separate paid gate be evaluated.

Paid execution requires all of:

1. Explicit per-run operator authorization for glm-5.3-flash and this endpoint.
2. Positive finite CNY budget, token/request limits and task deadline.
3. Complete free-candidate ledger or approved ineligibility exclusions.
4. Account entitlement resolved; unresolved 1113 blocks paid dispatch.
5. Fresh applicable rates and a conservative token-cost reservation.
6. No outstanding ambiguous request consuming an unaccounted reservation.

This user request approves planning; it does not supply a paid-run budget.
An environment variable alone must not substitute for the authorization record.
A preflight balance check does not prove entitlement or waive cost controls.

For concurrent paid requests, reserve budget atomically before each dispatch;
never let independent workers each spend the same remaining budget. Include
retries, cache storage and separately charged tools. Reject requests whose
worst-case reservation cannot be bounded. Client timeouts are not billing caps.
Provider usage caps or an accounting-enforcing gateway are needed for a strict
monetary ceiling; local token estimates are not a guarantee of actual charges.

Free-only mode disables provider-hosted web search, paid retrieval, knowledge
services and other billed extras. Local tools retain normal security approvals.
A free model does not make its tools, network egress or infrastructure free.

## 5. Exhaustion and error state machine

| Observation | Classification | Next action |
|---|---|---|
| Valid completion and required task checks pass | success | Stop chain |
| Verified model retired/unavailable | model_unavailable | Skip to next eligible free |
| Proven required capability absent | capability_ineligible | Record; next eligible free |
| Definitive non-executing model-specific rejection | rejected | Correct known schema or next free |
| Structured 1113 | billing_or_entitlement_blocked | No retry; halt task, no paid escalation |
| Authentication/permission error | credentials_blocked | Halt task |
| Ordinary documented rate limit | throttled | Bounded backoff only; no account cycling |
| Generic 400 | request_invalid_or_unknown | Inspect; do not infer effort incompatibility |
| Timeout/network interruption/5xx | outcome_unknown | Contain/reconcile; no blind replay |
| Partial stream, tool effects or unknown cancellation | recovery_required | Stop automatic fallback |
| Safety/policy rejection | safety_blocked | Do not evade by model switching |
| Deterministic failure on clean evaluation fixture | evaluation_failed | Next free only under approved policy |

A provider-wide failure must not generate a parade of pointless candidate calls.
A model-scoped rejection may advance within the free tier if definitively safe.
Do not automatically diagnose 1113 as model-scoped; validate account access first.
A quality failure after modifying files is not permission to rerun another agent
on the same dirty workspace. Use a reviewed checkpoint and confirmed containment.
Do not assume request_id is a provider idempotency guarantee.

Suggested initial retry budget: zero inference retries in qualification, then at
most one documented throttle retry per candidate with Retry-After and a total
run deadline. Implement backoff without consuming an unbounded task lifetime.
Free-exhaustion status must include each candidate's eligibility/outcome reason.
Unknown, recovery_required and transient outage are not clean exhaustion.

## 6. Model-specific reasoning policy

Keep requested intent medium -> high -> low where the API supports those levels.
Never emit max or xhigh. Do not test unsupported levels merely to discover an
already documented restriction.

The API says reasoning_effort applies only to GLM-5.2 and newer. For 5.3-Flash,
allowed levels are low/high/max; the documented default is max. Choose explicit
high, falling to explicit low only after reviewed compatibility evidence.
Do not send medium to 5.3-Flash; do not omit effort and inherit max.

GLM-4.7-Flash/4.5-Flash use their documented thinking.type controls, not invented
medium/high semantics. Omit unsupported reasoning_effort only for models where
that parameter is documented inapplicable. Record effective effort as
not_applicable/unobservable, never as 'verified medium'.

Qualification must verify how Cline 3.0.74 handles this distinction. If it injects
an unsupported effort, silently rewrites the route, or cannot satisfy policy,
mark that lane ineligible; direct API success does not repair the Cline lane.
For older models, permitting adaptive thinking is not proof of a bounded internal
reasoning intensity. If the operator requires such a guarantee, block them until
that policy requirement is resolved; never silently reinterpret it.

## 7. Implementation ownership and interfaces

Orama owns the Cline adapter, profiles and this Cline plan. PT owns its existing
orchestrator/runtime integration. Do not introduce a PT dependency on Orama.

Phase A establishes one versioned declarative policy artifact consumed by both
lanes. Proposed canonical home: PT config/bigmodel-free-first-policy.json.
Use only model/capability/pricing references and policy fields; no keys/prompts.
Before adopting a mirror, verify sibling-checkout availability and parity in CI.
Do not duplicate independent mutable candidate lists in skills or templates.

Proposed policy fields:

- policy_id, reviewed_at, source_urls, applicable_endpoint
- ordered_candidates, eligibility_requirements, retired_models
- lane_qualification, modality, context/output limits
- supported_reasoning_controls and explicit paid model effort
- pricing_status: free / paid / unknown (unknown is never zero)
- pricing_valid_until or explicit invalidation rule for reviewed promotion
- paid_fallback_default=false, retry limits, tool-billing exclusions

Proposed pure interfaces (not implemented by this plan):

- select_next_candidate(policy, task_requirements, evidence_ledger)
- classify_provider_result(http_status, structured_code, execution_state)
- authorize_paid_candidate(authorization, budget_state, candidate)
- build_provider_request(candidate, messages, capabilities)

Transport remains in each existing adapter, using canonical endpoint and
hardware-policy utilities. Do not create a second URL/SSRF parser.
Free/paid identity is pinned to exact scheme, host, API path and model ID.
Unrecognized endpoint overrides fail closed rather than inherit free status.

## 8. Orama changes to implement after plan approval

1. Inspect and preserve existing profile switching and backup tests.
2. Introduce a canonical bigmodel-free-first profile backed by qualified policy.
3. Keep bigmodel-glm52 as an additive compatibility alias with a clear warning;
   do not silently pretend the old nickname denotes a GLM-5.2 deployment.
4. Add a separately named paid glm-5.3-flash profile with explicit high effort.
5. Update switcher validation so general switching cannot bypass the financial
   gate or start inference discovery. Profile rendering remains offline.
6. Add a task runner or integrate the existing runner after tracing call sites.
   A profile file alone cannot implement fallback or enforce per-request spend.
7. Preserve outgoing config, unrelated providers, deduplicated backups and atomic
   writes. Reject empty/malformed secrets; safely encode JSON substitutions.
8. Run each worker with separate config, data and worktree. If shared state is
   unavoidable, lock the whole switch-run-restore lifecycle, not just writing.
9. Restore only state owned by this run; do not overwrite concurrent user edits.
10. Discover exact existing test paths before naming replacement suites. Add
    focused tests without assuming yesterday's local resolver was committed.

Never apply blind global text replacements to old lessons or evidence logs.
Append dated corrections identifying the superseded operational conclusion.
Do not rename coordinator personas, alter identity guards or queue semantics.

## 9. PT companion changes to implement

- Trace the current remote-provider adapter, CLI-worker bridge and budget paths.
- Implement or reuse the pure selector/classifier as the PT canonical policy API.
- Consume the same policy ID and qualification evidence from direct SDK workers.
- Carry financial mode, reservation and error state through dispatch/results.
- Stop fallback on uncertain tool execution and unresolved billing state.
- Keep local-first hardware policy and endpoint ownership unchanged.
- Append a new lesson for 1113/free-pricing/retirement distinctions. Preserve the
  episodic log's exact historical byte prefix and run its preservation gate.
- Do not infer control-plane addresses from discovery model-server endpoints.
- Do not alter PR #497's lesson or resolve its reported merge state in this work.

## 10. Separate qualification lanes

Keep independent evidence for:

1. Direct BigModel standard API, per free model.
2. Cline 3.0.74 using that standard API, per free model.
3. PT direct SDK using that standard API, per free model.
4. Cline -> ClinePass, only if this provider/model is actually offered there.
5. A ClinePass API gateway, only if officially supported and separately qualified.
6. Cline usage billing and BigModel Coding Plan, each a different billing route.
7. Paid standard-API glm-5.3-flash, subject to authorization/budget.

An unavailable subscription route is not eligible and is not silently substituted.
W&B and OpenRouter evidence is separate; neither proves BigModel qualification.
No subscription credit is treated as free standard-API usage.

For each required lane: generation -> stream -> harmless tool call -> tool-result
continuation -> isolated edit -> failing test/fix/passing test -> recovery test.
Validate finish reasons, tool arguments and final task assertions, not just HTTP
200. A 16-token thinking prompt can truncate without proving model failure.
Use adequate bounded output and task budgets, never provider maximums by default.

Use identical sanitized tasks, acceptance tests, permissions and task budgets in
comparisons. Capture effective model/provider, CLI version, request count,
wall time, usage and route-specific costs. Report compatibility and coding
quality separately. 'Best' becomes an empirical task-specific ranking only after
these tests, not an inference from the newest model name.

## 11. Cline 3.0.74 version gate

The current official CLI docs describe --config, --data-dir, --provider, --model,
--auto-approve, --thinking and --timeout. They are not proof of this local binary.
Capture cline --version, executable provenance and cline --help first.
Verify each flag and configuration key before building an invocation.
Do not upgrade the binary as a side effect of qualification.

Explicitly disable auto-approval in supervised tests. Isolate MCP configuration,
hooks, secrets and state. Never disable safety hooks to make a probe pass.
Inspect sanitized actual request settings, especially unsupported effort leakage.
Verify task timeout separately from provider timeout; do not assume 30000 units.
Streaming output and cancellation need their own recovery tests.

## 12. Mandatory offline regression matrix

- Candidate ordering; paid candidate cannot occur before free exhaustion.
- Retired Z1, FlashX and unknown-priced models never enter the free tier.
- Ineligible tools/modality/context produce explicit exclusions, not truncation.
- 1113 at HTTP 429 is billing blocked; genuine throttle is a different result.
- Billing/auth failures do not trigger paid execution or automatic recharge.
- Free-only can never reach paid transport, including retries and adapter defaults.
- Unknown endpoint, unknown price or stale promotion invalidates eligibility.
- No provider-hosted paid tools can be attached to free-only requests.
- Request builders never emit max/xhigh; 5.3 paid always sets high or approved low.
- Older models do not inherit unsupported reasoning_effort from shared CLI state.
- Timeout, partial stream, malformed 200 and incomplete tools cannot mark success.
- Tool side effects block blind fallback until containment/checkpoint review.
- Request IDs are not treated as idempotency without a documented guarantee.
- Budget reservations are atomic and include retry/concurrency exposure.
- Atomic switching, backup rotation, no-op, cleanup and concurrent-edit tests pass.
- Unknown cost is distinguishable from verified zero input/output token pricing.
- Sensitive fields and model reasoning text cannot appear in published evidence.
- Policy parity and historical-log preservation fail closed on missing evidence.

Run repository-selected existing suites plus new focused tests on POSIX and
Windows where locking/state behavior differs. Do not claim a full repository
pass from isolated policy unit tests.

## 13. Evidence, accounting and promotion freshness

Each record contains timestamp, lane, baseline commit/tree, policy hash, request
shape hash, model requested/returned, endpoint, thinking/effort transmitted,
authorization reference, reserved budget, HTTP/provider codes, tool state,
finish reason, tests, retries, timing, usage and cost confidence.
Keep documentary support, author-reported observations and independently run
results separate. Missing usage is unknown, not zero cost.
Do not publish API keys, full private prompts, reasoning content or raw headers.

Cache storage is temporarily free. Promotions need explicit eligible route,
claim/account conditions, validity window and expiry handling. An expired offer
never silently converts free-only traffic into paid traffic. If a storage charge
cannot be disabled or bounded, block free-only operation after the offer ends.
Regular switches do no live discovery. Qualification refresh is a separate
reviewed maintenance action. Check evidence freshness locally before dispatch;
stale pricing freezes promotion until refreshed without inference spending.

## 14. Delivery sequence and release gates

- [ ] Apply these additive plan patches in separate exact-tip local worktrees.
- [ ] Check repository instructions and content-based reanchor rules.
- [ ] Reconcile newer local changes by content; do not overwrite them blindly.
- [ ] Review official free availability, account constraints and policy freshness.
- [ ] Implement/test canonical selector and financial boundary in PT.
- [ ] Integrate policy-backed profiles and runner in Orama.
- [ ] Prove free-only isolation with mocked transports and network-disabled CI.
- [ ] Qualify approved free API/Cline/PT lanes with isolated, bounded probes.
- [ ] Keep paid route blocked until its separate budgeted authorization exists.
- [ ] Review full diffs, secrets, parity, historical records and rollback behavior.
- [ ] Obtain approval before pushes, PR creation, branch rewriting or merge.

Use new dedicated implementation branches anchored at the selected snapshots.
Do not expand the unrelated source PRs or claim they are already reviewed stable.
Rollback disables the new runner first and restores only owned configuration.
Do not automatically restore an unavailable or paid profile as a free default.
If no eligible free route remains, report a safe failure rather than spend.

## 15. Definition of done and current evidence boundary

Done requires actual runtime enforcement, passing relevant tests, reproducible
lane evidence, non-bypassable paid authorization, rollback verification and
review approval. This plan patch alone does not meet runtime completion.

For this deliverable: official pages and exact-tip source were inspected;
additive patch structure is checked in a scratch Git repository. No authenticated
inference calls, Cline execution, full-repository tests, paid requests, pushes,
PR edits, merges or production configuration changes were performed.
