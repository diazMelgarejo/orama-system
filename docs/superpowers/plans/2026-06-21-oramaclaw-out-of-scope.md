# OramaClaw Out-of-Scope Findings

This note records the failures from the broader validation run that were not part of the CodeRabbit fix scope for PR `#98`.

## Deferred Findings

1. `tests/test_control_plane_auth.py::test_portal_loopback_index_injects_cp_fetch_when_enforced`
   - The expected `cpFetch` injection is not present in the current portal index behavior.
   - This is a separate control-plane auth path and was not exercised by the CodeRabbit patch set.

2. `tests/test_single_agent.py::TestPackageIntegrity::test_skill_md_under_500_lines`
   - `bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/SKILL.md` is above the test's line limit.
   - The file is already carrying the new binding and orchestration material, so this needs a follow-up content trim rather than a mechanical fix.

3. `scripts/tests/test_discover.py::test_patch_openclaw_json`
   - The test expects a LAN-address rewrite that the current config does not perform.
   - This is discover/patch behavior, not part of the current CodeRabbit repairs.

4. `scripts/tests/test_discover.py::test_discover_fails_closed_when_perpetuatoolsroot_missing`
   - The test expects a hard failure where the current path now skips PT checks.
   - This needs a decision about the intended fail-closed contract before changing behavior.

5. `scripts/tests/test_openrouter_policy_order.py::test_openrouter_policy_order`
   - The run is missing `deployments/macbook-pro-head/openclaw/openclaw.model-policy.jsonc`.
   - This looks like an environment/repo fixture gap rather than a regression from the CodeRabbit patch.

6. `scripts/tests/test_openrouter_policy_order.py::test_openrouter_policy_order_respects_override`
   - Same missing policy file as above.

7. `scripts/tests/test_openrouter_policy_order.py::test_openrouter_policy_order_rejects_invalid_override`
   - Same missing policy file as above.

## Hand-off

These items were intentionally left out of the PR #98 fix set. Claude can pick them up as a separate cleanup pass without reworking the resolved CodeRabbit changes.
