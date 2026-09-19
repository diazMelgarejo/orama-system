# Plan: Dual-repo lockstep heal after orama #363 + PT #395

**Status:** Plan only — do not implement product code until explicit
confirmation.
**Reuse:** orama-system PR #363 (`cursor/tiered-pipeline-runtime-fb76`).
**PT #395:** MERGED 2026-09-19T12:17:47Z at
`85e1c86cb65499672d2b36decc95a01fc4c53c04`. No open PT PR to reuse.
**Canonical validator blob:** `003ac54187e98f5c38fad5906f9ec1ef43ce6f9e`
(sha256 `c7abdf8dc85d4cc33507d2cfd66d5697c1fc9e74b9316b38cec00c22ccb5cf6e`).
**Method:** orama-system 5-stage + AFRP + CIDF + integrative-merge
(synthesize, never amputate).
**Review pass:** 2026-09-19 criticisms folded in (CI wiring, one HTTP
contract, peer-map window, proxy negative control, depth matrix).

Canonical copies (GitHub, not a VM path):

```text
https://github.com/diazMelgarejo/orama-system/blob/cursor/tiered-pipeline-runtime-fb76/.claude/PRPs/plans/pr-363-395-lockstep-heal.plan.md
https://github.com/diazMelgarejo/orama-system/blob/cursor/tiered-pipeline-runtime-fb76/.claude/plans/pr-363-395-lockstep-heal.plan.md
```

```text
AFRP: Type C | Level Expert | Mode 2
ROLE: Systems architect for L2/L3 lockstep
GOAL: One plan that heals both repos without losing either side
CONSTRAINTS: No product code until confirm; reuse open PR #363;
             PT follow-up is a later PR
```

---

## Gate 0 — live state (re-fetched 2026-09-19)

Do not copy bytes from a moving PT target. This gate is closed:

| Fact | Evidence |
| --- | --- |
| PT #395 state | `MERGED` into `main` |
| Merge commit | `85e1c86c` |
| Orama #363 | `OPEN` on `cursor/tiered-pipeline-runtime-fb76` |
| Copy command | `git show 85e1c86c:src/utils/model_endpoint_url.py` from PT |

PT `main` CI after that merge is **red**, not because the peer branch 404'd,
but because PT `main` checks out **orama `main`**, whose validator AST still
has `startswith("127.")` and lacks `require_tls_for_non_loopback`. That is
the lockstep hole this plan heals. Handoff CI on #363 is otherwise green
except Markdownlint on this plan file (MD013/MD040) — wrap and fence as
part of this edit.

Stage 4 may copy from PT `main` at `85e1c86c`. Re-run this gate if PT
`main` moves before implementation.

---

## Summary

Two lockstep PRs were trying to do one thing: **orama stays stateless, PT
owns guarded pipeline execution, and a control-plane bearer must never ride
cleartext to a non-loopback host — including hostnames that only look like
`127.*`.**

PT #395 merged that policy into canonical
`src/utils/model_endpoint_url.py`. Orama #363 already has the same
**policy functions** and the pipeline bridge, but still has three gaps:

1. `PTPipelineClient` can send the bearer through `HTTP_PROXY`
   (`trust_env` default true).
2. The orama **mirror file** is not byte-identical to PT `main`
   (docstrings only on #363; **orama `main` is still the pre-TLS AST**).
3. Depth parsing accepts signed integers (`-1` skips the loop gate).

PT leftover work **cannot** go onto #395. It needs a **later PT PR**,
sequenced after orama #363 heals.

---

## User story

As a stack operator merging L2/L3 lockstep security work,
I want one harmonized policy file, a bearer client that cannot leak via
proxy, fail-closed depth parsing with **one HTTP contract**, and CI that
cannot skip or AST-blind the mirror,
so that the original #363/#395 threat model actually holds.

---

## Problem → solution

**Now:** Policy AST on #363 matches PT `main`; file SHAs do not. Orama
`main` AST does **not** match, so PT `main` CI fails today. The parity
script **is** invoked from both CI workflows, but it strips docstrings,
omits `_is_loopback_host`, never hashes the file, and **skips** when the
sibling checkout is missing. The new orama client hardened the target URL
and disabled redirects, but not env proxies. Depth uses `int()`.

**Desired:** PT `main` bytes of `model_endpoint_url.py` live on orama #363.
Mirror identity lives *outside* that file. CI fails closed if the sibling
is missing. Parity hashes the validator file **and** AST-checks
`_is_loopback_host`. Credentialed httpx uses `trust_env=False`. Both
repos use the same depth HTTP contract (below). PT CI map stops
pinning PR 363 after it merges.

---

## Metadata

- **Complexity:** Medium (small diffs, cross-repo sequencing)
- **Source PRD:** N/A (review of #363 after #395 merge)
- **Estimated files:** orama ~8–10; PT ~5–7 (later PR)
- **Confidence (single-pass, after confirm):** 8/10

---

## Original intent (re-read of PRs, comments, plans)

### Orama #363 was trying to ship

From `docs/plans/2026-05-29-01-cursor-PLAN.md` P1 and commit `746c1573`:

- Bridge `/oramasys` to PT’s **guarded** `/pipelines/{recipe}/run`,
  never `/orchestrate`.
- PT owns recipes, approvals, budgets, credentials.
- Orama stays stateless.
- Nested control-plane hops must carry pipeline refs; depth is bounded
  (`MAX_CONTROL_PLANE_DEPTH = 2`).
- Env aliases: `ORAMASYS_*` canonical, `ULTRATHINK_*` still documented.

CodeRabbit on #363 then forced two security heals (both resolved on the
PR):

| Finding | Commit | Keep |
| --- | --- | --- |
| Depth ceiling not enforced when refs present | `a88673f7` + tests `ddde337c` | Keep both checks distinct (missing refs vs at-ceiling) |
| Bearer over LAN HTTP to RFC1918 | `4218729f` (opt-in TLS flag) | Keep flag **opt-in**; only pipeline client sets True |
| `127.attacker.example` treated as loopback | `bb3eb7da` (shared lockstep with PT) | Keep ipaddress-only loopback |

Strengths to keep: atomic pipeline refs, recipe alnum/`_`/`-`,
`allow_public=False` even when env allows public model endpoints,
`follow_redirects=False`, replay-empty output allowed,
`_client_safe_detail`, integration markers + annotations on `/oramasys`
tests.

### PT #395 was trying to ship

Canonical side of CodeRabbit Finding 2, plus later heals on the **same**
branch (no second PT PR — that rule still applies to *395*, which is now
closed):

| Commit | Intent | Keep |
| --- | --- | --- |
| `44b67966` | `require_tls_for_non_loopback` default False | Keep opt-in; do not sweep LM Studio/Ollama HTTP |
| `9349998f` / `bb3eb7da` pair | Drop `startswith("127.")` | Keep |
| `718ba88` (coderabbitai) | `_host_allowed` docstring + return line backticks | Keep on canonical file |
| `7f8b834` | `orama_bridge._is_local_oramasys_endpoint` also sets TLS flag | Keep (PT-only) |
| `84cd350` | Bearer HTTPS `url_checker` on remote `ssrf_request`; packaged hosts.py 127 fix | Keep (PT-only) |
| `8cc3d170` | CI checkout of orama **#363 peer**, unquoted `GITHUB_OUTPUT`, no silent main fallback **for open declared peers** | Keep; add merged+404 exception only (Task B3) |
| Memory/lesson commits | Append-only records | Keep; do not rewrite |

Human intent: one PT branch for #395. That does **not** forbid a later
PT PR for *new* follow-ups after merge.

---

## Drift: why, how, when

### Timeline

| When | What | Effect |
| --- | --- | --- |
| 2026-05-25 | Shared validator born (both repos) | Two copies from day one |
| 2026-06-13 | `startswith("127.")` shortcut (orama `6914aa3c`) | Hostname `127.attacker.example` classifies as loopback |
| 2026-08-12 | orama `fde9d460` “sync from PT” | **Orama added** the 7-line “keep it byte-identical” paragraph. PT **never** had that text. AST parity (which **strips docstrings**) stayed green. |
| 2026-09-17 13:08–13:35 UTC | Lockstep TLS + 127 fix on both PRs | Policy functions match **on the PR pair** |
| 2026-09-17 20:05 UTC | PT only: CodeRabbit autofix `718ba88` | `_host_allowed` docstring + return-line backticks. **Never mirrored.** |
| 2026-09-19 12:17 UTC | PT #395 merges | Canonical = PT `main` blob `003ac541…` |
| 2026-09-19 12:18 UTC | PT `main` CI `35442454247` | **FAIL** parity vs orama `main` (still `127.` shortcut, no TLS kwarg) |
| 2026-09-19 review | Orama #363 still `c418645…` file | Policy AST equal to PT; module docstring + `_host_allowed` docs differ |

### Why CI did not catch docstring drift (and what it *did* catch)

`scripts/review/verify_model_endpoint_policy_parity.py` compares AST dumps
of `_host_allowed`, `validate_model_endpoint_url`,
`parse_model_endpoint_list` **after deleting function docstrings**. It
does **not** compare:

- module docstring
- `_is_loopback_host` (the function the TLS flag depends on)
- full-file bytes

Live wiring (confirmed, not assumed):

| Repo | Workflow | What it does |
| --- | --- | --- |
| orama | `.github/workflows/ci.yml` job `docs-pointer-sync` | Checkout PT same-named ref, else PT `main`; run the script if sibling dir exists; **else skip** |
| PT | `.github/workflows/ci.yml` job `git-hygiene` | On PRs, `resolve_orama_policy_ref.py`; declared checkout fail is fatal; on `main` push, checkout orama `main`; run the script if sibling dir exists; **else skip** |

So: CI **does** run the script on both repos. It still cannot see
docstring drift. It **can** see real AST drift — and that is why PT
`main` is red against orama `main` today. The skip-if-missing branch is
the remaining “human remembered to check out a sibling” hole.

Putting “byte-identical” *inside* the mirrored file guarantees drift: PT
will not carry an orama-only identity paragraph.

### What is better from each side

| Piece | Keep | Mode |
| --- | --- | --- |
| Policy functions + `_is_loopback_host` | Freeze by copying **PT `main` file bytes** to orama | 3 / 6 (PT is SSoT) |
| PT `_host_allowed` docstring + return line | Keep (canonical docs) | 3 |
| Orama “do not independently edit” intent | Keep **outside** the mirrored file: parity script header + AGENTS.md | 4 synthesize |
| Orama extra module paragraph inside the file | Do **not** copy into PT | 5 architecturally-correct |
| Orama function-style vs PT class-style tests | Keep **both styles**; union missing *behaviors* | 2 union |
| `trust_env=False` | Copy from PT `agent_launcher._pinned_get` | 6 |
| Distinct 409 reasons (no refs vs ceiling) | Keep orama’s split **messages** | 4 |
| Parse-failure HTTP status | **One contract** (see Task 3 / B1); do not document a permanent 409 vs 422 split | 6 api-correct |
| PT `orama_bridge` TLS + remote bearer HTTPS | Already on PT main | n/a |
| Parity script sibling env paths | Keep directional names | 6 |

---

## Harmonized design (5-stage)

### Stage 1 — Context

PT is runtime/state authority. Orama is a manually synced mirror of
*policy*, not a second parser. #363’s product work (pipeline bridge) is
in scope to **keep**. The heal is vertical-slice contract work:
persistence none, contract = validator + depth header + bearer
transport + CI that cannot skip the mirror.

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

Identity / sync rules live in:
  scripts/review/verify_model_endpoint_policy_parity.py
  .github/workflows/ci.yml (fail closed if sibling missing)
  AGENTS.md endpoint-transport section
NOT in the mirrored module docstring.
```

CIDF: file write in-repo (rank 5 scripting). Decide() before inserting
the identity paragraph anywhere: **do not insert it into the mirrored
file**.

### Stage 3 — Refinement (NOT building)

- Do not open a PT PR whose only job is to make `model_endpoint_url.py`
  match orama.
- Do not require TLS for LM Studio / Ollama / Win coder pool.
- Do not convert orama tests to PT class layout or vice versa.
- Do not rewrite #395 history or reopen #395.
- Do not put workstation paths in the plan or code.
- Do not change PR #363 body (comment-only).
- Do not fold Dependabot PRs #364/#365 into this heal.
- Do not keep a permanent 409-vs-422 split for the same invalid depth
  input.

### Stage 4 — Execution (after confirm)

Two sequenced PRs:

| Order | Repo | Vehicle | Base |
| --- | --- | --- | --- |
| 1 | orama-system | **Reuse #363** `cursor/tiered-pipeline-runtime-fb76` | `main` |
| 2 | Perpetua-Tools | **New PR**, branch ready **before** merging #363 so the map-retirement commit can land in the same sitting | `main` (`85e1c86c` + #395) |

Do not start PT product commits until orama #363 tip is the
byte-identical validator (otherwise PT CI vs #363 is green for the
wrong reason). **Do** prepare the PT branch/map-retirement commit so
PR 363 merge and PT map retirement are the same sitting.

### Stage 5 — Crystallize (after implement)

Append-only lesson: *mirror identity must not live inside the mirrored
blob; parity must include `_is_loopback_host` and a full-file hash;
CI must fail if the sibling checkout is missing; HTTP contracts for the
same invalid input must not diverge on purpose.*

---

## Repo A — orama-system (reuse PR #363)

### Mandatory reading

| Priority | File | Why |
| --- | --- | --- |
| P0 | PT `src/utils/model_endpoint_url.py` at `85e1c86c` | Bytes to copy |
| P0 | `src/orama_system/pt_pipeline_client.py` | TLS call site + httpx client |
| P0 | `src/orama_system/api_server.py` | Depth parser + loop gates |
| P0 | `scripts/review/verify_model_endpoint_policy_parity.py` | AST strip; missing hash / `_is_loopback_host` |
| P0 | `.github/workflows/ci.yml` (`docs-pointer-sync`) | Sibling skip hole |
| P1 | `tests/test_pt_pipeline_client.py` | Add proxy tests with negative control |
| P1 | `tests/test_api_server.py` | Depth matrix |
| P1 | PT `src/perpetua_tools/agent_launcher.py` | `trust_env=False` pattern |
| P2 | `docs/plans/2026-05-29-01-cursor-PLAN.md` | Original pipeline intent |

### Files to change (orama)

| File | Action | Why |
| --- | --- | --- |
| `src/utils/model_endpoint_url.py` | UPDATE | Replace with PT `85e1c86c` bytes |
| `src/orama_system/pt_pipeline_client.py` | UPDATE | `trust_env=False` on `AsyncClient` |
| `src/orama_system/api_server.py` | UPDATE | Fail-closed depth parse + 422 invalid |
| `scripts/review/verify_model_endpoint_policy_parity.py` | UPDATE | `_is_loopback_host` + file hash + identity note |
| `.github/workflows/ci.yml` | UPDATE | Fail if PT sibling missing (no skip) |
| `tests/test_pt_pipeline_client.py` | UPDATE | Proxy positive + negative control |
| `tests/test_api_server.py` | UPDATE | Exhaustive depth matrix |
| `tests/test_model_endpoint_url.py` | UPDATE | Union missing PT behaviors, orama style |
| `AGENTS.md` or CLAUDE.md transport bullet | UPDATE | Mirror is byte-identical; identity in parity script |

### Tasks — orama

#### Task 1: Copy canonical validator

- **ACTION:** From Perpetua-Tools:
  `git show 85e1c86c:src/utils/model_endpoint_url.py` → overwrite orama
  file. Confirm blob `003ac541…` and sha256
  `c7abdf8d…ccb5cf6e`.
- **IMPLEMENT:** No hand-edit of policy logic. Do not re-add the
  “canonical copy” module paragraph.
- **MIRROR:** PT `main` after #395 (`718ba88` docs included).
- **GOTCHA:** orama tests import the same module; docstring-only change
  must not break assertions (they key on RFC1918 / https messages).
- **VALIDATE:** `sha256sum` equal; parity script PASS with sibling = PT
  `85e1c86c`.

#### Task 2: Pin credentialed httpx (`trust_env=False`)

- **ACTION:** In `PTPipelineClient.run`, pass `trust_env=False` next to
  `follow_redirects=False`.
- **IMPLEMENT:**

```python
async with httpx.AsyncClient(
    transport=self.transport,
    timeout=timeout,
    follow_redirects=False,
    trust_env=False,
) as client:
```

- **MIRROR:** PT `agent_launcher._pinned_get`.
- **GOTCHA:** `httpx.MockTransport` as `transport=` **bypasses proxy
  mounts entirely**, whether or not `trust_env` is set. A test that only
  asserts “mounts empty” can pass even if `trust_env=False` is deleted.
- **VALIDATE (pair, not a single assert):**
  1. **Positive:** construct the client the same way as production
     (`trust_env=False`, `HTTP_PROXY` set, `NO_PROXY` empty) and assert
     `client._mounts` is empty **and** `client.trust_env is False`.
  2. **Negative control:** same constructor with `trust_env` left default
     or `True`, same `HTTP_PROXY`, assert `_mounts` is **non-empty**.
     That proves the test is exercising the flag, not MockTransport.
  3. Production `run()` path: never send `Authorization` to the proxy.

#### Task 3: Fail-closed depth — one HTTP contract

Pick **one** contract. Do not leave orama 409 vs PT 422 for the same
parse failure.

**Chosen contract (option b, api-correct):**

| Condition | HTTP | Error code | Who |
| --- | --- | --- | --- |
| Header missing or empty after strip | treat as 0 | n/a | both |
| Header present, not `^[0-9]+$` (includes `-1`, `+1`, `1_0`, `2.0`, junk) | **422** | `CONTROL_PLANE_DEPTH_INVALID` | both |
| Parsed int `> MAX` on **PT** (receive side) | **409** | `CONTROL_PLANE_LOOP` (PT may keep string detail until this PR; add the code) | PT |
| Parsed int `>= MAX` on **orama** (about to increment) | **409** | `CONTROL_PLANE_LOOP` | orama |
| Orama depth `>= 1` and missing pipeline refs | **409** | `CONTROL_PLANE_LOOP` | orama only |

Keep the two 409 **messages** (no refs vs ceiling). Do **not** collapse
them. Do **not** use 409 for parse failures.

`>=` vs `>` is **not** drift: orama increments before forwarding; PT
validates the received value. `MAX=2` means orama allows inbound 0 and 1
(forwards 1 and 2); PT allows received 0, 1, and 2; both refuse 3+.

- **ACTION:** Replace `int(raw)` with fullmatch `^[0-9]+$`. Invalid →
  422 `CONTROL_PLANE_DEPTH_INVALID`, never call PT.
- **GOTCHA:** Empty header remains 0 (true top-level). `int()` currently
  accepts `-1`, `+0`, underscores.

##### Exhaustive matrix (`MAX = 2`)

| Header | Refs | Orama | PT | `run()` / pipeline |
| --- | --- | --- | --- | --- |
| missing | no | 0, existing top-level path | implicit 0, proceed | orama may call PT |
| missing | yes | 0, refs present, not nested gate | proceed | may call |
| `0` | no | 0, not nested | proceed | may call |
| `0` | yes | 0, not nested | proceed | may call |
| `1` | no | 409 LOOP (must supply refs) | proceed (PT does not require orama refs) | orama: never |
| `1` | yes | 200, forward header `2` | proceed (`2 > 2` is false) | called |
| `2` | no | 409 LOOP (must supply refs; checked first) | proceed (`2 > 2` false) | orama: never |
| `2` | yes | 409 LOOP (ceiling, `>= 2`) | proceed | orama: never |
| `3` | yes or no | 409 LOOP (orama: refs check first if `>=1` without refs; else ceiling) | 409 LOOP (`3 > 2`) | never |
| `-1` | yes or no | **422** INVALID | **422** INVALID | never |
| `+1` | yes or no | **422** INVALID | **422** INVALID | never |
| `1_0` | yes or no | **422** INVALID | **422** INVALID | never |
| `abc` / `2.0` / ` ` (non-empty junk) | yes or no | **422** INVALID | **422** INVALID | never |

Whitespace-only after strip is **missing**, not junk.

#### Task 4: Parity checker includes `_is_loopback_host` + file hash

- **ACTION:** Add `"_is_loopback_host"` to `policy_functions` for
  `model_endpoint_url.py`.
- **ACTION:** For that file only, also compare sha256 of the full bytes
  (this is what catches module-docstring drift). Keep AST compare so a
  function-level diff stays readable. Leave `endpoint_policy_core.py` on
  AST-only unless a later contract says otherwise.
- **IMPLEMENT:** Mention in the **parity script** docstring that orama’s
  copy of `model_endpoint_url.py` must stay byte-identical to PT; do not
  put that sentence back in the validator.
- **GOTCHA:** PT script is directional. Same function-name tuple **and**
  hash rule must be added on PT in Repo B so both checkers agree.
- **VALIDATE:** Checker PASS against PT `85e1c86c` after Task 1.

#### Task 4b: CI must not skip the sibling (highest-leverage)

Confirmed: the script already runs in CI. The hole is `if [ -d sibling
]; then … else echo skip`.

- **ACTION:** In orama `.github/workflows/ci.yml` `docs-pointer-sync`,
  if `perpetua-tools-sibling` is missing after both checkout attempts,
  **fail the job**. Do not `continue-on-error` the PT `main` fallback
  into a skip.
- **IMPLEMENT:** Keep same-named-ref first, then PT `main` (already the
  “main first after miss” shape orama uses). Fail closed on the last
  miss.
- **GOTCHA:** Forks without `diazMelgarejo/Perpetua-Tools` visibility
  will go red. That is acceptable for this private lockstep pair; do not
  re-introduce skip for origin PRs.
- **VALIDATE:** A CI log line must show the parity script ran, not
  `skip: Perpetua-Tools not available`.

This task outranks Tasks 1–3 for preventing the next silent docstring
drift. Implement it in the same #363 batch, after Task 1 so the hash
check is green.

#### Task 5: Test union (do not amputate orama layout)

Add orama-style functions if missing coverage for: `file://`,
credentials, empty URL, `redact_endpoint_for_log`. Do not delete
existing `test_require_tls_flag_*` names.

#### Task 6: Optional CORS

`allow_headers` currently `Authorization`, `Content-Type`. PT uses
httpx, not browsers. **Skip unless** a browser client must send
`X-Control-Plane-Depth`. Default: skip.

---

## Repo B — Perpetua-Tools (later new PR; #395 is merged)

There is **no open PT PR**. Do not reopen or force-push #395. Open
**one** PT PR from `main`, with the map-retirement commit **ready
before** merging #363.

### Files to change (PT)

| File | Action | Why |
| --- | --- | --- |
| `orchestrator/fastapi_app.py` | UPDATE | Digits-only parse; 422 `CONTROL_PLANE_DEPTH_INVALID`; reject negatives |
| `scripts/review/verify_model_endpoint_policy_parity.py` | UPDATE | `_is_loopback_host` + file hash; identity note |
| `.github/workflows/ci.yml` | UPDATE | Fail if orama sibling missing on `main` push (today it ran and failed AST — keep that strictness; do not skip) |
| `scripts/review/resolve_orama_policy_ref.py` | UPDATE | 404 + peer PR `merged` → `main` only |
| `config/cross-repo-policy-stacks.json` | UPDATE | Drop or archive `peer_pull: 363` in the same sitting as #363 merge |
| `tests/test_orama_bridge.py` and/or pipeline route tests | UPDATE | Depth matrix 422/409 |
| `tests/test_resolve_orama_policy_ref.py` | UPDATE | merged+404 → main; open declared 404 still fails |
| `.agent/memory` / `docs/LESSONS.md` | APPEND only | Record that #363 peer map is retired |

Do **not** touch `src/utils/model_endpoint_url.py` unless a real policy
bug appears (none now).

### Tasks — PT

#### Task B1: Depth fail-closed (same contract as Task 3)

Today: `int(depth_raw)` then `if depth > MAX`. Non-integers already 422;
`-1` is allowed. Align with the matrix: digits-only; negatives 422
`CONTROL_PLANE_DEPTH_INVALID`; ceiling 409 `CONTROL_PLANE_LOOP`.

FastAPI `detail` may be a dict `{"error": "CONTROL_PLANE_DEPTH_INVALID",
"detail": "..."}` so clients can match orama’s JSON `error` field.

#### Task B2: Parity tuple + hash lockstep

Same `_is_loopback_host` addition and sha256 of
`model_endpoint_url.py`. Keep `ORAMA_SYSTEM_ROOT`. Do not copy orama’s
`PERPETUA_TOOLS_ROOT` names into PT.

#### Task B3: CI peer map + merged+404 exception

`config/cross-repo-policy-stacks.json` maps PT branch
`fix/pt-pipeline-endpoint-tls-20260917` → orama
`cursor/tiered-pipeline-runtime-fb76`.

**Clarify the review’s timing-gap claim:** Dependabot PRs #364/#365 do
**not** use that JSON key. PT `main` pushes already check out orama
`main`. `8cc3d170` already returns `main` when GitHub says peer pull
**merged**. The real post-merge liability is: #363 lands, GitHub deletes
the orama feature branch, a **stale PT PR still named**
`fix/pt-pipeline-endpoint-tls-20260917` runs, `fetch_pull_merged` lags
or 404s, resolver still asks for the deleted orama branch, declared
checkout fails closed.

**Correction (narrow exception, not a silent main guess):**

1. Have the PT map-retirement commit ready to merge in the **same
   sitting** as #363.
2. Resolver: if declared `peer_ref` checkout returns 404 **and** the
   GitHub pull `peer_pull` has `"merged": true`, then check out
   `main`. This is categorically different from “could not resolve, so
   guess main.”
3. If the pull is **open** (or merge state cannot be read), keep
   fail-closed. Do not weaken `8cc3d170` for open declared peers.
4. After #363 merges, delete or archive the JSON row so a recycled
   branch name cannot pin 363 forever.

#### Task B4: Do not regress #395 strengths

Leave `require_tls_for_non_loopback` default False. Leave `orama_bridge`
TLS classification. Leave `trust_env=False` on `_pinned_get`. Leave
packaged `hosts.py` without `127.` prefix.

---

## Sequencing

```text
PT #395 MERGED @ 85e1c86c  ── already done
PT main CI red vs orama main AST ── expected until #363 merges
orama #363 OPEN
    │
    ├─ this plan file (no product code)
    │
    ├─ CONFIRM
    │
    ├─ Heal commits on cursor/tiered-pipeline-runtime-fb76
    │     copy PT validator @ 85e1c86c
    │     trust_env=False + proxy negative control
    │     depth 422 INVALID / 409 LOOP matrix
    │     parity tuple + file hash
    │     CI fail if sibling missing
    │     tests
    │
    ├─ Prepare PT follow-up branch (map retirement + B1–B3)
    │     do not merge PT first
    │
    ├─ CI green on #363
    │
    ├─ SAME SITTING: merge #363 AND merge PT map-retirement
    │
    └─ Remainder of PT PR if not already in that sitting
          depth contract
          parity tuple + hash
          merged+404 exception
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
# SOURCE (after Task 3): src/orama_system/api_server.py
# 422 {"error": "CONTROL_PLANE_DEPTH_INVALID", ...}  parse failures
# 409 {"error": "CONTROL_PLANE_LOOP", ...}           refs / ceiling
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
    ("_host_allowed", "validate_model_endpoint_url",
     "parse_model_endpoint_list", "_is_loopback_host"),
)
# ADD: sha256 of that file’s bytes (not of endpoint_policy_core.py)
```

### TESTS

```python
# SOURCE: tests/test_pt_pipeline_client.py
#   pytest + construct real AsyncClient (not only MockTransport)
#   positive trust_env=False empty mounts; negative trust_env=True nonempty
# SOURCE: tests/test_api_server.py
#   @pytest.mark.integration TestClient, FakePipelineClient
#   one test per matrix row
```

---

## Testing strategy

### Orama

| Test | Input | Expected |
| --- | --- | --- |
| sha256 validator | PT `85e1c86c` vs orama file | equal `c7abdf8d…` |
| AST parity + `_is_loopback_host` | sibling PT `85e1c86c` | PASS |
| 127 hostname | `http://127.attacker.example:8000` | RFC1918 error |
| TLS flag LAN HTTP | `http://192.168.1.50:8000` + flag | https error |
| loopback HTTP + flag | `http://localhost:8000` | allowed |
| proxy positive | `trust_env=False`, `HTTP_PROXY` set | empty `_mounts`, `trust_env is False` |
| proxy negative | `trust_env=True`, same `HTTP_PROXY` | **non-empty** `_mounts` |
| depth matrix | every row in Task 3 table | status + `run()` called/not |
| CI sibling | missing checkout | job fails, no skip |

### PT (later)

| Test | Input | Expected |
| --- | --- | --- |
| depth matrix | same invalid rows | 422 INVALID, not success |
| ceiling `3` | | 409 LOOP |
| parity hash | orama after #363 merge | PASS |
| resolver | declared open + 404 | fail closed |
| resolver | declared merged + 404 | `main` |
| CI map | PT main job | checks out orama main; script runs |

---

## Validation commands

### Orama (on #363 branch)

```bash
sha256sum src/utils/model_endpoint_url.py
sha256sum ../Perpetua-Tools/src/utils/model_endpoint_url.py

PERPETUA_TOOLS_ROOT="$(pwd)/../Perpetua-Tools" \
  python scripts/review/verify_model_endpoint_policy_parity.py

python -m pytest -q \
  tests/test_model_endpoint_url.py \
  tests/test_pt_pipeline_client.py \
  tests/test_api_server.py

python scripts/review/repo_hygiene.py .
npx markdownlint-cli2 \
  .claude/PRPs/plans/pr-363-395-lockstep-heal.plan.md \
  .claude/plans/pr-363-395-lockstep-heal.plan.md
```

EXPECT: hashes equal; parity PASS; tests PASS; hygiene OK; lint OK.

### PT (later PR)

```bash
ORAMA_SYSTEM_ROOT="$(pwd)/../orama-system" \
  python scripts/review/verify_model_endpoint_policy_parity.py
python -m pytest -q \
  tests/test_orama_bridge.py \
  tests/test_resolve_orama_policy_ref.py
```

---

## Acceptance

- [ ] No new orama PR; heals land on #363
- [ ] Gate 0 re-checked: PT #395 still merged; copy from pinned SHA if
      `main` moved
- [ ] No PT product merge until #363 validator matches PT main and CI
      is green; PT **map-retirement** is staged for the same sitting
- [ ] PT `model_endpoint_url.py` unchanged unless a new policy bug
      appears
- [ ] Orama validator SHA == PT `85e1c86c` SHA
- [ ] `trust_env=False` + proxy positive **and** negative control
- [ ] Depth: both repos 422 `CONTROL_PLANE_DEPTH_INVALID` on junk /
      signed / underscores; 409 `CONTROL_PLANE_LOOP` for refs/ceiling
      only
- [ ] Parity checks `_is_loopback_host` **and** file sha256 in both
      scripts
- [ ] Orama (and later PT) CI **fails** if sibling checkout is missing
- [ ] Identity paragraph not reintroduced inside the mirrored file
- [ ] #395 strengths preserved (opt-in TLS, bridge TLS, packaged hosts,
      fail-closed for **open** declared peers)
- [ ] #363 strengths preserved (bridge, refs atomic, two 409 messages,
      no `/orchestrate`)
- [ ] No workstation-only download path in this file

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Copying PT file breaks an orama-only comment assumption | Low | Low | Tests don’t parse module docstring |
| `trust_env=False` breaks a documented proxy deployment | Low | Med | Control-plane token must not use HTTP_PROXY |
| Depth semantic change (`-1` used in the wild) | Very low | Low | Header is internal; PT always sends `"1"` |
| Changing orama parse failures from 409 to 422 | Low | Low | Header is internal; tests pin the new code |
| Opening PT PR too early vs stale 363 checkout | Med | Med | Byte-identical validator on #363 first; same-sitting map retirement |
| Dual parity-script edits diverge again | Med | Med | Same tuple + same hash rule, directional sibling only |
| Fail-closed sibling checkout breaks forks | Low | Low | Accept for this pair |

---

## What the 2026-09-19 review got right (do not regress)

- SSoT direction (PT `main` bytes → orama, not the reverse).
- Identity lives in the parity script, not the mirrored blob.
- `require_tls_for_non_loopback` stays opt-in.
- Test-union of styles, not a style fight.

## What this pass changed vs the previous plan

1. Re-fetched PT #395: merged; copy pin is `85e1c86c`.
2. Confirmed parity **is** in CI; added Task 4b (fail if sibling missing)
   and full-file hash so docstring drift cannot go green again.
3. One HTTP contract: 422 `CONTROL_PLANE_DEPTH_INVALID` vs 409
   `CONTROL_PLANE_LOOP`. No documented-forever split.
4. Peer-map: same-sitting retirement + merged+404→main only; Dependabot
   is not on that JSON key; PT `main` red is AST vs orama `main`.
5. Proxy negative control required.
6. Exhaustive depth matrix.
7. Canonical URL is GitHub, not `/opt/cursor/artifacts/…`.

---

## Notes

- Filtered review nits (CORS header list,
  `parse_model_endpoint_list` not forwarding TLS flag) stay out of
  default scope.
- This file is the implementation contract for `/prp-implement` after
  confirmation.

**WAITING FOR CONFIRMATION** before any product-code commits: proceed
with orama #363 heals? (yes / no / modify)
