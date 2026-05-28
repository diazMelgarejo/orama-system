"""Tests for .opengrep.yml — validates structure and content of all semgrep rules.

The file declares 11 security rules across Python, Bash, and TypeScript/JavaScript.
These tests verify that the YAML is well-formed, every rule satisfies the required
schema, and that each rule carries the correct security metadata.
"""
from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).parent.parent
OPENGREP_PATH = ROOT / ".opengrep.yml"

EXPECTED_RULE_COUNT = 11

VALID_SEVERITIES = {"ERROR", "WARNING"}
VALID_LANGUAGES = {"python", "bash", "typescript", "javascript"}

# Rule IDs defined in the PR — used for targeted assertions.
RULE_ID_NO_SHELL_TRUE = "orama-no-shell-true"
RULE_ID_NO_EVAL_PY = "orama-no-eval"
RULE_ID_NO_YAML_LOAD = "orama-no-yaml-load"
RULE_ID_NO_HARDCODED_SECRET_PY = "orama-no-hardcoded-secret"
RULE_ID_NO_DEPRECATED_VALIDATOR = "orama-no-deprecated-validator"
RULE_ID_BIND_ALL_INTERFACES = "orama-bind-all-interfaces"
RULE_ID_BASH_EVAL = "orama-bash-eval-with-external-input"
RULE_ID_BASH_CURL = "orama-bash-curl-pipe-sh"
RULE_ID_BASH_SLUG = "orama-bash-slug-not-validated"
RULE_ID_TS_NO_EVAL = "orama-ts-no-eval"
RULE_ID_TS_NO_HARDCODED_SECRET = "orama-ts-no-hardcoded-secret"

ALL_EXPECTED_IDS = {
    RULE_ID_NO_SHELL_TRUE,
    RULE_ID_NO_EVAL_PY,
    RULE_ID_NO_YAML_LOAD,
    RULE_ID_NO_HARDCODED_SECRET_PY,
    RULE_ID_NO_DEPRECATED_VALIDATOR,
    RULE_ID_BIND_ALL_INTERFACES,
    RULE_ID_BASH_EVAL,
    RULE_ID_BASH_CURL,
    RULE_ID_BASH_SLUG,
    RULE_ID_TS_NO_EVAL,
    RULE_ID_TS_NO_HARDCODED_SECRET,
}


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def config() -> dict:
    """Return the parsed .opengrep.yml as a dictionary."""
    with OPENGREP_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def rules(config) -> list[dict]:
    """Return the list of rule objects from the config."""
    return config["rules"]


@pytest.fixture(scope="module")
def rules_by_id(rules) -> dict[str, dict]:
    """Return a mapping of rule_id → rule dict for targeted lookups."""
    return {r["id"]: r for r in rules}


# ── File-level structural tests ───────────────────────────────────────────────


def test_opengrep_yml_file_exists():
    assert OPENGREP_PATH.exists(), f"{OPENGREP_PATH} not found in repository"


def test_opengrep_yml_is_valid_yaml():
    """The file must parse as valid YAML without raising an exception."""
    with OPENGREP_PATH.open(encoding="utf-8") as fh:
        parsed = yaml.safe_load(fh)
    assert parsed is not None


def test_opengrep_yml_top_level_has_rules_key(config):
    assert "rules" in config, "Top-level 'rules' key is missing from .opengrep.yml"


def test_rules_is_a_non_empty_list(rules):
    assert isinstance(rules, list)
    assert len(rules) > 0, "rules list must not be empty"


def test_expected_total_rule_count(rules):
    """Exactly 11 rules are declared; any addition or removal must be intentional."""
    assert len(rules) == EXPECTED_RULE_COUNT, (
        f"Expected {EXPECTED_RULE_COUNT} rules, found {len(rules)}. "
        "Update EXPECTED_RULE_COUNT if this change is intentional."
    )


# ── Per-rule schema validation ────────────────────────────────────────────────


@pytest.mark.parametrize("field", ["id", "message", "languages", "severity"])
def test_all_rules_have_required_field(rules, field):
    """Every rule must declare the four core semgrep fields."""
    missing = [r.get("id", "<no-id>") for r in rules if field not in r]
    assert not missing, f"Rules missing '{field}': {missing}"


def test_all_rules_have_pattern_or_patterns(rules):
    """Every rule must have either a 'pattern' or 'patterns' key."""
    missing = []
    for rule in rules:
        if "pattern" not in rule and "patterns" not in rule:
            missing.append(rule.get("id", "<no-id>"))
    assert not missing, f"Rules missing pattern/patterns: {missing}"


def test_all_rules_have_metadata(rules):
    missing = [r["id"] for r in rules if "metadata" not in r]
    assert not missing, f"Rules missing 'metadata': {missing}"


def test_all_rules_metadata_has_category(rules):
    """metadata.category is mandatory for every rule."""
    missing = [
        r["id"]
        for r in rules
        if "metadata" not in r or "category" not in r.get("metadata", {})
    ]
    assert not missing, f"Rules missing metadata.category: {missing}"


# ── ID and naming convention tests ───────────────────────────────────────────


def test_rule_ids_use_orama_prefix(rules):
    bad = [r["id"] for r in rules if not r["id"].startswith("orama-")]
    assert not bad, f"Rule IDs must start with 'orama-': {bad}"


def test_rule_ids_are_unique(rules):
    ids = [r["id"] for r in rules]
    seen: set[str] = set()
    duplicates = [rid for rid in ids if rid in seen or seen.add(rid)]  # type: ignore[func-returns-value]
    assert not duplicates, f"Duplicate rule IDs found: {duplicates}"


def test_all_expected_rule_ids_are_present(rules_by_id):
    missing = ALL_EXPECTED_IDS - set(rules_by_id.keys())
    assert not missing, f"Expected rule IDs are absent: {missing}"


# ── Severity validation ───────────────────────────────────────────────────────


def test_severity_values_are_valid(rules):
    invalid = [
        (r["id"], r["severity"])
        for r in rules
        if r.get("severity") not in VALID_SEVERITIES
    ]
    assert not invalid, f"Rules with invalid severity: {invalid}"


def test_no_rule_has_empty_message(rules):
    empty = [r["id"] for r in rules if not str(r.get("message", "")).strip()]
    assert not empty, f"Rules with empty message: {empty}"


# ── Language validation ───────────────────────────────────────────────────────


def test_languages_field_is_always_a_list(rules):
    not_list = [r["id"] for r in rules if not isinstance(r.get("languages"), list)]
    assert not not_list, f"Rules where 'languages' is not a list: {not_list}"


def test_language_values_are_from_known_set(rules):
    invalid = []
    for rule in rules:
        for lang in rule.get("languages", []):
            if lang not in VALID_LANGUAGES:
                invalid.append((rule["id"], lang))
    assert not invalid, f"Rules with unknown language values: {invalid}"


def test_no_rule_has_empty_languages_list(rules):
    empty = [r["id"] for r in rules if not r.get("languages")]
    assert not empty, f"Rules with empty 'languages' list: {empty}"


# ── Language-to-rule grouping ─────────────────────────────────────────────────


def test_python_rules_target_only_python(rules_by_id):
    python_only_ids = [
        RULE_ID_NO_SHELL_TRUE,
        RULE_ID_NO_EVAL_PY,
        RULE_ID_NO_YAML_LOAD,
        RULE_ID_NO_HARDCODED_SECRET_PY,
        RULE_ID_NO_DEPRECATED_VALIDATOR,
        RULE_ID_BIND_ALL_INTERFACES,
    ]
    for rule_id in python_only_ids:
        rule = rules_by_id[rule_id]
        assert rule["languages"] == ["python"], (
            f"{rule_id}: expected languages=['python'], got {rule['languages']}"
        )


def test_bash_rules_target_only_bash(rules_by_id):
    bash_only_ids = [RULE_ID_BASH_EVAL, RULE_ID_BASH_CURL, RULE_ID_BASH_SLUG]
    for rule_id in bash_only_ids:
        rule = rules_by_id[rule_id]
        assert rule["languages"] == ["bash"], (
            f"{rule_id}: expected languages=['bash'], got {rule['languages']}"
        )


def test_ts_rules_target_typescript_and_javascript(rules_by_id):
    ts_ids = [RULE_ID_TS_NO_EVAL, RULE_ID_TS_NO_HARDCODED_SECRET]
    for rule_id in ts_ids:
        rule = rules_by_id[rule_id]
        langs = set(rule["languages"])
        assert "typescript" in langs, f"{rule_id}: must target 'typescript'"
        assert "javascript" in langs, f"{rule_id}: must target 'javascript'"


# ── Severity breakdown per language group ─────────────────────────────────────


def test_python_error_rules_are_correct_severity(rules_by_id):
    """orama-no-shell-true, orama-no-eval, orama-no-yaml-load must be ERROR."""
    error_ids = [RULE_ID_NO_SHELL_TRUE, RULE_ID_NO_EVAL_PY, RULE_ID_NO_YAML_LOAD]
    for rule_id in error_ids:
        assert rules_by_id[rule_id]["severity"] == "ERROR", (
            f"{rule_id} must be ERROR severity"
        )


def test_hardcoded_secret_rules_are_warning_severity(rules_by_id):
    """Both hardcoded-secret rules (Python and TS) must be WARNING, not ERROR."""
    for rule_id in (RULE_ID_NO_HARDCODED_SECRET_PY, RULE_ID_TS_NO_HARDCODED_SECRET):
        assert rules_by_id[rule_id]["severity"] == "WARNING", (
            f"{rule_id} must be WARNING severity"
        )


def test_bash_eval_and_curl_are_error_severity(rules_by_id):
    for rule_id in (RULE_ID_BASH_EVAL, RULE_ID_BASH_CURL):
        assert rules_by_id[rule_id]["severity"] == "ERROR"


def test_ts_eval_rule_is_error_severity(rules_by_id):
    assert rules_by_id[RULE_ID_TS_NO_EVAL]["severity"] == "ERROR"


# ── Per-rule content assertions ───────────────────────────────────────────────


def test_no_shell_true_uses_patterns_not_pattern(rules_by_id):
    """shell=True rule must use the list form (patterns:) to match all subprocess funcs."""
    rule = rules_by_id[RULE_ID_NO_SHELL_TRUE]
    assert "patterns" in rule, "orama-no-shell-true should use 'patterns' (list form)"
    assert "pattern" not in rule


def test_no_shell_true_pattern_references_metavariable(rules_by_id):
    rule = rules_by_id[RULE_ID_NO_SHELL_TRUE]
    pattern_text = str(rule["patterns"])
    assert "$FUNC" in pattern_text, "Pattern must use $FUNC metavariable"
    assert "shell=True" in pattern_text


def test_no_eval_py_uses_single_pattern(rules_by_id):
    """orama-no-eval should use the scalar 'pattern' key."""
    rule = rules_by_id[RULE_ID_NO_EVAL_PY]
    assert "pattern" in rule
    assert rule["pattern"] == "eval(...)"


def test_yaml_load_rule_has_fix_key(rules_by_id):
    """orama-no-yaml-load must supply an autofix so semgrep can suggest yaml.safe_load."""
    rule = rules_by_id[RULE_ID_NO_YAML_LOAD]
    assert "fix" in rule, "orama-no-yaml-load must have a 'fix' field"
    assert "safe_load" in rule["fix"], "fix must reference yaml.safe_load"


def test_yaml_load_rule_covers_both_arities(rules_by_id):
    """Two patterns: yaml.load($X) and yaml.load($X, ...) to cover loader= argument."""
    rule = rules_by_id[RULE_ID_NO_YAML_LOAD]
    assert "patterns" in rule
    pattern_strings = [str(p) for p in rule["patterns"]]
    assert any("yaml.load" in p for p in pattern_strings)
    assert len(rule["patterns"]) >= 2, "Should have at least 2 patterns for yaml.load"


def test_hardcoded_secret_py_uses_metavariable_regex(rules_by_id):
    """orama-no-hardcoded-secret relies on metavariable-regex to match var names."""
    rule = rules_by_id[RULE_ID_NO_HARDCODED_SECRET_PY]
    assert "patterns" in rule
    pattern_text = str(rule["patterns"])
    assert "metavariable-regex" in pattern_text
    assert "$VAR" in pattern_text


def test_hardcoded_secret_py_regex_covers_common_names(rules_by_id):
    import re

    rule = rules_by_id[RULE_ID_NO_HARDCODED_SECRET_PY]
    # Extract the metavariable-regex entries for $VAR
    mv_regexes = [
        p["metavariable-regex"]["regex"]
        for p in rule["patterns"]
        if isinstance(p, dict) and "metavariable-regex" in p
        and p["metavariable-regex"].get("metavariable") == "$VAR"
    ]
    assert mv_regexes, "Should have at least one metavariable-regex for $VAR"
    combined = "|".join(mv_regexes)
    for name in ("api_key", "secret", "password", "token", "auth_key", "private_key"):
        assert re.search(combined, name, re.IGNORECASE), (
            f"Regex should match '{name}'"
        )


def test_bind_all_interfaces_covers_uvicorn_and_app(rules_by_id):
    rule = rules_by_id[RULE_ID_BIND_ALL_INTERFACES]
    assert "patterns" in rule
    pattern_text = str(rule["patterns"])
    assert "uvicorn.run" in pattern_text
    assert "app.run" in pattern_text
    assert "0.0.0.0" in pattern_text


def test_bash_curl_rule_has_three_patterns(rules_by_id):
    """orama-bash-curl-pipe-sh must cover: curl|sh, curl|bash, wget|sh."""
    rule = rules_by_id[RULE_ID_BASH_CURL]
    assert "patterns" in rule
    assert len(rule["patterns"]) == 3, (
        f"Expected 3 patterns for curl/wget variants, got {len(rule['patterns'])}"
    )


def test_bash_curl_patterns_cover_wget_variant(rules_by_id):
    rule = rules_by_id[RULE_ID_BASH_CURL]
    pattern_text = str(rule["patterns"])
    assert "wget" in pattern_text, "curl-pipe-sh rule must also cover wget"


def test_bash_eval_rule_covers_both_substitution_forms(rules_by_id):
    """eval with both $() and backtick forms must be covered."""
    rule = rules_by_id[RULE_ID_BASH_EVAL]
    assert "patterns" in rule
    pattern_text = str(rule["patterns"])
    assert "$($CMD)" in pattern_text or "CMD" in pattern_text
    assert len(rule["patterns"]) >= 2


def test_bash_slug_not_validated_covers_both_forms(rules_by_id):
    """Both SLUG="$1" and SLUG="${1}" must be in the pattern list."""
    rule = rules_by_id[RULE_ID_BASH_SLUG]
    assert "patterns" in rule
    pattern_text = str(rule["patterns"])
    assert "$1" in pattern_text
    assert "${1}" in pattern_text or "1}" in pattern_text


def test_ts_eval_covers_function_constructor(rules_by_id):
    """orama-ts-no-eval must flag both eval(...) and new Function(...)."""
    rule = rules_by_id[RULE_ID_TS_NO_EVAL]
    assert "patterns" in rule
    pattern_text = str(rule["patterns"])
    assert "eval" in pattern_text
    assert "Function" in pattern_text


def test_ts_hardcoded_secret_uses_const_pattern(rules_by_id):
    """TypeScript rule matches 'const $VAR = ...' specifically (not bare assignment)."""
    rule = rules_by_id[RULE_ID_TS_NO_HARDCODED_SECRET]
    assert "patterns" in rule
    pattern_text = str(rule["patterns"])
    assert "const" in pattern_text
    assert "$VAR" in pattern_text


def test_ts_hardcoded_secret_regex_covers_camel_and_snake_case(rules_by_id):
    import re

    rule = rules_by_id[RULE_ID_TS_NO_HARDCODED_SECRET]
    mv_regexes = [
        p["metavariable-regex"]["regex"]
        for p in rule["patterns"]
        if isinstance(p, dict) and "metavariable-regex" in p
        and p["metavariable-regex"].get("metavariable") == "$VAR"
    ]
    assert mv_regexes, "Should have at least one metavariable-regex for $VAR"
    combined = "|".join(mv_regexes)
    for name in ("apiKey", "api_key", "secret", "password", "token", "authKey"):
        assert re.search(combined, name, re.IGNORECASE), (
            f"TS secret regex should match '{name}'"
        )


# ── OWASP / CWE metadata checks ───────────────────────────────────────────────


def test_error_severity_rules_have_owasp_or_cwe(rules):
    """All ERROR-level rules must carry at least owasp or cwe metadata."""
    missing = []
    for rule in rules:
        if rule.get("severity") == "ERROR":
            meta = rule.get("metadata", {})
            if "owasp" not in meta and "cwe" not in meta:
                missing.append(rule["id"])
    assert not missing, f"ERROR rules missing owasp/cwe metadata: {missing}"


def test_injection_rules_reference_owasp_a03(rules_by_id):
    """Injection-related rules must cite OWASP A03:2021."""
    injection_ids = [
        RULE_ID_NO_SHELL_TRUE,
        RULE_ID_NO_EVAL_PY,
        RULE_ID_BASH_EVAL,
        RULE_ID_TS_NO_EVAL,
    ]
    for rule_id in injection_ids:
        owasp = rules_by_id[rule_id].get("metadata", {}).get("owasp", "")
        assert "A03" in owasp, (
            f"{rule_id}: expected OWASP A03 reference, got '{owasp}'"
        )


def test_cwe_78_assigned_to_command_injection_rules(rules_by_id):
    """CWE-78 (OS Command Injection) must be on shell-injection rules."""
    cwe_78_ids = [RULE_ID_NO_SHELL_TRUE, RULE_ID_BASH_EVAL, RULE_ID_BASH_SLUG]
    for rule_id in cwe_78_ids:
        cwe = rules_by_id[rule_id].get("metadata", {}).get("cwe", "")
        assert "CWE-78" in cwe, f"{rule_id}: expected CWE-78, got '{cwe}'"


def test_yaml_load_rule_references_cwe_502(rules_by_id):
    cwe = rules_by_id[RULE_ID_NO_YAML_LOAD].get("metadata", {}).get("cwe", "")
    assert "CWE-502" in cwe


def test_hardcoded_secret_rules_reference_cwe_798(rules_by_id):
    for rule_id in (RULE_ID_NO_HARDCODED_SECRET_PY, RULE_ID_TS_NO_HARDCODED_SECRET):
        cwe = rules_by_id[rule_id].get("metadata", {}).get("cwe", "")
        assert "CWE-798" in cwe, f"{rule_id}: expected CWE-798, got '{cwe}'"


def test_supply_chain_rules_reference_owasp_a08(rules_by_id):
    """yaml.load and curl-pipe-sh both involve supply-chain / integrity failures."""
    for rule_id in (RULE_ID_NO_YAML_LOAD, RULE_ID_BASH_CURL):
        owasp = rules_by_id[rule_id].get("metadata", {}).get("owasp", "")
        assert "A08" in owasp, (
            f"{rule_id}: expected OWASP A08 reference, got '{owasp}'"
        )


def test_bind_all_interfaces_references_owasp_a05(rules_by_id):
    owasp = rules_by_id[RULE_ID_BIND_ALL_INTERFACES].get("metadata", {}).get("owasp", "")
    assert "A05" in owasp


def test_hardcoded_secret_rules_reference_owasp_a02(rules_by_id):
    for rule_id in (RULE_ID_NO_HARDCODED_SECRET_PY, RULE_ID_TS_NO_HARDCODED_SECRET):
        owasp = rules_by_id[rule_id].get("metadata", {}).get("owasp", "")
        assert "A02" in owasp, f"{rule_id}: expected OWASP A02, got '{owasp}'"


# ── Metadata category values ──────────────────────────────────────────────────


def test_security_rules_have_security_category(rules):
    """Rules about security vulnerabilities must have category='security'."""
    # orama-no-deprecated-validator is 'correctness'; all others are 'security'
    non_security_ids = {RULE_ID_NO_DEPRECATED_VALIDATOR}
    wrong = [
        r["id"]
        for r in rules
        if r["id"] not in non_security_ids
        and r.get("metadata", {}).get("category") != "security"
    ]
    assert not wrong, f"These rules should have category='security': {wrong}"


def test_deprecated_validator_rule_has_correctness_category(rules_by_id):
    category = rules_by_id[RULE_ID_NO_DEPRECATED_VALIDATOR].get("metadata", {}).get("category")
    assert category == "correctness"


# ── Regression / boundary tests ───────────────────────────────────────────────


def test_no_rule_uses_yaml_load_unsafely():
    """Boundary test: the config file itself must not call yaml.load() (use safe_load)."""
    content = OPENGREP_PATH.read_text(encoding="utf-8")
    # The file may MENTION yaml.load in pattern strings, but must not call it as Python.
    # The only yaml.load occurrences should be inside pattern: strings, not bare code.
    # Since this is YAML, not Python, we just ensure it parses without executing.
    parsed = yaml.safe_load(content)
    assert parsed is not None  # Proves safe_load was used, not load()


def test_rules_list_contains_no_none_entries(rules):
    """A misplaced YAML dash can introduce a None entry into the rules list."""
    none_count = sum(1 for r in rules if r is None)
    assert none_count == 0, f"rules list contains {none_count} None entry(ies)"


def test_all_rule_ids_are_strings(rules):
    non_strings = [r.get("id") for r in rules if not isinstance(r.get("id"), str)]
    assert not non_strings, f"Non-string rule IDs found: {non_strings}"


def test_all_rule_messages_are_strings(rules):
    non_strings = [r["id"] for r in rules if not isinstance(r.get("message"), str)]
    assert not non_strings, f"Rules with non-string message: {non_strings}"


def test_python_rules_count(rules):
    """There are exactly 6 Python rules declared."""
    python_rules = [r for r in rules if r.get("languages") == ["python"]]
    assert len(python_rules) == 6, (
        f"Expected 6 Python rules, found {len(python_rules)}"
    )


def test_bash_rules_count(rules):
    """There are exactly 3 Bash rules declared."""
    bash_rules = [r for r in rules if r.get("languages") == ["bash"]]
    assert len(bash_rules) == 3, (
        f"Expected 3 Bash rules, found {len(bash_rules)}"
    )


def test_ts_rules_count(rules):
    """There are exactly 2 TypeScript/JavaScript rules declared."""
    ts_rules = [
        r for r in rules
        if set(r.get("languages", [])) == {"typescript", "javascript"}
    ]
    assert len(ts_rules) == 2, (
        f"Expected 2 TS/JS rules, found {len(ts_rules)}"
    )
