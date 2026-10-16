# P0 successor evidence receipt 4 — 2026-10-10

**Status:** final heads recorded. The Core `4d217f6b…` production pin is **ACTIVATED**
in Oramasys: the operator merged the consumer change and post-merge CI is green on both
`main` branches. One operator item remains open (section 3). This receipt supersedes the
heads of [receipt 3](P0-SUCCESSOR-EVIDENCE-RECEIPT-3-2026-10-10.md); earlier receipts
stay unchanged as history.

## 1. Heads read live (2026-10-10 UTC)

| Surface | Full SHA | Role |
| --- | --- | --- |
| Orama `main` | `792f4744391b4f984a1f3eccb8ca67f058c0aaa0` | Merged #395: receipts 2–3, handoff |
| Oramasys `main` | `fa6e1e37dfaeb9fb12ac6b3f9656a3a0d8479fa4` | Merged #27: result-file gate, schema 2 |
| Core `main` | `4d217f6b9e94e36554a9427198b8c2c4b7febc47` | Production Core, pinned by Oramasys `main` |

## 2. Post-merge verification

- Oramasys `main` at `fa6e1e37…`: eight of eight checks pass (two `test` jobs, six oracle
  cells) with the result-file gate enforced.
- Orama `main` at `792f4744…`: 23 checks pass; the `skill-scanner` job was still
  running when read and is not counted.
- Registry digests are unchanged from receipt 3 (`fbde64f2c3b2bec6`, `c1bf6b519f703184`,
  `4972754f7ceb0ad3`, `e270493a7c924871`).

## 3. Still open (operator)

- [ ] Branch protection on Oramasys `main` is off (API reports unprotected). Require the
  eight check names: two `test` jobs and the six oracle cells.
- [ ] Greptile security thread on #27 (action pinning): other actions still use movable
  major tags. Operator decision.

T1 stays gated; nothing here authorises it.
