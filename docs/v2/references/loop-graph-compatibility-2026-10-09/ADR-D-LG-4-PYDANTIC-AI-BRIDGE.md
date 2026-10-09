# D-LG-4 — Explicit Pydantic AI interoperability bridge

**Approved slice:** Phase 1 by operator instruction on 2026-10-09. This approves
bounded implementation, not framework runtime adoption, production egress or
deferred-tool approvals. Code lives in [Oramasys #23](https://github.com/oramasys/oramasys/pull/23).

## Decision

Implement an import-free graph_tool callable with an explicit typed input,
state mapper, output key, name and docstring. It invokes Core's single scheduler.
Refused or interrupted runs must raise rather than return stale prior output.
A caller registers this function in their own installed framework.

Implement as_node in one lazy-import allowlisted module. The caller supplies an
Agent, prompt/dependency mappers, output key and optional UsageLimits. It returns
a native async delta-producing node. Default production use refuses before any
framework import. Import errors propagate: broken installed dependencies are
not absence and do not enable duck-typed fallback.

Only explicit trusted offline-test calls may run exact TestModel/FunctionModel
instances with ALLOW_MODEL_REQUESTS=False. Recheck model selection and the
global gate before every run. A test harness also blocks socket connection
attempts. These checks are test constraints, not an adversarial sandbox:
caller-supplied tools and FunctionModel functions can execute arbitrary code.
The bridge is an untrusted effect, even if the model itself is offline.

| Surface | Implemented behavior | Remaining gate |
| --- | --- | --- |
| Text / structured output | Store local scratchpad value / JSON-mode model dump | Application data/privacy policy |
| Typed graph-as-tool | Real LCEL wrapping and Pydantic AI tool registration tested | Full public API compatibility matrix |
| Usage | Store request/input/output counters only | Policy-wide monotonic accounting |
| UsageLimitExceeded | Non-resumable structural interrupt, reason budget_exhausted; downstream nodes do not run; Core taxonomy unchanged | Global budget enforcement |
| DeferredToolRequests | Structural interrupt with sanitized pending count | Durable approval/resume contract |
| Streaming / iter | Unsupported in this slice | Sanitized projection and lifecycle tests |
| Production model/provider | Refused | Telos-backed transport plus durable admission/HITL |

Deferred requests are left pending, never auto-approved. No ToolDeferredResults
approval is synthesized; no automatic resume occurs. Do not export model
messages, tool arguments or output payloads as GraphEvent control metadata.

## Evidence and dependencies

Real offline oracles use LC 1.0.7, LG 1.0.3 and pydantic-ai-slim 1.0.18 in an
isolated, non-published environment. Its transitive packages are locked outside
pyproject metadata. An actual compatibility issue required opentelemetry-api
1.37.0 and griffe 1.14.0; the matching FastAPI 0.115.12 and OpenAI 1.109.1 are
oracle-only pins, not stack dependency restrictions.

Tests exercise text, structured output, tool calls, FunctionModel, usage limits,
deferred approval, changed-model refusal, schema-derived graph tool registration
and zero socket attempts. Framework-free tests enforce import boundaries.
These results establish only the named cells on Python 3.12; v0.x and other
version lines require separate locks and fixtures.

## Sources and rollback

Primary API facts: [testing](https://ai.pydantic.dev/testing/),
[deferred tools](https://ai.pydantic.dev/deferred-tools/),
[usage limits](https://ai.pydantic.dev/api/usage/).
Pinned source behavior, rather than latest documentation alone, is the oracle.

Rollback disables these explicitly called bridges; no automatic activation or
dependency exists. Preserve this approved slice and its evidence. Broader
pattern harvest (NodeContext, validator/retry wrappers, capture helpers) remains
backlog work and must not be advertised as shipped.
