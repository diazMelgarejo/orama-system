# M1 qualification groundwork receipt (2026-10-14)

State: **STAGED** (not QUALIFIED, not CANONICAL, not ACTIVATED). Evidence is exploratory: macOS
arm64 only, no
Linux cell, no frozen manifest digest. This receipt records what exists, what was independently
reproduced, and
what is still missing. It claims nothing beyond that and changes no pin, policy or ADR status.

Tags: **V** verified now, **H** historical, **D** design authority, **P** proposal, **U** unverified.

## 1. Scope and decisions in force

- Slice: qualify M1 on the final v2 dependency set; T3 (approval and effect boundary) is **not started**.
- Operator decisions: option A for lost-run takeover (explicit, owner-only, no daemon); external
  sources are
  cited by code only; Ubuntu tooling is authorised as draft PRs, **not** pin promotion and **not** merge.
- Merge freeze stands. Nothing here is merged. Assessment-contract source: S-A1 (sections 18.3 and 18.4).
- Still operator-owned and undecided: DEC-Q-04 (is `unknown` the right operator-facing terminal), DEC-Q-05
  (serving-gap disposition), DEC-E-01 (T3 freeze), and all merges.

## 2. Base identity

| Repo | Main at baseline (V) |
| --- | --- |
| oramasys | 99283f789f078689404653d5105b597e614160b0 |
| perpetua-core | 6d75cfe08af95992dddffab13ae3019aa9c41350 |
| telos | 931b6347142e8e66b31136e3ac8159d86eb5b2f7 |
| agate | 172bfc3ebf00d507856e70d0f6a0e7dbd577ffbc |
| phylax | e41f1e863c65c5f0aae08a6befad21170354b014 |

Production pins (V): core 609ff0ed99cf8eca6c9ef608e764b7a25b6b9973, telos
b2143083044496d93be3ca2dc88c28135e034d9f, agate 41a0da9d52e0131049a1469234ac56f6990fc635. Phylax is
not a
declared dependency. The older Core revision exercised by the core-r3 oracle cell is
34e4a8d22212d38d6ab100c1ad7fb2b19f56cb68 and has no gate seam (V, section 5).

## 3. Deliverables (all DRAFT, none merged)

| Lane | Artifact | Head | Pins / candidate (macOS) | CI |
| --- | --- | --- | --- | --- |
| Option A takeover | oramasys #38 | e1208f7 | 733/2, 749/2 | 11/11 at 8abafa6; re-run pending |
| Agate evidence age | oramasys #39 | 60f691f | 715/2, 741/2 | 11/11 at 6f68acf; re-run pending |
| Schema-3 manifest, data, digest | oramasys #40 | ddd0694 | 811/2, 827/2 | 11/11 at 2eccad1; re-run pending |
| Crash-window tests | oramasys #41 | d15037d | 719/2, 735/2 | 11/11 pass |
| Interaction-risk receipt validator | oramasys #42 | 3f1d8af | 742/2, 758/2 | 11/11 at c2722e1; re-run pending |
| Verify-only grant reader (L2i) | phylax #12 | 76e91e7 | 225 (full Phylax) | 3/3 pass |
| ADR 71 note, takeover entry-point design | orama-system #405 | 128e878 | docs gates | pass at 7f4d5d5; re-run pending |
| Memory graduation (16 lessons) | Perpetua-Tools #442 | a4647ff | repo gates | see PR |

Counts are `passed/skipped`. Exploratory manifest digest of the committed schema-3 candidate:
`002cdece6d38415e8c338c25a071a5c8ec4756fbcc07f4ce83db561fc3b9ac38` (**not frozen**).

## 4. Independence of checking

| Lane | Maker | Independent reproduction |
| --- | --- | --- |
| Option A | claude-main | Codex review rows applied; fresh-context review attempt failed on a session limit (no result); Cline check pending |
| L2i | Codex | Cline reproduced 98 focused and 225 full; claude-main reproduced 225 on the exact head |
| A1 (Telos negatives) | Codex | claude-main read exact-SHA snapshots; source claims confirmed; **no code, no new tests** |
| A3 (wheel cell) | Codex | Cline reproduced the wheel SHA-256; **source-to-wheel provenance not bound** (U) |
| Q2 / schema-3 | claude-main (subagent) | claude-main re-ran suites and digest; Cline check pending |

Fleet verdicts of "verified and ratified" were **not** accepted: local suite counts did not
supersede the
failing oracle cells that were live at the time (section 5).

## 5. Findings during integration (V)

1. Three PRs failed the offline-oracle cells. Two causes, both capability bands, neither a product defect:
   - oramasys #38 and #41: the older Core has no gate seam, so the runner refuses with
     `gate.core_seam_unavailable` and the child never reaches its marker. Fixed by moving the
modules under the
     collect-only-where-seam-exists package.
   - oramasys #39: a module-level skip added one skipped test per cell and exceeded the manifest skip
     allowance (production 2 over 1, core-r3 2 over 1, policy-r3 6 over 5). Fixed by collecting the
package only
     where the capability exists.
2. A peer's root-cause diagnosis (skip budget on all three) was right for #39 and wrong for #38 and
   #41; the job
   logs were the source of truth.
3. A concurrent-pickup attempt on L2i was discarded after a re-diff showed the owner's live
   workspace was
   stricter (private-file checks, no `immutable=1`); no copy was integrated.

### Independent review (fresh-context, read-only, final heads)

Four reviewers read the exact heads. #38, #41 and phylax #12 were approved with LOW notes. #39 was
approved with one MEDIUM (the capability gate could not tell absent from broken) and one LOW (the
age limit produced an allow already expired at the boundary); both were fixed. #40 was REQUESTED
CHANGES (production pins and the consumer SHA were not bound, schema-2 behaviour was not exactly
preserved, the digest script could exit 0 on an unbound digest) and #42 was REQUESTED CHANGES
(probability calibration, authority-claim and independence bypasses). #405 was REQUESTED CHANGES
(a claim attributed to the wrong repository, a stale publication statement, and an effect table
that said no state change). All findings were applied and re-verified by replaying the reviewers'
probes; this is a same-model-family check, not an independent-agent check.

## 6. Control-to-test register

| Control | Proving test(s) | Where | Status |
| --- | --- | --- | --- |
| A lost run is never replayed | `test_reopen_and_recovery_never_replays_a_node`; `test_a_run_killed_in_its_node_gets_a_conservative_terminal_without_replay` | #41; #38 | green |
| Lost run gets a conservative terminal (unknown, `run.process_lost`) | `test_a_run_killed_in_its_node_gets_a_conservative_terminal_without_replay` | #38 | green |
| Only the owner may take over | `test_a_non_owner_is_refused_and_the_run_is_untouched` | #38 | green |
| Takeover fences the original holder | `test_the_original_holder_is_fenced_and_cannot_write_a_second_terminal` | #38 | green |
| Takeover is compare-and-set on the epoch | `test_takeover_is_compare_and_set_on_the_epoch`; `test_a_competitor_that_bumps_the_epoch_after_the_snapshot_is_not_fenced_by_us` | #38 | green |
| Mismatched stores are refused before mutation | `test_mismatched_stores_are_rejected_before_any_state_changes` | #38 | green |
| One terminal, all recoverers converge | `test_two_concurrent_recoverers_converge_on_one_terminal`; `test_a_competitor_that_finishes_first_makes_us_return_its_receipt` | #38 | green |
| A completed run is returned unchanged by takeover | `test_a_completed_run_is_returned_unchanged` | #38 | green |
| A completed run's lease fences a low-level takeover | `test_completed_run_lease_fences_takeover_and_terminal_is_unchanged` (proves the lease seam only, not the command) | #41 | green |
| Killed in sink: settled, no terminal | `test_kill_in_sink_after_node_end_settles_accounting_without_terminal` | #41 | green |
| Stale measurement is refused; expiry capped by its age | `test_a_measurement_older_than_the_window_is_refused_as_stale`; `test_a_decision_never_outlives_its_measurement_even_with_a_long_validity` | #39 | green (candidate Agate only) |
| Schema relabelling cannot satisfy another schema's gate | `test_schema3_relabelled_as_schema2_is_rejected`; `test_schema2_relabelled_as_schema3_is_rejected` | #40 | green |
| Digest binds the manifest | `test_digest_binding_accepts_matching_and_rejects_other` | #40 | green |
| Unknown outcomes can never be omitted from a receipt | `test_unknown_outcomes_cannot_be_omitted` | #42 | green |
| Serving verifier does not call the file seed provider | `test_verify_only_opens_existing_state_without_secret_configuration` (patches `FileSeedProvider.load_seed` only; reviewers confirmed by reading that no other secret path is reachable) | phylax #12 | green, partial |
| Serving verifier is read-only and fails closed | `test_verify_only_uses_read_only_database_and_observes_revocation`; `test_verify_only_fails_closed_without_creating_state` | phylax #12 | green |

### Controls with **no** proving test (each is itself a finding)

| Gap | Note |
| --- | --- |
| Producer-set identity (telos, agate, phylax) | Only the Core record is verified by the install verifier |
| Required-capability collected-versus-skipped gate | Not implemented; schema 3 only forbids skips for final cells |
| Final-producers Ubuntu matrix | No Linux evidence exists |
| Telos expiry and revocation through the real authorizer at the gateway | A1 proposals, unimplemented |
| DNS-pin and TLS-hostname negatives | A1 proposals, unimplemented; no production connector in the gateway path |
| Refusal branches of the verify-only store (symlink, wrong owner, loose mode, sidecars, newer schema) | No test exercises them (phylax #12 reviewer finding, open); a regression dropping a check would pass all 225 tests |
| Serving script wired to `open_grant_verifier` | Not changed; ADR 71 serving gap remains in production (see the ADR note) |
| Workflow matrix covers schema 3 end to end | Workflow YAML untouched |

## 7. Not verified (U)

Linux/Ubuntu; a clean production install of the final producer set; the A3 wheel's source-SHA provenance;
the Windows skip path of the crash-window tests; real read-only mounts or NFS for the verify-only
store; any
claim in this receipt about behaviour beyond the exact heads listed in section 3.

## 8. Rollback

Every item is an unmerged draft: closing the PR is the rollback. No pin, workflow, manifest or ADR status
changed. The ADR 71 note (#405) is append-only.

## 9. Open operator items and next gates

1. Decide DEC-Q-04 and DEC-Q-05; decide merges (still frozen).
2. Provide Linux evidence and bind the A3 wheel to its source SHA before this receipt may move to QUALIFIED.
3. Implement the missing controls in section 6 before T3 starts; T3 needs the E1 freeze (DEC-E-01) first.

## 10. Addendum (appended 2026-10-14; sections 1-9 above are unchanged)

State remains **STAGED**. Nothing here qualifies, activates, re-pins or authorises a merge.

### 10.1 Operator decisions recorded (off-repository record)

| Decision | Disposition | What it does not do |
| --- | --- | --- |
| DEC-Q-04 | `unknown` is retained as the machine outcome; a proven run-level no-attempt is distinguished from an identified attempt whose result is unknown; operator label "Outcome unknown - reconciliation required"; release, replay and retry only through authenticated, idempotent, append-only reconciliation. | Missing evidence is never proof of no attempt. |
| DEC-Q-05 | The verify-only contract treats `verifier.unavailable` as distinct from invalid or revoked; unrelated service stays up, grant-backed requests fail closed with no ledger mutation; same-user and private-mode stay. | It does **not** enable serving; the serving script is still not wired (section 6). |
| DEC-E-01 | Distinct authority is a T3 design invariant; E1 freezes the authority matrix. | T3 code stays paused until the integrated slice, evidence and independent reviewers are ready together. |

The operator also accepted this receipt (X2) and the Perpetua-Tools lesson graduation as staged
snapshots. Acceptance is not merge authorisation; the merge freeze is unchanged.

### 10.2 Verify-only refusal branches: tested now versus still open

The section 6 row "Refusal branches of the verify-only store" is partly closed at phylax #12 commit
`1b4d17a` (tests; each refusal also asserts the durable bytes are unchanged):

| Case | Status |
| --- | --- |
| Missing database in an existing private directory | tested |
| Loose state directory | tested |
| Symlinked database; non-regular database; direct store construction on a missing or symlinked path | tested |
| Loose database mode (not tightened silently) | tested |
| Another owner | tested only by simulating the effective uid; no real foreign-owned file (needs root) |
| Symlinked and loose `-wal`, `-shm`, `-journal` sidecars | tested |
| Newer schema (refused, not migrated) | tested |
| No seed or P5 secret read and no durable write on open and verify | tested |
| Changed or replaced database path after open (`verifier.unavailable`) | tested (earlier head) |
| Stale-revocation-state versus unavailable versus invalid distinction at the Oramasys boundary | **not tested** (no Oramasys composition yet) |
| Real read-only mounts, NFS, non-POSIX permission models | **not tested** |

### 10.3 Stated limit: check, then open

The verifier checks the database path and SQLite then opens that path as a separate step. A
process able to write to the state directory could swap the file in the instant between them.
The identity re-checks before and after connecting narrow this window and do not close it, and the
tests show the checks fire when a swap is visible, not that the instant swap is impossible. The
guarantee therefore holds only while the state directory is private to one user. Closing it
requires retaining the validated connection instead of reopening by path. The same sentence is in
the Phylax docstrings at commit `f09afb7`.

### 10.4 Integration simulation (local, never pushed)

The five oramasys PRs (#40, #39, #38, #41, #42) were merged in that order onto base `99283f7` in
a scratch worktree: no conflicts; 890 passed and 2 skipped in the candidate cell, 863 and 2 in the
production cell, 809 and 2 with the older gate-less Core. Lint findings equal main's baseline.
This is macOS arm64 evidence only; it is not the Ubuntu matrix.
