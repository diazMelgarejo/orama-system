# Orama Housecleaning Leftovers — Next Steps

Date: 2026-07-14  
Branch: `2026-07-14-001-orama-housecleaning-leftovers`  
Source branch: `2026-07-12-001-gstack-safe-upgrade`

## Bucket

This branch preserves the general non-G7 cleanup/docs/skills leftovers from the stale `2026-07-12-001-gstack-safe-upgrade` branch.

Included commits:

- `ada33b53 docs(kimi-agent): document independent-review-voice usage + gotchas`
- `23bdf6bd docs(gstack): cross-link Kimi as an optional third review voice`
- `5d58e8e9 docs(shell-hygiene): add 15-minute default hard ceiling for backgrounded external dispatches`
- `ba9bb5bc docs(v2): add D23 single-operator-LAN threat-model descope ADR`
- `9554f0a1 docs(v2): catalogue references/patterns/, cross-link to 2026-07-12 work`
- `65966a22 docs(shell-hygiene): add concurrent git commit/add contention section`
- `97608700 docs(security): record multi-PR append-only-log landing-order case study`
- `93b11fe2 docs(v2): defer STM high-peer-count latency benchmark to v2.5`

Excluded on purpose:

- `e3abb562 feat(gstack): add gstack-safe-upgrade.sh, retire 2 upstream-absorbed fork patches` because it already landed via PR #148.
- `86c986f0 feat(skills,docs): add antigravity-agent fan-out skill + G7 async notifications analysis` because it belongs in the dedicated G7 PR.
- Perpetua-Tools `vendor/ecc-tools` submodule drift because it is a separate PT repo/submodule reconciliation item and currently reports commits not present locally.

## Current status

This is a preservation and housecleaning PR. It carries docs and skill guidance that were stranded on the stale branch after the gstack-safe-upgrade patch landed separately.

## Review checklist

- [ ] Confirm Kimi independent-review guidance is still accurate against current Kimi skill behavior.
- [ ] Confirm gstack cross-link to Kimi as optional third review voice matches current review workflow.
- [ ] Confirm shell-hygiene guidance around backgrounded external dispatch and concurrent git add/commit contention is still wanted.
- [ ] Confirm D23 single-operator-LAN threat-model descope ADR belongs in v2 docs.
- [ ] Confirm `docs/v2/references/patterns/README.md` is the desired home for pattern cataloguing.
- [ ] Confirm SECURITY.md case study is acceptable in canonical security docs, not better suited to `docs/wiki` only.
- [ ] Confirm STM high-peer-count latency benchmark remains deferred to v2.5.

## Follow-up items

- [ ] If this PR lands, delete or archive stale source branch `2026-07-12-001-gstack-safe-upgrade` after verifying no unique work remains.
- [ ] Reconcile Perpetua-Tools `vendor/ecc-tools` submodule drift in a separate PT issue/branch after checking the submodule remote contains the referenced commit.
- [ ] Consider a later docs index pass if reviewers want these leftover docs linked from a single landing page.
