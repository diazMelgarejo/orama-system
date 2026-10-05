# Sites MCP specifications

## 1. Intent and assumptions

A smallest useful private prompt workspace from v1 repos. PT main 50192e07 and Orama main 65e12090
were audited on 2026-10-05. User supplied `MCP-oramasys.md` requires preview/tool review and
explicit publish approval. No new provider identity or accessible model gateway was supplied; this
rollout is explicitly deterministic contract preparation. Mastery v3 informs intent, structure,
authority and evidence gates; this endpoint does not impersonate its full network workflow.

## 2. Architecture and authority

PT contract/data operations → reviewed exact snapshot → Orama stateless adapter → Workers/D1 Site.
The UI and MCP use identical handlers. Orama does not own mutable task runtime state. The deployed
Sites gateway must authenticate requests and strip/replace caller-supplied
`oai-authenticated-user-id`; browser sign-in is `/signin-with-chatgpt?return_to=%2F`. Missing
identity fails before data access. Private owner-only Site and plugin audience remain separate
native settings. No public raw Worker endpoint is authorized.

## 3. Tool artifacts and schemas

All schemas are objects with `additionalProperties:false`. Prompt fields `original` (required),
`role`, `goal`, `constraints`, `output_format` are strings, maximum 32,768 UTF-8 bytes each. The
schema's `maxLength` is a character limit; PT applies the stricter UTF-8 byte check. Whole HTTP JSON
bodies are bounded to 131,072 bytes including encoding/escaping.

| Tool | Required | Optional | Effect |
| --- | --- | --- | --- |
| `oramasys_prepare_prompt` | original | four prompt fields | Read-only deterministic construction; no save |
| `prompts_save` | original, request_key | four prompt fields | Insert private record; identical retries return existing record |
| `prompts_list` | none | limit integer 1–50 (default 20), before string ≤128 | Read private active page |
| `prompts_get` | id | none | Read private active/archived record or null |
| `prompts_archive` | id | none | Set archived flag; never delete original |

IDs/request keys use safe ASCII `[A-Za-z0-9_-]{1,128}`. Owner is hosting identity, never an
argument. Every tool requires identity; discovery/initialize/ping contain no private records and can
be answered without it. Read tools mark readOnlyHint true; write tools false; all are
nondestructive, idempotent and closed-world. Annotations guide clients, never substitute
authorization. The UI requests archive confirmation; MCP client write confirmation is
client-governed and cannot be guaranteed by annotations.

Stateless JSON-RPC over HTTP POST supports initialize, ping, tools/list and tools/call;
notifications return 202 with no side effect. No server session, SSE stream, arbitrary execution,
batch requests, event subscription or task delegation. Supported initialization versions are
2024-11-05, 2025-03-26 and 2025-06-18. Nonmatching browser Origin is rejected; no Origin is
permitted for authenticated MCP clients. GET returns 405. Requests/responses are noncacheable JSON.
Only typed `PromptError` validation failures are shown; every other error is replaced by a fixed
retry message, never classified by message text.

## 4. Acceptance evidence

Node tests: discovery, required identity, pure prepare, notification behavior, envelope/size
rejection, foreign-origin rejection, SQLite save/retry/conflict/isolation/archive/get lifecycle,
sanitized errors. PT tests independently exercise SQL ownership, source preservation and paginated
traversal. Assembly checks exact source/schema parity. Site lint, TypeScript, migration generation
and Workers build are additional gates, not substitutes for deployed authentication and migration
checks.

## 5. Risk and residual behavior

Platform trust: identity headers are not independently verifiable inside this module. Public sharing
requires gateway verification, per-user quotas/rate limits, backup/erasure policy and authenticated
multiuser acceptance. Archive retains personal data. History is newest-first by `(created_at, id)`;
pagination is not snapshot isolation. Host D1 migration ledger applies each migration once; schema
bootstrapping is never run per request. No model inference means no model-cost claim or hallucinated
agent output. Handwritten MCP support is intentionally narrow: expand only against official
protocol/client compatibility tests.

## 6. Rollout and feasible extension

Review private UI/tool contract; approve publish; deploy privately; test two identities, tool
discovery, save/retry and D1 retrieval; install generated plugin; only then consider sharing. Model
inference can be added through an allowlisted HTTPS bridge carrying authenticated operations. It
cannot directly reach a user's localhost/LAN from Workers. PT must own operation identity, durable
pending/verified/failed/unknown states, idempotent reconcile, timeouts/cancellation and verification
gate. A production bridge needs reachable host, authorization, endpoint-policy checks, retry budget,
secrets, cost limits and fault-injection tests. Full network activation is not made feasible merely
by exposing stdio handlers. The stdio `oramasys_solve`/`oramasys_delegate` handlers now fail closed
(isError, status `unavailable`) without a configured stage executor and report `done` only after
real stage output. Do not publish local portal launch/stop/config endpoints through generic MCP
tools.
