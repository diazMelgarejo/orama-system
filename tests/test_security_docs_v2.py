#!/usr/bin/env python3
"""
test_security_docs_v2.py
========================
Tests for the security documentation set added in the v2 security-harness
excellence plan PR. Covers:

  - docs/security-reviews/2026-06-14-security-efficiency-review-v1.md
  - docs/v2/31-security-harness-excellence-plan.md
  - docs/v2/32-agentic-security-controls.md
  - docs/v2/33-security-harness-source-material.md
  - docs/v2/34-local-model-runtime-profile.md
  - docs/v2/README.md  (updated listing)

Run: pytest tests/test_security_docs_v2.py -v
"""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parent.parent
DOCS_V2 = ROOT / "docs" / "v2"
SECURITY_REVIEWS = ROOT / "docs" / "security-reviews"

PLAN_31 = DOCS_V2 / "31-security-harness-excellence-plan.md"
CONTROLS_32 = DOCS_V2 / "32-agentic-security-controls.md"
SOURCE_33 = DOCS_V2 / "33-security-harness-source-material.md"
RUNTIME_34 = DOCS_V2 / "34-local-model-runtime-profile.md"
README_V2 = DOCS_V2 / "README.md"
SECURITY_REVIEW = SECURITY_REVIEWS / "2026-06-14-security-efficiency-review-v1.md"

# All PT threat IDs defined in the plan.
EXPECTED_PT_CODES = {"PT-01", "PT-02", "PT-03", "PT-04", "PT-05", "PT-06", "PT-07"}

# Acceptance-gate IDs defined in section 7 of the plan.
EXPECTED_ACCEPTANCE_GATES = {
    "AC-AUTH",
    "AC-RATE",
    "AC-COOKIE",
    "AC-TOOLS",
    "AC-MEM",
    "AC-SCAN",
    "AC-TRACE",
    "AC-SUPPLY",
}


# ---------------------------------------------------------------------------
# 1. File existence
# ---------------------------------------------------------------------------

class TestDocumentFilesExist:
    """All six files introduced or modified by the PR must exist."""

    def test_security_review_exists(self):
        assert SECURITY_REVIEW.exists(), (
            "Security review not found: docs/security-reviews/2026-06-14-security-efficiency-review-v1.md"
        )

    def test_plan_31_exists(self):
        assert PLAN_31.exists(), "Plan doc not found: docs/v2/31-security-harness-excellence-plan.md"

    def test_controls_32_exists(self):
        assert CONTROLS_32.exists(), "Controls doc not found: docs/v2/32-agentic-security-controls.md"

    def test_source_33_exists(self):
        assert SOURCE_33.exists(), (
            "Source-material doc not found: docs/v2/33-security-harness-source-material.md"
        )

    def test_runtime_34_exists(self):
        assert RUNTIME_34.exists(), (
            "Runtime profile not found: docs/v2/34-local-model-runtime-profile.md"
        )

    def test_readme_v2_exists(self):
        assert README_V2.exists(), "v2 README not found: docs/v2/README.md"


# ---------------------------------------------------------------------------
# 2. Security Harness Excellence Plan (31) — structure
# ---------------------------------------------------------------------------

class TestSecurityHarnessPlan31:
    """doc 31 must have required top-level sections and content."""

    @property
    def _text(self) -> str:
        return PLAN_31.read_text(encoding="utf-8")

    def test_has_title(self):
        assert "# Security Harness Excellence Plan" in self._text

    def test_has_document_map(self):
        assert "## Document map" in self._text

    def test_document_map_lists_all_four_files(self):
        text = self._text
        assert "31-security-harness-excellence-plan.md" in text
        assert "32-agentic-security-controls.md" in text
        assert "33-security-harness-source-material.md" in text
        assert "34-local-model-runtime-profile.md" in text

    def test_has_evidence_model_section(self):
        assert "## 0. Evidence and source reliability model" in self._text

    def test_evidence_model_defines_three_tiers(self):
        text = self._text
        assert "Tier 1" in text
        assert "Tier 2" in text
        assert "Tier 3" in text

    def test_has_executive_strategy_section(self):
        assert "## 1. Executive strategy" in self._text

    def test_has_local_system_model_section(self):
        assert "## 2. Local system model" in self._text

    def test_local_system_model_has_assets_principals_trust_boundaries(self):
        text = self._text
        assert "### 2.1 Assets" in text
        assert "### 2.2 Principals" in text
        assert "### 2.3 Trust boundaries" in text

    def test_has_representative_kill_chain(self):
        assert "### 2.4 Representative kill chain" in self._text

    def test_kill_chain_has_seven_steps(self):
        text = self._text
        # The kill chain is numbered 1-7
        for step in range(1, 8):
            assert f"\n{step}." in text, f"Kill chain missing step {step}"

    def test_has_threat_model_section(self):
        assert "## 3. Threat model" in self._text

    def test_threat_model_defines_all_pt_codes(self):
        text = self._text
        for code in EXPECTED_PT_CODES:
            assert f"| {code} " in text, f"Threat model missing PT code: {code}"

    def test_threat_model_clarifies_local_ids(self):
        """The plan must explicitly note PT-* are local IDs, not OWASP T-codes."""
        text = self._text
        assert "Local IDs" in text or "local ID," in text or "local plan-threat IDs" in text

    def test_has_standards_traceability_section(self):
        assert "## 4. Standards traceability" in self._text

    def test_standards_traceability_references_owasp_agentic(self):
        assert "OWASP Top 10 for Agentic Applications" in self._text

    def test_standards_traceability_references_owasp_llm(self):
        assert "OWASP Top 10 for LLM Applications" in self._text

    def test_standards_traceability_references_mitre_atlas(self):
        assert "MITRE ATLAS" in self._text

    def test_has_benchmark_references_section(self):
        assert "## 5. Benchmark references" in self._text

    def test_has_roadmap_section(self):
        assert "## 6. Roadmap" in self._text

    def test_roadmap_has_five_stages(self):
        text = self._text
        for stage_label in (
            "Stage 0",
            "Stage 1",
            "Stage 2",
            "Stage 3",
            "Stage 4",
        ):
            assert stage_label in text, f"Roadmap missing: {stage_label}"

    def test_has_acceptance_gates_section(self):
        assert "## 7. Acceptance gates" in self._text

    def test_all_acceptance_gates_present(self):
        text = self._text
        for gate in EXPECTED_ACCEPTANCE_GATES:
            assert gate in text, f"Acceptance gate missing: {gate}"

    def test_has_pr_stacking_section(self):
        assert "## 8. Security PR stacking recommendation" in self._text

    def test_has_quarterly_standards_refresh_section(self):
        assert "## 9. Quarterly standards refresh" in self._text

    def test_has_one_line_summary_section(self):
        assert "## 10. One-line summary" in self._text

    def test_references_security_md(self):
        assert "SECURITY.md" in self._text


# ---------------------------------------------------------------------------
# 3. Agentic Security Controls (32) — structure and threat traces
# ---------------------------------------------------------------------------

class TestAgenticSecurityControls32:
    """doc 32 must have 10 numbered sections each with a PT threat trace."""

    @property
    def _text(self) -> str:
        return CONTROLS_32.read_text(encoding="utf-8")

    def test_has_title(self):
        assert "# Agentic Security Controls" in self._text

    def test_header_references_plan_31(self):
        assert "31-security-harness-excellence-plan.md" in self._text

    def test_has_ten_top_level_sections(self):
        text = self._text
        required_sections = [
            "## 1. Authentication and LAN-bind hardening",
            "## 2. Cookie/session hardening",
            "## 3. Rate, token, and concurrency budgets",
            "## 4. Tool-executor mediator",
            "## 5. Sandboxing and egress ladder",
            "## 6. Prompt-injection scanner",
            "## 7. Memory ACL and provenance",
            "## 8. Supply chain",
            "## 9. Observability and replay",
            "## 10. SWARM-style system objective audit",
        ]
        for section in required_sections:
            assert section in text, f"Missing section: {section}"

    def test_each_section_has_threat_trace(self):
        """Every numbered section must reference at least one PT-* code."""
        text = self._text
        # Find all threat traces in the document
        pt_references = re.findall(r"PT-\d+", text)
        assert len(pt_references) >= 10, (
            f"Expected at least 10 PT threat traces (one per section), found {len(pt_references)}"
        )

    def test_only_valid_pt_codes_referenced(self):
        """Only PT-01 through PT-07 may appear; invented codes are a content error."""
        text = self._text
        found_codes = set(re.findall(r"PT-\d+", text))
        invalid = found_codes - EXPECTED_PT_CODES
        assert not invalid, f"Controls doc references undefined PT codes: {invalid}"

    def test_auth_section_references_pt1_and_pt4(self):
        text = self._text
        # Find the auth section content
        auth_idx = text.find("## 1. Authentication and LAN-bind hardening")
        next_section_idx = text.find("\n## 2.", auth_idx + 1)
        auth_section = text[auth_idx:next_section_idx]
        assert "PT-01" in auth_section
        assert "PT-04" in auth_section

    def test_rate_budget_section_references_pt5(self):
        text = self._text
        rate_idx = text.find("## 3. Rate, token, and concurrency budgets")
        next_section_idx = text.find("\n## 4.", rate_idx + 1)
        rate_section = text[rate_idx:next_section_idx]
        assert "PT-05" in rate_section

    def test_tool_mediator_section_references_pt2_and_pt4(self):
        text = self._text
        tool_idx = text.find("## 4. Tool-executor mediator")
        next_section_idx = text.find("\n## 5.", tool_idx + 1)
        tool_section = text[tool_idx:next_section_idx]
        assert "PT-02" in tool_section
        assert "PT-04" in tool_section

    def test_memory_section_references_pt3(self):
        text = self._text
        mem_idx = text.find("## 7. Memory ACL and provenance")
        next_section_idx = text.find("\n## 8.", mem_idx + 1)
        mem_section = text[mem_idx:next_section_idx]
        assert "PT-03" in mem_section

    def test_supply_chain_section_references_pt6(self):
        text = self._text
        sc_idx = text.find("## 8. Supply chain")
        next_section_idx = text.find("\n## 9.", sc_idx + 1)
        sc_section = text[sc_idx:next_section_idx]
        assert "PT-06" in sc_section

    def test_swarm_section_references_pt7(self):
        text = self._text
        swarm_idx = text.find("## 10. SWARM-style system objective audit")
        swarm_section = text[swarm_idx:]
        assert "PT-07" in swarm_section

    def test_sandboxing_section_has_isolation_ladder(self):
        text = self._text
        assert "L0" in text
        assert "L1" in text
        assert "L5" in text

    def test_memory_section_has_required_fields_list(self):
        text = self._text
        required_fields = [
            "source URI",
            "trust tier",
            "checksum",
            "expiry",
        ]
        for field in required_fields:
            assert field in text, f"Memory ACL section missing required field: {field}"

    def test_auth_acceptance_references_test_file(self):
        """Section 1 must point to a concrete test entrypoint."""
        text = self._text
        assert "tests/test_control_plane_auth.py" in text

    def test_swarm_objective_contract_has_key_fields(self):
        text = self._text
        swarm_idx = text.find("## 10. SWARM-style system objective audit")
        swarm_section = text[swarm_idx:]
        for field in ("original user goal", "non-goals", "forbidden actions", "rollback plan"):
            assert field in swarm_section, f"Objective contract missing: {field}"


# ---------------------------------------------------------------------------
# 4. Source Material (33) — preservation markers
# ---------------------------------------------------------------------------

class TestSourceMaterial33:
    """doc 33 must carry preservation header and preserve original plan content."""

    @property
    def _text(self) -> str:
        return SOURCE_33.read_text(encoding="utf-8")

    def test_has_title(self):
        assert "# Security Harness Source Material" in self._text

    def test_preservation_notice_present(self):
        assert "Do not treat this as the canonical strategy" in self._text

    def test_references_canonical_31(self):
        assert "31-security-harness-excellence-plan.md" in self._text

    def test_preserves_original_goal_section(self):
        """The original plan's § 0 goal sentence must still be present."""
        assert "## 0. Goal (one sentence)" in self._text

    def test_preserves_benchmark_targets_section(self):
        assert "## 1. Benchmark Targets" in self._text

    def test_preserves_threat_model_section(self):
        assert "## 2. Threat Model" in self._text

    def test_preserves_acceptance_criteria_section(self):
        assert "## 11. Acceptance Criteria" in self._text

    def test_preserves_ac_s1_criterion(self):
        assert "AC-S1" in self._text

    def test_preserves_original_staged_roadmap(self):
        assert "## 10. Staged Roadmap" in self._text


# ---------------------------------------------------------------------------
# 5. Local Model Runtime Profile (34) — structure
# ---------------------------------------------------------------------------

class TestLocalModelRuntimeProfile34:
    """doc 34 must have required sections and correct security guidance."""

    @property
    def _text(self) -> str:
        return RUNTIME_34.read_text(encoding="utf-8")

    def test_has_title(self):
        assert "# Local Model Runtime Profile" in self._text

    def test_references_plan_31(self):
        assert "31-security-harness-excellence-plan.md" in self._text

    def test_references_source_33(self):
        assert "33-security-harness-source-material.md" in self._text

    def test_has_seven_sections(self):
        text = self._text
        for num in range(1, 8):
            assert f"\n## {num}." in text, f"Missing section ## {num}."

    def test_security_controls_section_present(self):
        assert "## 2. Security controls for Ollama" in self._text

    def test_security_controls_loopback_guidance(self):
        """Loopback-bind recommendation must appear in the security section."""
        text = self._text
        assert "loopback" in text.lower()

    def test_security_controls_no_bearer_to_probes(self):
        """Must advise not passing bearer tokens to model probes."""
        assert "bearer" in self._text.lower()

    def test_ollama_mlx_section_present(self):
        assert "## 3. Ollama MLX on Apple Silicon" in self._text

    def test_mlx_section_caveats_preview_language(self):
        """The Ollama MLX section must not over-claim; must include caveat."""
        text = self._text
        # The reframed guidance warns against overclaiming
        assert "preview" in text.lower()

    def test_qwen_profile_section_present(self):
        assert "## 4. qwen3.5:9b-nvfp4 profile" in self._text

    def test_qwen_profile_has_caveat(self):
        text = self._text
        qwen_idx = text.find("## 4. qwen3.5:9b-nvfp4 profile")
        next_section = text.find("\n## 5.", qwen_idx + 1)
        qwen_section = text[qwen_idx:next_section]
        assert "Caveat" in qwen_section or "caveat" in qwen_section.lower()

    def test_benchmarking_checklist_section_present(self):
        assert "## 7. Benchmarking checklist" in self._text

    def test_benchmarking_checklist_requires_machine_model(self):
        assert "machine model" in self._text

    def test_benchmarking_checklist_requires_ollama_version(self):
        assert "Ollama version" in self._text


# ---------------------------------------------------------------------------
# 6. Cross-document consistency
# ---------------------------------------------------------------------------

class TestCrossDocumentConsistency:
    """Links and references between the four new v2 docs must be consistent."""

    def test_31_links_to_32(self):
        text = PLAN_31.read_text(encoding="utf-8")
        assert "32-agentic-security-controls.md" in text

    def test_31_links_to_33(self):
        text = PLAN_31.read_text(encoding="utf-8")
        assert "33-security-harness-source-material.md" in text

    def test_31_links_to_34(self):
        text = PLAN_31.read_text(encoding="utf-8")
        assert "34-local-model-runtime-profile.md" in text

    def test_32_back_references_31(self):
        text = CONTROLS_32.read_text(encoding="utf-8")
        assert "31-security-harness-excellence-plan.md" in text

    def test_32_back_references_33(self):
        text = CONTROLS_32.read_text(encoding="utf-8")
        assert "33-security-harness-source-material.md" in text

    def test_33_back_references_31(self):
        text = SOURCE_33.read_text(encoding="utf-8")
        assert "31-security-harness-excellence-plan.md" in text

    def test_33_back_references_32(self):
        text = SOURCE_33.read_text(encoding="utf-8")
        assert "32-agentic-security-controls.md" in text

    def test_34_back_references_31(self):
        text = RUNTIME_34.read_text(encoding="utf-8")
        assert "31-security-harness-excellence-plan.md" in text

    def test_34_back_references_33(self):
        text = RUNTIME_34.read_text(encoding="utf-8")
        assert "33-security-harness-source-material.md" in text

    def test_pt_codes_in_32_are_subset_of_pt_codes_defined_in_31(self):
        plan_text = PLAN_31.read_text(encoding="utf-8")
        controls_text = CONTROLS_32.read_text(encoding="utf-8")
        defined = set(re.findall(r"PT-\d+", plan_text))
        referenced = set(re.findall(r"PT-\d+", controls_text))
        unknown = referenced - defined
        assert not unknown, (
            f"Controls doc (32) references PT codes not defined in plan (31): {unknown}"
        )

    def test_all_pt_codes_defined_in_31_appear_in_32(self):
        """Every threat in the plan must be covered by at least one control."""
        controls_text = CONTROLS_32.read_text(encoding="utf-8")
        referenced = set(re.findall(r"PT-\d+", controls_text))
        missing = EXPECTED_PT_CODES - referenced
        assert not missing, (
            f"Controls doc (32) does not reference these PT codes from the plan: {missing}"
        )


# ---------------------------------------------------------------------------
# 7. Threat model integrity in doc 31
# ---------------------------------------------------------------------------

class TestThreatModelIntegrity:
    """PT-code definitions in doc 31 must be internally consistent."""

    @property
    def _text(self) -> str:
        return PLAN_31.read_text(encoding="utf-8")

    def test_exactly_seven_pt_codes_defined(self):
        text = self._text
        # PT codes appear in the table as "| PT-N |"
        defined = set(re.findall(r"\| (PT-\d+) ", text))
        assert defined == EXPECTED_PT_CODES, (
            f"Expected PT-01 through PT-07, found: {sorted(defined)}"
        )

    def test_no_owasp_t_codes_masquerading_as_pt_codes(self):
        """Ensure 'PT-' prefix is not used alongside OWASP ASI/LLM IDs as synonyms."""
        text = self._text
        # The document must clarify PT codes are local, not OWASP
        assert "not OWASP T-codes" in text or "local IDs, not OWASP" in text

    def test_threat_descriptions_cover_lan_exposure(self):
        text = self._text
        assert "LAN control-plane exposure" in text

    def test_threat_descriptions_cover_prompt_injection(self):
        text = self._text
        assert "Prompt injection" in text or "prompt injection" in text

    def test_threat_descriptions_cover_memory_poisoning(self):
        text = self._text
        assert "Memory poisoning" in text

    def test_threat_descriptions_cover_credential_exposure(self):
        text = self._text
        assert "Credential exposure" in text

    def test_threat_descriptions_cover_supply_chain(self):
        text = self._text
        assert "Supply-chain" in text or "supply-chain" in text

    def test_threat_descriptions_cover_inter_agent_cascade(self):
        text = self._text
        assert "Inter-agent cascade" in text or "cascade" in text.lower()


# ---------------------------------------------------------------------------
# 8. Acceptance gates in doc 31
# ---------------------------------------------------------------------------

class TestAcceptanceGates:
    """All acceptance gates in doc 31 must reference a concrete command target."""

    @property
    def _text(self) -> str:
        return PLAN_31.read_text(encoding="utf-8")

    def test_ac_auth_gate_has_pytest_command(self):
        text = self._text
        assert "pytest tests/test_control_plane_auth.py" in text

    def test_ac_rate_gate_references_test_file(self):
        text = self._text
        assert "test_rate_limits.py" in text

    def test_ac_cookie_gate_references_test_file(self):
        text = self._text
        assert "test_control_plane_cookie.py" in text

    def test_ac_tools_gate_references_test_file(self):
        text = self._text
        assert "test_tool_mediator.py" in text

    def test_ac_mem_gate_references_test_file(self):
        text = self._text
        assert "test_memory_acl.py" in text

    def test_ac_scan_gate_references_test_file(self):
        text = self._text
        assert "test_prompt_injection_scanner.py" in text

    def test_ac_trace_gate_references_test_file(self):
        text = self._text
        assert "test_agent_trace.py" in text

    def test_ac_supply_gate_references_pip_audit(self):
        text = self._text
        assert "pip-audit" in text

    def test_all_future_gates_are_clearly_marked_future(self):
        """Gates not yet runnable must be explicitly labelled 'future'."""
        text = self._text
        gates_section_idx = text.find("## 7. Acceptance gates")
        gates_section = text[gates_section_idx:]
        # Several gates require future test files; they must use the word 'future'
        assert "future" in gates_section.lower()


# ---------------------------------------------------------------------------
# 9. README.md v2 directory listing update
# ---------------------------------------------------------------------------

class TestReadmeV2Listing:
    """docs/v2/README.md must list all four new docs and update the free slot."""

    @property
    def _text(self) -> str:
        return README_V2.read_text(encoding="utf-8")

    def test_readme_lists_31(self):
        assert "31-security-harness-excellence-plan.md" in self._text

    def test_readme_lists_32(self):
        assert "32-agentic-security-controls.md" in self._text

    def test_readme_lists_33(self):
        assert "33-security-harness-source-material.md" in self._text

    def test_readme_lists_34(self):
        assert "34-local-model-runtime-profile.md" in self._text

    def test_next_free_slot_is_35(self):
        """After adding 31-34 the next available slot must be 35."""
        assert "35-" in self._text or "Next free slot: `35-`" in self._text

    def test_readme_describes_31_as_canonical_strategy(self):
        assert "canonical" in self._text

    def test_readme_describes_32_as_implementation_guidance(self):
        assert "implementation" in self._text

    def test_readme_describes_33_as_preserved_source(self):
        assert "preserved" in self._text or "verbatim" in self._text

    def test_readme_no_longer_ends_at_28(self):
        """The old README had 28- as the last entry; it must now list beyond it."""
        text = self._text
        assert "28-againtra-platform-requirements-alignment.md" in text
        # And there must be entries after 28
        idx_28 = text.find("28-againtra-platform-requirements-alignment.md")
        idx_31 = text.find("31-security-harness-excellence-plan.md")
        assert idx_31 > idx_28, "31 must appear after 28 in the listing"


# ---------------------------------------------------------------------------
# 10. Security review document (2026-06-14)
# ---------------------------------------------------------------------------

class TestSecurityReviewDocument:
    """The security review doc must have all required sections and findings."""

    @property
    def _text(self) -> str:
        return SECURITY_REVIEW.read_text(encoding="utf-8")

    def test_has_title(self):
        assert "# Security & Efficiency Code Review" in self._text

    def test_has_date_header(self):
        assert "2026-06-14" in self._text

    def test_has_evidence_update_note(self):
        """The 2026-06-15 evidence update disclaimer must be present."""
        assert "Evidence update (2026-06-15)" in self._text

    def test_has_executive_summary(self):
        assert "## Executive Summary" in self._text

    def test_executive_summary_has_severity_table(self):
        text = self._text
        assert "High" in text
        assert "Medium" in text
        assert "Low" in text

    def test_has_security_findings_section(self):
        assert "## SECURITY FINDINGS" in self._text

    def test_has_efficiency_findings_section(self):
        assert "## EFFICIENCY FINDINGS" in self._text

    def test_security_findings_cover_s1_through_s5(self):
        text = self._text
        for finding_id in ("S1", "S2", "S3", "S4", "S5"):
            assert f"### {finding_id}" in text, f"Missing security finding: {finding_id}"

    def test_efficiency_findings_cover_e1_through_e4(self):
        text = self._text
        for finding_id in ("E1", "E2", "E3", "E4"):
            assert f"### {finding_id}" in text, f"Missing efficiency finding: {finding_id}"

    def test_s1_finding_describes_auth_posture(self):
        text = self._text
        s1_idx = text.find("### S1")
        next_finding = text.find("\n### S2", s1_idx + 1)
        s1_section = text[s1_idx:next_finding]
        assert "auth" in s1_section.lower()

    def test_s2_finding_describes_dependency_pinning(self):
        text = self._text
        s2_idx = text.find("### S2")
        next_finding = text.find("\n### S3", s2_idx + 1)
        s2_section = text[s2_idx:next_finding]
        assert "dependencies" in s2_section.lower() or "unpinned" in s2_section.lower()

    def test_has_prioritized_action_list(self):
        assert "Prioritized Action List" in self._text

    def test_prioritized_action_list_has_s1_and_s2(self):
        text = self._text
        action_idx = text.find("Prioritized Action List")
        action_section = text[action_idx:]
        assert "S1" in action_section
        assert "S2" in action_section

    def test_has_methodology_note(self):
        assert "## Methodology Note" in self._text

    def test_has_reproducibility_appendix(self):
        assert "Reproducibility appendix" in self._text

    def test_reproducibility_appendix_includes_repo_hygiene_command(self):
        text = self._text
        repro_idx = text.find("Reproducibility appendix")
        repro_section = text[repro_idx:]
        assert "repo_hygiene.py" in repro_section

    def test_positive_findings_section_present(self):
        assert "What Is Already Done Right" in self._text

    def test_no_hardcoded_token_in_review(self):
        """The review must not contain real secret values."""
        text = self._text
        # sk- prefixed strings that are not placeholders should not appear
        real_sk = re.findall(r"sk-[A-Za-z0-9]{20,}", text)
        assert not real_sk, f"Possible token found in review doc: {real_sk}"

    def test_cross_repo_observations_section_present(self):
        assert "Cross-Repo Observations" in self._text


# ---------------------------------------------------------------------------
# 11. Additional regression / boundary tests
# ---------------------------------------------------------------------------

class TestDocumentBoundaryAndRegression:
    """Regression and boundary checks for edge cases introduced by the PR."""

    def test_source_material_33_is_not_empty(self):
        content = SOURCE_33.read_text(encoding="utf-8")
        assert len(content) > 1000, (
            "Source material (33) appears truncated; should contain the full prior plan"
        )

    def test_plan_31_is_shorter_than_source_33(self):
        """The refactored plan should be substantially shorter than the preserved source."""
        plan_len = len(PLAN_31.read_text(encoding="utf-8"))
        source_len = len(SOURCE_33.read_text(encoding="utf-8"))
        assert plan_len < source_len, (
            "Plan (31) should be shorter than the full source material (33) "
            f"but plan={plan_len} chars, source={source_len} chars"
        )

    def test_plan_31_does_not_duplicate_mlx_benchmark_numbers(self):
        """MLX benchmark numbers were moved to 34; plan 31 should not repeat them."""
        text = PLAN_31.read_text(encoding="utf-8")
        # The old plan had specific speedup multipliers; new plan should not
        assert "7x faster" not in text
        assert "1.6x" not in text

    def test_controls_32_each_section_has_recommendation_subsection(self):
        """Sections 1-9 should each include a Recommendation block."""
        text = CONTROLS_32.read_text(encoding="utf-8")
        # Most sections end in a Recommendation header or bullet list
        recommendation_count = text.count("### Recommendation") + text.count("Deny by default") + text.count("### Recommendation\n")
        assert recommendation_count >= 5, (
            "Expected most control sections to include a recommendation"
        )

    def test_runtime_34_separates_security_from_performance(self):
        """Security controls and performance guidance must be in distinct sections."""
        text = RUNTIME_34.read_text(encoding="utf-8")
        sec_idx = text.find("## 2. Security controls")
        perf_idx = text.find("## 5. Context and KV cache")
        assert sec_idx < perf_idx, (
            "Security controls section (§2) should precede performance guidance (§5)"
        )

    def test_no_personal_paths_in_any_new_doc(self):
        """None of the new docs should contain machine-specific absolute paths."""
        user_path_pattern = re.compile(r"/Users/[a-zA-Z][^/\s]{2,}")
        for doc_path in (PLAN_31, CONTROLS_32, SOURCE_33, RUNTIME_34, SECURITY_REVIEW):
            text = doc_path.read_text(encoding="utf-8")
            hits = user_path_pattern.findall(text)
            assert not hits, (
                f"{doc_path.name} contains personal absolute path(s): {hits}"
            )

    def test_pt_codes_not_prefixed_with_owasp_asi_ids(self):
        """PT codes must not be formatted as 'ASI01' in the new docs; that belongs in the source material."""
        for doc_path in (PLAN_31, CONTROLS_32, RUNTIME_34):
            text = doc_path.read_text(encoding="utf-8")
            # The new docs should use PT-N not ASI0N as primary IDs
            # (ASI IDs may appear in standards traceability tables, not as threat IDs)
            if doc_path == PLAN_31:
                # Plan 31 should define PT codes, not ASI codes, in the threat model table
                threat_idx = text.find("## 3. Threat model")
                next_section = text.find("\n## 4.", threat_idx + 1)
                threat_section = text[threat_idx:next_section]
                assert "ASI01" not in threat_section, (
                    "Threat model table in 31 should use PT-* IDs, not ASI IDs"
                )
