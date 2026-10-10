# P0 successor evidence receipt 2 — 2026-10-10

**Status:** staged evidence for review. P0 is **not yet QUALIFIED**: the consumer pair is
tested at its final producer revision, but the merged consumer pair does not exist until
Oramasys #26 merges. This receipt records state after Orama #394 merged and supersedes the
heads and pins of [receipt 1](P0-SUCCESSOR-EVIDENCE-RECEIPT-2026-10-10.md); that file stays
unchanged as the snapshot of its own commit.

## 1. Heads read live (2026-10-10 UTC)

| Surface | Full SHA | Role |
| --- | --- | --- |
| Orama `main` (merged #394) | `28672bf366e5a4a6917f2cb9236eaf696e70c97b` | Canonical registry with the restored pre-R3 archive; the producer revision for consumer CI |
| Oramasys #26, repinned head | `6a43697674eb454d7c0f2797a0565cefd7907f34` | Manifest, install verifier, README recipe fix, producer pin at the merge SHA |
| Oramasys `main` | `f4dbf338138ede5967b4d3456e940750467e9b1f` | Unchanged: old consumer pair until #26 merges |
| Core `main` | `4d217f6b9e94e36554a9427198b8c2c4b7febc47` | Production Core target (unchanged) |

## 2. Registry digests on Orama `main`

All four canonical files match the Oramasys #26 fixtures byte for byte (first 16 hex shown;
full values are in receipt 1 §3): `ownership-registry.json` `fbde64f2c3b2bec6`,
`-pre-r3` `c1bf6b519f703184` (original archive bytes restored), `-policy-r3`
`4972754f7ceb0ad3`, `-core-r3` `e270493a7c924871`. The pins in receipt 1 §2 still hold except
the producer pin, which is now the `main` merge SHA above, never a branch or discovered tip.

## 3. Verification at Oramasys #26 `6a43697`

| Check | Result |
| --- | --- |
| `test` jobs on Python 3.11 and 3.12 (clean production install, verifier from outside the checkout, coverage gate) | Pass |
| Six oracle cells: production, policy-r3, core-r3 × 3.11, 3.12 | All pass |
| Manifest: exactly six cells; missing, duplicate, extra, mispinned, unknown-key and workflow-drift mutations rejected | 22 tests pass |
| Install verifier: PEP 610 identity, editable and non-git rejection, location, symbols, graph smoke | 17 tests pass; CLI passes for `4d217f6…` and fails for `04759a5…` |

## 4. Open before QUALIFIED

- [ ] Result-file gate: reject a cell that ran zero tests or skipped more than its measured
  allowance (policy-r3 legitimately skips R3 suites).
- [ ] Branch protection requires all eight check names, so no cell can be dropped.
- [ ] Operator merges #26; then test the merged Oramasys `main` against Orama `main`
  (main-to-main parity) and record receipt 3 with the merge SHA.
- [ ] Only then: PT memory correction and graduation; T1 stays gated.
