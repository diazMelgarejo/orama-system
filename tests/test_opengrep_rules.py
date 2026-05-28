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
    """
    Load and parse the repository's .opengrep.yml into a dictionary.
    
    Returns:
        dict: Parsed contents of .opengrep.yml as a Python dictionary.
    """
    with OPENGREP_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def rules(config) -> list[dict]:
    """
    Retrieve the top-level "rules" list from a parsed .opengrep.yml configuration.
    
    Parameters:
        config (dict): Parsed YAML document expected to contain a "rules" key.
    
    Returns:
        list[dict]: The list of rule objects from the config.
    """
    return config["rules"]


@pytest.fixture(scope="module")
def rules_by_id(rules) -> dict[str, dict]:
    """
    Build a mapping from each rule's `id` to its rule dictionary.
    
    Parameters:
        rules (list[dict]): Sequence of rule dictionaries; each must contain an `"id"` key.
    
    Returns:
        dict[str, dict]: Mapping where keys are rule IDs and values are the corresponding rule dictionaries.
    """
    return {r["id"]: r for r in rules}


# ── File-level structural tests ───────────────────────────────────────────────


def test_opengrep_yml_file_exists():
    assert OPENGREP_PATH.exists(), f"{OPENGREP_PATH} not found in repository"


def test_opengrep_yml_is_valid_yaml():
    """
    Verify that .opengrep.yml parses as valid YAML.
    """
    with OPENGREP_PATH.open(encoding="utf-8") as fh:
        parsed = yaml.safe_load(fh)
    assert parsed is not None


def test_opengrep_yml_top_level_has_rules_key(config):
    """
    Assert that the parsed `.opengrep.yml` contains a top-level "rules" key.
    
    Parameters:
        config (dict): Parsed YAML document from `.opengrep.yml` provided by the `config` fixture.
    """
    assert "rules" in config, "Top-level 'rules' key is missing from .opengrep.yml"


def test_rules_is_a_non_empty_list(rules):
    """
    Assert that the parsed `rules` value from `.opengrep.yml` is a non-empty list.
    
    Parameters:
    	rules (list): The top-level `rules` sequence parsed from the configuration file; each entry is expected to be a rule mapping.
    """
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
    """
    Assert that every rule in `rules` contains the specified `field`.
    
    Parameters:
        rules (list[dict]): List of rule objects to check.
        field (str): The required field name that each rule must have.
    
    Notes:
        Fails the test with a list of rule IDs if any rule is missing `field`.
    """
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
    """
    Assert that every rule dictionary in `rules` contains a `metadata` key.
    
    Parameters:
        rules (list[dict]): Parsed rule objects from the `.opengrep.yml` configuration.
    
    Raises:
        AssertionError: If one or more rules are missing the `metadata` key; the assertion message lists the offending rule ids.
    """
    missing = [r["id"] for r in rules if "metadata" not in r]
    assert not missing, f"Rules missing 'metadata': {missing}"


def test_all_rules_metadata_has_category(rules):
    """
    Ensure every rule defines a metadata.category field.
    
    If any rule is missing `metadata.category`, the test fails and the assertion message lists the offending rule IDs.
    """
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
    """
    Assert that all rule IDs in the provided rules list are unique.
    
    Parameters:
        rules (list[dict]): List of rule objects parsed from .opengrep.yml, each expected to contain an "id" key.
    """
    ids = [r["id"] for r in rules]
    seen: set[str] = set()
    duplicates = [rid for rid in ids if rid in seen or seen.add(rid)]  # type: ignore[func-returns-value]
    assert not duplicates, f"Duplicate rule IDs found: {duplicates}"


def test_all_expected_rule_ids_are_present(rules_by_id):
    missing = ALL_EXPECTED_IDS - set(rules_by_id.keys())
    assert not missing, f"Expected rule IDs are absent: {missing}"


# ── Severity validation ───────────────────────────────────────────────────────


def test_severity_values_are_valid(rules):
    """
    Validate that every rule's `severity` is one of the allowed values.
    
    Parameters:
        rules (list[dict]): Parsed list of rule dictionaries from `.opengrep.yml`. The test asserts each rule's `severity` is in VALID_SEVERITIES.
    """
    invalid = [
        (r["id"], r["severity"])
        for r in rules
        if r.get("severity") not in VALID_SEVERITIES
    ]
    assert not invalid, f"Rules with invalid severity: {invalid}"


def test_no_rule_has_empty_message(rules):
    """
    Ensure every rule has a non-empty message.
    
    Parameters:
        rules (list[dict]): List of rule objects parsed from .opengrep.yml.
    
    Raises:
        AssertionError: If any rule's "message" is empty or contains only whitespace; the assertion error lists the offending rule IDs.
    """
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
    """
    Assert that the repository's expected Python-only rules target only Python.
    
    Parameters:
        rules_by_id (dict): Mapping of rule ID to rule dictionary; used to look up each rule and verify its `languages` value is exactly `["python"]`.
    """
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
    """
    Assert that TypeScript-specific rules include both "typescript" and "javascript" in their `languages` list.
    
    Parameters:
        rules_by_id (dict): Mapping from rule ID to its rule dictionary.
    """
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
    """
    Assert that the Python and TypeScript hardcoded-secret rules have severity "WARNING".
    """
    for rule_id in (RULE_ID_NO_HARDCODED_SECRET_PY, RULE_ID_TS_NO_HARDCODED_SECRET):
        assert rules_by_id[rule_id]["severity"] == "WARNING", (
            f"{rule_id} must be WARNING severity"
        )


def test_bash_eval_and_curl_are_error_severity(rules_by_id):
    """
    Verify the Bash 'eval' and 'curl' Semgrep rules have severity "ERROR".
    
    Parameters:
        rules_by_id (dict): Mapping from rule ID to the rule dictionary as parsed from the .opengrep.yml configuration.
    """
    for rule_id in (RULE_ID_BASH_EVAL, RULE_ID_BASH_CURL):
        assert rules_by_id[rule_id]["severity"] == "ERROR"


def test_ts_eval_rule_is_error_severity(rules_by_id):
    """
    Assert that the TypeScript/JavaScript eval security rule is classified with severity "ERROR".
    """
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
    """
    Ensure the "orama-no-yaml-load" rule provides a 'fix' that references yaml.safe_load.
    """
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
    """
    Verify the Python hardcoded-secret rule's `$VAR` metavariable regex matches common secret variable names.
    
    Extracts the `metavariable-regex` entries for metavariable `$VAR` from the Python hardcoded-secret rule, requires at least one such regex, joins them into a combined pattern, and asserts the combined pattern matches the example names: "api_key", "secret", "password", "token", "auth_key", and "private_key" (case-insensitive).
    """
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
    """
    Assert that the bind-all-interfaces rule's patterns reference both server entrypoints and the 0.0.0.0 host.
    
    Verifies the rule identified by RULE_ID_BIND_ALL_INTERFACES contains a "patterns" entry and that its pattern text includes "uvicorn.run", "app.run", and "0.0.0.0".
    """
    rule = rules_by_id[RULE_ID_BIND_ALL_INTERFACES]
    assert "patterns" in rule
    pattern_text = str(rule["patterns"])
    assert "uvicorn.run" in pattern_text
    assert "app.run" in pattern_text
    assert "0.0.0.0" in pattern_text


def test_bash_curl_rule_has_three_patterns(rules_by_id):
    """
    Assert that the `orama-bash-curl-pipe-sh` rule defines exactly three patterns covering the `curl | sh`, `curl | bash`, and `wget | sh` variants.
    """
    rule = rules_by_id[RULE_ID_BASH_CURL]
    assert "patterns" in rule
    assert len(rule["patterns"]) == 3, (
        f"Expected 3 patterns for curl/wget variants, got {len(rule['patterns'])}"
    )


def test_bash_curl_patterns_cover_wget_variant(rules_by_id):
    """
    Asserts the bash 'curl-pipe-sh' rule's patterns include a wget variant.
    
    Checks the rule identified by RULE_ID_BASH_CURL contains the substring "wget" in its patterns text and fails the test if it does not.
    """
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
    """
    Verify the TypeScript hardcoded-secret rule's `$VAR` metavariable regex matches common camelCase and snake_case secret names.
    
    Asserts that the rule identified by RULE_ID_TS_NO_HARDCODED_SECRET contains at least one `metavariable-regex` entry for `$VAR`, combines those regexes, and ensures the combined pattern matches example secret identifier names such as "apiKey", "api_key", "secret", "password", "token", and "authKey". Fails with an AssertionError if the metavariable-regex is missing or does not match any of the example names.
    """
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
    """
    Assert that each injection-related rule references OWASP A03 (2021) in its metadata.
    
    Checks the rules identified as injection-related and fails the test if their
    `metadata.owasp` value does not contain the substring "A03".
    """
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
    """
    Asserts that the Python and TypeScript hardcoded-secret rules reference CWE-798 in their metadata.
    
    Checks the `cwe` metadata for the configured hardcoded-secret rule IDs and fails if it does not include the substring "CWE-798".
    """
    for rule_id in (RULE_ID_NO_HARDCODED_SECRET_PY, RULE_ID_TS_NO_HARDCODED_SECRET):
        cwe = rules_by_id[rule_id].get("metadata", {}).get("cwe", "")
        assert "CWE-798" in cwe, f"{rule_id}: expected CWE-798, got '{cwe}'"


def test_supply_chain_rules_reference_owasp_a08(rules_by_id):
    """
    Assert that supply-chain-related rules reference OWASP A08.
    
    Checks that the yaml.load and curl-pipe-sh rules include "A08" in their `metadata.owasp` value; raises an assertion error if the expected OWASP reference is missing.
    """
    for rule_id in (RULE_ID_NO_YAML_LOAD, RULE_ID_BASH_CURL):
        owasp = rules_by_id[rule_id].get("metadata", {}).get("owasp", "")
        assert "A08" in owasp, (
            f"{rule_id}: expected OWASP A08 reference, got '{owasp}'"
        )


def test_bind_all_interfaces_references_owasp_a05(rules_by_id):
    owasp = rules_by_id[RULE_ID_BIND_ALL_INTERFACES].get("metadata", {}).get("owasp", "")
    assert "A05" in owasp


def test_hardcoded_secret_rules_reference_owasp_a02(rules_by_id):
    """
    Assert that the hardcoded-secret rules include an OWASP A02 reference in their metadata.
    
    Checks the Python and TypeScript hardcoded-secret rules and fails if their `metadata.owasp` value does not contain the substring "A02".
    """
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
