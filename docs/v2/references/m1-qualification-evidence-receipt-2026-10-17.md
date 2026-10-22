# M1 qualification evidence receipt (2026-10-17)

State: **EVIDENCE RUN PASSED; receipt published on operator instruction. Amended 2026-10-17
(section 8): operator acceptance recorded and the fresh independent runtime review reported.**
This is not a qualification claim, not a pin promotion, not a merge and not an activation. It
records metadata only (identifiers, digests, counts, statuses). No retained record content is
reproduced here.

Tags: **V** verified now, **H** historical, **D** design authority, **P** proposal, **U** unverified.

## 1. Operator instruction and scope

- The operator's instruction on 2026-10-17, quoted: "Run 38916773943 passed, Publish metadata-only
  receipt PR now!" This receipt records that run and nothing broader.
- Formal evidence acceptance, pin promotion, merges, serving activation and E1 ratification remain
  operator-owned and are **not** performed or implied by this document.
- Claim boundary: GitHub-hosted Ubuntu, Python 3.11 and 3.12, installed-set qualification evidence
  of the candidate set at the consumer commit below. Not Windows, macOS, NFS or read-only mounts; not
  physical-hardware execution of the hardware profiles (fixtures only); not calibrated SWARM
  population risk; not production install or pin promotion; not T3 behaviour; Phylax is
  composition-only and not a default dependency.

## 2. Identity (V)

| Item | Value |
| --- | --- |
| Repository / PR | oramasys/oramasys, qualification PR 45 |
| Harness commit H | 3332b615668d4040ff9d0e8cc0d888870e6160fa (branch cline/pr45-consumer-ancestry-20261016, PR 46) |
| Consumer commit C | f8898b35d5249e483b2f4a68c097957e675a0ef4 |
| Consumer wheel sha256 | d7be7fe398fd1e86567e717f2f1725a48381d553798bf32ef20e4d140f484340 |
| Workflow run | 38916773943, attempt 1, mode evidence, event workflow_dispatch |
| Run conclusion | success: freeze-gate, final-producers (3.11), final-producers (3.12) |
| Freeze approval comment | [PR 45 comment 6217460696](https://github.com/oramasys/oramasys/pull/45#issuecomment-6217460696) |
| Manifest digest | 4892b6ba9894eee0e85deae3dcbb020a82f3afb55fadc7424f2a3cfa2dd6bae2 |
| Coverage digest | 6af7fa7a02fa6fca3b34ec0eff06a7e281c9b3f92d8de3bbdd4d325f8656b326 |

Producers installed from the frozen install plan (V, from identity.json in the sealed record):

| Producer | Distribution | Commit |
| --- | --- | --- |
| endpoint-policy | oramasys-telos | 931b6347142e8e66b31136e3ac8159d86eb5b2f7 |
| grant-authority | oramasys-phylax | 0c3e860749b3ff8f62e102679f1f415f8acf0a61 |
| hardware-eligibility | oramasys-agate | 172bfc3ebf00d507856e70d0f6a0e7dbd577ffbc |
| neutral-mechanics | perpetua-core | 6d75cfe08af95992dddffab13ae3019aa9c41350 |

## 3. Artifacts and cell results (V)

| Cell | Artifact id | Archive sha256 |
| --- | --- | --- |
| 3.11 | 12052419483 | 8b101513fe57920f7f63f7a8f85a02647600d70c384e26398e0797509cca7968 |
| 3.12 | 12052219902 | cd28c2c7fb2f1b85612d0507b7ae33daa47edc986a92ef3e037ab67151fea8ee |

Artifacts expire 90 days after the run; this receipt carries the digests, not the archives.

Per cell: seal mode evidence, job status success, evidence true, complete true, no
problems, head 3332b615, 19 sealed files; 1245 tests, 0 failures, 0 errors, 0 skipped;
required collection modules 13; rebuild comparison reproducible with 0 mismatches; four install
reports per cell; six mandatory scenarios present.

## 4. Sealed file digests (V)

SHA-256 of each sealed file as recorded in each cell's evidence-status.json.

| File | 3.11 | 3.12 |
| --- | --- | --- |
| approval-binding.json | f6b4d9f4dfd0924ae160aa73693c5412d4e8ad0919ebc19117be4dd010e2fb8c | f6b4d9f4dfd0924ae160aa73693c5412d4e8ad0919ebc19117be4dd010e2fb8c |
| collection-gate.json | f4f6e4f05076b62074f95382445a783ae48fa34daa3f505e574c4f2eb2f93505 | f4f6e4f05076b62074f95382445a783ae48fa34daa3f505e574c4f2eb2f93505 |
| collection.json | c998b2fb67db2afb9a4ecc47c67e932e9e90b6964921b78d44381e7e02c41a68 | c998b2fb67db2afb9a4ecc47c67e932e9e90b6964921b78d44381e7e02c41a68 |
| final-results.xml | 471fc21a524e309c92aaa32c69512e42e3d42fcccd39328822c1afff63cced42 | 71a4e61a8cb2d329899c4f6407588199ab6555e64f13a27d1947cff3b1eb1144 |
| identity.json | 6fee79a0465be07109890b25afcd79b0ba5ddc335d674b2f575afa1a92bb1b76 | 6fee79a0465be07109890b25afcd79b0ba5ddc335d674b2f575afa1a92bb1b76 |
| install-reports/producer-1.json | e530ea8e53a75ddf0b5d0664eb721c4eadadb74485af9106ff17f490542d4eed | e530ea8e53a75ddf0b5d0664eb721c4eadadb74485af9106ff17f490542d4eed |
| install-reports/producer-2.json | e530ea8e53a75ddf0b5d0664eb721c4eadadb74485af9106ff17f490542d4eed | e530ea8e53a75ddf0b5d0664eb721c4eadadb74485af9106ff17f490542d4eed |
| install-reports/producer-3.json | e530ea8e53a75ddf0b5d0664eb721c4eadadb74485af9106ff17f490542d4eed | e530ea8e53a75ddf0b5d0664eb721c4eadadb74485af9106ff17f490542d4eed |
| install-reports/producer-4.json | e530ea8e53a75ddf0b5d0664eb721c4eadadb74485af9106ff17f490542d4eed | e530ea8e53a75ddf0b5d0664eb721c4eadadb74485af9106ff17f490542d4eed |
| provenance-one.json | d96ca32982d3f72375c7a273034e7768b42af053ac2e675aa70c49d8bb6e8998 | 36ed3e046697dc13b0766843c9f0bc8e313373fe1fb0cd59d310db021413d202 |
| provenance-two.json | d96ca32982d3f72375c7a273034e7768b42af053ac2e675aa70c49d8bb6e8998 | 36ed3e046697dc13b0766843c9f0bc8e313373fe1fb0cd59d310db021413d202 |
| rebuild-comparison.json | 4c295975a380163cd7a71470b49e9a7f2764d8794883f5dea203a5eb6ee289a2 | 4c295975a380163cd7a71470b49e9a7f2764d8794883f5dea203a5eb6ee289a2 |
| scenario-traces/POP-CAPABILITY-1.json | 3300bab0a0ffe3194b67377fa839a9b23f9c9237fdfb0c6890403db9e3157217 | 3300bab0a0ffe3194b67377fa839a9b23f9c9237fdfb0c6890403db9e3157217 |
| scenario-traces/POP-CASCADE-1.json | e5462adea01f02d6298743e69cf79e59c6b1cab59adb6ffe8788496b28042167 | e5462adea01f02d6298743e69cf79e59c6b1cab59adb6ffe8788496b28042167 |
| scenario-traces/POP-COMMON-1.json | 598391f5150083b80f176fe196017ee60aa08600a995724a4acd44d62b10fe80 | 598391f5150083b80f176fe196017ee60aa08600a995724a4acd44d62b10fe80 |
| scenario-traces/POP-COMMS-1.json | e261af4ee6bd47a0936d47489bb028175c3bf9cc805c315014abf8321318dbb4 | e261af4ee6bd47a0936d47489bb028175c3bf9cc805c315014abf8321318dbb4 |
| scenario-traces/POP-CONFORM-1.json | 7500daa54bb0362b26364296cb423d3dc5382b09b301b05da0accda968e5649c | 7500daa54bb0362b26364296cb423d3dc5382b09b301b05da0accda968e5649c |
| scenario-traces/POP-MOTIVE-1.json | e94a0b1d7ad36ad849ef75e34cedc87be4bd30de4db6f8d93bb5fff6195f5578 | e94a0b1d7ad36ad849ef75e34cedc87be4bd30de4db6f8d93bb5fff6195f5578 |
| scenarios.json | fe82742b219351d5b84cf950b3ef8e0790175e989cffa1d0234154a13962e080 | fe82742b219351d5b84cf950b3ef8e0790175e989cffa1d0234154a13962e080 |

## 5. Checking performed and its independence

| Check | Who | Status |
| --- | --- | --- |
| Seal fields, 19 of 19 digests per cell, JUnit counts, approval binding, rebuild result | claude-main | V; recomputed from the downloaded artifacts; a co-author of the runner, so **not independent** |
| Repository verifiers: qualification_freeze.py verify and qualification_approval.py verify at H | claude-main | V; both exit 0; **not independent** |
| Full ten-check recompute, tests at H (1238 passed, 2 skipped), PR 50 review | agnes-antigravity-claude (first instance) | V; that instance wrote the ancestry guard in H, so its drift-guard check is a self-review; other checks are non-maker |
| Ancestry guard at 9fad272 | codex-primary-orchestrator | Reviewed correct; operator accepted that review as sufficient for the guard |
| Read-through of 9b981267..H | agy (headless, no shell) | APPROVE_SCOPED; ran no tests |
| Fresh fully independent checker instance (run facts, repository verifiers, all ten checks) | pending | **U**; instruction posted on the coordination board; not yet returned. *Superseded 2026-10-17: see section 8.* |

The scenario receipts are fixed-fixture deterministic outputs reporting an unapproved status. They
are **structural** evidence only, not behavioural or population-level evidence. Whether M1 accepts
structural-only scenario evidence is the operator's decision.

## 6. Known limitation and follow-up

- Finding P2 from the read-through review: the seal at H rejected empty required top-level files but
  hashed empty files inside the scenario-traces and install-reports directories without flagging
  them. Neither artifact of this run contains an empty file (V), so this run is unaffected. The fix
  is in oramasys draft PR 50 (head 6aa8b8b3405adbe324ef1fde1536ebfe5fb70e04, 15 of 15 checks
  green) and is not part of H; merging it changes the approved head and needs a new approval.

## 7. Not done and still operator-owned (as first published; see section 8 for the amendment)

Fast-forward of the qualification branch to H, commit of the freeze record, formal evidence
acceptance, pin promotion (core 6d75cfe0, telos 931b6347, agate 172bfc3e; phylax unchanged), serving
activation, the E1 ratification comment, and every merge.

## 8. Amendment 2026-10-17 (appended; earlier sections are unchanged history)

Amended on the operator's instruction and by Codex's reconciliation (board row 4768), in this existing
receipt PR and not in a second one. Earlier caveats stay as written; this section only adds records.

| Record | Source | Status |
| --- | --- | --- |
| Fresh independent runtime review: run 38916773943 at H, clean detached checkout, read-only; checks 1 to 10 reported with commands and results | agnes-antigravity-claude, board row 4764 | **V as reported**; Codex classified it as runtime evidence and reconciled it (row 4768); this author did not re-run it. Check 2b was reported NOT RUN there |
| Check 2b, the approval verifier at H, exit 0 | claude-main (board row 4728, not independent); the operator ran it personally with their own session credential, terminal log relayed at board row 4775 (summary at row 4772) | **V**; exit 0 by the operator's own run, relayed by an agent and not observed by this author |
| Headless fresh-instance attempt | codex-primary-orchestrator, board row 4760 | **NOT RUN**: print mode denied command execution; it is not counted as a review |
| Codex maker-involved checks (186 focused tests at H, PR 50 seal suite 23 passed, archives, hashes, collection gate) | codex-primary-orchestrator, board row 4749 | V; maker-involved, not independent. Verdict then: not ready for unconditional closure until the fresh checker returned |
| Operator acceptance | the operator's direct instructions of 2026-10-17 and the relayed directive at board row 4757 | Recorded as the operator's decision. Scope: acceptance of this run's evidence as bounded below |
| PR 45 branch fast-forward to H | operator instruction, executed 2026-10-17; remote ref verified equal to H | Done. The branch now holds the approved harness head |

Accepted boundary, stated by the operator and by Codex: the scenarios are structural fixed-fixture
evidence, not hardware or live-population validation. Acceptance does not turn any check that was not
run into a pass, and it does not authorize pin promotion, serving activation, T3 work or unrelated
merges; each keeps its own gate. Serving stays fail-closed (the grant-serving switch is unset).

Residual limitation recorded by Codex (row 4749): the seal checks bytes, not their origin. A non-empty
`identity.json` copied from another run is sealed as evidence by the harness head and by PR 50. No
substitution was seen in this run. The follow-up is a design and ownership decision, not a finding that
the artifacts are compromised.

Related final heads on the board: the E1 amendment is orama-system PR 410 at
7c0acce33ec2ffaaa6944dc2d8fabd754ad65385 (it supersedes the intermediate 2831c3e4); the Perpetua-Tools
memory and guard fix is PR 446 at 3b29c465f9d963b1c2ad321f536fc852fdf52f63. The operator's
ratification directive (row 4757) covers that batch; this receipt does not itself ratify E1.

No freeze-record commit is made on the qualification branches. The freeze script offers only a proposal
and a verify mode, and a new commit would change the approved head (board row 4779). The binding is the
operator's approval comment together with the sealed `approval-binding.json` in each artifact.
