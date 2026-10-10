# P0 successor evidence receipt 3 — 2026-10-10

**Status:** staged evidence for review. Oramasys #26 is merged and the merged pair is
tested. P0 is **not yet QUALIFIED**: the result-file gate ([Oramasys #27][pr27]) is open,
and branch protection does not yet require the eight check names. This receipt supersedes
the heads of [receipt 2](P0-SUCCESSOR-EVIDENCE-RECEIPT-2-2026-10-10.md); earlier receipts
stay unchanged as history.

## 1. Heads read live (2026-10-10 UTC)

| Surface | Full SHA | Role |
| --- | --- | --- |
| Orama `main` | `28672bf366e5a4a6917f2cb9236eaf696e70c97b` | Merged #394; producer revision |
| Oramasys `main` | `9e90ac4c4d6f880f0cebf25cb17db18545c2e11b` | Merged #26: production Core pin, manifest, verifier |
| Oramasys #27 | `2d265ac7da0b44fdf4ffafa3258c7a2fb9a35e3a` | Result-file gate, manifest schema 2 |
| Core `main` | `4d217f6b9e94e36554a9427198b8c2c4b7febc47` | Production Core, pinned by Oramasys `main` |

## 2. Main-to-main parity (actually measured)

The four canonical registry files on Orama `main` and the four fixtures on Oramasys `main`
have identical SHA-256 digests (first 16 hex): `fbde64f2c3b2bec6`, `c1bf6b519f703184`
(pre-R3, original bytes), `4972754f7ceb0ad3`, `e270493a7c924871`. CI on Oramasys `main`
at the merge commit: eight of eight checks pass (two `test` jobs, six oracle cells).

## 3. Result gate at Oramasys #27 `2d265ac`

Per-cell allowances measured from the green matrix: production and core-r3 378 passed and
1 skipped; policy-r3 362 passed and 5 skipped. Floors are 360 and 345 passed. Eight of
eight checks pass with the gate enforced and a JUnit receipt retained per cell.

## 4. Open before QUALIFIED

- [ ] Operator merges Oramasys #27; the gate then runs on `main`.
- [ ] Branch protection requires the eight check names.
- [ ] Operator merges Orama #395 so receipts 2 and 3 reach `main`.
- [ ] Mark P0 QUALIFIED/CANONICAL only after the above; then PT memory correction.

[pr27]: https://github.com/oramasys/oramasys/pull/27
