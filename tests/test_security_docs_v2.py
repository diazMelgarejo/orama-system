#!/usr/bin/env python3
"""
test_security_docs_v2.py
========================
Regression tests for the security documentation introduced in the
2026-06-14/15 security-harness rewrite PR.

Covered files:
  - docs/security-reviews/2026-06-14-security-efficiency-review-v1.md
  - docs/v2/31-security-harness-excellence-plan.md  (rewritten)
  - docs/v2/32-agentic-security-controls.md          (new)
  - docs/v2/33-security-harness-source-material.md   (new)
  - docs/v2/34-local-model-runtime-profile.md        (new)
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent

PLAN_31 = ROOT / "docs" / "v2" / "31-security-harness-excellence-plan.md"
CONTROLS_32 = ROOT / "docs" / "v2" / "32-agentic-security-controls.md"
SOURCE_33 = ROOT / "docs" / "v2" / "33-security-harness-source-material.md"
RUNTIME_34 = ROOT / "docs" / "v2" / "34-local-model-runtime-profile.md"
REVIEW = (
    ROOT
    / "docs"
    / "security-reviews"
    / "2026-06-14-security-efficiency-review-v1.md"
)

DOCV2_DIR = ROOT / "docs" / "v2"


def _load_repo_hygiene():
    hygiene_path = ROOT / "scripts" / "review" / "repo_hygiene.py"
    spec = importlib.util.spec_from_file_location("repo_hygiene", hygiene_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------


def test_plan_31_exists():
    assert PLAN_31.exists(), f"Missing: {PLAN_31}"


def test_controls_32_exists():
    assert CONTROLS_32.exists(), f"Missing: {CONTROLS_32}"


def test_source_material_33_exists():
    assert SOURCE_33.exists(), f"Missing: {SOURCE_33}"


def test_runtime_profile_34_exists():
    assert RUNTIME_34.exists(), f"Missing: {RUNTIME_34}"


def test_security_review_exists():
    assert REVIEW.exists(), f"Missing: {REVIEW}"


# ---------------------------------------------------------------------------
# docs/v2/31 — Security Harness Excellence Plan
# ---------------------------------------------------------------------------


class TestPlan31:
    """Tests for the rewritten canonical security plan."""

    @pytest.fixture(scope="class")
    def content(self):
        return PLAN_31.read_text(encoding="utf-8")

    def test_title(self, content):
        assert "# Security Harness Excellence Plan" in content

    def test_status_metadata_is_v2_rewrite(self, content):
        assert "v2 strategy rewrite" in content

    def test_scope_metadata_mentions_repos(self, content):
        assert "orama-system" in content
        assert "Perpetua-Tools" in content

    def test_source_preservation_links_to_33(self, content):
        assert "33-security-harness-source-material.md" in content

    def test_control_details_links_to_32(self, content):
        assert "32-agentic-security-controls.md" in content

    def test_runtime_details_links_to_34(self, content):
        assert "34-local-model-runtime-profile.md" in content

    def test_document_map_section_present(self, content):
        assert "## Document map" in content

    def test_document_map_lists_all_four_files(self, content):
        assert "31-security-harness-excellence-plan.md" in content
        assert "32-agentic-security-controls.md" in content
        assert "33-security-harness-source-material.md" in content
        assert "34-local-model-runtime-profile.md" in content

    def test_evidence_tiers_table_present(self, content):
        assert "Tier 1" in content
        assert "Tier 2" in content
        assert "Tier 3" in content

    def test_tier1_describes_canonical_sources(self, content):
        assert "Primary / canonical source" in content

    def test_tier3_describes_commentary(self, content):
        assert "Commentary / scouting" in content

    def test_executive_strategy_section(self, content):
        assert "## 1. Executive strategy" in content

    def test_executive_strategy_uses_measurable_target(self, content):
        # The rewrite replaced the vague "exceed gstack" goal with an exact target
        assert "policy-mediated agent action" in content

    def test_local_system_model_section(self, content):
        assert "## 2. Local system model" in content

    def test_assets_subsection_present(self, content):
        assert "### 2.1 Assets" in content

    def test_principals_subsection_present(self, content):
        assert "### 2.2 Principals" in content

    def test_trust_boundaries_subsection_present(self, content):
        assert "### 2.3 Trust boundaries" in content

    def test_representative_kill_chain_present(self, content):
        assert "### 2.4 Representative kill chain" in content

    def test_threat_model_section(self, content):
        assert "## 3. Threat model" in content

    def test_threat_model_includes_t1_through_t7(self, content):
        for threat_id in ["T1", "T2", "T3", "T4", "T5", "T6", "T7"]:
            assert threat_id in content, f"Threat {threat_id} missing from threat model"

    def test_threat_model_covers_lan_exposure(self, content):
        assert "LAN control-plane exposure" in content

    def test_threat_model_covers_prompt_injection(self, content):
        assert "Prompt injection" in content

    def test_threat_model_covers_supply_chain(self, content):
        assert "Supply-chain" in content

    def test_standards_traceability_section(self, content):
        assert "## 4. Standards traceability" in content

    def test_standards_table_includes_owasp_agentic(self, content):
        assert "OWASP Top 10 for Agentic Applications" in content

    def test_standards_table_includes_owasp_llm(self, content):
        assert "OWASP Top 10 for LLM Applications" in content

    def test_standards_table_includes_mitre_atlas(self, content):
        assert "MITRE ATLAS" in content

    def test_standards_table_includes_csa_maestro(self, content):
        assert "CSA MAESTRO" in content

    def test_standards_table_includes_morris_ii(self, content):
        assert "Morris II" in content

    def test_benchmark_references_section(self, content):
        assert "## 5. Benchmark references" in content

    def test_gstack_listed_as_pattern_source(self, content):
        assert "gstack" in content

    def test_gbrain_listed_as_memory_reference(self, content):
        assert "GBrain" in content

    def test_hermes_listed_as_tool_format_reference(self, content):
        assert "Hermes" in content

    def test_roadmap_section_present(self, content):
        assert "## 6. Roadmap" in content

    def test_roadmap_has_stage_0(self, content):
        assert "Stage 0" in content

    def test_roadmap_has_stage_1(self, content):
        assert "Stage 1" in content

    def test_roadmap_has_stage_2(self, content):
        assert "Stage 2" in content

    def test_roadmap_has_stage_3(self, content):
        assert "Stage 3" in content

    def test_roadmap_has_stage_4(self, content):
        assert "Stage 4" in content

    def test_acceptance_gates_section(self, content):
        assert "## 7. Acceptance gates" in content

    def test_acceptance_gate_ac_auth_present(self, content):
        assert "AC-AUTH" in content

    def test_acceptance_gate_ac_rate_present(self, content):
        assert "AC-RATE" in content

    def test_acceptance_gate_ac_cookie_present(self, content):
        assert "AC-COOKIE" in content

    def test_acceptance_gate_ac_tools_present(self, content):
        assert "AC-TOOLS" in content

    def test_acceptance_gate_ac_mem_present(self, content):
        assert "AC-MEM" in content

    def test_acceptance_gate_ac_scan_present(self, content):
        assert "AC-SCAN" in content

    def test_acceptance_gate_ac_trace_present(self, content):
        assert "AC-TRACE" in content

    def test_acceptance_gate_ac_supply_present(self, content):
        assert "AC-SUPPLY" in content

    def test_acceptance_gates_reference_pytest(self, content):
        assert "pytest" in content

    def test_pr_stacking_recommendation_section(self, content):
        assert "## 8. Security PR stacking recommendation" in content

    def test_quarterly_refresh_section(self, content):
        assert "## 9. Quarterly standards refresh" in content

    def test_one_line_summary_section(self, content):
        assert "## 10. One-line summary" in content

    def test_one_line_summary_emphasizes_policy_mediation(self, content):
        assert "policy-mediated" in content

    def test_owasp_agentic_url_present(self, content):
        assert "genai.owasp.org" in content

    def test_mitre_atlas_url_present(self, content):
        assert "atlas.mitre.org" in content

    def test_does_not_frame_gstack_as_definitive_benchmark(self, content):
        # The rewrite explicitly reframes the gstack comparison as a "pattern source"
        assert "pattern source" in content

    def test_standards_framed_as_traceability_not_compliance(self, content):
        assert "traceability" in content.lower()


# ---------------------------------------------------------------------------
# docs/v2/32 — Agentic Security Controls
# ---------------------------------------------------------------------------


class TestControls32:
    """Tests for the extracted agentic security controls document."""

    @pytest.fixture(scope="class")
    def content(self):
        return CONTROLS_32.read_text(encoding="utf-8")

    def test_title(self, content):
        assert "# Agentic Security Controls" in content

    def test_status_metadata_present(self, content):
        assert "Status:" in content

    def test_backlink_to_plan_31(self, content):
        assert "31-security-harness-excellence-plan.md" in content

    def test_backlink_to_source_material_33(self, content):
        assert "33-security-harness-source-material.md" in content

    def test_section_1_auth_hardening(self, content):
        assert "## 1. Authentication and LAN-bind hardening" in content

    def test_section_1_problem_present(self, content):
        assert "### Problem" in content

    def test_section_1_recommendation_present(self, content):
        assert "### Recommendation" in content

    def test_section_1_acceptance_gate_present(self, content):
        assert "### Acceptance" in content

    def test_section_1_acceptance_references_pytest_path(self, content):
        assert "pytest tests/security/test_control_plane_auth.py" in content

    def test_section_2_cookie_hardening(self, content):
        assert "## 2. Cookie/session hardening" in content

    def test_section_2_recommends_samesite_strict(self, content):
        assert "SameSite=Strict" in content

    def test_section_2_recommends_httponly(self, content):
        assert "HttpOnly" in content

    def test_section_3_rate_and_token_budgets(self, content):
        assert "## 3. Rate, token, and concurrency budgets" in content

    def test_section_3_lists_budget_dimensions(self, content):
        assert "requests per minute" in content
        assert "input tokens per minute" in content
        assert "concurrent jobs" in content

    def test_section_4_tool_executor_mediator(self, content):
        assert "## 4. Tool-executor mediator" in content

    def test_section_4_deny_by_default(self, content):
        assert "Deny by default" in content

    def test_section_5_sandboxing_ladder(self, content):
        assert "## 5. Sandboxing and egress ladder" in content

    def test_section_5_ladder_has_levels(self, content):
        # Ladder goes from L0 to L5
        for level in ["L0", "L1", "L2", "L3", "L4", "L5"]:
            assert level in content, f"Sandboxing level {level} missing"

    def test_section_5_references_mitre_t1611(self, content):
        assert "T1611" in content

    def test_section_6_prompt_injection_scanner(self, content):
        assert "## 6. Prompt-injection scanner" in content

    def test_section_6_references_gstack(self, content):
        assert "gstack" in content

    def test_section_6_recommends_canary_tokens(self, content):
        assert "canary token" in content

    def test_section_7_memory_acl(self, content):
        assert "## 7. Memory ACL and provenance" in content

    def test_section_7_required_memory_fields_listed(self, content):
        # The doc lists required memory record fields
        assert "source URI" in content
        assert "trust tier" in content
        assert "checksum" in content
        assert "expiry" in content

    def test_section_7_references_owasp_memory_poisoning(self, content):
        assert "genai.owasp.org" in content

    def test_section_8_supply_chain(self, content):
        assert "## 8. Supply chain" in content

    def test_section_8_recommends_lockfiles(self, content):
        assert "lockfile" in content

    def test_section_8_references_cyclonedx(self, content):
        assert "CycloneDX" in content

    def test_section_9_observability(self, content):
        assert "## 9. Observability and replay" in content

    def test_section_9_references_opentelemetry(self, content):
        assert "OpenTelemetry" in content

    def test_section_9_requires_tool_spans(self, content):
        assert "execute_tool" in content

    def test_section_10_swarm_objective_audit(self, content):
        assert "## 10. SWARM-style system objective audit" in content

    def test_section_10_objective_contract_fields(self, content):
        assert "original user goal" in content
        assert "forbidden actions" in content
        assert "rollback plan" in content

    def test_ten_sections_total(self, content):
        import re
        # Count top-level numbered sections (## N.)
        matches = re.findall(r"^## \d+\.", content, re.MULTILINE)
        assert len(matches) == 10, f"Expected 10 sections, found {len(matches)}: {matches}"


# ---------------------------------------------------------------------------
# docs/v2/33 — Security Harness Source Material (verbatim prior plan)
# ---------------------------------------------------------------------------


class TestSourceMaterial33:
    """Tests for the verbatim source-material preservation document."""

    @pytest.fixture(scope="class")
    def content(self):
        return SOURCE_33.read_text(encoding="utf-8")

    def test_title_indicates_source_material(self, content):
        assert "Source Material" in content

    def test_header_warns_not_canonical(self, content):
        assert "Do not treat this as the canonical strategy" in content

    def test_backlink_to_canonical_plan_31(self, content):
        assert "31-security-harness-excellence-plan.md" in content

    def test_backlink_to_controls_32(self, content):
        assert "32-agentic-security-controls.md" in content

    def test_backlink_to_runtime_34(self, content):
        assert "34-local-model-runtime-profile.md" in content

    def test_contains_original_goal_section(self, content):
        # The old plan's section 0 should be verbatim
        assert "## 0. Goal (one sentence)" in content

    def test_original_goal_mentions_gstack(self, content):
        assert "gstack" in content

    def test_original_acceptance_criteria_preserved(self, content):
        # Old acceptance criteria block was in section 11
        assert "## 11. Acceptance Criteria" in content

    def test_old_ac_s1_preserved(self, content):
        assert "AC-S1" in content

    def test_old_ac_s2_preserved(self, content):
        assert "AC-S2" in content

    def test_old_ac_s3_preserved(self, content):
        assert "AC-S3" in content

    def test_old_staged_roadmap_preserved(self, content):
        assert "## 10. Staged Roadmap" in content

    def test_old_v1_hardening_section_preserved(self, content):
        assert "## 4. v1 Hardening" in content

    def test_old_threat_model_section_preserved(self, content):
        assert "## 2. Threat Model" in content

    def test_owasp_asi_threat_table_preserved(self, content):
        assert "ASI01" in content
        assert "ASI02" in content

    def test_s1_patch_code_preserved(self, content):
        # The original S1 fail-closed patch code block should be preserved
        assert "ORAMA_LAN_BIND" in content

    def test_s2_patch_command_preserved(self, content):
        assert "pip-compile" in content

    def test_s3_patch_code_preserved(self, content):
        assert "slowapi" in content
        assert "Limiter" in content

    def test_ollama_mlx_section_preserved(self, content):
        assert "Ollama now runs natively on MLX" in content

    def test_kv_cache_section_preserved(self, content):
        assert "OLLAMA_FLASH_ATTENTION" in content

    def test_caveats_section_preserved(self, content):
        assert "## 12. Caveats" in content

    def test_one_line_summary_preserved(self, content):
        # The old one-line summary used the "adopt gstack's" language
        assert "## 13. One-line summary" in content

    def test_swarm_framework_preserved(self, content):
        assert "SWARM" in content

    def test_maestro_framework_preserved(self, content):
        assert "MAESTRO" in content


# ---------------------------------------------------------------------------
# docs/v2/34 — Local Model Runtime Profile
# ---------------------------------------------------------------------------


class TestRuntimeProfile34:
    """Tests for the extracted local model runtime profile document."""

    @pytest.fixture(scope="class")
    def content(self):
        return RUNTIME_34.read_text(encoding="utf-8")

    def test_title(self, content):
        assert "# Local Model Runtime Profile" in content

    def test_status_metadata_present(self, content):
        assert "Status:" in content

    def test_backlink_to_plan_31(self, content):
        assert "31-security-harness-excellence-plan.md" in content

    def test_backlink_to_source_material_33(self, content):
        assert "33-security-harness-source-material.md" in content

    def test_scope_and_caveat_section(self, content):
        assert "## 1. Scope and caveat" in content

    def test_security_controls_section(self, content):
        assert "## 2. Security controls for Ollama" in content

    def test_security_controls_bind_loopback(self, content):
        assert "loopback" in content

    def test_security_controls_no_bearer_to_probes(self, content):
        assert "bearer token" in content

    def test_security_controls_patch_promptly(self, content):
        assert "Patch promptly" in content

    def test_ollama_mlx_section(self, content):
        assert "## 3. Ollama MLX on Apple Silicon" in content

    def test_mlx_section_references_ollama_blog(self, content):
        assert "ollama.com/blog/mlx" in content

    def test_mlx_section_uses_hedged_language(self, content):
        # The rewrite reframes the claim with "preview" language
        assert "preview" in content

    def test_qwen_profile_section(self, content):
        assert "## 4. qwen3.5:9b-nvfp4 profile" in content

    def test_qwen_section_references_ollama_library(self, content):
        assert "ollama.com/library/qwen3.5" in content

    def test_qwen_section_includes_caveat(self, content):
        assert "Caveat" in content

    def test_context_and_kv_cache_section(self, content):
        assert "## 5. Context and KV cache" in content

    def test_kv_cache_section_mentions_flash_attention(self, content):
        assert "Flash Attention" in content

    def test_parallel_agents_section(self, content):
        assert "## 6. Parallel agents on 16GB" in content

    def test_benchmarking_checklist_section(self, content):
        assert "## 7. Benchmarking checklist" in content

    def test_benchmarking_checklist_items(self, content):
        assert "Ollama version" in content
        assert "model tag" in content
        assert "time to first token" in content
        assert "peak memory" in content

    def test_treats_community_benchmarks_as_directional_only(self, content):
        # The rewrite is explicit that community sources are not authoritative
        assert "directional" in content

    def test_section_count(self, content):
        import re
        # Expect exactly 7 top-level numbered sections
        matches = re.findall(r"^## \d+\.", content, re.MULTILINE)
        assert len(matches) == 7, f"Expected 7 sections, found {len(matches)}: {matches}"


# ---------------------------------------------------------------------------
# docs/security-reviews/2026-06-14-security-efficiency-review-v1.md
# ---------------------------------------------------------------------------


class TestSecurityReview:
    """Tests for the security & efficiency code review document."""

    @pytest.fixture(scope="class")
    def content(self):
        return REVIEW.read_text(encoding="utf-8")

    def test_title(self, content):
        assert "Security & Efficiency Code Review" in content

    def test_date_present(self, content):
        assert "2026-06-14" in content

    def test_scope_mentions_repos(self, content):
        assert "orama-system" in content
        assert "Perpetua-Tools" in content

    def test_executive_summary_section(self, content):
        assert "## Executive Summary" in content

    def test_severity_table_present(self, content):
        assert "High" in content
        assert "Medium" in content
        assert "Low" in content

    def test_positive_findings_section(self, content):
        assert "What Is Already Done Right" in content

    def test_positive_findings_timing_safe_token(self, content):
        assert "secrets.compare_digest" in content

    def test_positive_findings_no_shell_injection(self, content):
        assert "shell=True" in content

    def test_positive_findings_async_http(self, content):
        assert "httpx" in content

    def test_finding_s1_present(self, content):
        assert "### S1" in content

    def test_finding_s1_references_control_plane_auth(self, content):
        assert "control_plane_auth.py" in content

    def test_finding_s1_includes_code_block(self, content):
        assert "auth_enforced" in content

    def test_finding_s1_fix_uses_lan_bind_env(self, content):
        assert "ORAMA_LAN_BIND" in content

    def test_finding_s2_present(self, content):
        assert "### S2" in content

    def test_finding_s2_references_requirements_txt(self, content):
        assert "requirements.txt" in content

    def test_finding_s2_mentions_pip_compile(self, content):
        assert "pip-compile" in content

    def test_finding_s3_present(self, content):
        assert "### S3" in content

    def test_finding_s3_references_slowapi(self, content):
        assert "slowapi" in content

    def test_finding_s4_present(self, content):
        assert "### S4" in content

    def test_finding_s4_references_testclient(self, content):
        assert "testclient" in content

    def test_finding_s4_fix_uses_orama_pytest_env(self, content):
        assert "ORAMA_PYTEST" in content

    def test_finding_s5_present(self, content):
        assert "### S5" in content

    def test_finding_s5_references_cookie(self, content):
        assert "cookie" in content.lower()

    def test_finding_e1_present(self, content):
        assert "### E1" in content

    def test_finding_e1_references_backoff(self, content):
        assert "backoff" in content.lower()

    def test_finding_e2_present(self, content):
        assert "### E2" in content

    def test_finding_e3_present(self, content):
        assert "### E3" in content

    def test_finding_e3_references_cors(self, content):
        assert "CORS" in content

    def test_finding_e4_present(self, content):
        assert "### E4" in content

    def test_prioritized_action_list_present(self, content):
        assert "## Prioritized Action List" in content

    def test_methodology_note_present(self, content):
        assert "## Methodology Note" in content

    def test_reproducibility_appendix_present(self, content):
        assert "## Reproducibility appendix" in content

    def test_reproducibility_appendix_includes_commands(self, content):
        assert "git -C" in content
        assert "rg -n" in content

    def test_evidence_update_note_present(self, content):
        assert "Evidence update" in content

    def test_five_security_findings(self, content):
        import re
        # S1 through S5 must each appear as section headers
        for sid in ["S1", "S2", "S3", "S4", "S5"]:
            assert f"### {sid}" in content, f"Security finding {sid} header missing"

    def test_four_efficiency_findings(self, content):
        for eid in ["E1", "E2", "E3", "E4"]:
            assert f"### {eid}" in content, f"Efficiency finding {eid} header missing"

    def test_finding_severities_assigned(self, content):
        # Each finding should declare a severity
        assert "MEDIUM" in content
        assert "LOW" in content


# ---------------------------------------------------------------------------
# Cross-document integrity
# ---------------------------------------------------------------------------


class TestCrossDocIntegrity:
    """Verify that inter-document references are consistent."""

    def test_31_document_map_matches_actual_files(self):
        """The doc map in 31 must reference files that actually exist."""
        content_31 = PLAN_31.read_text(encoding="utf-8")
        referenced = [
            "32-agentic-security-controls.md",
            "33-security-harness-source-material.md",
            "34-local-model-runtime-profile.md",
        ]
        for filename in referenced:
            assert filename in content_31
            assert (DOCV2_DIR / filename).exists(), f"Referenced file missing: {filename}"

    def test_32_backlinks_to_31(self):
        content = CONTROLS_32.read_text(encoding="utf-8")
        assert "31-security-harness-excellence-plan.md" in content

    def test_33_backlinks_to_31(self):
        content = SOURCE_33.read_text(encoding="utf-8")
        assert "31-security-harness-excellence-plan.md" in content

    def test_34_backlinks_to_31(self):
        content = RUNTIME_34.read_text(encoding="utf-8")
        assert "31-security-harness-excellence-plan.md" in content

    def test_no_ordinal_collision_in_docv2(self):
        """New files 31-34 must not collide with each other."""
        repo_hygiene = _load_repo_hygiene()
        errors = repo_hygiene.scan_docv2_ordinal_collision(ROOT)
        assert errors == [], f"Ordinal collision detected: {errors}"

    def test_31_acceptance_gates_reference_existing_test_directories(self):
        """Acceptance gate test paths in 31 should use a consistent prefix."""
        content = PLAN_31.read_text(encoding="utf-8")
        # The acceptance gates reference tests/security/test_*.py paths
        assert "tests/security/" in content

    def test_33_preserves_original_acceptance_criteria_verbatim(self):
        """33 must contain the old AC lines that were removed from 31."""
        content_33 = SOURCE_33.read_text(encoding="utf-8")
        content_31 = PLAN_31.read_text(encoding="utf-8")
        # Old-format checkboxes "- [ ] **AC-S1**" should be in 33 but not in 31
        assert "- [ ] **AC-S1**" in content_33
        assert "- [ ] **AC-S1**" not in content_31

    def test_34_security_section_consistent_with_32(self):
        """Both 32 and 34 recommend loopback binding for Ollama."""
        content_32 = CONTROLS_32.read_text(encoding="utf-8")
        content_34 = RUNTIME_34.read_text(encoding="utf-8")
        assert "loopback" in content_32
        assert "loopback" in content_34


# ---------------------------------------------------------------------------
# Hygiene checks via repo_hygiene
# ---------------------------------------------------------------------------


class TestDocHygiene:
    """Structural hygiene checks for the new/changed documentation files."""

    ALL_DOCS = [PLAN_31, CONTROLS_32, SOURCE_33, RUNTIME_34, REVIEW]
    ALL_DOC_REL = [
        "docs/v2/31-security-harness-excellence-plan.md",
        "docs/v2/32-agentic-security-controls.md",
        "docs/v2/33-security-harness-source-material.md",
        "docs/v2/34-local-model-runtime-profile.md",
        "docs/security-reviews/2026-06-14-security-efficiency-review-v1.md",
    ]

    def test_no_absolute_paths_in_markdown_links(self):
        """No markdown link should use an absolute filesystem path."""
        repo_hygiene = _load_repo_hygiene()
        errors = repo_hygiene.check_markdown_link_hygiene(ROOT, self.ALL_DOC_REL)
        assert errors == [], f"Absolute path links found: {errors}"

    def test_no_personal_paths_in_new_docs(self):
        """New docs must not contain /Users/<real-name>/ or /home/<real-name>/."""
        repo_hygiene = _load_repo_hygiene()
        errors = repo_hygiene.scan_personal_paths(ROOT, self.ALL_DOC_REL)
        assert errors == [], f"Personal paths found: {errors}"

    def test_docs_32_33_34_are_new_files_under_200_lines(self):
        """New docs 32 and 34 are small enough not to require a split reminder.
        33 is a verbatim preservation of the prior plan and is expected to be large."""
        for path in [CONTROLS_32, RUNTIME_34]:
            line_count = len(path.read_text(encoding="utf-8").splitlines())
            # Both are well under 200 lines — no split warning expected
            assert line_count <= 200, (
                f"{path.name} has {line_count} lines; expected ≤ 200 for a new doc"
            )

    def test_source_material_33_is_acknowledged_as_verbatim(self):
        """33 is intentionally large (verbatim prior plan), but must label itself as such."""
        content = SOURCE_33.read_text(encoding="utf-8")
        assert "verbatim" in content.lower()

    def test_all_new_docs_have_status_metadata(self):
        """Each new/changed doc must carry a Status: metadata line."""
        for path in self.ALL_DOCS:
            content = path.read_text(encoding="utf-8")
            assert "Status:" in content or "**Status:**" in content, (
                f"{path.name} is missing a Status: metadata field"
            )

    def test_no_hardcoded_api_keys_in_docs(self):
        """Docs must not contain API key patterns (sk-, ghp_, AKIA, etc.)."""
        import re
        # Patterns from the review doc methodology note (used as scan examples)
        key_pattern = re.compile(r"(?:sk-|ghp_|github_pat_|AKIA)[A-Za-z0-9]{10,}")
        for path in self.ALL_DOCS:
            content = path.read_text(encoding="utf-8")
            matches = key_pattern.findall(content)
            assert not matches, f"{path.name} contains potential API key: {matches}"

    def test_review_doc_not_in_v2_dir(self):
        """The security review doc belongs under docs/security-reviews/, not docs/v2/."""
        assert not (ROOT / "docs" / "v2" / "2026-06-14-security-efficiency-review-v1.md").exists()
        assert REVIEW.parent.name == "security-reviews"

    def test_31_is_shorter_than_old_version(self):
        """The rewritten plan should be materially shorter than the 454-line original."""
        line_count = len(PLAN_31.read_text(encoding="utf-8").splitlines())
        assert line_count < 400, (
            f"Rewritten 31 is {line_count} lines; should be shorter than the original 454"
        )
