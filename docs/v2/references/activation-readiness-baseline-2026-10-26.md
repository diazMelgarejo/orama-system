# Activation-readiness baseline receipt (2026-10-26)

State: **DRAFT baseline receipt, metadata only.** This is not a merge, not a pin promotion and
not an activation. It records identifiers, digests, counts and statuses observed on 2026-10-26.
It does not enable serving, effects, transport, continuation or autonomous settlement.
`ORAMA_GRANT_SERVING` stays unset. A draft pull request, a green check or this file is not an
activation, enablement or ratification record; those decisions are operator-owned.

Tags: **V** verified now from the named source, **H** historical, **P** proposal, **U** unverified.

## 1. Scope and claim boundary

- Scope: the exact heads of `main` in six repositories, the producer pins the Oramasys `main`
  branch records, the registry and manifest digests of the active compatibility generation, the
  E1 ratification reconciliation, and the candidate pull requests that are open at the time of
  writing (reference only).
- Claim boundary: this receipt says what existed and what was observed. It does not say the set
  is activated, qualified for production, or safe to serve. It does not repeat any evidence run;
  it cites the M1 generation-2 receipt for that.
- Not claimed: Windows, macOS, NFS or read-only-mount behaviour; physical hardware execution;
  any T3 behaviour; any serving behaviour; any release-3-to-5 behaviour.
- M1 generation-2 (see
  [the generation-2 qualification receipt](m1-gen2-qualification-evidence-receipt-2026-10-18.md))
  is **installed-set evidence, not activation**. It shows that one candidate set installed and
  passed its qualification cells. It does not authorize serving or any effect, and this receipt
  does not upgrade it.

## 2. Identity of each `main` head (V)

Source for each row: `gh api repos/<repo>/commits/main`, then
`gh api repos/<repo>/commits/<sha>/check-runs`, read on 2026-10-26.

| Repository | `main` head (full SHA) | Check runs on that head | Legacy statuses |
| --- | --- | --- | --- |
| oramasys/perpetua-core | 6d75cfe08af95992dddffab13ae3019aa9c41350 | 2 total: 2 success | none |
| oramasys/oramasys | a0a3e6728c914521e132fb677c8aaaf2df00cade | 15 total: 15 success | none |
| oramasys/phylax | 31afe7f485bec9d305531d9edc3460ab066dc8c5 | 3 total: 3 success | none |
| oramasys/telos | 931b6347142e8e66b31136e3ac8159d86eb5b2f7 | 2 total: 2 success | none |
| oramasys/agate | 172bfc3ebf00d507856e70d0f6a0e7dbd577ffbc | 2 total: 2 success | none |
| diazMelgarejo/orama-system | cae8bf98819eb6e3fdfb41d08fd007c32dcb0ba0 | 24 total: 24 success | none |

Required-check note (V): the branch-protection query for `main` returned "not protected" in the
five Oramasys-organization repositories and "required status checks not enabled" in
orama-system. No repository therefore defines a required-check set through branch protection,
and the column above reports every check run on the head, not a required subset. A green count
is evidence about that head only.

## 3. Producer pins (V)

Source: `pyproject.toml` on oramasys/oramasys `main` (a0a3e672...).

| Producer | Pinned commit | Relation to that producer's `main` head |
| --- | --- | --- |
| perpetua-core (neutral mechanics) | 6d75cfe08af95992dddffab13ae3019aa9c41350 | equal to `main` |
| oramasys-telos (endpoint policy) | 931b6347142e8e66b31136e3ac8159d86eb5b2f7 | equal to `main` |
| oramasys-agate (hardware eligibility) | 172bfc3ebf00d507856e70d0f6a0e7dbd577ffbc | equal to `main` |
| oramasys-phylax (grant-serving extra) | 0c3e860749b3ff8f62e102679f1f415f8acf0a61 | **lags** phylax `main` |

The phylax pin `0c3e8607...` is the verify-only grant-authority commit recorded in generation
m1-gen2 and in `requirements/compatibility-phylax-verify-only.txt`. Phylax `main` is at
`31afe7f4...`, so the pin does not include everything on phylax `main`. Whether to move it is a
separate pin-promotion decision; this receipt does not make it.

## 4. Registry and manifest digests (V)

Source: `requirements/generations/m1-gen2/generation.json` and
`requirements/ACTIVE-GENERATION.json` on oramasys/oramasys `main`.

| Item | Exact value |
| --- | --- |
| Active generation id | m1-gen2 |
| ACTIVE-GENERATION record_sha256 | 661371f533c9a9f3ec1d9de070580ffaef95076db79597d90de22a81290efb17 |
| Transition receipt | requirements/generations/transitions/0002-activate-m1-gen2.json |
| Registry repository / ref | orama-system / a5bdcd2b76a865e61f0ff2e752550ee73d18f82e |
| Registry digest (sha256) | 1f1531d94f73309f2c3271af41313fd15bf5438ba0a91355ea81111fb66fcb34 |
| Manifest digest | 309d44440d4db0938ed55891ffa5a26768b420033982e6eaf71c1382b1d9a32f |
| Coverage digest | 6af7fa7a02fa6fca3b34ec0eff06a7e281c9b3f92d8de3bbdd4d325f8656b326 |
| Allowlist digest | 6ecbbfe8e65f1e9cc2ee5ddb4077c8e7b57a664cf558403b69d5708da57b2ae0 |
| Inventory digest | 47c7790b0d95eef57f5cb6ad7f86dcae77fb4ae7aa0b0667b2deb86d4479845c |
| Harness commit | 902d2a8edc3fb1b9f7a91fe93a8aca6f4f000100 |
| Consumer commit | 133553a6d05b8704e6e4010f581d57623829f4b2 |
| Evidence run | 39070456148 (artifacts 12114393254 for 3.11, 12114559526 for 3.12) |

The generation file records the three production pins as equal to their candidates and gives the
grant-authority producer a candidate only, with no production pin recorded. That matches the
pin table above: the phylax commit is a pinned extra, not a promoted production pin.

## 5. E1 reconciliation (V, from the R4 reference set)

Each row cites the exact head recorded in the named source. No row says "ratified" without one.

| E1 scope | Status | Exact head | Source |
| --- | --- | --- | --- |
| Parts 1 and 2 | RATIFIED | 59c623fa27497183d3a1c4ed19585d87623eae22 | [ratification addendum][add] |
| Part 3, Section 3.3 | RATIFIED (operator, first packet) | 6459b30e77a6ab22297307374e64dd8872c9b796 | [first packet][pkt] |
| Part 3, Sections 1 and 2 | RATIFIED (operator, 2026-10-24) | 03bf20b77d66c60e0a4d78e7fbb0b245151d0cfb | [S1-S2 matrix][mat] |
| Part 3, Section 3.1 | PENDING | none recorded | [first packet][pkt], [S1-S2 matrix][mat] |
| Part 3, Section 3.2 | PENDING | none recorded | [first packet][pkt], [S1-S2 matrix][mat] |
| Part 3, Section 4 | PENDING | none recorded | [first packet][pkt], [S1-S2 matrix][mat] |

The Parts 1 and 2 addendum states that it excludes Part 3. The S1-S2 matrix states that Sections
3.1, 3.2 and 4 are excluded from that decision, and the first packet states that they remain
unratified. Test matrices for the three ratified Part 3 slices are in the linked packets; this
receipt does not restate them.

[add]: r4-safety-compatibility-platform-2026-10-10/2026-10-19-e1-specification-ratification-addendum.md
[pkt]: r4-safety-compatibility-platform-2026-10-10/E1-C2-PART3-RATIFICATION-ACCEPTANCE-PACKET-2026-10-22.md
[mat]: r4-safety-compatibility-platform-2026-10-10/E1-C2-PART3-S12-ACCEPTANCE-MATRIX-2026-10-24.md

## 6. Open candidate pull requests (reference only, V)

None of these is touched, merged or endorsed by this receipt. Heads were read on 2026-10-26.

| Pull request | State | Head (full SHA) | Note |
| --- | --- | --- | --- |
| oramasys/phylax 22 | open | 0eeae11c62fa06038445c59f7a74cc77a191a826 | effect-grant v2 boundary candidate |
| oramasys/oramasys 77 | open | edf97b658fe896453152109211e187282d3174b0 | readiness and inert driver groundwork |
| diazMelgarejo/orama-system 455 | open | 279cd8d4aab54c2281e85db8fa3d86cccbba6fba | successor of 454 |
| diazMelgarejo/orama-system 454 | closed, not merged | 85f1e9805d5f705cd10a5a621ba42b822b939419 | superseded by 455 |
| diazMelgarejo/Perpetua-Tools 470 | open | 6079829e8652fb8e1febc262de720758468efbcf | documentation candidate |

## 7. Alignment of the executive map with the Release 0 to 2 plan

| Topic | Executive map | Release 0 to 2 plan | Aligned rule |
| --- | --- | --- | --- |
| Wave-2 merges (phylax 20 and 21, oramasys 76, orama 438 and 439, PT 463 and 464) | recommends merging | not addressed | already merged on main; nothing to do |
| Serving switch 2026-11-07 | scheduled activation | no date, merge or CI authorizes | the date is a target for a separate operator decision only |
| P3 composition contract | ratify Part 1 v2 wire | freeze contract before code | build against Part 1 effect-grant v2 (phylax 22 candidate); ratification stays with the operator |
| P8 spec cards (Part 3 Sections 3.1, 3.2, 4) | defer | list pending sections separately | pending; listed separately in Section 5 above |
| Fast-mode exception | adopt allow-path | out of scope | untouched |
| PR shape | not addressed | one new draft per repo | D0 orama off main; D1 stacked on phylax 22; D2 stacked on oramasys 77; D3 telos off main; D4 not opened (Core seam exists); Agate no draft |
| Ledger | not addressed | fresh ledger, fencing and adapter | extend the existing Oramasys attempt store; no second ledger |

## 8. Independence of the records above

| Record | Independent source | Independent of this receipt | What it does not show |
| --- | --- | --- | --- |
| Main heads and check runs | GitHub API read at time of writing | yes (re-runnable) | that a check set is required or sufficient |
| Producer pins | `pyproject.toml` on oramasys main | yes | that a pin is promoted for production use |
| Registry and manifest digests | `generation.json`, `ACTIVE-GENERATION.json` | yes | activation of any capability |
| M1 generation-2 evidence | [generation-2 receipt](m1-gen2-qualification-evidence-receipt-2026-10-18.md) | yes | serving, effects or T3 behaviour |
| E1 ratification heads | R4 reference set, linked above | yes | ratification of the pending sections |
| Capability schema and contract freeze | [contract freeze](r0-r2-contract-freeze-2026-10-26.md) | no, authored with this receipt | anything beyond a draft |

Two independent reviewers at the final candidate heads are still required before any
activation discussion; this receipt does not count as that review.
