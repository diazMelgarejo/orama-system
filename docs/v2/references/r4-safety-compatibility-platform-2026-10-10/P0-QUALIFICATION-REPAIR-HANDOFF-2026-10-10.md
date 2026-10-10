# P0 qualification repair handoff — 2026-10-10

**Status:** staged for review; neither repair is an activation or merge approval.

## Safe published locations

| Repository | Draft PR | Immutable staged revision | Purpose |
| --- | --- | --- | --- |
| `diazMelgarejo/orama-system` | [#394](https://github.com/diazMelgarejo/orama-system/pull/394) | `8287e40ee99186e8e3937aab8f892f517147d4e7` | Restore the archived pre-R3 bytes and publish the revised P0–T2 plan. |
| `oramasys/oramasys` | [#26](https://github.com/oramasys/oramasys/pull/26) | `566409be45257561ba0fdbc76f94a718af7aaa5c` | Stage explicit production selection, original historical pins, the restored fixture, and candidate-pinned CI. |

Both branches were published as additive commits. No branch was force-updated, deleted, rebased, or
merged.

## Corrected evidence

- The original pre-R3 registry is the blob from merged Orama commit
  `bccc1528260e86a854c946d61a3f273aa52b742d`, not a reformatted JSON rendering.
- The restored `ownership-registry-pre-r3.json` and the Oramasys fixture are both exactly 4,883
  bytes with SHA-256 `c1bf6b519f703184745e61142f259ae8eb73d163210bb1395437f8a82c2b402f`.
- Production now selects an explicit baseline; it does not automatically adopt a candidate profile.
- Historical policy-R3 and core-R3 lanes retain their original Core revisions.
- The staged production Core revision is `4d217f6b9e94e36554a9427198b8c2c4b7febc47`.
- Oramasys CI is pinned to the immutable Orama repair candidate above. It must move to the actual
  **merge** SHA only after #394 is accepted.

## Verification captured locally

- The restored archive parses as JSON and matches the digest above.
- The staged Oramasys production test command completed with `335 passed`.
- Authority scan, compile smoke, `pip check`, and `git diff --check` passed. The environment emitted
  stale `~penai` distribution warnings during dependency inspection; `pip check` still reported no
  broken requirements.

## Deliberately not claimed

P0 is not qualified yet. The revision-2 plan requires a versioned six-cell qualification manifest
and proof from a clean, non-editable fresh install. Those records do not yet exist. Code review is
also still required. The staged candidate SHA is evidence for review, not the final canonical merge
identity.

## Next operator sequence

1. Review draft #394 and draft #26, including the required code-review pass.
2. Implement the revision-2 P0 manifest and fresh-install qualification harness; run and retain all
   six cells.
3. Record the results as staged, then qualified. Do not activate either registry state on partial
   evidence.
4. After #394 is merged, update #26 from the candidate SHA to the actual Orama merge SHA; rerun the
   required cells.
5. Merge only after the rerun evidence, reviews, and merge policy succeed. Then write the PT
   continuity record and begin T1 using the revision-2 plan.

## Recovery rule

If a published source or fixture looks wrong, preserve the existing commit as evidence, recover from
the named immutable blob or commit, and publish a successor repair. Do not rewrite historical memory
to make a later interpretation appear original.

## Revision-3 follow-up — 2026-10-10 UTC

The [REV3 execution plan](P0-THROUGH-T2-EXECUTION-PLAN-REV3-2026-10-10.md) now governs
the next sequence. The earlier table records immutable staged revisions, not a promise
that branch heads never advance. At this follow-up's start, #394 was
`d711ce6425f332c24ea04ba34da9dbdefa0768b1`
and #26 was still `566409be45257561ba0fdbc76f94a718af7aaa5c`; both were open drafts.

- Retain the promoted canonical registry (`fbde64f2…`) and repaired archive (`c1bf6b51…`).
  All four staged file pairs match bytes; consumer main remains on the earlier pair.
- Capture a P0.0 drift receipt, then finish the six-cell manifest and clean wheel proof
  before either draft is merged. After #394 merges, pin #26 to that actual merge SHA
  and rerun the required cells before the consumer merge. This corrects any ambiguous
  "after merge, before either merge" wording in prior PR metadata.
- Freeze the unified gate contract; implement the Core seam and T1 step-ledger foundation
  together, then extend delivery, accounting and stop. Preserve structural graph limits.
- An abandoned task cannot gain late commit authority; an unknown hold can be adjusted
  only through authenticated, evidenced, idempotent append-only reconciliation.
- This change is documentation only. Earlier `335 passed` evidence is unchanged;
  no six-cell, fresh-install, runtime gate or termination claim is added here.

Publication uses two logical documentation commits and one final non-force update to
the existing #394 branch. #26 needs no content or pin change for this planning-only
revision: its pinned candidate registry bytes are unchanged. Preserve the uploaded
source and all earlier plans; PT graduation still follows canonical qualification.

## Revision-3 decision record: suggestions not adopted — 2026-10-10 UTC

The attached REV3 synthesis was preserved unchanged as
[review input](P0-THROUGH-T2-REV3-SYNTHESIS-INPUT.md). Its useful mechanisms were
adopted in the active [REV3 plan](P0-THROUGH-T2-EXECUTION-PLAN-REV3-2026-10-10.md):
P0.0 drift receipts, one dispatch gate, trusted callable references, bounded delivery,
single-writer accounting, fencing, and append-only unknown-hold reconciliation. The
following proposals were rejected or narrowed for the stated evidence-based reasons.

| Suggestion or interpretation | Decision | Reason and replacement |
| --- | --- | --- |
| Restore the old pre-R3 registry as Orama `main`'s canonical registry | Rejected | The old bytes are preserved only as the historical archive. Current R3 canonical bytes (`fbde64f2…`) are an intentional merged baseline; replacing them would downgrade schema and fabricate main-to-main parity. Record drift and qualify the staged pair instead. |
| Treat P0 as unstarted because Oramasys `main` retains the old pair | Narrowed | P0 is unqualified, but #26 already stages the consumer changes. Its evidence must be evaluated at its immutable head, separately from `main`. |
| Move or fast-forward a tag to identify the candidate | Rejected | Mutable tag identity defeats provenance and invalidates receipts. Full commit SHAs bind candidate, merge and test evidence. |
| Discover the live producer registry from Orama `main` at consumer runtime | Rejected | Dynamic discovery allows unqualified producer changes to alter consumer behavior. The manifest and workflows pin immutable SHA/digest pairs. |
| Let the prior `335 passed` result, `pip check`, or JSON semantic equality qualify P0 | Rejected | These checks cannot prove all six profile/interpreter cells, clean non-editable installation, PEP 610 source identity, or byte preservation. Retain them only as supporting evidence. |
| Assert a Core `__commit__` or `__version__` field | Rejected | The inspected Core target does not export a reliable field. The clean-install verifier reads pinned package provenance from PEP 610 `direct_url.json` and runs a real symbol/graph smoke. |
| Make Core own Phylax/Agate policy, accounting, or terminal outcome semantics | Rejected | Core needs a neutral gate protocol only. Oramasys authenticates authority, owns policy and durable accounting, and maps delivery uncertainty to terminal outcomes. |
| Keep independent admission, delivery, and budget counters or three competing scheduler seams | Rejected | They can disagree under fan-out, crash or revocation. REV3 consolidates their execution decision into one ordered gate and one hold/settlement source while retaining Core's structural `max_steps` limit. |
| Treat `asyncio.wait_for`, task cancellation, or a thread interrupt as guaranteed termination | Rejected | A callback may suppress cancellation and Python cannot safely kill arbitrary threads. Use bounded waiting, tracked tasks, fence epochs and supported isolation/abort mechanisms; unresolved effects remain `unknown`. |
| Release a crash-time unknown hold automatically | Rejected | A late dispatch or commit could still race release. Reconciliation requires an authenticated, unique, evidenced append-only adjustment after fencing proves the release/settlement cannot race. |
| Infer a last qualified pair from matching files, branch position, or an old pin | Rejected | Qualification needs retained receipts. Until they exist, report the predecessor as unknown rather than inventing a safe activation target. |
| Add a documentation-only change to #26 for REV3 | Deferred as unnecessary | #26 already pins the immutable #394 candidate and its runtime content is unchanged. Updating it would create unrelated churn; it must change only after #394's actual merge SHA exists. |
| Begin PT lesson/memory publication now | Rejected for now | PT continuity follows canonical qualification evidence through its append-only tooling. Planning and staged tests do not establish that evidence. |

This record rejects implementation claims, not historical evidence. Earlier plans and
the uploaded analysis remain readable inputs with dated supersession links.
