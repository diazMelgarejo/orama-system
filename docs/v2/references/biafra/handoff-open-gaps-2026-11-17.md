# Handoff: Biafra open gaps (doc 76) — execution plan for the next agents

Written 2026-11-17 at the end of the lockstep remediation session. Companion to
[doc 76 section 13](../../76-biafra-outer-seat-canonical-plan.md) and the
[remediation record](lockstep-remediation-2026-11-17.md).

> **Current state: read section 9 first.** Sections 0 to 8 are the 2026-11-17 plan, kept as written.
> Since then other agents finished several lanes and the operator ruled on G6 and G11 (2026-11-23).

## 0. State you inherit

| Repo | PR | Branch | Head | State |
| --- | --- | --- | --- | --- |
| Perpetua-Tools (PT, producer, runtime/state authority) | #516 | `2026-11-17-001-biafra-seat-canonical` | `8baf942` | Open, NOT merged |
| orama-system (consumer, stateless) | #519 | `2026-11-17-001-biafra-seat-canonical` | `59a63fd9` | Open, NOT merged; pins PT `1963c7b` in `.github/pt-dispatch-test-ref` |

- G3 and G9 are resolved on #519 (doc 76 §4 and §13). Read doc 76 §13 before anything else.
- Still open in doc 76: **G1, G2, G4, G6, G7, G8, G10, G11.** G5 is out of scope (no `oramasys/*`
  repository is mutated).
- Live gates and serving stay off. Never set `ORAMA_GRANT_SERVING`. Arming one bounded live cycle
  is a separate operator act and is not part of this plan.

## 1. Rules (non-negotiable, from PT `.agent` memory and the operator)

1. Never merge without an explicit operator instruction. Do not push to #516/#519 unless the operator
   says to extend them; otherwise start new dated branches after they merge
   (`2026-11-NN-001-biafra-open-gaps`), **one PR per repo**, **push once per PR**.
2. Collect once, fix the owning abstraction once, failing-first test (RED, then GREEN), docstrings on
   every touched function/class, docstring-only commits proven by `ast.dump` equality.
3. Lockstep: anything that changes a shared contract goes PT first, then orama pins the pushed PT head
   in `.github/pt-dispatch-test-ref`, then orama pushes.
4. PT owns durable state (ledgers, budgets, memory). orama stays stateless.
5. Memory edits are additive only: new linked records with `supersedes`; never rewrite a row.
6. Never edit `docs/v2/references/biafra/live-cycle-2026-11-17/harness/` (preserved evidence).
7. Commit identity `Claude <noreply@anthropic.com>`; no model names; no `Co-authored-by`; no
   workstation paths; markdown wrapped at 100 columns (CI `Changed Markdown` / `Markdownlint-cli2`).
8. A new CRITICAL/HIGH aguara finding in `bin/agents` needs a written justification in
   `config/agent-security/aguara-agents.baseline.md` and operator approval before re-baselining.

## 2. Triage: decide first, then code

Four gaps are operator decisions, two are small code changes, two are blocked on systems that do not
exist yet. Ask the operator **one gate of questions** (Wave A) before writing code.

| Gap | Kind | Blocked on | Minimal fix | Size |
| --- | --- | --- | --- | --- |
| G4 stall window | Decision + 1 constant | Operator: keep 3? | Named constant + test | XS |
| G6 persona draft | Decision (review) | Operator reads SOUL.md | Mark accepted or apply edits | XS |
| G8 `_finite` precision | Decision + guard | Operator: doubles everywhere? | Refuse ints with abs above 2**53 | S |
| G11 Wanda vs Cline W&B | Decision | Operator: which governs? | Additive supersede on the losing side | S |
| G10 metric registry | Code | — | Declared-metric set, refuse unknown names | S |
| G7 provider re-probe | Ops + code | — | Same-day probe record checked in one live preflight (bundle with `read_pin`) | S–M |
| G1 Anamnesis ledger | Blocked | Anamnesis provisioning | Read-only reader protocol only; no storage | M (later) |
| G2 Kungfu atoms | Blocked | Kungfu published, O1–O3 evaluable | Syntactic atom-id check, marked unverified | S (later) |

## 3. Wave A — one operator question gate (no code)

Ask together, record each answer as a `DECISIONS.md` entry in PT memory and a row update in doc 76 §4:

1. **G4:** Keep the stall window at 3 consecutive valid reverts, or set N?
2. **G6:** Accept the persona draft in `bin/agents/metaresearch-outer/SOUL.md` as written
   (including the added boundary "questions the work's assumptions, does not diagnose the
   person"), or give edits?
3. **G8:** Do all consumers compute in IEEE doubles? Recommended answer: tighten anyway — refuse
   integers whose magnitude exceeds 2**53 (exactly representable bound), so no value is silently
   rounded.
4. **G11:** Which governs the W&B route — Wanda's soul card (`bin/agents/wanda/SOUL.md`, Cline CLI
   forbidden) or PT `lesson_8d873e4e2f73` (W&B DeepSeek through Cline)?

## 4. Wave B — code lanes (parallel, one subagent each, isolated worktrees)

Each lane: RED test first, smallest diff, docstrings, report RED/GREEN counts and the commit subject.

### Lane B1 — G4 + G8 (`bin/agents/seat_contracts.py`, orama)

- G4: introduce `STALL_WINDOW = <operator value>` and use it as the `stall_report(trace, window=...)`
  default (`seat_contracts.py:250`). Test: default equals the constant; a trace of N reverts stalls,
  N-1 does not.
- G8 (if the operator accepts the recommendation): in `_finite` (`seat_contracts.py:60`) return False
  for an `int` with `abs(value) > 2**53`; update the docstring. Tests: `2**53` accepted, `2**53 + 1`
  refused, `10**400` refused, floats unchanged. Re-run `tests/test_seat_contracts.py` and the
  `tests/fixtures/mechanism_card/` suite to confirm no fixture relied on huge ints.

### Lane B2 — G10 metric registry (orama, possibly PT-owned data)

- Today `held_out_metric` and `metric_name` accept any identifier (`seat_contracts.py:26, 296`;
  `biafra_cycle.py:63`).
- Minimal fix: a declared set of metric names, seeded from names actually in use:
  `val_bpb_heldout`, `held_out_class_bc_comment_cases` (fixtures) and the live-cycle ledger names
  (`card_validity_and_grounding_failures`, `failed_observed_defect_cases`, `failed_prelaunch_cases`,
  `failed_reviewer_cases`, `failed_verified_defect_cases`, `review_format_violations`).
- Where it lives: if the operator treats the registry as durable policy, it belongs in PT (`config/`)
  and orama reads it — lockstep. Otherwise a frozen constant in `seat_contracts.py`. Ask in Wave A if
  unsure; default to the orama constant (smallest, reversible) and note it.
- `validate_mechanism_card` refuses an unknown `held_out_metric`/`inner_metric`; cycles refuse an
  unknown `metric_name`. Tests: known accepted, unknown refused, error names the field.

### Lane B3 — G7 + the pin TODO (`bin/agents/biafra_cycle.py`, orama)

- One `live_preflight(...)` called by `live_cycle` before the spend gate reservation:
  1. `read_pin(pin_path)` must succeed and equal the evaluator digest (closes the §13.5 TODO
     "live cycle reads no pin").
  2. A provider probe record dated today (model order, effort acceptance, balance where applicable)
     must exist; the probe itself is the read-only model-list call already described in the runbook
     (`live-pair-loop-runbook.md` "Provider re-probe" row). Missing or stale → refuse before any spend.
- No network in tests: inject the probe record. Do not arm anything.

### Lane B4 — G11 (after the operator rules)

- If the soul card governs: add a PT memory lesson that supersedes `lesson_8d873e4e2f73` (additive).
- If the lesson governs: edit `bin/agents/wanda/SOUL.md` to allow the Cline W&B route, citing the
  lesson. Close doc 76 §8.4. Lockstep both repos in one session.

### Lane B5 — G6 docs only

- Apply the operator's edits (if any) to `bin/agents/metaresearch-outer/SOUL.md`; mark G6 Resolved.

## 5. Wave C — blocked (do not start without the dependency)

- **G1 Anamnesis:** when Anamnesis is provisioned, PT (state authority) gains a read-only trace reader
  that validates each entry with the existing trace validator; orama reads through the PT bridge. Until
  then, keep Biafra fail-closed and change nothing. Retrofit map: doc 76 §6.
- **G2 Kungfu:** when Kungfu is published with evaluable O1–O3, cards reference atom revisions and the
  manifest validator becomes the second ownership check. Until then, at most a syntactic atom-id check
  that labels references "unverified". Retrofit map: doc 76 §6.

## 6. Integration and closing

1. Integrator verifies every lane report against the diff and tests (do not trust summaries).
2. Independent read-only reviewer per repo; fix its findings failing-first.
3. Affected suites: `tests/test_seat_contracts.py tests/test_biafra_seats.py tests/test_biafra_cycle*.py
   tests/test_agent_security_baseline.py`; then the full suite against base (expect the same
   environment-only failures listed in §7, nothing new).
4. Lint locally before pushing: `npx -y markdownlint-cli2 <changed .md>` and run
   `aguara scan bin/agents --ci --baseline config/agent-security/aguara-agents.baseline.json`.
5. Update doc 76 §4 rows to Resolved with the decision source, add PT memory (`DECISIONS.md` + linked
   lessons), push PT once, pin, push orama once, update both PR descriptions. Do not merge.

## 7. Known baseline failures (not caused by this work)

The orama full suite in this cloud container shows the same 24 failures at the base `bd5931a2` and at
`fd21122c`; all pass in GitHub CI (`test (3.11/3.12/3.13)` green at `fd21122c`):

- 13 in `test_spawn_dispatch_governance.py` (12) and `test_dispatch_race.py` (1):
  `scripts/spawn_agents.py:199` fails closed with "PT dispatch authority is unavailable: invalid
  editable ownership" because the local PT virtualenv is an editable install owned by another
  checkout ("incomplete editable source").
- 9 in `test_portal_dispatch_errors.py`: the portal loads the same `spawn_agents` module, so the same
  refusal surfaces as HTTP 500 instead of the mapped 403/422/503.
- 2 in `test_markdown_lint_gate.py`: `markdownlint-cli2@0.17.2` is not installed locally.

A new failure outside that set is yours. PT shows 5 environment-only failures (Git state discovery
in the sandbox), identical at base.

## 8. Later TODOs carried over (doc 76 §13.5)

Native macOS kqueue verification; hard wall-clock deadline for the W&B request; route or refuse
`AGENT_PROVIDER=openai` with a W&B `OPENAI_BASE_URL`; redundant `lesson_371473e17ad0`; generic filler
test docstrings; PR-carried memory vs `lesson_94a6ff5363ae`.

## 9. Status update (2026-11-23)

### 9.1 What changed since sections 0 to 8

| Item | State |
| --- | --- |
| Perpetua-Tools #516 and orama #519 | Merged by the operator. |
| G4, G7, G8, G10, the live-cycle pin check | Done on main (doc 76 section 14): `STALL_WINDOW` retained, live preflight (pin plus same-day local evidence), integer guard at 2**53, one metric registry. The generic OpenAI route refuses W&B, and the W&B request runs in a killable worker with parent-owned spend. Lanes B1 to B3 are finished. |
| G6 | Accepted as written by the operator on 2026-11-23. |
| G11 | The operator ruled on 2026-11-23: split by role. Wanda keeps the OpenAI client and her soul card. That client stays outside the spend gate and is not an authorized unattended or paid path. The Biafra seats are designated to use Cline under the shared spend gate once the launcher can bound both total output and request count (`live_cycle()` refuses today). Doc 76 section 15 records both rulings. |
| G1, G2 | Still blocked on Anamnesis and on published Kungfu atoms with evaluable O1 to O3. Change nothing until they exist. |
| 60-day leaf lifetime | Confirmed by the operator as current policy (renewal agreement v2). The Perpetua-Tools `DECISIONS.md` entry records it; reverting would be one constant, `LEAF_VALIDITY_DAYS`, and the tests derive from it. |
| Live activation | Not armed. Still a separate operator act (section 9.3). |

### 9.2 Pull requests (all merged; as of 2026-11-23)

| Repo | Pull request | Merge commit |
| --- | --- | --- |
| Perpetua-Tools | 519, MC2 rescue and LAN peer TLS notes | `97522f2` |
| Perpetua-Tools | 520, the G6 and G11 rulings | `2045bf9` |
| orama-system | 524, Mac peer discovery, TLS startup, the rulings and this handoff | `4caaae20` |
| oramasys | 104, controller service rescue | `4b344626` |

Each repo has one open follow-up, not merged:

| Repo | Pull request | Commits that record the Wanda decision and the port loop |
| --- | --- | --- |
| Perpetua-Tools | 521 | `42f840cb` (decision and lesson correction) |
| orama-system | 525 | `e81d0672` (decision), `d6e5909a` (port loop) |

Later commits can sit on top of these. Read the current tip with `gh pr view` before editing.
Never force-push.

### 9.3 What remains, in order

1. **Review the two follow-up PRs.** Wanda's decision is made: `wanda_chat.py` stays a direct
   OpenAI client, outside the spend gate, and is not an authorized unattended or paid path.
   Do not wrap it in the gate in these pulls. This is a policy, not a guard: nothing in code stops
   it. Two invocation paths were checked: the command in `SKILL.md`, and the `wanda-wandb` agent
   registered in `bin/agents/REGISTRY.yml` (card `bin/agents/wanda/agent.md`). No Perpetua-Tools
   code and no scheduler references either.
2. **Live activation (operator only).** Needs a real task with a reproducing defect, a fixed
   evaluator, `pin_evaluator` run first, named provider, budget, request limit and deadline, a
   same-day read-only provider probe (effort `high` for the V4.1 models), the operator's own
   attestation at the interactive prompt, and the gate variables set for that one command only. The
   code now enforces the pin and the same-day evidence; it cannot do the provider probe or the
   attestation. Stop without retry on a paid-credit demand, a rejected effort, or an existing
   marker file.
3. **Verify what is still unverified:**
   - the PowerShell form of the stdin bearer curl command (only curl 8.5.0 on Linux was tested);
   - `-no-CAstore` on LibreSSL, the macOS system `openssl` (only OpenSSL 3.0.13 was tested);
   - Apple's own `/bin/bash` and macOS userland tools (BSD `sed`, `awk`, `nc`, `openssl`) against
     `start.sh`; only a Linux build of bash 3.2.57 was run (see below);
   - the kqueue exit probe and the 18 macOS-only sandbox tests, never run natively;
   - Windows, for the sandbox and the discovery paths.
   Checked since the last update: `_normalize_port` gives the same result on a real bash 3.2.57 as on
   bash 5 for all 18 test inputs, and the three `start.sh` test files pass under it (67 passed, 2
   skipped; the skips are the PowerShell tests), identical to the control run. A frozen-lockfile
   `pnpm install` (pnpm 10.28.0) for the `qs` pin exits 0, resolves only `qs@6.16.1` and leaves the
   lockfile unchanged. The flush path's
   `_parse_port_remap` reads ports with `int()` and range-checks them, so a zero-padded port is read
   as decimal and an out-of-range one is refused; the old equality bug could only emit an identity
   remap.
4. **Small carry-overs, mostly closed:** `lesson_371473e17ad0` was retracted as redundant (its
   `supersedes` was null, not one id; `lesson_d4ac6209ce38` names it as the same correction and covers
   every point). Fifty generic filler docstrings in four test files now say what each helper does,
   proven docstring-only by AST equality. PR-carried memory overrode `lesson_94a6ff5363ae` for the
   2026-11-17 consolidation only.

### 9.4 Known environment-only failures (not caused by this work)

- orama full suite in the cloud container: 24 failures that pass in CI. Thirteen in
  `test_spawn_dispatch_governance.py` and `test_dispatch_race.py` and nine in
  `test_portal_dispatch_errors.py` come from the spawn guard refusing an editable install owned by
  another checkout. Two in `test_markdown_lint_gate.py` come from `markdownlint-cli2@0.17.2` not
  being installed.
- Perpetua-Tools: 5 failures where Git state discovery fails in the sandbox.
- A new failure outside these sets is yours.

### 9.5 Working practices earned this session

- **Do not trust a bot's claim; test it.** One review said `s_client -CAfile` leaves the default
  trust directory active. A scratch CA pair showed it does not, while `openssl verify -CAfile` does.
  Separately, the 60-day leaf change broke two tests that hardcoded 30 days and had never run in CI.
- **Fetch with an explicit refspec**, for example
  `git fetch origin +refs/heads/X:refs/remotes/origin/X`, then `git merge --ff-only` before you edit.
  A plain `git fetch origin X` leaves no remote-tracking ref. For the same reason, after
  `git push origin HEAD:X` the stop hook can warn of an unpushed commit even though the remote has
  it; check the remote, then run the same fetch to clear the warning.
- **Memory is append-only.** Use `.agent/tools/learn.py` and `.agent/tools/correct_lesson.py`; never
  hand-edit JSONL. Keep literal temp paths and IP literals out of tracked text, because the
  hygiene gate scans the committed range (`--address-diff-base` and `--address-diff-head`).
- **Lint with the pinned tool:** `npx markdownlint-cli2@0.17.2`. Working-memory files under
  `.agent/memory/working/` are excluded from the markdown lint workflow.
- **CI test jobs wait on the hygiene job.** A failing hygiene gate hides test failures, so run the
  tests locally before you push.
- **Edit each file once, commit in logical batches, push once per repo,** and reply to each bot
  thread as `@Bot we fixed this in commit SHA, description`, naming the commit that really fixed it.
- **The platform re-adds a footer** after the attribution lines when a PR description is edited.
- **Worktrees in the cloud container are ephemeral.** Commit and push early
  (`lesson_d93efb48bb52`).
