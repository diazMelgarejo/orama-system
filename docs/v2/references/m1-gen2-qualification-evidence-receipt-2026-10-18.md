# M1 generation-2 qualification evidence receipt (2026-10-18)

State: **EVIDENCE RUN PASSED AND ACCEPTED BY THE OPERATOR; receipt published.** This is not a pin
promotion, not a merge and not an activation. It records metadata only (identifiers, digests,
counts, statuses). No retained record content is reproduced.

Tags: **V** verified now, **H** historical, **D** design authority, **P** proposal, **U** unverified.

## 1. Operator decisions and scope

- Approval: the operator posted the freeze approval from their own terminal,
  [PR 55 comment 6241262040](https://github.com/oramasys/oramasys/pull/55#issuecomment-6241262040)
  (author diazMelgarejo, unedited).
- Acceptance: the operator replied "accepted" in the session after the recompute below, on 2026-10-18.
- Not performed or implied here: merges, promotion activation (the promotion record stays
  `proposed` and `production-pin-promotion` stays disabled), serving activation, T3.
- Claim boundary: GitHub-hosted Ubuntu, Python 3.11 and 3.12, installed-set evidence of the
  generation-2 set at the consumer commit below. Not Windows, macOS, NFS or read-only mounts; not
  physical-hardware execution; not calibrated SWARM population risk; scenario receipts are
  fixed-fixture structural evidence; Phylax is composition-only.

## 2. Identity (V)

| Item | Value |
| --- | --- |
| Repository / PR | oramasys/oramasys, harness PR 55 (stacked on consumer PR 53) |
| Harness commit H2 | 902d2a8edc3fb1b9f7a91fe93a8aca6f4f000100 |
| Consumer commit C2 | 133553a6d05b8704e6e4010f581d57623829f4b2 |
| Consumer wheel sha256 | 15452354f1a94ff00318d22c1ce463e9991c23c92a7cbf0904cb4e2712ef84e4 |
| Workflow run | 39070456148, attempt 1, mode evidence, event workflow_dispatch |
| Run conclusion | success: freeze-gate, final-producers (3.11), final-producers (3.12) |
| Manifest digest | 309d44440d4db0938ed55891ffa5a26768b420033982e6eaf71c1382b1d9a32f |
| Coverage digest | 6af7fa7a02fa6fca3b34ec0eff06a7e281c9b3f92d8de3bbdd4d325f8656b326 |
| Allowlist digest | 6ecbbfe8e65f1e9cc2ee5ddb4077c8e7b57a664cf558403b69d5708da57b2ae0 |
| Registry snapshot | orama-system PR 414 at a5bdcd2b76a865e61f0ff2e752550ee73d18f82e (sha256 1f1531d94f73309f2c3271af41313fd15bf5438ba0a91355ea81111fb66fcb34) |

Producers installed from the frozen plan (V, from identity.json):

| Producer | Distribution | Commit |
| --- | --- | --- |
| endpoint-policy | oramasys-telos | 931b6347142e8e66b31136e3ac8159d86eb5b2f7 |
| grant-authority | oramasys-phylax | 0c3e860749b3ff8f62e102679f1f415f8acf0a61 |
| hardware-eligibility | oramasys-agate | 172bfc3ebf00d507856e70d0f6a0e7dbd577ffbc |
| neutral-mechanics | perpetua-core | 6d75cfe08af95992dddffab13ae3019aa9c41350 |

## 3. Artifacts and cell results (V)

| Cell | Artifact id | Archive sha256 |
| --- | --- | --- |
| 3.11 | 12114393254 | d50486ca98651138f9ec50a7209c1ba0f9b7a1378293d9ef3aeda9d4d81600cf |
| 3.12 | 12114559526 | 069ef886e2990a20da82feaad2c08b5b29940e5ce2b3125dfa97f56c29422234 |

Artifacts expire 90 days after the run; this receipt carries the digests, not the archives.

Per cell: seal mode evidence, job status success, evidence true, complete true, no
problems, 19 sealed files; 1302 tests, 0 failures, 0 errors, 0 skipped; 13 required collection
modules; rebuild comparison reproducible with 0 mismatches; 4 install reports and 6 scenario traces.

## 4. Sealed file digests (V)

| File | 3.11 | 3.12 |
| --- | --- | --- |
| approval-binding.json | dfddccea9b29439e69af734d5da67c4a5a76fad28d1920e77cd92bbd6e52aae0 | dfddccea9b29439e69af734d5da67c4a5a76fad28d1920e77cd92bbd6e52aae0 |
| collection-gate.json | 52a2d9da90131af4d4829779561a242842b22c09a66ec1594f657231510c2605 | 52a2d9da90131af4d4829779561a242842b22c09a66ec1594f657231510c2605 |
| collection.json | a4eb1239eb5f1f8cd4e2f8795c093957919eff2bc84561b6d280747cd40add3b | a4eb1239eb5f1f8cd4e2f8795c093957919eff2bc84561b6d280747cd40add3b |
| final-results.xml | 6db34a48e6edd029e7f6f95038d61b04ecab598e10257111add9b57797a91053 | b98c29928d4cf2d02c00dd4ceb28c7c6da2b39506bd0b3f62344174426f850b5 |
| identity.json | 4a8eed3ffce8f7e904919cf5ec0c3edc4f8b59c433c8d4d889c9cf99639e9a8d | 4a8eed3ffce8f7e904919cf5ec0c3edc4f8b59c433c8d4d889c9cf99639e9a8d |
| install-reports/producer-1.json | e530ea8e53a75ddf0b5d0664eb721c4eadadb74485af9106ff17f490542d4eed | e530ea8e53a75ddf0b5d0664eb721c4eadadb74485af9106ff17f490542d4eed |
| install-reports/producer-2.json | e530ea8e53a75ddf0b5d0664eb721c4eadadb74485af9106ff17f490542d4eed | e530ea8e53a75ddf0b5d0664eb721c4eadadb74485af9106ff17f490542d4eed |
| install-reports/producer-3.json | e530ea8e53a75ddf0b5d0664eb721c4eadadb74485af9106ff17f490542d4eed | e530ea8e53a75ddf0b5d0664eb721c4eadadb74485af9106ff17f490542d4eed |
| install-reports/producer-4.json | e530ea8e53a75ddf0b5d0664eb721c4eadadb74485af9106ff17f490542d4eed | e530ea8e53a75ddf0b5d0664eb721c4eadadb74485af9106ff17f490542d4eed |
| provenance-one.json | a807b3e78f4eec2965db8f76f6947b927bc21906dfc438bd2ea9b9410244e5f2 | cbccdeee087d661d06bc45065a367709ddaec91323b3b9f700960b0d2e5939f8 |
| provenance-two.json | a807b3e78f4eec2965db8f76f6947b927bc21906dfc438bd2ea9b9410244e5f2 | cbccdeee087d661d06bc45065a367709ddaec91323b3b9f700960b0d2e5939f8 |
| rebuild-comparison.json | 4c295975a380163cd7a71470b49e9a7f2764d8794883f5dea203a5eb6ee289a2 | 4c295975a380163cd7a71470b49e9a7f2764d8794883f5dea203a5eb6ee289a2 |
| scenario-traces/POP-CAPABILITY-1.json | 3300bab0a0ffe3194b67377fa839a9b23f9c9237fdfb0c6890403db9e3157217 | 3300bab0a0ffe3194b67377fa839a9b23f9c9237fdfb0c6890403db9e3157217 |
| scenario-traces/POP-CASCADE-1.json | e5462adea01f02d6298743e69cf79e59c6b1cab59adb6ffe8788496b28042167 | e5462adea01f02d6298743e69cf79e59c6b1cab59adb6ffe8788496b28042167 |
| scenario-traces/POP-COMMON-1.json | 598391f5150083b80f176fe196017ee60aa08600a995724a4acd44d62b10fe80 | 598391f5150083b80f176fe196017ee60aa08600a995724a4acd44d62b10fe80 |
| scenario-traces/POP-COMMS-1.json | e261af4ee6bd47a0936d47489bb028175c3bf9cc805c315014abf8321318dbb4 | e261af4ee6bd47a0936d47489bb028175c3bf9cc805c315014abf8321318dbb4 |
| scenario-traces/POP-CONFORM-1.json | 7500daa54bb0362b26364296cb423d3dc5382b09b301b05da0accda968e5649c | 7500daa54bb0362b26364296cb423d3dc5382b09b301b05da0accda968e5649c |
| scenario-traces/POP-MOTIVE-1.json | e94a0b1d7ad36ad849ef75e34cedc87be4bd30de4db6f8d93bb5fff6195f5578 | e94a0b1d7ad36ad849ef75e34cedc87be4bd30de4db6f8d93bb5fff6195f5578 |
| scenarios.json | cfa7e5c933f4a9f1f8576a96164695a9e79513486fcf251546637feeb48986eb | cfa7e5c933f4a9f1f8576a96164695a9e79513486fcf251546637feeb48986eb |

## 5. Checking performed and its independence

| Check | Who | Status |
| --- | --- | --- |
| Seal fields, 19 of 19 digests per cell, JUnit counts, approval binding, rebuild, identity | claude-main | V; wrote H2, so **not independent** |
| Collection gate (1302 executed, 0 skipped, 13 modules), provenance one vs two, seal reconstruction, freeze binding, 95 adversarial and gate tests | codex-primary-orchestrator (board row 4810, APPROVE_WITH_NOTES) | V; did not write H2; a different instance than the design author for this recompute |
| Identities in the promotion record | cline-audit-integration (board row 4805, APPROVE) | V |
| Approval comment fetched and compared | claude-main, and the hosted freeze-gate in CI | V |
| Comment API verifier run locally by a reviewer | codex | **U**; its host lacked a CA bundle. The hosted freeze-gate performed it |

## 6. Status of the promotion

Registry snapshot (orama-system 414), consumer (oramasys 53) and harness (oramasys 55) are drafts at
the heads above. Merge order, as merge commits: 414, then 53, then 55. Rollback target: generation 1
(H 3332b615, C f8898b35, manifest 4892b6ba, coverage 6af7fa7a, run 38916773943), archived unchanged
under requirements/history/m1-gen1/ in PR 55.
