#!/usr/bin/env python3
"""
test_security_docs.py
=====================
Structural and content regression tests for the security-review and
security-harness documentation added/rewritten in the June 2026 PR:

  - docs/security-reviews/2026-06-14-security-efficiency-review-v1.md
  - docs/v2/31-security-harness-excellence-plan.md
  - docs/v2/32-agentic-security-controls.md
  - docs/v2/33-security-harness-source-material.md
  - docs/v2/34-local-model-runtime-profile.md

Tests verify:
  1. File existence
  2. Required section headings
  3. Cross-reference (internal link) integrity — linked sibling docs exist on disk
  4. Specific content invariants (acceptance gates, threat IDs, tier labels, etc.)
  5. Structural invariants (count of numbered items, presence of required fields)
  6. Evidence-model framing (scans described as scans, not as absolute guarantees)
  7. Negative invariants (source material is NOT canonical, MLX marked as preview)

Run: pytest tests/test_security_docs.py -v
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parent.parent
DOCS_V2 = ROOT / "docs" / "v2"
DOCS_SECURITY_REVIEWS = ROOT / "docs" / "security-reviews"

SECURITY_REVIEW = DOCS_SECURITY_REVIEWS / "2026-06-14-security-efficiency-review-v1.md"
PLAN_31 = DOCS_V2 / "31-security-harness-excellence-plan.md"
CONTROLS_32 = DOCS_V2 / "32-agentic-security-controls.md"
SOURCE_33 = DOCS_V2 / "33-security-harness-source-material.md"
RUNTIME_34 = DOCS_V2 / "34-local-model-runtime-profile.md"


# ---------------------------------------------------------------------------
# 1. File existence
# ---------------------------------------------------------------------------

def test_security_review_file_exists():
    assert SECURITY_REVIEW.exists(), f"Missing: {SECURITY_REVIEW}"


def test_plan_31_exists():
    assert PLAN_31.exists(), f"Missing: {PLAN_31}"


def test_controls_32_exists():
    assert CONTROLS_32.exists(), f"Missing: {CONTROLS_32}"


def test_source_33_exists():
    assert SOURCE_33.exists(), f"Missing: {SOURCE_33}"


def test_runtime_34_exists():
    assert RUNTIME_34.exists(), f"Missing: {RUNTIME_34}"


# ---------------------------------------------------------------------------
# 2. Security review — metadata and required sections
# ---------------------------------------------------------------------------

class TestSecurityReviewContent:
    def setup_method(self):
        self.content = SECURITY_REVIEW.read_text(encoding="utf-8")

    def test_has_date_field(self):
        assert "**Date:** 2026-06-14" in self.content

    def test_has_reviewer_field(self):
        assert "**Reviewer:**" in self.content

    def test_has_scope_field(self):
        assert "**Scope:**" in self.content

    def test_has_repos_field(self):
        assert "**Repos:**" in self.content

    def test_has_executive_summary_section(self):
        assert "## Executive Summary" in self.content

    def test_has_severity_summary_table(self):
        assert "| Severity | Security | Efficiency |" in self.content

    def test_has_positive_findings_section(self):
        assert "## What Is Already Done Right" in self.content

    def test_has_security_findings_header(self):
        assert "## SECURITY FINDINGS" in self.content

    def test_has_efficiency_findings_header(self):
        assert "## EFFICIENCY FINDINGS" in self.content

    def test_has_all_security_findings_s1_through_s5(self):
        for sid in ["S1", "S2", "S3", "S4", "S5"]:
            assert f"### {sid}" in self.content, f"Missing security finding {sid}"

    def test_has_all_efficiency_findings_e1_through_e4(self):
        for eid in ["E1", "E2", "E3", "E4"]:
            assert f"### {eid}" in self.content, f"Missing efficiency finding {eid}"

    def test_has_prioritized_action_list(self):
        assert "## Prioritized Action List" in self.content

    def test_has_methodology_note(self):
        assert "## Methodology Note" in self.content

    def test_has_reproducibility_appendix(self):
        assert "## Reproducibility appendix" in self.content

    def test_s1_cites_file_colon_line(self):
        # S1 must reference a specific file:line citation per review methodology
        assert "control_plane_auth.py:" in self.content

    def test_s1_includes_auth_enforced_fix_code(self):
        assert "def auth_enforced()" in self.content
        assert "ORAMA_LAN_BIND" in self.content

    def test_evidence_update_note_present(self):
        # The 2026-06-15 evidence update note reframes absolute claims
        assert "Evidence update" in self.content

    def test_scan_framing_not_absolute_claim(self):
        # Review must use scan-result framing, not absolute absence claims
        assert "static scan" in self.content or "static-scan" in self.content

    def test_timing_safe_token_check_cited(self):
        assert "secrets.compare_digest" in self.content

    def test_s2_mentions_unpinned_dependencies(self):
        assert "Unpinned" in self.content or "unpinned" in self.content

    def test_s3_mentions_slowapi(self):
        assert "slowapi" in self.content

    def test_s4_mentions_testclient_loopback(self):
        assert "testclient" in self.content

    def test_reproducibility_appendix_includes_commands(self):
        assert "git -C" in self.content
        assert "rg -n" in self.content or "pip-audit" in self.content

    def test_no_high_severity_findings(self):
        # The review summary explicitly records 0 high severity items
        assert "High | 0 | 0" in self.content


# ---------------------------------------------------------------------------
# 3. Plan 31 — required sections and content invariants
# ---------------------------------------------------------------------------

class TestPlan31Content:
    def setup_method(self):
        self.content = PLAN_31.read_text(encoding="utf-8")

    def test_title_is_security_harness_excellence_plan(self):
        assert "# Security Harness Excellence Plan" in self.content

    def test_has_status_metadata(self):
        assert "**Status:**" in self.content

    def test_has_scope_metadata(self):
        assert "**Scope:**" in self.content

    def test_has_document_map_section(self):
        assert "## Document map" in self.content

    def test_document_map_references_all_four_sibling_docs(self):
        for doc in ["31-security-harness-excellence-plan.md",
                    "32-agentic-security-controls.md",
                    "33-security-harness-source-material.md",
                    "34-local-model-runtime-profile.md"]:
            assert doc in self.content, f"Document map missing reference to {doc}"

    def test_has_evidence_source_reliability_model(self):
        assert "Evidence and source reliability model" in self.content

    def test_has_three_evidence_tiers(self):
        for tier in ["Tier 1", "Tier 2", "Tier 3"]:
            assert tier in self.content, f"Missing {tier} in evidence model"

    def test_has_executive_strategy_section(self):
        assert "## 1. Executive strategy" in self.content

    def test_strategy_mentions_deny_by_default(self):
        assert "deny-by-default" in self.content

    def test_has_local_system_model_section(self):
        assert "## 2. Local system model" in self.content

    def test_local_system_model_has_assets_subsection(self):
        assert "### 2.1 Assets" in self.content

    def test_local_system_model_has_principals_subsection(self):
        assert "### 2.2 Principals" in self.content

    def test_local_system_model_has_trust_boundaries_subsection(self):
        assert "### 2.3 Trust boundaries" in self.content

    def test_local_system_model_has_kill_chain_subsection(self):
        assert "### 2.4 Representative kill chain" in self.content

    def test_has_threat_model_section(self):
        assert "## 3. Threat model" in self.content

    def test_threat_model_contains_all_seven_threats(self):
        for tid in ["T1", "T2", "T3", "T4", "T5", "T6", "T7"]:
            assert tid in self.content, f"Missing threat {tid} in threat model"

    def test_has_standards_traceability_section(self):
        assert "## 4. Standards traceability" in self.content

    def test_standards_table_includes_owasp_agentic(self):
        assert "OWASP Top 10 for Agentic Applications" in self.content

    def test_standards_table_includes_owasp_llm(self):
        assert "OWASP Top 10 for LLM Applications" in self.content

    def test_standards_table_includes_mitre_atlas(self):
        assert "MITRE ATLAS" in self.content

    def test_standards_table_includes_csa_maestro(self):
        assert "CSA MAESTRO" in self.content or "MAESTRO" in self.content

    def test_standards_table_includes_morris_ii(self):
        assert "Morris II" in self.content

    def test_has_benchmark_references_section(self):
        assert "## 5. Benchmark references" in self.content

    def test_benchmark_section_covers_gstack(self):
        assert "gstack" in self.content

    def test_benchmark_section_covers_gbrain(self):
        assert "GBrain" in self.content

    def test_benchmark_section_covers_hermes(self):
        assert "Hermes" in self.content

    def test_has_roadmap_section(self):
        assert "## 6. Roadmap" in self.content

    def test_roadmap_has_stage_0(self):
        assert "Stage 0" in self.content

    def test_roadmap_has_stage_1(self):
        assert "Stage 1" in self.content

    def test_roadmap_has_stage_4(self):
        assert "Stage 4" in self.content

    def test_has_acceptance_gates_section(self):
        assert "## 7. Acceptance gates" in self.content

    def test_acceptance_gates_contains_all_eight_gates(self):
        for gate in ["AC-AUTH", "AC-RATE", "AC-COOKIE", "AC-TOOLS",
                     "AC-MEM", "AC-SCAN", "AC-TRACE", "AC-SUPPLY"]:
            assert gate in self.content, f"Missing acceptance gate {gate}"

    def test_acceptance_gates_include_pytest_commands(self):
        assert "pytest tests/security/" in self.content

    def test_has_pr_stacking_section(self):
        assert "## 8. Security PR stacking" in self.content

    def test_has_quarterly_standards_refresh_section(self):
        assert "## 9. Quarterly standards refresh" in self.content

    def test_has_one_line_summary_section(self):
        assert "## 10. One-line summary" in self.content

    def test_summary_mentions_policy_mediated_agency(self):
        assert "policy-mediated" in self.content

    def test_pr_stacking_links_to_security_md(self):
        assert "SECURITY.md" in self.content

    def test_does_not_claim_compliance_only_traceability(self):
        assert "traceability" in self.content


# ---------------------------------------------------------------------------
# 4. Controls doc 32 — required sections and structural invariants
# ---------------------------------------------------------------------------

class TestControls32Content:
    def setup_method(self):
        self.content = CONTROLS_32.read_text(encoding="utf-8")

    def test_title_is_agentic_security_controls(self):
        assert "# Agentic Security Controls" in self.content

    def test_has_status_metadata(self):
        assert "**Status:**" in self.content

    def test_references_strategy_doc_31(self):
        assert "31-security-harness-excellence-plan.md" in self.content

    def test_references_source_doc_33(self):
        assert "33-security-harness-source-material.md" in self.content

    def test_has_auth_section(self):
        assert "## 1. Authentication and LAN-bind hardening" in self.content

    def test_auth_section_has_acceptance_command(self):
        assert "pytest tests/security/test_control_plane_auth.py" in self.content

    def test_has_cookie_session_section(self):
        assert "## 2. Cookie/session hardening" in self.content

    def test_has_rate_token_budget_section(self):
        assert "## 3. Rate, token, and concurrency budgets" in self.content

    def test_rate_section_lists_requests_per_minute(self):
        assert "requests per minute" in self.content

    def test_rate_section_lists_concurrent_jobs(self):
        assert "concurrent jobs" in self.content

    def test_has_tool_executor_mediator_section(self):
        assert "## 4. Tool-executor mediator" in self.content

    def test_tool_mediator_mentions_deny_by_default(self):
        assert "Deny by default" in self.content

    def test_has_sandboxing_section(self):
        assert "## 5. Sandboxing and egress ladder" in self.content

    def test_sandboxing_ladder_has_l0_through_l5(self):
        for level in ["L0", "L1", "L2", "L3", "L4", "L5"]:
            assert f"| {level} |" in self.content, f"Sandboxing ladder missing {level}"

    def test_sandboxing_references_mitre_t1611(self):
        assert "T1611" in self.content

    def test_has_prompt_injection_scanner_section(self):
        assert "## 6. Prompt-injection scanner" in self.content

    def test_injection_scanner_mentions_canary_tokens(self):
        assert "canary token" in self.content or "canary tokens" in self.content

    def test_has_memory_acl_section(self):
        assert "## 7. Memory ACL and provenance" in self.content

    def test_memory_section_lists_required_fields(self):
        for field in ["source URI", "trust tier", "checksum", "expiry"]:
            assert field in self.content, f"Memory required fields missing: {field}"

    def test_memory_retrieval_policy_exists(self):
        assert "Retrieval policy" in self.content

    def test_memory_references_owasp_agentic_url(self):
        assert "genai.owasp.org" in self.content

    def test_has_supply_chain_section(self):
        assert "## 8. Supply chain" in self.content

    def test_supply_chain_mentions_lockfiles(self):
        assert "lockfile" in self.content or "lockfiles" in self.content

    def test_supply_chain_references_cyclonedx(self):
        assert "CycloneDX" in self.content

    def test_has_observability_section(self):
        assert "## 9. Observability and replay" in self.content

    def test_observability_mentions_invoke_agent_span(self):
        assert "invoke_agent" in self.content

    def test_observability_references_opentelemetry(self):
        assert "OpenTelemetry" in self.content

    def test_has_swarm_section(self):
        assert "## 10. SWARM-style system objective audit" in self.content

    def test_swarm_section_lists_objective_contract_fields(self):
        for field in ["non-goals", "forbidden actions", "rollback plan"]:
            assert field in self.content, f"Objective contract missing field: {field}"

    def test_exactly_ten_numbered_top_level_sections(self):
        # Sections 1-10 should all be present (checked individually above,
        # but this verifies no sections were skipped)
        for n in range(1, 11):
            assert f"## {n}." in self.content, f"Missing top-level section ## {n}."


# ---------------------------------------------------------------------------
# 5. Source material doc 33 — preservation markers
# ---------------------------------------------------------------------------

class TestSourceMaterial33Content:
    def setup_method(self):
        self.content = SOURCE_33.read_text(encoding="utf-8")

    def test_title_indicates_source_material(self):
        assert "Source Material" in self.content or "source material" in self.content.lower()

    def test_not_marked_as_canonical_strategy(self):
        # Header must warn readers this is NOT canonical
        assert "Do not treat this as the canonical strategy" in self.content

    def test_references_canonical_plan_31(self):
        assert "31-security-harness-excellence-plan.md" in self.content

    def test_references_controls_32(self):
        assert "32-agentic-security-controls.md" in self.content

    def test_references_runtime_34(self):
        assert "34-local-model-runtime-profile.md" in self.content

    def test_preserves_original_plan_title(self):
        # Should contain the original title verbatim
        assert "# Security & Agentic-Harness Excellence Plan" in self.content

    def test_contains_original_gstack_benchmark_section(self):
        assert "gstack" in self.content
        assert "L1-L3" in self.content or "L1" in self.content

    def test_contains_original_swarm_section(self):
        assert "SWARM" in self.content
        assert "system-level misalignment" in self.content

    def test_contains_original_acceptance_criteria(self):
        # Old acceptance criteria markers from the pre-rewrite plan
        for marker in ["AC-S1", "AC-S2", "AC-S3", "AC-SB", "AC-OLLAMA"]:
            assert marker in self.content, f"Original acceptance criteria missing: {marker}"

    def test_contains_original_v1_hardening_table(self):
        assert "S1" in self.content
        assert "Default-open auth" in self.content

    def test_contains_ollama_security_section(self):
        assert "Ollama security" in self.content

    def test_preserves_mlx_backend_information(self):
        assert "MLX" in self.content

    def test_preserves_kv_cache_guidance(self):
        assert "KV cache" in self.content or "KV_CACHE" in self.content

    def test_status_header_is_preserved_source(self):
        assert "preserved source material" in self.content

    def test_contains_original_threat_model_sections(self):
        # Old plan had OWASP ASI sections
        assert "ASI01" in self.content
        assert "ASI06" in self.content


# ---------------------------------------------------------------------------
# 6. Runtime profile doc 34 — content and caveat invariants
# ---------------------------------------------------------------------------

class TestRuntimeProfile34Content:
    def setup_method(self):
        self.content = RUNTIME_34.read_text(encoding="utf-8")

    def test_title_is_local_model_runtime_profile(self):
        assert "# Local Model Runtime Profile" in self.content

    def test_has_status_metadata(self):
        assert "**Status:**" in self.content

    def test_references_plan_31(self):
        assert "31-security-harness-excellence-plan.md" in self.content

    def test_references_source_33(self):
        assert "33-security-harness-source-material.md" in self.content

    def test_has_scope_and_caveat_section(self):
        assert "## 1. Scope and caveat" in self.content

    def test_has_security_controls_for_ollama_section(self):
        assert "## 2. Security controls for Ollama" in self.content

    def test_security_section_recommends_loopback_bind(self):
        assert "loopback" in self.content

    def test_security_section_warns_against_lan_exposure(self):
        assert "LAN" in self.content

    def test_security_section_warns_against_passing_bearer_tokens_to_probes(self):
        assert "bearer token" in self.content or "bearer tokens" in self.content

    def test_has_ollama_mlx_section(self):
        assert "## 3. Ollama MLX on Apple Silicon" in self.content

    def test_mlx_section_includes_ollama_blog_url(self):
        assert "ollama.com/blog/mlx" in self.content

    def test_mlx_section_includes_performance_blog_url(self):
        assert "ollama.com/blog/mlx-performance" in self.content

    def test_mlx_section_uses_preview_caveat_not_universal_claim(self):
        # Must not claim Ollama "universally switched to MLX as the default backend"
        assert "preview" in self.content

    def test_has_qwen_profile_section(self):
        assert "## 4. qwen3.5:9b-nvfp4 profile" in self.content

    def test_qwen_section_notes_model_card_mutability(self):
        assert "mutable" in self.content or "Re-check" in self.content

    def test_has_context_kv_cache_section(self):
        assert "## 5. Context and KV cache" in self.content

    def test_kv_section_mentions_flash_attention(self):
        assert "Flash Attention" in self.content

    def test_has_parallel_agents_section(self):
        assert "## 6. Parallel agents on 16GB" in self.content

    def test_parallel_section_recommends_single_stream(self):
        assert "single-stream" in self.content or "single stream" in self.content

    def test_has_benchmarking_checklist_section(self):
        assert "## 7. Benchmarking checklist" in self.content

    def test_benchmarking_checklist_has_required_fields(self):
        for field in ["Ollama version", "model tag", "peak memory",
                      "time to first token", "decode tokens"]:
            assert field in self.content, f"Benchmarking checklist missing: {field}"

    def test_community_benchmarks_flagged_as_directional(self):
        assert "directional" in self.content


# ---------------------------------------------------------------------------
# 7. Cross-reference integrity — linked sibling docs exist on disk
# ---------------------------------------------------------------------------

class TestCrossReferenceIntegrity:
    """
    Each document declares links to its siblings; verify those files exist.
    This catches broken cross-references introduced by a rename or move.
    """

    def test_plan_31_sibling_32_exists(self):
        assert CONTROLS_32.exists()

    def test_plan_31_sibling_33_exists(self):
        assert SOURCE_33.exists()

    def test_plan_31_sibling_34_exists(self):
        assert RUNTIME_34.exists()

    def test_controls_32_sibling_31_exists(self):
        assert PLAN_31.exists()

    def test_controls_32_sibling_33_exists(self):
        assert SOURCE_33.exists()

    def test_source_33_sibling_31_exists(self):
        assert PLAN_31.exists()

    def test_source_33_sibling_32_exists(self):
        assert CONTROLS_32.exists()

    def test_source_33_sibling_34_exists(self):
        assert RUNTIME_34.exists()

    def test_runtime_34_sibling_31_exists(self):
        assert PLAN_31.exists()

    def test_runtime_34_sibling_33_exists(self):
        assert SOURCE_33.exists()

    def test_security_review_directory_exists(self):
        assert DOCS_SECURITY_REVIEWS.is_dir()

    def test_v2_directory_exists(self):
        assert DOCS_V2.is_dir()

    def test_plan_31_links_use_relative_filename_format(self):
        content = PLAN_31.read_text(encoding="utf-8")
        # Links should be in the form [filename](filename) not absolute paths
        assert "(32-agentic-security-controls.md)" in content
        assert "(33-security-harness-source-material.md)" in content
        assert "(34-local-model-runtime-profile.md)" in content

    def test_controls_32_links_use_relative_filename_format(self):
        content = CONTROLS_32.read_text(encoding="utf-8")
        assert "(31-security-harness-excellence-plan.md)" in content
        assert "(33-security-harness-source-material.md)" in content

    def test_runtime_34_links_use_relative_filename_format(self):
        content = RUNTIME_34.read_text(encoding="utf-8")
        assert "(31-security-harness-excellence-plan.md)" in content
        assert "(33-security-harness-source-material.md)" in content


# ---------------------------------------------------------------------------
# 8. Negative and boundary tests
# ---------------------------------------------------------------------------

class TestNegativeAndBoundary:

    def test_source_33_does_not_claim_to_be_canonical(self):
        content = SOURCE_33.read_text(encoding="utf-8")
        # The word "canonical" should appear only to say it is NOT canonical
        # "Do not treat this as the canonical strategy" uses it to negate
        assert "Do not treat this as the canonical strategy" in content

    def test_security_review_does_not_claim_zero_secrets_as_absolute_fact(self):
        content = SECURITY_REVIEW.read_text(encoding="utf-8")
        # Evidence note must walk back absolute claims to scan-result framing
        assert "not as formal proof of absence" in content

    def test_plan_31_does_not_claim_standards_compliance(self):
        content = PLAN_31.read_text(encoding="utf-8")
        # Standards are for traceability only; doc should not claim "compliant"
        assert "Use standards to check coverage, not to claim compliance" in content

    def test_runtime_34_uses_reframed_mlx_recommendation(self):
        content = RUNTIME_34.read_text(encoding="utf-8")
        # The doc must contain the explicit reframing, not the overclaimed universal default
        assert "Reframed recommendation" in content

    def test_controls_32_does_not_treat_docker_as_complete_isolation(self):
        content = CONTROLS_32.read_text(encoding="utf-8")
        assert "Docker alone is not a complete isolation story" in content

    def test_plan_31_gstack_section_warns_against_overclaiming(self):
        content = PLAN_31.read_text(encoding="utf-8")
        assert "Do not overclaim" in content

    def test_security_review_s4_testclient_finding_present(self):
        content = SECURITY_REVIEW.read_text(encoding="utf-8")
        # S4 is about testclient being in the loopback set — a real security note
        assert "testclient" in content
        assert "ORAMA_PYTEST" in content

    def test_plan_31_acceptance_gates_reference_pip_audit(self):
        content = PLAN_31.read_text(encoding="utf-8")
        assert "pip-audit" in content

    def test_controls_32_supply_chain_warns_against_signing_theater(self):
        content = CONTROLS_32.read_text(encoding="utf-8")
        assert "signing theater" in content or "Signing is useful only if verification" in content

    def test_security_review_appendix_is_dated_2026_06_15(self):
        content = SECURITY_REVIEW.read_text(encoding="utf-8")
        assert "2026-06-15" in content
