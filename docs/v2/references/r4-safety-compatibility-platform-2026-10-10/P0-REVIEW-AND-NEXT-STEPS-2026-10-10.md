# P0 review and post-P0 execution roadmap

**Date:** 2026-10-10 UTC. **Status:** corrected implementation design; P0 qualification in progress.
AFRP: Type C | Level Practitioner | Mode 2.

The [P0 implementation plan](PLAN-P0-CORE-PIN-PROMOTION.md) incorporates the corrections
below. This addendum records their rationale; it does not claim P0 qualification, automated
review, merge or enablement. Runtime implementation starts with the bounded test, fixture,
workflow and pin work described there. Agents never merge.
The [parent plan](PLAN-R4-EXECUTION.md) remains the capability and dependency authority.

## 1. Fresh prerequisites

Read from GitHub during this review, rather than inferred from conversation state:

| Surface | Revision | Disposition |
| --- | --- | --- |
| Orama #392 | `bccc1528260e86a854c946d61a3f273aa52b742d` | Merged 2026-10-10 08:31:31 UTC |
| PT #432 | `8cdd4926ed20aacdc5bb04dc0a84d93ce05bfba3` | Merged 2026-10-10 08:32:08 UTC |
| Core main | `4d217f6b9e94e36554a9427198b8c2c4b7febc47` | Recommended immutable production target |
| Oramasys main | `f4dbf338138ede5967b4d3456e940750467e9b1f` | Production Core still pre-R3 |
| Oramasys #22 | `e0a9b5294cdcbda187030ccd63ecb6e6d890ac66` | Open draft; knowledge portal, not pin/fixture/workflow overlap |

Core main tree remains `0890ef970ab26fa7982ea15fc235c0fe9d1a603f`.
Oramasys main tree remains `579fd199ff254345d2f3e4dd99c65ae2720f741f`.
The three canonical registry blobs on merged Orama main equal the corresponding
Oramasys fixture blobs. Recomputed canonical SHA-256 digests remain:

| Profile | SHA-256 |
| --- | --- |
| baseline | `c1bf6b519f703184745e61142f259ae8eb73d163210bb1395437f8a82c2b402f` |
| policy-r3 | `7aeed7456db148383698f6df97a38632dbf72f23d411f9c773ed6cb10ab777fb` |
| core-r3 | `498e9383667252b841845d4dc061853adfe3e3864d976a3e2f7c8a59eea3adab` |

This proves current T0 registry parity, not P0 qualification. T0 restoration and
registry refresh are narrower than the parent T0 requirement inventory and typed-record
freeze; do not mark all T0 or M0 complete from the restoration record alone.

## 2. Review findings and recommended decisions

### R1: Make the cross-repository order acyclic

The registry is canonical in Orama, not Core. No Core change is needed for P0.
The draft's Oramasys-first publication followed by Orama evidence is incomplete:
Oramasys CI must pin an immutable Orama commit containing the promoted canonical registry.

Use one Orama PR for the P0 plan and proposed canonical registry promotion. Preserve
the old baseline bytes in a historical file and leave both candidate profiles intact.
After qualification and review, the operator merges this canonical record. The
Oramasys promotion PR pins that exact merged Orama revision in both workflows.
The Orama merge alone is a normative registry step, not runtime promotion.
The consumer pin, fixture, digest, assertions and workflows move in one Oramasys
commit batch; partial consumer promotion is a defect.

Final qualification evidence cites the exact tested Oramasys head before its merge.
A later dated closure record cites the operator's merged SHA. Never insert a
not-yet-existing merge SHA into a record or edit T0 to make it appear current.
PT memory follows canonical evidence and records only observed states.

### R2: Production conformance must actually select the promoted baseline

`src/tests/test_ownership_registry.py` currently selects a candidate using
`HAS_R3`, regardless of the production dependency. Its explicit candidate assertion
still names the old production pin. A manifest-only promotion could therefore pass
candidate tests without proving the new baseline.

Add an explicit qualification profile and test the baseline by default.
Invalid/missing required profiles and absent canonical checkout fail the required
lane. Record the immutable installed Core identity separately from the profile.
Keep candidate status and historical pin assertions limited to historical lanes.
Mutation tests must detect a wrong baseline digest, stale pin, missing canonical
fixture, wrong profile and planned fields that are actually implemented.

### R3: Keep historical lanes separate from production

The policy-r3 fixture describes schema-1 Core plus policy restrictions; it cannot
be tested as a schema-2 production baseline without rewriting history.
Run policy-r3 against historical pre-R3 Core `04759a50c748444ff97136ea95c1e1289eac3a1a`.
Run core-r3 against its recorded candidate `34e4a8d22212d38d6ab100c1ad7fb2b19f56cb68`.
Run the promoted baseline against the reviewed merge target `4d217f6b9e94e36554a9427198b8c2c4b7febc47`.

All required profile-specific cells must run. A capability intentionally outside a
historical profile is explicitly not applicable, not an accepted silent skip.
Production requires R3 and cannot use the candidate overlay to satisfy the pin gate.

### R4: Inventory all live assertions and pinned checkouts

| Existing Oramasys path | Required treatment |
| --- | --- |
| `pyproject.toml` | Promote production Core to the full merge SHA |
| `.github/workflows/ci.yml` | Pin merged canonical Orama revision; require production R3 |
| `.github/workflows/compatibility-oracles.yml` | Separate production and historical candidate proof |
| `src/tests/fixtures/graph-ownership-registry.json` | Exact promoted canonical bytes |
| `src/tests/test_ownership_registry.py` | New baseline digest, explicit lane and fail-closed canonical parity |
| `src/tests/test_perpetua_graph_spec.py` | Review the old validation revision; update active claims, retain historical fixtures |
| `src/tests/test_policy_restrictions_core_r3.py` | Required R3 in production; no silent module skip |
| `requirements/compatibility-core-candidate.txt` | Retain immutable historical test-only candidate |
| `requirements/compatibility-oracles-py312.txt` | Inspect install compatibility; change only with a demonstrated need |
| `README.md`, `docs/COMPATIBILITY_REVIEW_2026-10-09.md` | Dated qualification update; preserve historical statements |

This is a verified initial map, not permission to assume there are no other pins.
Re-run tracked-file inventory on the exact execution heads before editing.
Orama owns `ownership-registry.json` and its historical baseline archive;
Oramasys owns the byte-identical consumer fixture and all runtime/CI assertions.

### R5: Clean installation cannot use an overlay as its identity proof

Use a new environment, disable installation cache, install the committed consumer
manifest and record the dependency install's immutable source revision. Run
`pip check` before suites. `--no-deps -e core-candidate` is an oracle overlay,
not proof that the production manifest resolved the new pin.

Prove schema-1 graph IDs remain stable, schema-2 is used only for R3 graphs,
settle-all/name-ordered/atomic local-only R3 semantics, and loaded-state
`ainvoke` still restarts at START. Run complete affected native and offline
oracle suites on supported Python 3.11 and 3.12 lanes. Record actual commands,
counts and environment identities, never historical totals as fresh results.
Qualify a disposable combination with surviving Oramasys #22 before claiming
combined-branch compatibility; do not merge #22 or adopt its unrelated features.

## 3. What happens immediately after P0

| Order | Work | Owner | Exit gate before the next capability |
| --- | --- | --- | --- |
| 1 | Complete scoped T0 requirement disposition and freeze T1/T2 interfaces | Orama authority + owning repos | Reviewed exact fields, versions, outcomes, failure taxonomy and tests |
| 2 | T1 artifact admission and policy binding | Oramasys; Phylax and Agate owning interfaces | Fail-closed real admission before indexing; no authority from callable strings |
| 3 | T2 neutral observation delivery | Core | Detached payloads, ordered single drain, visible telemetry failure, critical persistence blocks progress |
| 4 | T2 terminal policy and run-wide accounting | Oramasys | Cancellation stops next dispatch; budgets survive retries, nesting and restart |
| 5 | M1 closure | Orama evidence then PT memory | Merged P0 plus qualified T1 and T2; statuses distinguish tested/published/merged/enabled |
| 6 | T3 approval/effect transaction spine | Oramasys | Versioned store, CAS, scoped grants, outbox, crash/revocation/restart tests |
| 7 | T4 transport and T5 continuation | Oramasys + Core neutral protocols + Telos authority | Qualified effect reconciliation and true continuation, not replay at START |
| 8 | T6/T7 and selected T8/T9; T10 last | Contract-specific owners | Parent milestones and per-slice reviews, no blanket parity or exactly-once claim |

T1 and T2 may be designed together after their scoped T0 freeze; they remain separate
reviewable slices and must not implement against undefined or moving interfaces.
No provider sandbox, production egress, H1/H2 deployment or new external credentials
are implied by approval to open a P0 PR.

## 4. PR strategy and execution state

- One active logical PR per affected repository. This Orama PR carries the corrected
  canonical P0 plan and registry promotion. The paired Oramasys P0 PR carries the exact
  consumer pin, fixture, test and workflow update.
- #22 is unrelated and is not a substitute promotion branch. Qualify its resulting combined
  tree in a disposable check before claiming compatibility.
- PT #432 is merged; never push to it again. A new PT memory PR follows observed
  canonical evidence, uses memory tooling, and preserves every historical JSONL byte.
- No Core PR for P0. T2 is the next justified Core slice, after interface review.
- One final publication per repository per approved implementation batch. Orama
  before PT. Guard non-force ref updates and independently fetch the remote tree.
- Rollback by reviewed revert/forward commits. Canonical registry and runtime
  consumer have separate commits; reverting the consumer restores its old pinned
  canonical checkout. Do not claim a single commit can revert all repositories.

**Operator review remains required before merge:** verify the target revision, profile matrix,
clean-install evidence and new dated P0 evidence record. Until then, neither PR is enabled.
