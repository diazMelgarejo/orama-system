# Plan: Dual-repo lockstep heal after orama #363 + PT #395

**Status:** Plan only — do not implement until explicit confirmation  
**Reuse:** [orama-system PR #363](https://github.com/diazMelgarejo/orama-system/pull/363) (`cursor/tiered-pipeline-runtime-fb76`)  
**PT #395:** [merged](https://github.com/diazMelgarejo/Perpetua-Tools/pull/395) 2026-09-19 — no open PT PR to reuse  
**Method:** orama-system 5-stage + AFRP + CIDF + integrative-merge (synthesize, never amputate)

```text
AFRP: Type C | Level Expert | Mode 2
ROLE: Systems architect for L2/L3 lockstep
GOAL: One downloadable plan that heals both repos without losing either side
CONSTRAINTS: No code until confirm; reuse open PR #363; PT follow-up is a later PR
```

---

## Summary

Two lockstep PRs were trying to do one thing: **orama stays stateless, PT owns guarded pipeline execution, and a control-plane bearer must never ride cleartext to a non-loopback host — including hostnames that only look like `127.*`.**

PT #395 merged that policy into the canonical `src/utils/model_endpoint_url.py`. Orama #363 already has the same **policy functions** and the pipeline bridge, but still has three gaps:

1. `PTPipelineClient` can send the bearer through `HTTP_PROXY` (`trust_env` default true).
2. The orama **mirror file** is not byte-identical to PT `main` (docstrings only).
3. Depth parsing accepts signed integers (`-1` skips the loop gate).

PT has matching leftover work that **cannot** go onto #395 (merged, no open PT PRs). It needs a **later PT PR**, sequenced after orama #363 heals, not a twin “parity” PR that rewrites the canonical file.

---

## User story

As a stack operator merging L2/L3 lockstep security work,  
I want one harmonized policy file, a bearer client that cannot leak via proxy, and fail-closed depth parsing on both sides,  
so that CI parity stays honest and the original #363/#395 threat model actually holds.

---

## Problem → solution

**Now:** Policy AST matches; file SHAs do not. CI strips docstrings, so “byte-identical” in orama’s module docstring is a lie the checker never enforces. `_is_loopback_host` is not even in `FILES_TO_CHECK`. The new orama client hardened the *target URL* and disabled redirects, but not env proxies. Depth uses `int()`.

**Desired:** PT `main` bytes of `model_endpoint_url.py` live on orama #363. Mirror identity lives *outside* that file. Parity checker also hashes `_is_loopback_host`. Credentialed httpx uses `trust_env=False`. Depth parsers fail closed on both repos. PT CI map stops pinning #363 after it merges.

---

## Metadata

- **Complexity:** Medium (small diffs, cross-repo sequencing)
- **Source PRD:** N/A (review of #363 after #395 merge)
- **Estimated files:** orama ~6–8; PT ~4–6 (later PR)
- **Confidence (single-pass, after confirm):** 8/10

---

## Original intent (re-read of PRs, comments, plans)

### Orama #363 was trying to ship

From `docs/plans/2026-05-29-01-cursor-PLAN.md` P1 and commit `746c1573`:

- Bridge `/oramasys` to PT’s **guarded** `/pipelines/{recipe}/run`, never `/orchestrate`.
- PT owns recipes, approvals, budgets, credentials.
- Orama stays stateless.
- Nested control-plane hops must carry pipeline refs; depth is bounded (`MAX_CONTROL_PLANE_DEPTH = 2`).
- Env aliases: `ORAMASYS_*` canonical, `ULTRATHINK_*` still documented.

CodeRabbit on #363 then forced two security heals (both resolved on the PR):

| Finding | Commit | Keep |
| --- | --- | --- |
| Depth ceiling not enforced when refs present | `a88673f7` + tests `ddde337c` | Keep both checks distinct (missing refs vs at-ceiling) |
| Bearer over LAN HTTP to RFC1918 | `4218729f` (opt-in TLS flag) | Keep flag **opt-in**; only pipeline client sets True |
| `127.attacker.example` treated as loopback | `bb3eb7da` (shared lockstep with PT) | Keep ipaddress-only loopback |

Strengths to keep: atomic pipeline refs, recipe alnum/`_`/`-`, `allow_public=False` even when env allows public model endpoints, `follow_redirects=False`, replay-empty output allowed, `_client_safe_detail`, integration markers + annotations on `/oramasys` tests.

### PT #395 was trying to ship

Canonical side of CodeRabbit Finding 2, plus later heals on the **same** branch (no second PT PR — that rule still applies to *395*, which is now closed):

| Commit | Intent | Keep |
| --- | --- | --- |
| `44b67966` | `require_tls_for_non_loopback` default False | Keep opt-in; do not sweep LM Studio/Ollama HTTP |
| `9349998f` / `bb3eb7da` pair | Drop `startswith("127.")` | Keep |
| `718ba88` (coderabbitai) | `_host_allowed` docstring + `Returns \`scheme://host:port\`` | Keep on canonical file |
| `7f8b834` | `orama_bridge._is_local_oramasys_endpoint` also sets TLS flag | Keep (PT-only) |
| `84cd350` | Bearer HTTPS `url_checker` on remote `ssrf_request`; packaged hosts.py 127 fix | Keep (PT-only) |
| `8cc3d170` | CI checkout of orama **#363 peer**, unquoted `GITHUB_OUTPUT`, no silent main fallback | Keep the resolver; **update the map after #363 merges** |
| Memory/lesson commits | Append-only records | Keep; do not rewrite |

Human intent in comments: one PT branch, ordinary fast-forward, “do not open a second PR” *for 395*. That does **not** forbid a later PT PR for *new* follow-ups after merge.

---

## Drift: why, how, when

### Timeline

| When | What | Effect |
| --- | --- | --- |
| 2026-05-25 | Shared validator born (both repos) | Two copies from day one |
| 2026-06-13 | `startswith("127.")` shortcut appears (orama layout refactor `6914aa3c`) | Hostname `127.attacker.example` classifies as loopback |
| 2026-08-12 | orama `fde9d460` “sync from PT” | **Orama added** the 7-line “Canonical copy… keep it byte-identical” paragraph. PT **never** had that text. Commit message admits drift was docs-only and that AST parity (which **strips docstrings**) was already green. They *merged in orama’s own cross-repo note rather than discarding it* — that is the paradox. |
| 2026-09-17 13:08–13:35 UTC | Lockstep TLS + 127 fix on both PRs (`4218729f`/`bb3eb7da` vs `44b67966`/`9349998f`) | Policy functions match |
| 2026-09-17 20:05 UTC | PT only: CodeRabbit autofix `718ba88` | Adds `_host_allowed` docstring; changes return line to ``scheme://host:port``. **Never mirrored to orama.** |
| 2026-09-19 12:17 UTC | PT #395 merges | Canonical = PT `main` blob `003ac541…` |
| 2026-09-19 review | Orama #363 still `c418645…` | Policy AST equal; module docstring + `_host_allowed` docs + return-line backticks differ |

### Why CI did not catch it

`scripts/review/verify_model_endpoint_policy_parity.py` compares AST dumps of `_host_allowed`, `validate_model_endpoint_url`, `parse_model_endpoint_list` **after deleting function docstrings**. It does **not** compare:

- module docstring
- `_is_loopback_host` (the function the TLS flag depends on)
- full-file bytes

So “byte-identical” in orama’s module docstring is a human contract the machine never enforced. Putting that contract *inside* the file that must be identical guarantees drift: PT will not carry an orama-only identity paragraph.

### What is better from each side

| Piece | Keep | Mode |
| --- | --- | --- |
| Policy functions + `_is_loopback_host` | Identical already; freeze by copying **PT `main` file bytes** to orama | 3 superset / 6 api-correct (PT is SSoT) |
| PT `_host_allowed` docstring + return line | Keep (canonical docs) | 3 |
| Orama “do not independently edit” intent | Keep **outside** the mirrored file: parity script header + AGENTS.md/CLAUDE.md pointer | 4 synthesize |
| Orama extra module paragraph inside the file | Do **not** copy into PT | 5 architecturally-correct (identity in the payload is the bug) |
| Orama function-style tests vs PT class-style tests | Keep **both styles**; union missing *behaviors* | 2 union |
| `trust_env=False` | Copy from PT `agent_launcher._pinned_get` into orama `PTPipelineClient` | 6 |
| Distinct 409 reasons (no refs vs ceiling) | Keep orama’s split | 4 |
| PT `orama_bridge` TLS + remote bearer HTTPS | Already on PT main; do not reimplement in orama | n/a |
| Parity script sibling env paths | Keep directional (`PERPETUA_TOOLS_ROOT` vs `ORAMA_SYSTEM_ROOT`) | 6 — scripts are **not** byte-identical on purpose |

---

## Harmonized design (5-stage)

### Stage 1 — Context

PT is runtime/state authority. Orama is a manually synced mirror of *policy*, not a second parser. #363’s product work (pipeline bridge) is in scope to **keep**. The heal is vertical-slice contract work: persistence none, contract = validator + depth header + bearer transport.

### Stage 2 — Architecture

```
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

Identity / sync rules live in:
  scripts/review/verify_model_endpoint_policy_parity.py  (both repos, directional)
  AGENTS.md endpoint-transport section
NOT in the mirrored module docstring.
```

CIDF: this is a file write in-repo (rank 5 scripting). Decide() before inserting the identity paragraph anywhere: **do not insert it into the mirrored file**.

### Stage 3 — Refinement (NOT building)

- Do not open a PT PR whose only job is to make `model_endpoint_url.py` match orama.
- Do not require TLS for LM Studio / Ollama / Win coder pool.
- Do not convert orama tests to PT class layout or vice versa.
- Do not rewrite #395 history or reopen #395.
- Do not put workstation paths in the plan or code.
- Do not change PR #363 body (comment-only).
- Do not fold Dependabot PRs #364/#365 into this heal.

### Stage 4 — Execution (after confirm)

Two sequenced PRs:

| Order | Repo | Vehicle | Base |
| --- | --- | --- | --- |
| 1 | orama-system | **Reuse #363** `cursor/tiered-pipeline-runtime-fb76` | `main` |
| 2 | Perpetua-Tools | **New PR after #363 is green** (no open PT PR exists) | `main` (already contains #395) |

Do not start PT until orama tip is the byte-identical validator, or PT CI will keep checking out #363 and stay green for the wrong reason (AST-only).

### Stage 5 — Crystallize (after implement)

Append-only lesson: *mirror identity must not live inside the mirrored blob; parity must include `_is_loopback_host` and optionally a full-file hash.*

---

## Repo A — orama-system (reuse PR #363)

### Mandatory reading

| Priority | File | Lines | Why |
| --- | --- | --- | --- |
| P0 | `src/utils/model_endpoint_url.py` on **PT `main`** | all | Bytes to copy |
| P0 | `src/orama_system/pt_pipeline_client.py` | 67–125 | TLS call site + httpx client |
| P0 | `src/orama_system/api_server.py` | 667–674, 677+ | Depth parser + loop gates |
| P0 | `scripts/review/verify_model_endpoint_policy_parity.py` | 26–35, 41–58 | AST strip; missing `_is_loopback_host` |
| P1 | `tests/test_pt_pipeline_client.py` | all | Add proxy test |
| P1 | `tests/test_api_server.py` | 178+ | Depth tests to extend |
| P1 | PT `src/perpetua_tools/agent_launcher.py` | 326–342 | `trust_env=False` pattern |
| P2 | `docs/plans/2026-05-29-01-cursor-PLAN.md` | P1 | Original pipeline intent |

### Files to change (orama)

| File | Action | Why |
| --- | --- | --- |
| `src/utils/model_endpoint_url.py` | UPDATE | Replace with PT `main` bytes (docstrings included) |
| `src/orama_system/pt_pipeline_client.py` | UPDATE | `trust_env=False` on `AsyncClient` |
| `src/orama_system/api_server.py` | UPDATE | Fail-closed depth parse |
| `scripts/review/verify_model_endpoint_policy_parity.py` | UPDATE | Add `_is_loopback_host`; document identity here |
| `tests/test_pt_pipeline_client.py` | UPDATE | HTTP_PROXY must not see Authorization |
| `tests/test_api_server.py` | UPDATE | `-1`, `+1`, `1_0`, garbage still 409 / fail closed |
| `tests/test_model_endpoint_url.py` | UPDATE | Union any PT behaviors still missing (file/credentials/empty/redact) **in orama function style** |
| `AGENTS.md` or CLAUDE.md transport bullet | UPDATE | One sentence: mirror is byte-identical; identity lives in the parity script |

### Tasks — orama

#### Task 1: Copy canonical validator

- **ACTION:** `git show origin/main:src/utils/model_endpoint_url.py` from Perpetua-Tools → overwrite orama file. Confirm `sha256` match.
- **IMPLEMENT:** No hand-edit of policy logic. Do not re-add the “canonical copy” module paragraph.
- **MIRROR:** PT `main` after #395 (`718ba88` docs included).
- **GOTCHA:** orama tests import the same module; docstring-only change must not break assertions (they key on RFC1918 / https messages).
- **VALIDATE:** `sha256sum` equal; `python scripts/review/verify_model_endpoint_policy_parity.py` PASS with sibling = PT main.

#### Task 2: Pin credentialed httpx (`trust_env=False`)

- **ACTION:** In `PTPipelineClient.run`, pass `trust_env=False` next to `follow_redirects=False`.
- **IMPLEMENT:**

```python
async with httpx.AsyncClient(
    transport=self.transport,
    timeout=timeout,
    follow_redirects=False,
    trust_env=False,
) as client:
```

- **MIRROR:** PT `agent_launcher._pinned_get` (`trust_env=False`, `follow_redirects=False`).
- **IMPORTS:** already `httpx`.
- **GOTCHA:** Tests using `MockTransport` must still work; `trust_env` does not affect mock transport.
- **VALIDATE:** New test: set `HTTP_PROXY` to a LAN URL, `NO_PROXY` empty; handler/mock must receive the request **directly** (or assert mounts empty). Never send `Authorization` to the proxy. Pattern: construct client the same way and inspect `_mounts` / `trust_env`.

#### Task 3: Fail-closed depth

- **ACTION:** Replace `int(raw)` with digits-only (or `raw.isdecimal()` / fullmatch `^[0-9]+$`) and reject values outside `0..MAX`. Invalid → treat as `MAX+1` (existing fail-closed for garbage) **without** calling PT.
- **IMPLEMENT:** Keep the two 409 branches (no refs vs ceiling). Negative and `+1` and `1_0` must **not** become a top-level call.
- **MIRROR:** Current split comments in `api_server.py` 662–665. Do **not** collapse the two errors.
- **GOTCHA:** Empty header remains 0 (true top-level). `int()` currently accepts `-1`, `+0`, underscores.
- **VALIDATE:** Tests with `X-Control-Plane-Depth: -1` (with and without pipeline refs): 409, `PTPipelineClient.run` never called when header present and nested semantics require a gate. Decide: any **present** non-canonical header is invalid (MAX+1). That means `-1` with refs hits ceiling 409; `-1` without refs hits “must supply refs” because inbound_depth >= 1. Document that in the test names.

Recommended semantics (architecturally-correct):

```
missing header     → 0 (top-level)
0                  → 0
1                  → 1 (need refs; forward as 2)
2 or more          → 409 ceiling
anything else      → MAX+1 → 409 (refs: ceiling; no refs: must-use-guarded-route)
```

#### Task 4: Parity checker includes `_is_loopback_host`

- **ACTION:** Add `"_is_loopback_host"` to `policy_functions` for `model_endpoint_url.py`.
- **IMPLEMENT:** Mention in the module docstring of the **parity script** that orama’s copy of `model_endpoint_url.py` must stay byte-identical to PT; do not put that sentence back in the validator.
- **GOTCHA:** PT script is directional (looks for orama sibling). Same function-name tuple must be added on PT in Repo B so both checkers agree.
- **VALIDATE:** Checker still PASS against PT main after Task 1.

#### Task 5: Test union (do not amputate orama layout)

Add orama-style functions if missing coverage for: `file://`, credentials, empty URL, `redact_endpoint_for_log`. Do not delete existing `test_require_tls_flag_*` names.

#### Task 6: Optional CORS

`allow_headers` currently `Authorization`, `Content-Type`. PT uses httpx, not browsers. **Skip unless** a browser client must send `X-Control-Plane-Depth`. Default: skip.

---

## Repo B — Perpetua-Tools (later new PR; #395 is merged)

There is **no open PT PR** as of this plan. Do not reopen or force-push #395. After orama Task 1–4 are on #363 and CI-green, open **one** PT PR from `main`.

### Files to change (PT)

| File | Action | Why |
| --- | --- | --- |
| `orchestrator/fastapi_app.py` | UPDATE | Same fail-closed depth as orama Task 3 |
| `scripts/review/verify_model_endpoint_policy_parity.py` | UPDATE | Add `_is_loopback_host`; identity note in **this** script |
| `config/cross-repo-policy-stacks.json` | UPDATE | After #363 merges, drop or mark the `peer_pull: 363` mapping so CI uses orama `main` |
| `tests/test_orama_bridge.py` and/or pipeline route tests | UPDATE | Depth `-1` / junk header |
| `.agent/memory` / `docs/LESSONS.md` | APPEND only | Record that #363 peer map is retired |

Do **not** touch `src/utils/model_endpoint_url.py` unless a real policy bug appears (none now).

### Tasks — PT

#### Task B1: Depth fail-closed

Today: `int(depth_raw)` then `if depth > MAX`. `-1` is allowed. Align with orama Task 3 (invalid → 422 or 409; pick **one** and match orama’s HTTP shape as closely as PT’s existing 422-for-non-integer vs 409-for-too-deep split allows).

Harmonize: keep PT’s 422 for non-integer (already better than orama’s silent MAX+1) **and** reject negatives as 422. That is api-correct: PT already distinguishes parse error vs ceiling. Orama may keep MAX+1→409 to avoid changing #363’s CONTROL_PLANE_LOOP contract, **or** orama can 422 on parse errors to match PT. Prefer **PT 422 + orama 409 CONTROL_PLANE_LOOP for nested misuse**, but both must reject negatives. Document the remaining status-code difference if kept.

#### Task B2: Parity tuple lockstep

Same `_is_loopback_host` addition. Keep `ORAMA_SYSTEM_ROOT` sibling lookup. Do not copy orama’s `PERPETUA_TOOLS_ROOT` names into PT.

#### Task B3: CI peer map

`config/cross-repo-policy-stacks.json` maps PT branch `fix/pt-pipeline-endpoint-tls-20260917` → orama `cursor/tiered-pipeline-runtime-fb76`. After #363 merges:

- Resolver already designed to return `main` when the peer PR is merged (`8cc3d170`).
- Verify on a PT CI run against `main` that checkout is orama `main`, not a stale branch.
- If the JSON row is only for the merged PT branch name, delete or archive the row so a recycled branch name cannot pin 363 forever.

#### Task B4: Do not regress #395 strengths

Leave `require_tls_for_non_loopback` default False. Leave `orama_bridge` TLS classification. Leave `trust_env=False` on `_pinned_get`. Leave packaged `hosts.py` without `127.` prefix.

---

## Sequencing

```
PT #395 MERGED ────────────────────────────────────────────── already done
orama #363 OPEN
    │
    ├─ this plan file (no product code)
    │
    ├─ CONFIRM
    │
    ├─ Heal commits on cursor/tiered-pipeline-runtime-fb76
    │     copy PT validator
    │     trust_env=False
    │     depth fail-closed
    │     parity tuple
    │     tests
    │
    ├─ CI green on #363
    │
    ├─ Merge #363
    │
    └─ NEW PT PR (only then)
          depth fail-closed
          parity tuple
          retire 363 peer map
```

---

## Patterns to mirror

### NAMING

```python
# SOURCE: src/orama_system/pt_pipeline_client.py
CONTROL_PLANE_DEPTH_HEADER = "X-Control-Plane-Depth"
require_tls_for_non_loopback=True
```

### ERROR_HANDLING

```python
# SOURCE: src/orama_system/pt_pipeline_client.py
except ModelEndpointPolicyError as exc:
    raise PTPipelineError("trusted PT pipeline endpoint is invalid") from exc
# SOURCE: src/orama_system/api_server.py
return JSONResponse(status_code=409, content={"error": "CONTROL_PLANE_LOOP", ...})
```

### HTTP CLIENT

```python
# SOURCE: Perpetua-Tools/src/perpetua_tools/agent_launcher.py:334-338
async with httpx.AsyncClient(
    timeout=timeout,
    transport=_PinnedAsyncHTTPTransport(target),
    follow_redirects=False,
    trust_env=False,
) as client:
```

### PARITY CHECKER

```python
# SOURCE: scripts/review/verify_model_endpoint_policy_parity.py:26-34
_FileSpec(
    "model_endpoint_url.py",
    ("_host_allowed", "validate_model_endpoint_url", "parse_model_endpoint_list"),
)
# ADD: "_is_loopback_host"
```

### TESTS

```python
# SOURCE: tests/test_pt_pipeline_client.py — pytest + httpx.MockTransport + monkeypatch env
# SOURCE: tests/test_api_server.py — @pytest.mark.integration TestClient, FakePipelineClient
```

---

## Testing strategy

### Orama

| Test | Input | Expected |
| --- | --- | --- |
| sha256 validator | PT main vs orama file | equal |
| AST parity + `_is_loopback_host` | sibling PT main | PASS |
| 127 hostname | `http://127.attacker.example:8000` | RFC1918 error |
| TLS flag LAN HTTP | `http://192.168.1.50:8000` + flag | https error |
| loopback HTTP + flag | `http://localhost:8000` | allowed |
| proxy | `HTTP_PROXY` set, loopback base | no proxy hop / no bearer to proxy |
| depth `-1` with refs | header present | 409, run() not called |
| depth `1` with refs | | 200, forwarded depth 2 |
| depth `2` with refs | | 409 |
| missing header, no refs | | existing fallback path |

### PT (later)

| Test | Input | Expected |
| --- | --- | --- |
| pipeline depth `-1` | | 422 or 409, not success |
| parity tuple | orama main after #363 merge | PASS |
| CI map | PT main job | checks out orama main |

---

## Validation commands

### Orama (on #363 branch)

```bash
# file identity
sha256sum src/utils/model_endpoint_url.py
sha256sum ../Perpetua-Tools/src/utils/model_endpoint_url.py

PERPETUA_TOOLS_ROOT="$(pwd)/../Perpetua-Tools" \
  python scripts/review/verify_model_endpoint_policy_parity.py

python -m pytest -q \
  tests/test_model_endpoint_url.py \
  tests/test_pt_pipeline_client.py \
  tests/test_api_server.py

python scripts/review/repo_hygiene.py .
```

EXPECT: hashes equal; parity PASS; tests PASS; hygiene OK.

### PT (later PR)

```bash
ORAMA_SYSTEM_ROOT="$(pwd)/../orama-system" \
  python scripts/review/verify_model_endpoint_policy_parity.py
python -m pytest -q tests/test_orama_bridge.py
```

---

## Acceptance

- [ ] No new orama PR; heals land on #363
- [ ] No PT PR until #363 validator matches PT main and CI is green
- [ ] PT `model_endpoint_url.py` unchanged unless a new policy bug appears
- [ ] Orama validator SHA == PT main SHA
- [ ] `trust_env=False` + proxy test
- [ ] Depth rejects signed/junk headers on orama; PT later matches rejection
- [ ] Parity checks `_is_loopback_host` in both scripts
- [ ] Identity paragraph not reintroduced inside the mirrored file
- [ ] #395 strengths preserved (opt-in TLS, bridge TLS, packaged hosts, CI resolver)
- [ ] #363 strengths preserved (bridge, refs atomic, two 409 modes, no /orchestrate)

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Copying PT file breaks an orama-only comment assumption | Low | Low | Tests don’t parse module docstring |
| `trust_env=False` breaks a documented proxy deployment | Low | Med | Control-plane token must not use HTTP_PROXY; operators use explicit transport |
| Depth semantic change (`-1` used in the wild) | Very low | Low | Header is internal; PT always sends `"1"` |
| Opening PT PR too early vs stale 363 checkout | Med | Med | Sequence: merge/sync orama first |
| Dual parity-script edits diverge again | Med | Med | Same tuple, directional sibling only |

---

## Notes

- Filtered review nits (CORS header list, `parse_model_endpoint_list` not forwarding TLS flag) stay out of default scope.
- This file is the implementation contract for `/prp-implement` after confirmation.
- Downloadable copy: `/opt/cursor/artifacts/pr-363-395-lockstep-heal.plan.md`

**WAITING FOR CONFIRMATION** before any product-code commits: proceed with orama #363 heals? (yes / no / modify)
