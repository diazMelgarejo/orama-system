<!-- markdownlint-disable MD013 MD022 MD025 MD031 MD032 MD040 MD055 MD056 MD058 -->

# Plan: Dual-repo lockstep heal after orama PR 363 + PT PR 395

**Status:** Plan only — do not implement product code until explicit confirmation. This document
is the implementation contract for `/prp-implement`. It has no length cap: every pattern, line
range, test name, CI hole, and HTTP body an implementer would otherwise have to rediscover is
written here.
**Reuse:** orama-system PR 363 (`cursor/tiered-pipeline-runtime-fb76`). **PT PR 395:** MERGED
2026-09-19T12:17:47Z at `85e1c86cb65499672d2b36decc95a01fc4c53c04`. No open PT PR to reuse.
**Canonical validator blob:** `003ac54187e98f5c38fad5906f9ec1ef43ce6f9e` (sha256
`c7abdf8dc85d4cc33507d2cfd66d5697c1fc9e74b9316b38cec00c22ccb5cf6e`). **Method:** orama-system
5-stage + AFRP + CIDF + integrative-merge (synthesize, never amputate). **Review passes folded
in:** 2026-09-19 criticisms (CI wiring, one HTTP contract, peer-map window, proxy negative
control, depth matrix) plus this expansion pass (full call-site encyclopedia, exact patches, TDD
order, skip-hole inventory).
Canonical copies (GitHub, not a VM path):

```text
https://github.com/diazMelgarejo/orama-system/blob/cursor/tiered-pipeline-runtime-fb76/.claude/PRPs/plans/pr-363-395-lockstep-heal.plan.md
https://github.com/diazMelgarejo/orama-system/blob/cursor/tiered-pipeline-runtime-fb76/.claude/plans/pr-363-395-lockstep-heal.plan.md
```

```text
AFRP: Type C | Level Expert | Mode 2
ROLE: Systems architect for L2/L3 lockstep
GOAL: Heal both repos without losing either side; CI cannot skip the mirror
CONSTRAINTS: No product code until confirm; reuse open PR 363;
             PT follow-up is a later PR; comment-only on the PR 363 body
```

## Table of contents

1. How to use this document
2. Gate 0 — live state
3. Summary, user story, problem to solution
4. Metadata
5. Original intent (PR 363 / PR 395)
6. Drift timeline and why CI lied
7. Skip-hole inventory (four independent skip paths)
8. Harmonized design (5-stage) and alternatives rejected
9. Request lifecycle traces
10. Unified discovery table
11. External research (httpx)
12. Repo A tasks with exact patches
13. Repo B tasks with exact patches
14. Exhaustive depth matrix and worked examples
15. Test encyclopedia (names, fixtures, assertions)
16. Sequencing, commits, rollback
17. Validation commands and acceptance
18. Risks, non-goals, waiting confirmation
## How to use this document
Implementers must treat this file as the only spec. Do not re-litigate SSoT direction,
TLS-default, or opening a second PR 395. Do not search for 'the other copy of the plan' on a
cloud VM path. If a step would require grepping the repo, the answer is already in the discovery
table or the exact-patch sections. Product-code commits start only after the human says yes. PR
363 body stays comment-only; do not clobber the Summary.
Suggested `/prp-implement` order is TDD inside each task: write the failing test named in the
encyclopedia, then the minimal production change, then the validation command for that task. Do
not batch Tasks 1–4b into one untested commit. A reasonable commit split is listed under
Sequencing.
## Gate 0 — live state (re-fetched 2026-09-19)
Do not copy bytes from a moving PT target. Re-run this gate if PT `main` moved since `85e1c86c`.

| Fact | Evidence |
| --- | --- |
| PT PR 395 state | `MERGED` into `main` |
| Merge commit | `85e1c86c` |
| Orama PR 363 | `OPEN` on `cursor/tiered-pipeline-runtime-fb76` |
| Copy command | `git show 85e1c86c:src/utils/model_endpoint_url.py` from PT |
| PT main CI after merge | run `35442454247` job Git hygiene **FAILURE** |
| Failure text | `model-endpoint-policy-parity: FAIL — model_endpoint_url.py policy functions diverged` |
| AST delta (peer orama main vs local PT) | orama `main` still has `startswith('127.')`; PT has TLS kwarg + `_is_loopback_host` |
| Orama PR 363 markdownlint | was red on the short plan (MD013/MD040); wrap/fence is required on this file |

PT `main` CI is red because a **main push** checks out **orama `main`**, not the PR 363 branch.
The JSON peer map is keyed only by the old PT branch `fix/pt-pipeline-endpoint-tls-20260917`.
Dependabot PRs 364/365 do not use that key. Healing PR 363 then merging it is what greens PT
`main` parity, not a PT-first PR.
## Summary
Two lockstep PRs were trying to do one thing: orama stays stateless, PT owns guarded pipeline
execution, and a control-plane bearer must never ride cleartext to a non-loopback host —
including hostnames that only look like `127.*`.
PT PR 395 merged that policy into canonical `src/utils/model_endpoint_url.py`. Orama PR 363
already has the same policy functions on the PR branch and the pipeline bridge, but still has
these gaps:

1. `PTPipelineClient.run` builds `httpx.AsyncClient` with `follow_redirects=False`
   but omits `trust_env=False` (httpx default is trust env proxies).
2. The orama **mirror file on the PR** is not byte-identical to PT `main`
   (module docstring + `_host_allowed` docs + return-line backticks).
3. **orama `main`** is still the pre-TLS AST (`startswith("127.")`).
4. Depth parsing uses `int(raw)`, so `-1`, `+1`, and `1_0` are accepted.
5. Parity CI is wired but can skip, strips docstrings, omits `_is_loopback_host`,
   and never hashes the file.
PT leftover work cannot go onto PR 395. It needs a later PT PR, sequenced after orama PR 363
heals, with the peer-map retirement ready in the same sitting as the merge.
## User story
As a stack operator merging L2/L3 lockstep security work, I want one harmonized policy file, a
bearer client that cannot leak via proxy, fail-closed depth parsing with one HTTP contract, and
CI that cannot skip or AST-blind the mirror, so that the original PR 363 / PR 395 threat model
actually holds.
## Problem to solution
**Now:** Policy AST on PR 363 matches PT `main`; file SHAs do not. orama `main` AST does not
match, so PT `main` CI fails today. The parity script is invoked from both CI workflows, but it
strips docstrings, omits `_is_loopback_host`, never hashes the file, returns 0 when the sibling
is missing, and (on PT) treats a missing peer *file* as skip-success. The new orama client
hardened the target URL and disabled redirects, but not env proxies. Depth uses `int()`.
**Desired:** PT `main` bytes of `model_endpoint_url.py` live on orama PR 363. Mirror identity
lives outside that file. CI fails closed if the sibling is missing. Parity hashes the validator
file and AST-checks `_is_loopback_host`. Credentialed httpx uses `trust_env=False` with a
negative-control test. Both repos use the depth HTTP contract below. PT CI map stops pinning PR
363 after it merges.
## Metadata

- **Complexity:** Medium (small diffs, cross-repo sequencing, CI fail-closed)
- **Source PRD:** N/A (review of PR 363 after PT PR 395 merge)
- **PRD Phase:** N/A
- **Estimated files:** orama 8–10; PT 5–7 (later PR)
- **UX:** Internal change — no user-facing UX transformation
- **Confidence (single-pass, after confirm):** 8/10
## Original intent (re-read of PRs, comments, plans)
### Orama PR 363 was trying to ship
From `docs/plans/2026-05-29-01-cursor-PLAN.md` P1 and commit `746c1573`:

- Bridge `/oramasys` to PT’s **guarded** `/pipelines/{recipe}/run`, never
  `/orchestrate`.
- PT owns recipes, approvals, budgets, credentials.
- Orama stays stateless.
- Nested control-plane hops must carry pipeline refs; depth is bounded
  (`MAX_CONTROL_PLANE_DEPTH = 2`).
- Env aliases: `ORAMASYS_*` canonical, `ULTRATHINK_*` still documented.
CodeRabbit then forced two security heals (both resolved on the PR):

| Finding | Commit | Keep |
| --- | --- | --- |
| Depth ceiling not enforced when refs present | `a88673f7` + tests `ddde337c` | Keep both 409 messages (missing refs vs at-ceiling) |
| Bearer over LAN HTTP to RFC1918 | `4218729f` (opt-in TLS flag) | Keep flag **opt-in**; only pipeline client sets True |
| `127.attacker.example` treated as loopback | `bb3eb7da` (shared lockstep with PT) | Keep ipaddress-only loopback |
Strengths to keep: atomic pipeline refs, recipe alnum/`_`/`-`, `allow_public=False` even when
env allows public model endpoints, `follow_redirects=False`, replay-empty output allowed,
`_client_safe_detail`, integration markers + annotations on `/oramasys` tests,
`test_client_has_no_orchestrate_route_fallback`.
### PT PR 395 was trying to ship
Canonical side of CodeRabbit Finding 2, plus later heals on the same branch. The 'no second PR'
rule still applies to 395 (closed). It does not forbid a later PT PR for new follow-ups after
merge.

| Commit | Intent | Keep |
| --- | --- | --- |
| `44b67966` | `require_tls_for_non_loopback` default False | Keep opt-in; do not sweep LM Studio/Ollama HTTP |
| `9349998f` / `bb3eb7da` pair | Drop `startswith("127.")` | Keep |
| `718ba88` (coderabbitai) | `_host_allowed` docstring + return line backticks | Keep on canonical file |
| `7f8b834` | `orama_bridge._is_local_oramasys_endpoint` also sets TLS flag | Keep (PT-only) |
| `84cd350` | Bearer HTTPS `url_checker` on remote `ssrf_request`; packaged hosts.py 127 fix | Keep (PT-only) |
| `8cc3d170` | CI checkout of orama PR 363 peer, unquoted GITHUB_OUTPUT, no silent main fallback for **open** declared peers | Keep; add merged+404 exception only (Task B3) |
| Memory/lesson commits | Append-only records | Keep; do not rewrite |
## Drift: why, how, when
### Timeline

| When | What | Effect |
| --- | --- | --- |
| 2026-05-25 | Shared validator born (both repos) | Two copies from day one |
| 2026-06-13 | `startswith("127.")` shortcut (orama `6914aa3c`) | Hostname `127.attacker.example` classifies as loopback |
| 2026-08-12 | orama `fde9d460` “sync from PT” | Orama **added** the 7-line “keep it byte-identical” paragraph. PT never had that text. AST parity (which strips docstrings) stayed green. |
| 2026-09-17 13:08–13:35 UTC | Lockstep TLS + 127 fix on both PRs | Policy functions match **on the PR pair** |
| 2026-09-17 20:05 UTC | PT only: CodeRabbit autofix `718ba88` | `_host_allowed` docstring + return-line backticks. Never mirrored. |
| 2026-09-19 12:17 UTC | PT PR 395 merges | Canonical = PT `main` blob `003ac541…` |
| 2026-09-19 12:18 UTC | PT `main` CI `35442454247` | FAIL parity vs orama `main` |
| 2026-09-19 review | Orama PR 363 file SHA still `c418645…` class | Policy AST equal to PT; docs differ |
### What the AST checker actually compares
`scripts/review/verify_model_endpoint_policy_parity.py` walks the module AST, keeps only named
`FunctionDef` nodes, **deletes the first-body string Expr (function docstring)**, then
`ast.dump`s. It does not compare module docstring, `_is_loopback_host`, or file bytes. The unit
test `test_extract_policy_source_ignores_docstring_differences` encodes that blindness on
purpose. After this heal, keep that test for the AST helper, and add a new test that the
**file-hash** path fails on docstring-only drift for `model_endpoint_url.py`.
## Skip-hole inventory (four independent skip paths)
The 2026-09-19 review asked: confirm CI wiring; do not assume. Confirmed: both workflows invoke
the script. These four paths can still produce a green check without a real compare:

| ID | Where | Today | Heal |
| --- | --- | --- | --- |
| S1 | orama `.github/workflows/ci.yml` `docs-pointer-sync` | `if [ -d perpetua-tools-sibling ]; then … else echo skip` plus `continue-on-error: true` on both PT checkouts | Fail the job if the directory is missing after both attempts |
| S2 | PT `.github/workflows/ci.yml` `git-hygiene` | same `if [ -d orama-system ]` skip on **main push** if checkout failed (`continue-on-error: true` on main fallback) | Fail if missing on origin CI; do not skip |
| S3 | orama/PT `verify_*.py` `main()` | `peer_dir is None` prints skip and **returns 0** | Return 1 (or raise) when invoked from CI; local laptop without sibling may still skip only if an explicit env `PARITY_ALLOW_MISSING_SIBLING=1` is set — default fail closed in CI |
| S4 | PT `_check_one` | missing **peer file** prints skip and **returns True** (success) | For `model_endpoint_url.py`, missing peer file is FAIL. Keep skip-success only for `endpoint_policy_core.py` if a historical branch lacks it, or fail both — prefer fail both on `main` after PR 363 |
Task 4b is the highest-leverage orama change because S1+S3 together are exactly the trust model
that let docstring drift ship. S4 explains how a PT job can checkout orama and still skip the
validator if the path is wrong.
## What is better from each side

| Piece | Keep | Mode |
| --- | --- | --- |
| Policy functions + `_is_loopback_host` | Freeze by copying PT `main` file bytes to orama | 3 / 6 (PT is SSoT) |
| PT `_host_allowed` docstring + return line | Keep (canonical docs) | 3 |
| Orama “do not independently edit” intent | Keep outside the mirrored file | 4 synthesize |
| Orama extra module paragraph inside the file | Do not copy into PT | 5 architecturally-correct |
| Orama function-style vs PT class-style tests | Keep both styles; union missing behaviors | 2 union |
| `trust_env=False` | Copy from PT `agent_launcher._pinned_get` | 6 |
| Distinct 409 **messages** (no refs vs ceiling) | Keep orama’s split messages | 4 |
| Parse-failure HTTP status | One contract: 422 INVALID vs 409 LOOP | 6 api-correct |
| `>= MAX` (orama) vs `> MAX` (PT) | Keep both operators; they sit on opposite sides of increment | 5 |
| PT `orama_bridge` TLS + remote bearer HTTPS | Already on PT main | n/a |
| Parity script sibling env names | Keep directional | 6 |
## Harmonized design (5-stage)
### Stage 1 — Context
PT is runtime/state authority. Orama is a manually synced mirror of policy, not a second parser.
PR 363’s product work (pipeline bridge) is in scope to keep. The heal is vertical-slice contract
work: no persistence, contract = validator + depth header + bearer transport + CI that cannot
skip the mirror.
### Stage 2 — Architecture

```text
                    ┌─────────────────────────────────────┐
                    │ PT src/utils/model_endpoint_url.py  │  SSoT bytes
                    │ (including _is_loopback_host)       │
                    └──────────────┬──────────────────────┘
                                   │ copy on policy change
                    ┌──────────────▼──────────────────────┐
                    │ orama src/utils/model_endpoint_url.py│  identical blob
                    └──────────────┬──────────────────────┘
                                   │ used by
                    ┌──────────────▼──────────────────────┐
                    │ PTPipelineClient                    │
                    │  require_tls_for_non_loopback=True  │
                    │  follow_redirects=False             │
                    │  trust_env=False                    │  NEW
                    │  allow_public=False                 │
                    └─────────────────────────────────────┘

Hop:
  client → orama POST /oramasys
        → _control_plane_depth (parse)
        → refs gate / ceiling gate
        → PTPipelineClient.run (depth+1, bearer)
        → PT POST /pipelines/{recipe}/run
        → fastapi_app depth parse (receive side)
```
Identity / sync rules live in the parity script, CI fail-closed sibling checkout, and an
AGENTS.md transport bullet. NOT in the mirrored module docstring. CIDF: file write in-repo (rank
5 scripting). Decide() before inserting the identity paragraph anywhere: do not insert it into
the mirrored file.
### Stage 3 — Refinement (NOT building)

- Do not open a PT PR whose only job is to make `model_endpoint_url.py`
  match orama.
- Do not require TLS for LM Studio / Ollama / Win coder pool.
- Do not convert orama tests to PT class layout or vice versa.
- Do not rewrite PR 395 history or reopen it.
- Do not put workstation paths in the plan or code.
- Do not change the PR 363 body (comment-only).
- Do not fold Dependabot PRs 364/365 into this heal.
- Do not keep a permanent 409-vs-422 split for the same invalid depth input.
- Do not weaken `8cc3d170` for **open** declared peers.
### Alternatives considered and rejected

| Alternative | Why rejected |
| --- | --- |
| Copy orama’s identity paragraph into PT so hashes match without deleting it | Puts transport-layer identity into the payload; PT is SSoT and never wanted that paragraph |
| Full-file hash for `endpoint_policy_core.py` in the same change | That file is allowed AST-parity with possible comment drift; out of default scope |
| Make orama and PT both use `>=` (or both `>`) for ceiling | They sit on opposite sides of increment; unifying the operator would change hop capacity |
| Collapse both 409 messages into one | CodeRabbit Finding 1 required keeping refs-missing vs ceiling distinct |
| Keep orama 409 for parse failures to avoid changing PR 363 contract | Recreates the diagnosed anti-pattern (silent contract split) |
| Silent main fallback when declared peer 404s while PR still open | Exactly what `8cc3d170` forbids |
| `trust_env=False` test that only uses `MockTransport` | MockTransport bypasses mounts regardless of the flag |
### Stage 4 — Execution vehicles

| Order | Repo | Vehicle | Base |
| --- | --- | --- | --- |
| 1 | orama-system | Reuse PR 363 `cursor/tiered-pipeline-runtime-fb76` | `main` |
| 2 | Perpetua-Tools | New PR, branch ready before merging PR 363 | `main` (`85e1c86c`) |
### Stage 5 — Crystallize (after implement)
Append-only lesson: mirror identity must not live inside the mirrored blob; parity must include
`_is_loopback_host` and a full-file hash; CI must fail if the sibling checkout is missing; the
Python checker must not return 0 on missing sibling; HTTP contracts for the same invalid input
must not diverge on purpose.
## Request lifecycle traces
### Trace A — top-level /oramasys with pipeline refs (happy path)

```text
POST /oramasys  (no depth header)
  body: task_description, task_type, pipeline_trace_id, pipeline_idempotency_key
auth middleware (control_plane_auth_failure) → next
_control_plane_depth → 0
has_pipeline_refs True
inbound_depth >= 1? no → skip both 409 gates
PTPipelineClient.run(..., control_plane_depth=1)
  validate_model_endpoint_url(..., require_tls_for_non_loopback=True, allow_public=False)
  httpx.AsyncClient(follow_redirects=False, trust_env=False)  # after heal
  POST {base}/pipelines/{recipe}/run
    headers: Authorization, Idempotency-Key, X-Control-Plane-Depth: 1
PT fastapi: depth_raw "1" → int 1 → 1 > 2? no → proceed
200 OramasysResponse
```
### Trace B — nested depth=1 without refs (existing test)

```text
POST /oramasys  header X-Control-Plane-Depth: 1  (no pipeline refs)
_control_plane_depth → 1
inbound_depth >= 1 and not has_pipeline_refs
→ 409 CONTROL_PLANE_LOOP "Nested control-plane calls must use …"
FakePipelineClient.run never called
```
### Trace C — attacker `-1` with refs (the hole)

```text
TODAY:
  int("-1") → -1
  inbound_depth >= 1? no
  inbound_depth >= 2? no
  calls PTPipelineClient.run(control_plane_depth=0)
  nested attacker skipped both gates

AFTER HEAL:
  "-1" does not match ^[0-9]+$
  → 422 CONTROL_PLANE_DEPTH_INVALID
  run() never called
```
### Trace D — PT receive side `int('-1')`

```text
TODAY: int("-1") succeeds; -1 > 2 is False; pipeline proceeds.
AFTER HEAL: 422 CONTROL_PLANE_DEPTH_INVALID before recipe lookup.
```
## Unified discovery table

| Category | File:Lines | Pattern | Key snippet |
| --- | --- | --- | --- |
| Naming | `src/orama_system/pt_pipeline_client.py:19` | header constant | `CONTROL_PLANE_DEPTH_HEADER = "X-Control-Plane-Depth"` |
| Naming | `src/orama_system/api_server.py:44` | ceiling | `MAX_CONTROL_PLANE_DEPTH = 2` |
| Error | `api_server.py:684-707` | JSON 409 | `{"error": "CONTROL_PLANE_LOOP", "detail": ...}` |
| Error | `pt_pipeline_client.py:92-93` | wrap policy | `raise PTPipelineError("trusted PT pipeline endpoint is invalid") from exc` |
| Error | PT `fastapi_app.py:1019-1028` | HTTPException | 422 string detail today; 409 string detail for ceiling |
| HTTP client | `pt_pipeline_client.py:112-116` | httpx | `AsyncClient(transport=..., timeout=..., follow_redirects=False)` missing trust_env |
| HTTP client | PT `agent_launcher.py:334-338` | httpx | same plus `trust_env=False` |
| Auth | `pt_pipeline_client.py:105-108` | bearer | `**auth_headers()` + Idempotency-Key + depth |
| URL policy | `pt_pipeline_client.py:87-91` | TLS flag | `allow_public=False, require_tls_for_non_loopback=True` |
| Tests | `tests/test_api_server.py:181-320` | FakePipelineClient | `monkeypatch.setattr(api_server, "PTPipelineClient", Fake)` |
| Tests | `tests/test_pt_pipeline_client.py:47-49` | MockTransport | `transport=httpx.MockTransport(handler)` |
| Tests | `tests/test_verify_model_endpoint_policy_parity.py:76-83` | AST strips docs | docstring-only equal |
| Config | `pipeline-routing.yml` via client | recipes | alnum `_` `-` only |
| Config | PT `config/cross-repo-policy-stacks.json` | peer map | PT branch → orama `cursor/tiered-pipeline-runtime-fb76`, `peer_pull` 363 |
| CI | orama `ci.yml:274-316` | sibling | same-named then main; skip if missing |
| CI | PT `ci.yml:32-97` | resolver | declared fail-closed; main push → orama main |
| Deps | `httpx` | already imported | do not add packages |
## External research (httpx)

```text
KEY_INSIGHT: httpx.AsyncClient(trust_env=True by default) mounts HTTP_PROXY /
  HTTPS_PROXY / ALL_PROXY from the environment. Authorization headers are
  forwarded to that proxy unless mounts are empty.
APPLIES_TO: PTPipelineClient.run AsyncClient kwargs
GOTCHA: Passing transport=httpx.MockTransport(...) bypasses proxy mount
  routing entirely. Inspecting _mounts on a MockTransport client does not
  prove trust_env. Construct a second client WITHOUT a custom transport
  (or with default transport) to assert mounts. Production tests that use
  MockTransport still need trust_env=False on the production call path
  so a later constructor change is what the source review sees.

KEY_INSIGHT: follow_redirects=False is already set; a 30x to another host
  would not automatically replay the bearer. Proxies are a different hop.
APPLIES_TO: do not treat redirects as covering the proxy case
GOTCHA: httpx 0.27+ still defaults trust_env True (verify against the
  pinned httpx in orama pyproject at implement time)

KEY_INSIGHT: Python int("-1"), int("+1"), int("1_0") all succeed.
  str.isdecimal() is False for those. str.isdigit() is False for those
  on Python 3. Underscore is accepted by int() as PEP 515.
APPLIES_TO: depth parser; use fullmatch r"^[0-9]+$" not int()/try
GOTCHA: isdecimal() also rejects empty string — good (empty already
  handled by strip → missing → 0). Do not use int() in an except path
  as a fallback.
```
## Repo A — orama-system (reuse PR 363)
### Mandatory reading

| Priority | File | Lines | Why |
| --- | --- | --- | --- |
| P0 | PT `src/utils/model_endpoint_url.py` at `85e1c86c` | all | Bytes to copy |
| P0 | `src/orama_system/pt_pipeline_client.py` | 70–143 | TLS call site + httpx client |
| P0 | `src/orama_system/api_server.py` | 667–707, 790–799 | Depth parser, gates, increment |
| P0 | `scripts/review/verify_model_endpoint_policy_parity.py` | 26–118 | AST strip; skip return 0 |
| P0 | `.github/workflows/ci.yml` | 274–326 | Sibling skip hole S1 |
| P1 | `tests/test_pt_pipeline_client.py` | all | Add proxy tests |
| P1 | `tests/test_api_server.py` | 181–320 | FakePipelineClient + depth tests |
| P1 | `tests/test_verify_model_endpoint_policy_parity.py` | 53–107 | Update FILES_TO_CHECK; add hash test |
| P1 | PT `src/perpetua_tools/agent_launcher.py` | 326–342 | `trust_env=False` pattern |
| P2 | `docs/plans/2026-05-29-01-cursor-PLAN.md` | P1 | Original pipeline intent |
| P2 | `tests/test_model_endpoint_url.py` | all | Union any missing PT behaviors |
### Files to change (orama)

| File | Action | Why |
| --- | --- | --- |
| `src/utils/model_endpoint_url.py` | UPDATE | Replace with PT `85e1c86c` bytes |
| `src/orama_system/pt_pipeline_client.py` | UPDATE | `trust_env=False` on `AsyncClient` |
| `src/orama_system/api_server.py` | UPDATE | Fail-closed depth parse + 422 invalid |
| `scripts/review/verify_model_endpoint_policy_parity.py` | UPDATE | `_is_loopback_host` + file hash + fail on missing sibling |
| `.github/workflows/ci.yml` | UPDATE | Fail if PT sibling missing |
| `tests/test_pt_pipeline_client.py` | UPDATE | Proxy positive + negative control |
| `tests/test_api_server.py` | UPDATE | Exhaustive depth matrix |
| `tests/test_verify_model_endpoint_policy_parity.py` | UPDATE | Hash fails on docstring-only drift |
| `tests/test_model_endpoint_url.py` | UPDATE | Union missing PT behaviors, orama style |
| `AGENTS.md` transport bullet | UPDATE | Mirror is byte-identical; identity in parity script |
### Task 1: Copy canonical validator
ACTION: From a Perpetua-Tools checkout at `85e1c86c`: `git show
85e1c86c:src/utils/model_endpoint_url.py` overwrite `src/utils/model_endpoint_url.py`. Confirm
`git hash-object` equals `003ac54187e98f5c38fad5906f9ec1ef43ce6f9e` and sha256 equals
`c7abdf8dc85d4cc33507d2cfd66d5697c1fc9e74b9316b38cec00c22ccb5cf6e`. If PT `main` moved, re-pin
Gate 0 before copying. IMPLEMENT: no hand-edit. Do not re-add the Canonical copy /
byte-identical module paragraph (lines 7–12 of the current orama file). GOTCHA: existing orama
tests key on RFC1918 / https messages, not module docs. VALIDATE: hashes equal; after Task 4 the
parity script PASS vs PT sibling.
If `hash-object` mismatches, STOP. Do not 'fix up' docs to make CI green. The whole point is
byte identity with PT.
### Task 2: Pin credentialed httpx (`trust_env=False`)
ACTION: In `PTPipelineClient.run`, pass `trust_env=False` next to `follow_redirects=False`
(lines 112–116 today).

```python
async with httpx.AsyncClient(
    transport=self.transport,
    timeout=timeout,
    follow_redirects=False,
    trust_env=False,
) as client:
```
MIRROR: PT `agent_launcher._pinned_get` lines 334–338. GOTCHA: tests using `MockTransport` still
work; `trust_env` does not affect that transport. That is why Task 2 tests must construct a
client **without** MockTransport for the mounts assertions.
#### Task 2 tests (required pair)
Add a helper in `tests/test_pt_pipeline_client.py` that builds `httpx.AsyncClient` with the same
kwargs as production except it omits `transport=` so default mounts apply. Do not inspect mounts
on the MockTransport used by `test_client_calls_only_guarded_pt_pipeline_*`.

```python
def _production_client_kwargs(**overrides):
    timeout = httpx.Timeout(120.0, connect=10.0)
    kwargs = dict(
        timeout=timeout,
        follow_redirects=False,
        trust_env=False,
    )
    kwargs.update(overrides)
    return kwargs


def test_pipeline_httpx_client_disables_env_proxy_mounts(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:9")
    monkeypatch.delenv("NO_PROXY", raising=False)
    with httpx.AsyncClient(**_production_client_kwargs()) as client:
        assert client.trust_env is False
        assert dict(client._mounts) == {} or not client._mounts


def test_pipeline_httpx_client_mounts_when_trust_env_left_on(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.delenv("NO_PROXY", raising=False)
    with httpx.AsyncClient(
        **_production_client_kwargs(trust_env=True)
    ) as client:
        assert client.trust_env is True
        assert client._mounts  # non-empty: negative control
```
If `_mounts` is empty even with `trust_env=True` in this environment, the negative control
failed — do not ship Task 2 claiming victory. Switch assertion to whatever httpx exposes for
proxy config in the pinned version, but keep the contrast (False vs True) in one file.
### Task 3: Fail-closed depth — one HTTP contract
Chosen contract (option b, api-correct). Do not leave orama 409 vs PT 422 for the same parse
failure.

| Condition | HTTP | Error code | Who |
| --- | --- | --- | --- |
| Header missing or empty after strip | treat as 0 | n/a | both |
| Header present, not `^[0-9]+$` | **422** | `CONTROL_PLANE_DEPTH_INVALID` | both |
| Parsed int `> MAX` on PT (receive) | **409** | `CONTROL_PLANE_LOOP` | PT |
| Parsed int `>= MAX` on orama (about to increment) | **409** | `CONTROL_PLANE_LOOP` | orama |
| Orama depth `>= 1` and missing pipeline refs | **409** | `CONTROL_PLANE_LOOP` | orama only |
Keep the two 409 **messages** (no refs vs ceiling). `>=` vs `>` is not drift: orama increments
before forwarding; PT validates the received value. MAX=2 means orama allows inbound 0 and 1
(forwards 1 and 2); PT allows received 0, 1, and 2; both refuse 3+.
#### Exact replacement for `_control_plane_depth`

```python
import re

_DEPTH_RE = re.compile(r"^[0-9]+$")


class ControlPlaneDepthInvalid(ValueError):
    """Present header is not a canonical unsigned decimal."""


def _control_plane_depth(http_request: Request) -> int:
    raw = http_request.headers.get(CONTROL_PLANE_DEPTH_HEADER, "").strip()
    if not raw:
        return 0
    if _DEPTH_RE.fullmatch(raw) is None:
        raise ControlPlaneDepthInvalid(raw)
    return int(raw)  # safe: digits only
```
In `run_oramasys`, catch `ControlPlaneDepthInvalid` **before** the `inbound_depth >= 1` gates
and return:

```python
return JSONResponse(
    status_code=422,
    content={
        "error": "CONTROL_PLANE_DEPTH_INVALID",
        "detail": (
            "X-Control-Plane-Depth must be an unsigned decimal integer"
        ),
    },
)
```
Do not call `PTPipelineClient.run` on that path. Do not map invalid to `MAX+1` anymore; that
collapsed parse errors into 409 LOOP and is the anti-pattern this review closed.
#### Exhaustive matrix (MAX = 2)

| Header | Refs | Orama | PT | `run()` / pipeline |
| --- | --- | --- | --- | --- |
| missing | no | 0, existing top-level path | implicit 0 | orama may call PT |
| missing | yes | 0, refs present, not nested gate | proceed | may call |
| `0` | no | 0, not nested | proceed | may call |
| `0` | yes | 0, not nested | proceed | may call |
| `1` | no | 409 LOOP (must supply refs) | proceed (PT does not require orama refs) | orama: never |
| `1` | yes | 200, forward header `2` | proceed (`2 > 2` is false) | called |
| `2` | no | 409 LOOP (must supply refs; checked first) | proceed (`2 > 2` false) | orama: never |
| `2` | yes | 409 LOOP (ceiling, `>= 2`) | proceed | orama: never |
| `3` | no | 409 LOOP (refs check first) | 409 LOOP (`3 > 2`) | never |
| `3` | yes | 409 LOOP (ceiling) | 409 LOOP | never |
| `-1` | yes or no | **422** INVALID | **422** INVALID | never |
| `+1` | yes or no | **422** INVALID | **422** INVALID | never |
| `1_0` | yes or no | **422** INVALID | **422** INVALID | never |
| `abc` | yes or no | **422** INVALID | **422** INVALID | never |
| `2.0` | yes or no | **422** INVALID | **422** INVALID | never |
| `00` | yes | digits-only → int 0 | int 0 | treat as 0 (leading zeros OK) |
| `+0` | yes or no | 422 INVALID | 422 INVALID | never |
Whitespace-only after strip is missing, not junk. Leading zeros (`00`) match `^[0-9]+$` and
become 0; that is acceptable. Do not invent a separate error for leading zeros.
#### Worked `int()` cases (why digits-only)

| Raw | `int(raw)` today | `^[0-9]+$` | After heal |
| --- | --- | --- | --- |
| `-1` | -1 (skips orama gates) | no | 422 |
| `+1` | 1 (looks like nested) | no | 422 |
| `1_0` | 10 (PEP 515) | no | 422 |
| `2.0` | ValueError → old orama MAX+1 → 409 | no | 422 |
| `1` | 1 | yes | existing gates |
| `` | not parsed | n/a | 0 |
### Task 4: Parity checker includes `_is_loopback_host` + file hash
ACTION: Add `_is_loopback_host` to `policy_functions` for `model_endpoint_url.py`. ACTION: For
that file only, also compare sha256 of the full bytes. Keep AST compare so a function-level diff
stays readable in CI logs. Leave `endpoint_policy_core.py` on AST-only. IMPLEMENT: mention
byte-identity in the **parity script** module docstring, not in the validator. ACTION: `main()`
must not return 0 when sibling is missing unless `PARITY_ALLOW_MISSING_SIBLING=1` (local only).
CI must not set that env.

```python
_FileSpec(
    "model_endpoint_url.py",
    ("_host_allowed", "validate_model_endpoint_url",
     "parse_model_endpoint_list", "_is_loopback_host"),
    require_identical_bytes=True,
)
```
Extend `_FileSpec` with `require_identical_bytes: bool = False` rather than a parallel list.
GOTCHA: PT script is directional (`ORAMA_SYSTEM_ROOT`). Same tuple and hash rule must land on PT
in Repo B so both checkers agree.
Update `test_extract_policy_source_raises_on_missing_function` fixtures that list the three
names: include `_is_loopback_host` in any completeness assertion of
`FILES_TO_CHECK[0].policy_functions`. Add
`test_model_endpoint_url_byte_hash_detects_docstring_only_drift`.
### Task 4b: CI must not skip the sibling
In orama `.github/workflows/ci.yml` job `docs-pointer-sync`:

1. Keep same-named PT ref checkout (`continue-on-error: true` is OK here).
2. Keep clear + PT `main` fallback.
3. Change PT `main` fallback from `continue-on-error: true` to **false**
   (or keep true but then fail explicitly).
4. Replace the skip branch with:

```yaml
      - name: Verify model endpoint policy parity with Perpetua-Tools
        env:
          PERPETUA_TOOLS_ROOT: ${{ github.workspace }}/perpetua-tools-sibling
        run: |
          if [ ! -d "$PERPETUA_TOOLS_ROOT/src/utils" ]; then
            echo "::error::Perpetua-Tools sibling missing; refusing skip."
            exit 1
          fi
          python3 scripts/review/verify_model_endpoint_policy_parity.py
```
The docs/v2 pointer step may keep a skip if that is a separate concern; do not couple it.
GOTCHA: forks without access to `diazMelgarejo/Perpetua-Tools` will go red. Accept for this
pair.
### Task 5: Test union
Orama `tests/test_model_endpoint_url.py` already has 127-prefix, TLS flag, link-local,
parse-list tests (see encyclopedia below). Diff against PT `tests/test_model_endpoint_url.py` at
`85e1c86c`. Union missing *behaviors* as extra `def test_*` functions. Do not delete
`test_require_tls_flag_*`. Likely gaps: `file://`, credentials in URL, empty URL,
`redact_endpoint_for_log` if PT has them and orama does not.
### Task 6: Optional CORS — skip
`allow_headers` currently Authorization, Content-Type. PT uses httpx. Skip unless a browser must
send X-Control-Plane-Depth.
## Repo B — Perpetua-Tools (later new PR; PR 395 is merged)
There is no open PT PR. Do not reopen or force-push 395. Open one PT PR from `main`, with the
map-retirement commit ready before merging orama PR 363.
### Files to change (PT)

| File | Action | Why |
| --- | --- | --- |
| `orchestrator/fastapi_app.py` | UPDATE | Digits-only parse; 422 dict; reject negatives |
| `scripts/review/verify_model_endpoint_policy_parity.py` | UPDATE | `_is_loopback_host` + file hash; fail missing sibling/file |
| `.github/workflows/ci.yml` | UPDATE | Fail if orama sibling missing on main push (S2) |
| `scripts/review/resolve_orama_policy_ref.py` | UPDATE | 404 + peer PR merged → main only |
| `config/cross-repo-policy-stacks.json` | UPDATE | Drop or archive `peer_pull: 363` same sitting as PR 363 merge |
| pipeline route tests (new) | ADD | Depth matrix; none exist today |
| `tests/test_resolve_orama_policy_ref.py` | UPDATE | merged+404 → main; open declared 404 still fails |
| `tests/test_verify_model_endpoint_policy_parity.py` | UPDATE | Hash + `_is_loopback_host` |
| `.agent/memory` / `docs/LESSONS.md` | APPEND only | Record that PR 363 peer map is retired |
Do not touch `src/utils/model_endpoint_url.py` unless a real policy bug appears (none now).
### Task B1: Depth fail-closed (same contract as Task 3)
Today `orchestrator/fastapi_app.py` 1015–1028: `int(depth_raw)` then `if depth > MAX`.
Non-integers already 422 string detail; `-1` is allowed. Replace with digits-only. FastAPI
detail should be a dict so clients can match orama’s JSON `error` field:

```python
depth_raw = http_request.headers.get(CONTROL_PLANE_DEPTH_HEADER, "").strip()
if depth_raw:
    if re.fullmatch(r"^[0-9]+$", depth_raw) is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "CONTROL_PLANE_DEPTH_INVALID",
                "detail": "X-Control-Plane-Depth must be an unsigned decimal integer",
            },
        )
    depth = int(depth_raw)
    if depth > MAX_CONTROL_PLANE_DEPTH:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "CONTROL_PLANE_LOOP",
                "detail": "Control-plane call depth exceeded",
            },
        )
```
PT has **no** existing test for these HTTPExceptions (grep 2026-09-19). Add tests next to
whatever currently hits `/pipelines/{recipe}/run` (likely `tests/test_orama_bridge.py` or
fastapi TestClient tests). Cover `-1`, `1_0`, `3`, missing header, `2`.
### Task B2: Parity tuple + hash lockstep
Same `_is_loopback_host` addition and sha256 of `model_endpoint_url.py`. Keep
`ORAMA_SYSTEM_ROOT`. Do not copy orama’s `PERPETUA_TOOLS_ROOT` names. Change `_check_one`:
missing peer **file** for `model_endpoint_url.py` returns False, not True (close S4). Change
`main()` missing sibling: return 1 unless allow-env (close S3).
### Task B3: CI peer map + merged+404 exception
`config/cross-repo-policy-stacks.json` maps PT branch `fix/pt-pipeline-endpoint-tls-20260917` →
orama `cursor/tiered-pipeline-runtime-fb76` with `peer_pull` 363.
Clarify the review’s timing-gap claim: Dependabot PRs 364/365 do not use that JSON key. PT
`main` pushes already check out orama `main`. `8cc3d170` already returns `main` when GitHub says
peer pull merged. The real post-merge liability is a stale PT PR still named
`fix/pt-pipeline-endpoint-tls-20260917` after GitHub deletes the orama feature branch, if
`fetch_pull_merged` lags or 404s, so the resolver still asks for the deleted orama branch and
declared checkout fails closed.

Correction (narrow exception, not a silent main guess):

1. Have the PT map-retirement commit ready to merge in the same sitting
   as PR 363.
2. Resolver: if declared `peer_ref` checkout returns 404 **and** the GitHub
   pull `peer_pull` has `"merged": true`, then check out `main`.
3. If the pull is **open** (or merge state cannot be read), keep fail-closed.
4. After PR 363 merges, delete or archive the JSON row so a recycled
   branch name cannot pin 363 forever.
5. Update `test_records_live_orama_pr_363_peer_equivalents` accordingly
   (it currently asserts the live pin).
Implementing (2) requires the workflow to distinguish checkout 404 from other failures. If
Actions does not expose 404 vs auth-fail cleanly, prefer same-sitting map retirement (1)+(4) as
the primary control, and add a unit test on the resolver that simulates merged=True → main
(already exists as `test_merged_peer_pull_uses_main`). Do not guess main on undeclared refs.
### Task B4: Do not regress PR 395 strengths
Leave `require_tls_for_non_loopback` default False. Leave `orama_bridge` TLS classification.
Leave `trust_env=False` on `_pinned_get`. Leave packaged `hosts.py` without `127.` prefix.
## Test encyclopedia
### Existing orama tests that must keep passing

| Test | File | Must still |
| --- | --- | --- |
| `test_client_calls_only_guarded_pt_pipeline_with_auth_and_idempotency` | `test_pt_pipeline_client.py` | Bearer, idempotency, depth header `1`, path `/pipelines/.../run` |
| `test_client_has_no_orchestrate_route_fallback` | same | no `/orchestrate` |
| `test_client_accepts_idempotent_replay_without_redispatching` | same | empty output + replay True |
| `test_http_bridge_uses_guarded_pt_pipeline_when_approval_refs_are_supplied` | `test_api_server.py` | 200, FakePipelineClient called |
| `test_nested_control_plane_call_requires_pipeline_approval_refs` | same | 409 LOOP, no refs |
| `test_control_plane_depth_at_ceiling_is_rejected_even_with_valid_pipeline_refs` | same | 409 LOOP, `calls == {}` |
| `test_control_plane_depth_one_below_ceiling_is_forwarded_at_the_ceiling` | same | 200, forwarded depth == MAX |
| `test_pipeline_approval_references_must_be_supplied_together` | same | 422 pydantic |
| `test_127_prefix_hostname_not_treated_as_loopback` | `test_model_endpoint_url.py` | RFC1918-style error |
| `test_require_tls_flag_rejects_http_to_rfc1918_private_host` | same | https error |
| `test_extract_policy_source_ignores_docstring_differences` | `test_verify_model_endpoint_policy_parity.py` | AST helper still strips function docs |
### New orama tests to add (one per matrix row that is new)

| Suggested name | Header | Refs | Expect |
| --- | --- | --- | --- |
| `test_depth_negative_with_refs_is_invalid` | `-1` | yes | 422 INVALID, `calls == {}` |
| `test_depth_negative_without_refs_is_invalid` | `-1` | no | 422 INVALID (not 409 LOOP) |
| `test_depth_plus_prefix_is_invalid` | `+1` | yes | 422 |
| `test_depth_underscore_is_invalid` | `1_0` | yes | 422 |
| `test_depth_float_is_invalid` | `2.0` | yes | 422 |
| `test_depth_garbage_is_invalid` | `abc` | no | 422 |
| `test_depth_zero_without_refs_is_top_level` | `0` | no | existing non-pipeline path (not 409) |
| `test_depth_three_with_refs_is_loop` | `3` | yes | 409 LOOP, `calls == {}` |
Reuse the FakePipelineClient pattern at `tests/test_api_server.py:187-202`. Use
`TestClient(api_server.app, raise_server_exceptions=True)`. Auth: these tests currently do not
set a bearer; if middleware starts requiring one in this environment, copy the fixture from
`tests/test_control_plane_auth.py` rather than inventing a new one. Do not change auth in this
heal.
### Parity unit tests to add

```python
def test_files_to_check_model_endpoint_includes_is_loopback_host():
    spec = next(s for s in verify_parity.FILES_TO_CHECK
                if s.filename == "model_endpoint_url.py")
    assert "_is_loopback_host" in spec.policy_functions


def test_model_endpoint_byte_hash_detects_docstring_only_drift(tmp_path):
    # same AST, different module docstring → hash mismatch → _check_one False
    ...
```
## Sequencing, commits, rollback

```text
PT PR 395 MERGED @ 85e1c86c  ── already done
PT main CI red vs orama main AST ── expected until PR 363 merges
orama PR 363 OPEN
    │
    ├─ this plan file (no product code) ── current
    │
    ├─ CONFIRM
    │
    ├─ Heal commits on cursor/tiered-pipeline-runtime-fb76
    │     1. test(depth): 422 matrix (red)
    │     2. fix(api): digits-only depth + 422 body
    │     3. test(httpx): proxy positive+negative (red)
    │     4. fix(client): trust_env=False
    │     5. chore(utils): copy PT validator bytes
    │     6. test(parity): hash + _is_loopback_host (red)
    │     7. fix(parity): tuple + hash + fail missing sibling
    │     8. ci: fail if PT sibling missing
    │
    ├─ Prepare PT follow-up branch (map retirement + B1–B3)
    │     do not merge PT first
    │
    ├─ CI green on PR 363
    │
    ├─ SAME SITTING: merge PR 363 AND merge PT map-retirement
    │
    └─ Remainder of PT PR if not already in that sitting
```
Rollback: revert the orama heal commits on the PR 363 branch; do not revert PT PR 395. If PR 363
merged and PT map was retired, restoring the map is append/update of JSON, not a rewrite of
lessons.
Commit messages (conventional): `fix(api):`, `fix(client):`, `chore(utils):`, `test(api):`,
`ci:` — use `scripts/git/commit-clean.sh` after `verify-staged-for-commit.sh`. Do not stage
unrelated dirty `scripts/cursor/*` or `scripts/git/*`.
## Validation commands
### Orama (on PR 363 branch)

```bash
git hash-object src/utils/model_endpoint_url.py
# expect 003ac54187e98f5c38fad5906f9ec1ef43ce6f9e

: "${PERPETUA_TOOLS_ROOT:?set to the Perpetua-Tools checkout}"
sha256sum src/utils/model_endpoint_url.py
sha256sum "$PERPETUA_TOOLS_ROOT/src/utils/model_endpoint_url.py"

python scripts/review/verify_model_endpoint_policy_parity.py

python -m pytest -q \
  tests/test_model_endpoint_url.py \
  tests/test_pt_pipeline_client.py \
  tests/test_api_server.py \
  tests/test_verify_model_endpoint_policy_parity.py

python scripts/review/repo_hygiene.py .
npx markdownlint-cli2 \
  .claude/PRPs/plans/pr-363-395-lockstep-heal.plan.md \
  .claude/plans/pr-363-395-lockstep-heal.plan.md
```
EXPECT: hashes equal; parity PASS; tests PASS; hygiene OK; lint OK. A CI log line on PR 363 must
show the parity script ran, not skip.
### PT (later PR)

```bash
ORAMA_SYSTEM_ROOT="${ORAMA_SYSTEM_ROOT:?set to the orama-system checkout}" \
  python scripts/review/verify_model_endpoint_policy_parity.py
python -m pytest -q \
  tests/test_orama_bridge.py \
  tests/test_resolve_orama_policy_ref.py \
  tests/test_verify_model_endpoint_policy_parity.py \
  tests/test_model_endpoint_url.py
```
## Acceptance

- [ ] No new orama PR; heals land on PR 363
- [ ] Gate 0 re-checked: PT PR 395 still merged; copy from pinned SHA if
      `main` moved
- [ ] No PT product merge until PR 363 validator matches PT main and CI
      is green; PT map-retirement is staged for the same sitting
- [ ] PT `model_endpoint_url.py` unchanged unless a new policy bug appears
- [ ] Orama validator SHA == PT `85e1c86c` SHA
- [ ] `trust_env=False` + proxy positive **and** negative control
- [ ] Depth: both repos 422 `CONTROL_PLANE_DEPTH_INVALID` on junk /
      signed / underscores; 409 `CONTROL_PLANE_LOOP` for refs/ceiling only
- [ ] Parity checks `_is_loopback_host` **and** file sha256 in both scripts
- [ ] S1–S4 skip holes closed (workflow, script missing sibling, PT missing
      peer file)
- [ ] Identity paragraph not reintroduced inside the mirrored file
- [ ] PR 395 strengths preserved (opt-in TLS, bridge TLS, packaged hosts,
      fail-closed for **open** declared peers)
- [ ] PR 363 strengths preserved (bridge, refs atomic, two 409 messages,
      no `/orchestrate`)
- [ ] No workstation-only download path in this file
- [ ] PR 363 body not clobbered
## Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Copying PT file breaks an orama-only comment assumption | Low | Low | Tests don’t parse module docstring |
| `trust_env=False` breaks a documented proxy deployment | Low | Med | Control-plane token must not use HTTP_PROXY |
| Depth semantic change (`-1` used in the wild) | Very low | Low | Header is internal; PT always sends `"1"` |
| Changing orama parse failures from 409 to 422 | Low | Low | Header is internal; tests pin the new code |
| FastAPI dict `detail` breaks a client expecting a string | Low | Low | Control-plane is internal; document both shapes |
| Opening PT PR too early vs stale 363 checkout | Med | Med | Byte-identical validator on PR 363 first; same-sitting map retirement |
| Dual parity-script edits diverge again | Med | Med | Same tuple + same hash rule, directional sibling only |
| Fail-closed sibling checkout breaks forks | Low | Low | Accept for this pair |
| Negative-control mounts empty on some httpx versions | Low | Med | Pin assertion to actual httpx API; do not skip the contrast |
## What the 2026-09-19 review got right (do not regress)

- SSoT direction (PT `main` bytes → orama, not the reverse).
- Identity lives in the parity script, not the mirrored blob.
- `require_tls_for_non_loopback` stays opt-in.
- Test-union of styles, not a style fight.
## What plan revisions changed

1. Re-fetched PT PR 395: merged; copy pin is `85e1c86c`.
2. Confirmed parity **is** in CI; added Task 4b + S1–S4 skip inventory
   and full-file hash so docstring drift cannot go green again.
3. One HTTP contract: 422 `CONTROL_PLANE_DEPTH_INVALID` vs 409
   `CONTROL_PLANE_LOOP`. No documented-forever split.
4. Peer-map: same-sitting retirement + merged+404→main only.
5. Proxy negative control required.
6. Exhaustive depth matrix + `int()` worked examples + exact patches.
7. Canonical URL is GitHub, not `/opt/cursor/artifacts/…`.
8. This expansion: lifecycle traces, discovery table, httpx research,
   test encyclopedia, TDD commit split, PT “no tests exist today” note.
## Notes
Filtered review nits (CORS header list, `parse_model_endpoint_list` not forwarding TLS flag)
stay out of default scope. This file is the implementation contract for `/prp-implement` after
confirmation.

**WAITING FOR CONFIRMATION** before any product-code commits: proceed with orama PR 363 heals?
(yes / no / modify)

## Appendix A — current orama `_control_plane_depth` + gates (do not keep `int(raw)`)

```python
def _control_plane_depth(http_request: Request) -> int:
    raw = http_request.headers.get(CONTROL_PLANE_DEPTH_HEADER, "").strip()
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError:
        return MAX_CONTROL_PLANE_DEPTH + 1


@app.post("/oramasys", response_model=OramasysResponse)
async def run_oramasys(req: OramasysRequest, http_request: Request) -> OramasysResponse:
    start = time.perf_counter()
    inbound_depth = _control_plane_depth(http_request)
    has_pipeline_refs = bool(req.pipeline_trace_id and req.pipeline_idempotency_key)
    if inbound_depth >= 1:
        if not has_pipeline_refs:
            return JSONResponse(
                status_code=409,
                content={
                    "error": "CONTROL_PLANE_LOOP",
                    "detail": (
                        "Nested control-plane calls must use pipeline_trace_id and "
                        "pipeline_idempotency_key to invoke PT's guarded pipeline route"
                    ),
                },
            )
        # MAX_CONTROL_PLANE_DEPTH bounds nesting independent of whether PT's
        # own orchestrator separately re-validates depth -- valid pipeline
        # refs must not exempt a request from the ceiling, only from the
        # "must use the guarded route" check above.
        if inbound_depth >= MAX_CONTROL_PLANE_DEPTH:
            return JSONResponse(
                status_code=409,
                content={
                    "error": "CONTROL_PLANE_LOOP",
                    "detail": (
                        f"Control-plane depth {inbound_depth} is at or beyond the "
                        f"maximum of {MAX_CONTROL_PLANE_DEPTH}; further nesting is refused"
                    ),
                },
            )
```

## Appendix B — current `PTPipelineClient.run` (add `trust_env=False` only)

```python
        self,
        *,
        task_type: str,
        prompt: str,
        trace_id: str,
        idempotency_key: str,
        control_plane_depth: int = 1,
    ) -> PTPipelineResult:
        headers = {
            **auth_headers(),
            "Idempotency-Key": idempotency_key,
            CONTROL_PLANE_DEPTH_HEADER: str(control_plane_depth),
        }
        timeout = httpx.Timeout(120.0, connect=10.0)
        try:
            async with httpx.AsyncClient(
                transport=self.transport,
                timeout=timeout,
                follow_redirects=False,
            ) as client:
                response = await client.post(
                    self.pipeline_url(task_type),
                    headers=headers,
                    json={"prompt": prompt, "trace_id": trace_id},
                )
                response.raise_for_status()
                body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise PTPipelineError("PT pipeline request failed") from exc
        output = body.get("output") if isinstance(body, dict) else None
        models_used = body.get("models_used") if isinstance(body, dict) else None
        replay = body.get("replay") is True if isinstance(body, dict) else False
        if (
            not isinstance(output, str)
            or (not replay and not output.strip())
            or not isinstance(models_used, dict)
        ):
            raise PTPipelineError("PT pipeline returned an invalid response")
        return PTPipelineResult(
            output=output,
            models_used={
                str(stage): str(model)
                for stage, model in models_used.items()
                if str(stage).strip() and str(model).strip()
            },
            replay=replay,
        )
```

## Appendix C — current PT depth parse (digits-only + dict detail)

```python
    depth_raw = http_request.headers.get(CONTROL_PLANE_DEPTH_HEADER, "").strip()
    if depth_raw:
        try:
            depth = int(depth_raw)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail="Control-plane depth header must be an integer",
            ) from None
        if depth > MAX_CONTROL_PLANE_DEPTH:
            raise HTTPException(
                status_code=409,
                detail="Control-plane call depth exceeded",
            )
```

## Appendix D — current orama CI sibling block (close S1)

```yaml
  docs-pointer-sync:
    name: docs/v2 → downstream pointer sync gate (zero-fragmentation)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5

      - name: Checkout Perpetua-Tools (PR branch for stacked cross-repo parity)
        if: github.event_name == 'pull_request'
        id: checkout-pt-pr
        uses: actions/checkout@v5
        with:
          repository: diazMelgarejo/Perpetua-Tools
          ref: ${{ github.head_ref }}
          path: perpetua-tools-sibling
          fetch-depth: 1
          persist-credentials: false
          submodules: false
        continue-on-error: true

      - name: Clear perpetua-tools-sibling before main fallback
        if: github.event_name != 'pull_request' || steps.checkout-pt-pr.outcome != 'success'
        run: rm -rf perpetua-tools-sibling

      - name: Checkout Perpetua-Tools (main fallback)
        if: github.event_name != 'pull_request' || steps.checkout-pt-pr.outcome != 'success'
        uses: actions/checkout@v5
        with:
          repository: diazMelgarejo/Perpetua-Tools
          ref: main
          path: perpetua-tools-sibling
          fetch-depth: 1
          persist-credentials: false
          submodules: false
        continue-on-error: true

      - name: Verify model endpoint policy parity with Perpetua-Tools
        run: |
          if [ -d perpetua-tools-sibling ]; then
            PERPETUA_TOOLS_ROOT="$GITHUB_WORKSPACE/perpetua-tools-sibling" \
              python3 scripts/review/verify_model_endpoint_policy_parity.py
          else
            echo "skip: Perpetua-Tools not available in this CI run"
          fi

      - name: Verify docs/v2 pointers in sync with downstream Perpetua-Tools
        run: |
          if [ -d perpetua-tools-sibling ]; then
            PERPETUA_TOOLS_ROOT="$GITHUB_WORKSPACE/perpetua-tools-sibling" \
              bash scripts/git/sync-docs-v2-pointers.sh --check \
              "$GITHUB_WORKSPACE/perpetua-tools-sibling"
          else
            echo "skip: Perpetua-Tools not available in this CI run"
          fi
```

## Appendix E — `int()` vs canonical decimal (copy into test comments)

Python 3.12 behavior used as the threat model:

- `int("-1") == -1`
- `int("+1") == 1`
- `int("1_0") == 10`
- `int("2.0")` raises ValueError
- `" -1 ".strip()` then `int` still parses

Never use `int()` without a digits-only preflight on this header.

## Appendix F — JSON bodies (clients may match `error`)

Orama 422:

```json
{"error": "CONTROL_PLANE_DEPTH_INVALID", "detail": "X-Control-Plane-Depth must be an unsigned decimal integer"}
```

Orama 409 missing refs (keep wording):

```json
{"error": "CONTROL_PLANE_LOOP", "detail": "Nested control-plane calls must use pipeline_trace_id and pipeline_idempotency_key to invoke PT's guarded pipeline route"}
```

Orama 409 ceiling (keep wording):

```json
{"error": "CONTROL_PLANE_LOOP", "detail": "Control-plane depth {inbound_depth} is at or beyond the maximum of 2; further nesting is refused"}
```
