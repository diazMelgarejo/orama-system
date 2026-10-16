# P0 successor evidence receipt — 2026-10-10

**Status:** staged evidence for review. P0 is **not qualified**: the six-cell manifest and
the clean, non-editable install verifier do not exist yet. This receipt is the single
reference for heads, pins and registry digests; other P0 documents link here.
**Supersedes for current state:** the identifiers scattered across the
[repair handoff](P0-QUALIFICATION-REPAIR-HANDOFF-2026-10-10.md) and
[revision 3](P0-THROUGH-T2-EXECUTION-PLAN-REV3-2026-10-10.md) §1. The
[T0 record](T0-RESTORATION-AND-REGISTRY-BASELINE-2026-10-10.md) stays unchanged as the
dated snapshot of its own commit; this receipt is its successor, not an edit.

Rule: a commit cannot name its own SHA inside itself. Revisions created after this receipt
are recorded by the next successor receipt, not by editing this one.

## 1. Heads read live (2026-10-10 UTC)

| Surface | Full SHA | Role |
| --- | --- | --- |
| Orama `main` (merged #393) | `f5a9e005fb7a980f00ef9d9ff6081b79d86b2fb3` | Canonical R3 registry promoted; archive bytes were reserialized |
| Orama #394, registry-bearing candidate | `8287e40ee99186e8e3937aab8f892f517147d4e7` | Archive repair; the producer revision consumer CI pins |
| Orama #394, last head before this receipt | `997d4143394a3e4e6ee61a47166ba61c4ad67cd4` | Documentation only after `8287e40`; registry blobs identical |
| Oramasys `main` | `f4dbf338138ede5967b4d3456e940750467e9b1f` | Old consumer pair (pre-R3 production Core) |
| Oramasys #26, reviewed head | `566409be45257561ba0fdbc76f94a718af7aaa5c` | Production pin, profiles and byte-identical fixtures staged |
| Oramasys #26, single-pin test | `79d11a91f042d40c1543e85f83adde83dc1e0cdf` | Adds pin-consistency tests; no pin, fixture or registry change |
| Core `main` | `4d217f6b9e94e36554a9427198b8c2c4b7febc47` | Production Core target |

## 2. Pins

| Edge | Pinned value | Where it is enforced |
| --- | --- | --- |
| Consumer CI → Orama registry | `8287e40ee99186e8e3937aab8f892f517147d4e7` | Both Oramasys workflows; one-SHA test on #26 |
| Production → Core | `4d217f6b9e94e36554a9427198b8c2c4b7febc47` | `pyproject.toml`, production lane file, clean-install check, registry `qualification_profile` |
| policy-r3 lane → Core | `04759a50c748444ff97136ea95c1e1289eac3a1a` | Lane file and registry profile (historical schema 1) |
| core-r3 lane → Core | `34e4a8d22212d38d6ab100c1ad7fb2b19f56cb68` | Lane file and registry profile (historical schema 2) |
| Oramasys `main` production → Core | `04759a50c748444ff97136ea95c1e1289eac3a1a` | Unchanged until #26 is merged |

The consumer stays pinned to `8287e40` although #394 has newer heads: those commits change
documentation only, so the registry bytes are identical (§3). Repin once, to #394's actual
merge SHA, then rerun the required cells. Never discover a baseline from Orama `main`.

## 3. Registry digests (SHA-256) and what changed them

| Canonical file | T0 at `bccc152` | Orama `main` `f5a9e00` | #394 `8287e40` and later | Oramasys #26 fixture |
| --- | --- | --- | --- | --- |
| `ownership-registry.json` | `c1bf6b519f703184745e61142f259ae8eb73d163210bb1395437f8a82c2b402f` | `fbde64f2c3b2bec62f703137f5fddb480d502440b9e1b229c15292816b52f7e2` | `fbde64f2…f7e2` | `fbde64f2…f7e2` |
| `ownership-registry-pre-r3.json` | absent | `ab0bcf96099e2bf81ce62138032456d87d0bbf966cf2a2c7bccbab8ea96a6417` | `c1bf6b519f703184745e61142f259ae8eb73d163210bb1395437f8a82c2b402f` | `c1bf6b51…402f` |
| `ownership-registry-policy-r3.json` | `7aeed7456db148383698f6df97a38632dbf72f23d411f9c773ed6cb10ab777fb` | `4972754f7ceb0ad3e908f6583533fec3c59a807732ac86c3ee967df33e29e36f` | `4972754f…e36f` | `4972754f…e36f` |
| `ownership-registry-core-r3.json` | `498e9383667252b841845d4dc061853adfe3e3864d976a3e2f7c8a59eea3adab` | `e270493a7c924871e50fcf384c792a6922a375976127e26214f69b7c89ba9437` | `e270493a…9437` | `e270493a…9437` |

| Change | Revision | Why |
| --- | --- | --- |
| Canonical baseline → R3 production | `c707d8df` (merged in #393) | Promote the reviewed R3 producer/consumer contract: records, literals, decision references and a `production` qualification profile pinned to Core `4d217f6` |
| Pre-R3 archive created | `c707d8df` (merged in #393) | Retain the old baseline as history; it was reserialized, so its bytes differed (`ab0bcf96…`) although its JSON was equal |
| Pre-R3 archive restored | `8287e40e` (#394) | Restore the exact original blob (`e727f384c0e6…`, 4,883 bytes) from `bccc152` |
| policy-r3 and core-r3 | `c707d8df` (merged in #393) | Only `qualification_profile` changed: `production_core_pin` became the lane's own `core_pin` (policy-r3 `04759a5`, core-r3 `34e4a8d` instead of `04759a5`); records unchanged |

Main-to-main parity is broken until #26 merges: Orama `main` holds R3 bytes and Oramasys
`main` still holds the T0 fixtures. Staged-to-staged parity holds for all four files.

## 4. Verification recorded at the heads above

| Check | Result | Counts as P0 qualification? |
| --- | --- | --- |
| #26 CI at `566409b`: tests on 3.11/3.12 and six oracle cells (three profiles × two interpreters) | All green | No: the manifest, exact-cell rejection and install verifier are absent |
| Byte-preservation assertion `test_pre_r3_archive_preserves_the_original_baseline_bytes` (#26) | Present and passing | Supporting only; no surviving record shows it observed failing first |
| Canonical-checkout parity `test_orama_checkout_is_byte_identical` (#26 CI) | Passing against `8287e40` | Supporting |
| Single-pin tests on `79d11a9` (clean venv, non-editable, Core `4d217f6`) | 324 passed, 1 skipped, coverage 88% | Supporting; mutation of a ref or lane SHA fails |
| Orama #394 markdownlint at `997d414` | Passing | Not applicable |

## 5. Open before QUALIFIED

- [ ] Six-cell `requirements/compatibility-manifest.json` with exact-cell rejection.
- [ ] `verify_production_install` with PEP 610 identity and a real graph smoke.
- [ ] All six cells rerun at exact heads, receipts retained.
- [ ] After #394 merges: repin #26 to the merge SHA, rerun, then a new successor receipt.
