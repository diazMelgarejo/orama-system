# C0 merge-content reconciliation — 2026-11-06

**Register row:** C0 in the
[master closure plan](../MASTER-CLOSURE-AND-IMPLEMENTATION-PLAN-2026-11-06.md).
**Scope:** compares the candidate tips named by that plan against the merged
`main` trees of orama-system, Oramasys and Perpetua-Tools. This record is
evidence for C0 only. It is not review, qualification or activation evidence.

## Inputs

- Merge confirmation: the user confirmed on 2026-11-06 that the PRs below merged.
- Push hold: the user released it on 2026-11-06 for one PR per affected repository.
- Comparison method: read-only `git` object comparison in local clones, plus
  read-only GitHub REST reads of the PR records and the current `main` branch heads.
  Nothing was fetched into, pushed to or rewritten in those clones.

## Exact revisions

| Repository | PR | Plan candidate | PR head merged | Merge commit on `main` | First parent (`main` before) | Kind |
| --- | --- | --- | --- | --- | --- | --- |
| `diazMelgarejo/orama-system` | #475 | `6f5112b96b71c018e206cfe15cc6b16b80b6f9a1` | `a485860014520db9d690cd76215ea89607596d8c` | `1a370467725e9f659ffa218fbbee0cf8ec8a0de0` | `c5fcfdf3716ae4d2437b98f251aed73ba22b4299` | two-parent merge commit |
| `oramasys/oramasys` | #93 | `b952dc69fb808244ca22cfc991fd8d29086adbde` | `b952dc69fb808244ca22cfc991fd8d29086adbde` | `2188a9433d5c5d31d746fb50826623028ec54100` | `f89f82c6c8e256378fac0f9b072738f0f28480f1` | two-parent merge commit |
| `oramasys/oramasys` | #94 | — (follow-up after #93) | `0c945f32dcb7e77664238f6cc12a307cba5d79b5` | `fe4049ed75b5adaaadcdcd0fbe5f215e33b2c650` | `2188a9433d5c5d31d746fb50826623028ec54100` | two-parent merge commit |
| `diazMelgarejo/Perpetua-Tools` | #480 | `256f97bc95bb19a67af4fd554098c7f45f4cc03e` | `8c18090842ed18092585c7cc04784e8960022558` | `e4cd20e0c51ad93ae7321f255042c7550a85972a` | `a1e59e50e7dd794584fb5b0cd459924345c0e833` | two-parent merge commit |

GitHub REST reported each PR as `merged=true` with the merge commit above, and
reported these `main` heads at the time of reading: orama-system `1a370467`,
Oramasys `fe4049e`, Perpetua-Tools `e4cd20e`.

## Findings

No PR was squash-merged or rebased. For every merge:

1. the plan candidate is an ancestor of the merged PR head;
2. the merge commit's first parent is an ancestor of the PR head, so `main`
   had no concurrent commits for the merge to combine;
3. the merge commit's tree is byte-identical to the PR head's tree.

| Repository | Candidate in merged history | Merge tree = PR head tree | Tree object |
| --- | --- | --- | --- |
| orama-system | yes | yes | `dfb3a96ed23ae25403dad559470c289b9f0174b2` |
| Oramasys (#93) | yes (candidate is the head) | yes | `97ebb14c80c50d6f7694b59ec0ff829ca14ba225` |
| Oramasys (#94) | n/a | yes | `61d742b3e27547c06aa22712612426b888111270` |
| Perpetua-Tools | yes | yes | `a08af10013a9da71c3dc06b4ffc2672b97cc8eb0` |

### Paths changed after each candidate

orama-system, `6f5112b9..1a370467` (commits `a9e6a673`, `0d029058`, `3dfc78c2`,
`82cf8f1f`, `a4858600`, then the merge):

- `A docs/v2/MASTER-CLOSURE-AND-IMPLEMENTATION-PLAN-2026-11-06.md`
- `M scripts/review/check_architecture_map_parity.py`
- `M tests/test_architecture_map_parity.py`

Oramasys, `b952dc69..fe4049e` (#94 commits `1e80681`, `d5df6ed`, `dbf9d71`,
`ea02aaf`, `0c945f3`, then the merge):

- `M .github/workflows/architecture-map-parity.yml`
- `A docs/MASTER-CLOSURE-HANDOFF-2026-11-06.md`

Perpetua-Tools, `256f97bc..e4cd20e` (commits `1794f80`, `b5ca535`, `f2727eb`,
`8c18090`, then the merge):

- `A .agent/memory/candidates/graduated/1f4dc3245c3f.json`
- `A .agent/memory/candidates/graduated/412331953120.json`
- `A .agent/memory/candidates/graduated/702c622c62f6.json`
- `M .agent/memory/episodic/AGENT_LEARNINGS.jsonl`
- `M .agent/memory/semantic/LESSONS.md`
- `M .agent/memory/semantic/lessons.jsonl`
- `M docs/next/2026-08-23-coordination-consolidation-part3-plan.md`
- `A docs/next/MASTER-CLOSURE-HANDOFF-2026-11-06.md`

These are the later plan, checker and memory commits that went into the same
PRs. They are not omissions.

### Missing candidate content

None found. Every candidate is contained in merged history, and every merge tree
equals its PR head tree. No candidate content was dropped by a squash, a
conflict resolution or a concurrent edit. No local plan commit needs to be
reapplied. Local branches in the read-only clones had no commits beyond their
remote `main`.

### PR inventory

Open PRs at the time of reading, via GitHub REST:

- orama-system: #476 only, a Dependabot `vite` bump in `web/`, unrelated to this
  closure work.
- Oramasys: none.
- Perpetua-Tools: none.

Each affected repository can therefore receive at most one new closure PR from
a branch based on the merged `main` above.

## Limits

- Merge confirmation and the push-hold release are user statements recorded on
  2026-11-06. They do not approve the content of later closure PRs.
- Signature and verification badges were not evaluated. No commit was amended,
  rebased or force-pushed.
- Satellite repositories (Core, Telos, Phylax, Agate, Anamnesis) were not part
  of these merges and were not compared.
