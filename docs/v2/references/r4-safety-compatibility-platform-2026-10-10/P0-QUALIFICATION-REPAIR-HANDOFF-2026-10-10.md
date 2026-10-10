# P0 qualification repair handoff — 2026-10-10

**Status:** staged for review; neither repair is an activation or merge approval.

## Safe published locations

| Repository | Draft PR | Immutable staged revision | Purpose |
|---|---|---|---|
| `diazMelgarejo/orama-system` | [#394](https://github.com/diazMelgarejo/orama-system/pull/394) | `8287e40ee99186e8e3937aab8f892f517147d4e7` | Restore the archived pre-R3 bytes and publish the revised P0–T2 plan. |
| `oramasys/oramasys` | [#26](https://github.com/oramasys/oramasys/pull/26) | `566409be45257561ba0fdbc76f94a718af7aaa5c` | Stage explicit production selection, original historical pins, the restored fixture, and candidate-pinned CI. |

Both branches were published as additive commits. No branch was force-updated, deleted, rebased, or merged.

## Corrected evidence

- The original pre-R3 registry is the blob from merged Orama commit `bccc1528260e86a854c946d61a3f273aa52b742d`, not a reformatted JSON rendering.
- The restored `ownership-registry-pre-r3.json` and the Oramasys fixture are both exactly 4,883 bytes with SHA-256 `c1bf6b519f703184745e61142f259ae8eb73d163210bb1395437f8a82c2b402f`.
- Production now selects an explicit baseline; it does not automatically adopt a candidate profile.
- Historical policy-R3 and core-R3 lanes retain their original Core revisions.
- The staged production Core revision is `4d217f6b9e94e36554a9427198b8c2c4b7febc47`.
- Oramasys CI is pinned to the immutable Orama repair candidate above. It must move to the actual **merge** SHA only after #394 is accepted.

## Verification captured locally

- The restored archive parses as JSON and matches the digest above.
- The staged Oramasys production test command completed with `335 passed`.
- Authority scan, compile smoke, `pip check`, and `git diff --check` passed. The environment emitted stale `~penai` distribution warnings during dependency inspection; `pip check` still reported no broken requirements.

## Deliberately not claimed

P0 is not qualified yet. The revision-2 plan requires a versioned six-cell qualification manifest and proof from a clean, non-editable fresh install. Those records do not yet exist. Code review is also still required. The staged candidate SHA is evidence for review, not the final canonical merge identity.

## Next operator sequence

1. Review draft #394 and draft #26, including the required code-review pass.
2. Implement the revision-2 P0 manifest and fresh-install qualification harness; run and retain all six cells.
3. Record the results as staged, then qualified. Do not activate either registry state on partial evidence.
4. After #394 is merged, update #26 from the candidate SHA to the actual Orama merge SHA; rerun the required cells.
5. Merge only after the rerun evidence, reviews, and merge policy succeed. Then write the PT continuity record and begin T1 using the revision-2 plan.

## Recovery rule

If a published source or fixture looks wrong, preserve the existing commit as evidence, recover from the named immutable blob or commit, and publish a successor repair. Do not rewrite historical memory to make a later interpretation appear original.
