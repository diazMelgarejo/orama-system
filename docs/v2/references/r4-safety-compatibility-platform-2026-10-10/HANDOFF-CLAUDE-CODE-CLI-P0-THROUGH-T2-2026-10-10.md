# Handoff for Claude Code CLI — P0 through T2 (2026-10-10)

**Purpose:** let the next agent continue exactly where this session stopped, without
re-deriving state. Read sections 1 to 3 before touching anything. Everything here was read
live on 2026-10-10 UTC; re-read heads before acting, because branches move.

**Hard rules (non-negotiable):**

- The agent never merges. The operator merges; if a merge is blocked, report it, never work
  around it. Never force-push, delete branches or rewrite history.
- Security invariant: tracked content names categories only. No private identity, email,
  credential, device or endpoint address, or workstation path literals. Exact values live in
  an off-repo registry loaded at runtime; tests use synthetic values.
- GitHub through REST only (`gh api`); GraphQL is blocked. Review threads and draft state use
  the `ccr` routes under `/pulls/{n}/ccr/`.
- Commit author `Claude <noreply@anthropic.com>`; follow the newest attribution trailers in
  the session. Dated branches `yyyy-mm-dd-NNN-brief-summary`. Orama docs: run
  `python3 scripts/review/repo_hygiene.py .` before committing; markdownlint MD013 is 100
  columns (tables, headings, code blocks exempt).
- `git fetch origin main` alone leaves `origin/main` stale. Use
  `git fetch origin '+refs/heads/main:refs/remotes/origin/main'`.
- CodeRabbit allows one included review per hour and skips drafts. Verify each finding
  against current code; fix only still-valid ones.

## 1. Where things stand

| Item | State | Link |
| --- | --- | --- |
| Orama #392, #393, #394 | Merged. `main` is `28672bf3…` with the canonical R3 registry and restored pre-R3 archive bytes | [#394][o394] |
| Perpetua-Tools #432, #434 | Merged (R3 compatibility entry; entry recording merged SHAs) | [#432][pt432] |
| Oramasys #26 | Merged. `main` is `9e90ac4c…`: production Core pin, six profiles, manifest, clean-install verifier | [#26][y26] |
| Oramasys #27 | **Open, CI 8/8 green at `b6e99dc7…`.** Per-cell result gate, manifest schema 2, review findings fixed; one security thread (action pinning) left open for the operator | [#27][y27] |
| Orama #395 | **Open draft.** Receipts 2 and 3 plus this handoff | [#395][o395] |
| Core `main` | `4d217f6b…` — the production Core pin | [perpetua-core][core] |

**P0 is not QUALIFIED.** Evidence, pinned to commits: [receipt 3][r3] (snapshot at
`84f64cc3…`; a later receipt supersedes it), [receipt 2][r2], [receipt 1][r1]. Main-to-main registry parity and CI on both mains
are verified.

## 2. First actions (in order)

1. Re-read live state: PR states of Oramasys #27 and Orama #395, both mains, CI on each head.
2. If Oramasys #27 is merged: confirm CI on the merge commit; the gate is then live on `main`.
3. Ask the operator to require the eight check names in branch protection (two `test` jobs
   and six oracle cells: production, policy-r3, core-r3 × Python 3.11, 3.12). The agent cannot
   set this and must not claim it is done.
4. After the operator merges #395 and #27, verify green post-merge CI on both mains, then
   write receipt 4 recording the final heads. The state machine in [PLAN-P0][planp0] ends at
   ACTIVATED (operator-merged consumer SHA plus green post-merge verification): mark it only
   then, publish the dated Orama closure, and only after that add the Perpetua-Tools
   correction (its WORKSPACE state block still says the P0 plan is unpublished).
5. Do not start T1 code before step 4 is recorded in full. T1 stays gated.

## 3. What exists and where

| Concern | Location |
| --- | --- |
| Single Core pin test, producer-SHA test, README recipe guard | [`src/tests/test_compatibility_pins.py`][pins] |
| Six-cell manifest and validator | [`requirements/compatibility-manifest.json`][manifest], `src/orama/compat/manifest.py` |
| Clean install proof (PEP 610, symbols, graph smoke) | [`scripts/verify_production_install.py`][verifier] |
| Oracle matrix and result gate | [`compatibility-oracles.yml`][oracles], `scripts/verify_cell_results.py` (#27) |
| Registry fixtures (byte-identical to Orama) | `src/tests/fixtures/graph-ownership-registry*.json` |
| Reproduction recipe per lane | [`tests/oracles/README.md`][oracleready] |

Core identity is proved by the PEP 610 `direct_url.json` record, because Core exports no
commit or version attribute. Editable overlays and candidate checkouts are oracle evidence
only, never the production-install proof. Historical lanes (policy-r3 `04759a50…`, core-r3
`34e4a8d2…`) keep their original Core revisions; a historical Core lacks `ReducerSpec` and
`JoinSpec`, so real-Core tests gate on `ORAMA_REQUIRE_CORE_R3`.

## 4. Roadmap to T2 (the plan of record is [revision 3][rev3])

Revision 2 is superseded. Each task: reproduce a named failing invariant, implement the
minimal reviewed change, run focused and affected suites, review the diff, one logical batch.

### P0 — finish qualification (current)

- Remaining checklist is section 2. Exit: receipt 4, QUALIFIED then CANONICAL recorded,
  rollback path (old pair stays active until the new pair qualifies) untouched.
- Release protocol and rollback: [REV3 §3 P0.3][rev3].

### T1 — executable identity and admission lifecycle ([REV3 §4][rev3])

- Freeze canonical encodings, clock and expiry policy, provider interfaces and the neutral
  `DispatchGate` protocol in Core; Oramasys implements it. Fixed gate order: authority and
  lease, stop, delivery health, budget. Contract: [CONTRACT-DISPATCH-GATE][gate].
- Tests first: `os:system`, dotted lookup, aliases and unknown keys are rejected without
  fallback; stale policy and non-Observed evidence refuse; expiry or revocation between
  admission and node dispatch, and before reducer execution, refuses.
- Guard actual execution boundaries inside the one scheduler (`CompiledGraph._run`) through
  a neutral reviewed hook. Fake providers live in test-only packages excluded from the wheel;
  production refuses when no real provider is configured.
- Owners do not move: Core protocol, Oramasys implementation, Phylax decides adjustment
  authority, Telos secures endpoints. See [durable HITL contract][hitl] for clock policy.

### T2-A — bounded neutral observation delivery ([REV3 §5][rev3])

- Ordered event identity `(run_id, sequence)`, detached payloads, bounded FIFO queues for
  non-critical sinks (enqueue never blocks the scheduler). Critical sinks acknowledge
  explicit persistence boundaries, not every streamed token.
- Tests: slow telemetry does not delay nodes; mutation isolation; ordered sinks; async
  callbacks never block the loop; retain task references and use `asyncio.wait` with a
  timeout for async critical delivery. R3 settle-all semantics and one drain are preserved;
  no observer schedules nodes.

### T2-B — single-writer accounting and cooperative stop ([REV3 §6][rev3])

- One SQLite accounting writer with fencing, unique run and attempt keys, integer units,
  WAL with `synchronous=FULL`, outcomes completed/interrupted/cancelled/refused/budget/unknown.
- Frozen contracts (do not re-open without the operator): three-step commit publication
  (durable `CommitIntent`, synchronous fenced publish with no `await`, idempotent
  settlement); all-or-nothing batch reservation for fan-out; Phylax-issued single-use
  adjustment grants consumed transactionally and validated against the hold's **remaining
  balance**. All in [CONTRACT-DISPATCH-GATE][gate].
- Subprocess crash tests at each window (before reserve, after hold, after start marker,
  after intent, after publish). Recovery never replays the attempt. Unknown holds are never
  released automatically.
- Honest guarantees only: cooperative stop with a 1000 ms grace; no claim that cancelled
  work stopped; `ainvoke(loaded_state)` restarts at START and is not durable continuation.

### Out of scope until T2 is qualified

T3 effect grants, T4 provider transport, T5 durable continuation, remote workers, and any
exactly-once delivery claim.

## 5. Gotchas that cost time already

- A hand-written CI matrix can silently lose a cell; the manifest plus result gate exist to
  prevent that. Do not add a second pin table; extend the single-pin tests instead.
- `ainvoke` on a loaded state is a fresh traversal. Do not describe it as resume.
- Mutable refs (branch names, tags, discovered baselines) never count as evidence. Pin full
  SHAs; a commit cannot name its own SHA, so the next receipt records it.
- Terminal summary of a merged PR can lag; verify with `gh api repos/{o}/{r}/pulls/{n}` and
  the check-runs endpoint, not the UI.

[o394]: https://github.com/diazMelgarejo/orama-system/pull/394
[o395]: https://github.com/diazMelgarejo/orama-system/pull/395
[pt432]: https://github.com/diazMelgarejo/Perpetua-Tools/pull/432
[y26]: https://github.com/oramasys/oramasys/pull/26
[y27]: https://github.com/oramasys/oramasys/pull/27
[core]: https://github.com/oramasys/perpetua-core/commit/4d217f6b9e94e36554a9427198b8c2c4b7febc47
[r1]: https://github.com/diazMelgarejo/orama-system/blob/28672bf366e5a4a6917f2cb9236eaf696e70c97b/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/P0-SUCCESSOR-EVIDENCE-RECEIPT-2026-10-10.md
[r2]: https://github.com/diazMelgarejo/orama-system/blob/84f64cc3334167c8391571a686606b4a5ad9174b/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/P0-SUCCESSOR-EVIDENCE-RECEIPT-2-2026-10-10.md
[r3]: https://github.com/diazMelgarejo/orama-system/blob/84f64cc3334167c8391571a686606b4a5ad9174b/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/P0-SUCCESSOR-EVIDENCE-RECEIPT-3-2026-10-10.md
[rev3]: https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/P0-THROUGH-T2-EXECUTION-PLAN-REV3-2026-10-10.md
[gate]: https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/CONTRACT-DISPATCH-GATE.md
[hitl]: https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/CONTRACT-DURABLE-HITL-EFFECTS.md
[planp0]: https://github.com/diazMelgarejo/orama-system/blob/main/docs/v2/references/r4-safety-compatibility-platform-2026-10-10/PLAN-P0-CORE-PIN-PROMOTION.md
[pins]: https://github.com/oramasys/oramasys/blob/main/src/tests/test_compatibility_pins.py
[manifest]: https://github.com/oramasys/oramasys/blob/main/requirements/compatibility-manifest.json
[verifier]: https://github.com/oramasys/oramasys/blob/main/scripts/verify_production_install.py
[oracles]: https://github.com/oramasys/oramasys/blob/main/.github/workflows/compatibility-oracles.yml
[oracleready]: https://github.com/oramasys/oramasys/blob/main/tests/oracles/README.md
