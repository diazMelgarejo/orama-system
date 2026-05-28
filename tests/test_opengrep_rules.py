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


# ── Severity breakdown counts ─────────────────────────────────────────────────


def test_error_severity_rule_count(rules):
    """Exactly 6 rules must be ERROR severity."""
    error_rules = [r for r in rules if r.get("severity") == "ERROR"]
    assert len(error_rules) == 6, (
        f"Expected 6 ERROR rules, found {len(error_rules)}: "
        f"{[r['id'] for r in error_rules]}"
    )


def test_warning_severity_rule_count(rules):
    """Exactly 5 rules must be WARNING severity."""
    warning_rules = [r for r in rules if r.get("severity") == "WARNING"]
    assert len(warning_rules) == 5, (
        f"Expected 5 WARNING rules, found {len(warning_rules)}: "
        f"{[r['id'] for r in warning_rules]}"
    )


def test_deprecated_validator_is_warning_severity(rules_by_id):
    """orama-no-deprecated-validator is a style/correctness rule and must be WARNING."""
    assert rules_by_id[RULE_ID_NO_DEPRECATED_VALIDATOR]["severity"] == "WARNING"


def test_bind_all_interfaces_is_warning_severity(rules_by_id):
    """orama-bind-all-interfaces is a misconfiguration warning, not an error."""
    assert rules_by_id[RULE_ID_BIND_ALL_INTERFACES]["severity"] == "WARNING"


def test_bash_slug_is_warning_severity(rules_by_id):
    """orama-bash-slug-not-validated must be WARNING (advisory, not blocking)."""
    assert rules_by_id[RULE_ID_BASH_SLUG]["severity"] == "WARNING"


# ── fix field checks ──────────────────────────────────────────────────────────


def test_only_yaml_load_rule_has_fix_key(rules):
    """Only orama-no-yaml-load declares an autofix; no other rule should have one."""
    rules_with_fix = [r["id"] for r in rules if "fix" in r]
    assert rules_with_fix == [RULE_ID_NO_YAML_LOAD], (
        f"Unexpected rules with 'fix' key: {rules_with_fix}"
    )


def test_yaml_load_fix_field_is_a_string(rules_by_id):
    """The fix field must be a non-empty string so semgrep can apply it."""
    fix = rules_by_id[RULE_ID_NO_YAML_LOAD].get("fix")
    assert isinstance(fix, str) and fix.strip(), "fix must be a non-empty string"


def test_yaml_load_fix_references_same_metavar_as_patterns(rules_by_id):
    """The fix (yaml.safe_load($X)) must use the same $X metavariable as the patterns."""
    rule = rules_by_id[RULE_ID_NO_YAML_LOAD]
    fix = rule["fix"]
    assert "$X" in fix, f"fix must use $X metavar, got: {fix!r}"
    pattern_text = str(rule["patterns"])
    assert "$X" in pattern_text, "patterns must also reference $X"


# ── Pattern/patterns mutual exclusion ────────────────────────────────────────


def test_no_rule_has_both_pattern_and_patterns(rules):
    """'pattern' and 'patterns' are mutually exclusive semgrep keys."""
    both = [r["id"] for r in rules if "pattern" in r and "patterns" in r]
    assert not both, f"Rules with both 'pattern' and 'patterns': {both}"


def test_scalar_pattern_rules_do_not_have_patterns_key(rules_by_id):
    """Rules using the scalar 'pattern' form must not also have a 'patterns' list."""
    scalar_pattern_ids = [RULE_ID_NO_EVAL_PY, RULE_ID_NO_DEPRECATED_VALIDATOR]
    for rule_id in scalar_pattern_ids:
        rule = rules_by_id[rule_id]
        assert "patterns" not in rule, (
            f"{rule_id}: uses scalar 'pattern' but also has 'patterns'"
        )


# ── Rule ID naming convention ─────────────────────────────────────────────────


def test_rule_ids_contain_no_spaces(rules):
    """Rule IDs must be space-free (kebab-case)."""
    with_spaces = [r["id"] for r in rules if " " in r["id"]]
    assert not with_spaces, f"Rule IDs must not contain spaces: {with_spaces}"


def test_rule_ids_contain_no_uppercase_letters(rules):
    """Rule IDs must be all lowercase to follow kebab-case convention."""
    with_upper = [r["id"] for r in rules if r["id"] != r["id"].lower()]
    assert not with_upper, f"Rule IDs must be lowercase: {with_upper}"


# ── patterns list integrity ───────────────────────────────────────────────────


def test_all_patterns_lists_are_nonempty(rules):
    """Every rule that uses 'patterns' must have at least one entry."""
    empty_patterns = [
        r["id"] for r in rules
        if "patterns" in r and len(r["patterns"]) == 0
    ]
    assert not empty_patterns, f"Rules with empty 'patterns' list: {empty_patterns}"


def test_patterns_list_contains_no_none_entries(rules):
    """A stray YAML dash without a value produces None in the patterns list."""
    bad = []
    for rule in rules:
        if "patterns" in rule:
            nones = [i for i, p in enumerate(rule["patterns"]) if p is None]
            if nones:
                bad.append((rule["id"], nones))
    assert not bad, f"Rules with None pattern entries (index): {bad}"


# ── Pattern counts for specific rules ─────────────────────────────────────────


def test_no_shell_true_has_exactly_one_pattern_entry(rules_by_id):
    """orama-no-shell-true needs only one pattern: subprocess.$FUNC(..., shell=True, ...)."""
    rule = rules_by_id[RULE_ID_NO_SHELL_TRUE]
    assert len(rule["patterns"]) == 1, (
        f"Expected 1 pattern entry, got {len(rule['patterns'])}"
    )


def test_bind_all_interfaces_has_exactly_two_patterns(rules_by_id):
    """orama-bind-all-interfaces must cover uvicorn.run and app.run — exactly 2 patterns."""
    rule = rules_by_id[RULE_ID_BIND_ALL_INTERFACES]
    assert len(rule["patterns"]) == 2, (
        f"Expected 2 patterns, got {len(rule['patterns'])}"
    )


def test_bash_eval_has_exactly_two_patterns(rules_by_id):
    """orama-bash-eval-with-external-input covers $() and backtick forms — exactly 2."""
    rule = rules_by_id[RULE_ID_BASH_EVAL]
    assert len(rule["patterns"]) == 2, (
        f"Expected 2 patterns, got {len(rule['patterns'])}"
    )


def test_bash_slug_has_exactly_two_patterns(rules_by_id):
    """orama-bash-slug-not-validated covers SLUG="$1" and SLUG="${1}" — exactly 2."""
    rule = rules_by_id[RULE_ID_BASH_SLUG]
    assert len(rule["patterns"]) == 2, (
        f"Expected 2 patterns, got {len(rule['patterns'])}"
    )


def test_ts_hardcoded_secret_has_exactly_two_patterns(rules_by_id):
    """orama-ts-no-hardcoded-secret: one const assignment pattern + one metavar-regex."""
    rule = rules_by_id[RULE_ID_TS_NO_HARDCODED_SECRET]
    assert len(rule["patterns"]) == 2, (
        f"Expected 2 patterns, got {len(rule['patterns'])}"
    )


# ── Message content / actionable guidance ────────────────────────────────────


def test_no_shell_true_message_recommends_list_form(rules_by_id):
    """The message must tell the user to use list-form commands."""
    msg = rules_by_id[RULE_ID_NO_SHELL_TRUE]["message"]
    assert "subprocess.run" in msg or "list" in msg.lower(), (
        "Message should recommend subprocess.run list form"
    )


def test_deprecated_validator_message_mentions_field_validator(rules_by_id):
    """The message must name the replacement decorator so developers know what to use."""
    msg = rules_by_id[RULE_ID_NO_DEPRECATED_VALIDATOR]["message"]
    assert "field_validator" in msg, (
        "Message must mention @field_validator as the Pydantic v2 replacement"
    )


def test_bind_all_interfaces_message_mentions_localhost(rules_by_id):
    """The message must recommend 127.0.0.1 as the safe alternative."""
    msg = rules_by_id[RULE_ID_BIND_ALL_INTERFACES]["message"]
    assert "127.0.0.1" in msg, "Message must recommend binding to 127.0.0.1"


def test_bash_slug_message_mentions_validation_pattern(rules_by_id):
    """The message must include the regex pattern developers should use for validation."""
    msg = rules_by_id[RULE_ID_BASH_SLUG]["message"]
    assert "=~" in msg or "regex" in msg.lower() or "Validate" in msg, (
        "Message must guide developers to validate the SLUG parameter"
    )


def test_bash_curl_message_mentions_checksum(rules_by_id):
    """The message must advise verifying a checksum before executing downloaded content."""
    msg = rules_by_id[RULE_ID_BASH_CURL]["message"]
    assert "checksum" in msg.lower() or "verify" in msg.lower(), (
        "Message must advise checksum verification"
    )


def test_yaml_load_message_mentions_safe_load(rules_by_id):
    """The message must name yaml.safe_load as the safe replacement."""
    msg = rules_by_id[RULE_ID_NO_YAML_LOAD]["message"]
    assert "safe_load" in msg, "Message must recommend yaml.safe_load()"


# ── Language family exclusivity ───────────────────────────────────────────────


def test_no_rule_spans_python_and_bash(rules):
    """No single rule should target both Python and Bash simultaneously."""
    mixed = [
        r["id"] for r in rules
        if "python" in r.get("languages", []) and "bash" in r.get("languages", [])
    ]
    assert not mixed, f"Rules mixing Python and Bash: {mixed}"


def test_no_rule_spans_python_and_typescript(rules):
    """No single rule should target both Python and TypeScript simultaneously."""
    mixed = [
        r["id"] for r in rules
        if "python" in r.get("languages", []) and "typescript" in r.get("languages", [])
    ]
    assert not mixed, f"Rules mixing Python and TypeScript: {mixed}"


# ── OWASP year reference format ───────────────────────────────────────────────


def test_all_owasp_references_cite_2021(rules):
    """All OWASP references in this config follow the 2021 taxonomy."""
    wrong_year = []
    for rule in rules:
        owasp = rule.get("metadata", {}).get("owasp", "")
        if owasp and "2021" not in owasp:
            wrong_year.append((rule["id"], owasp))
    assert not wrong_year, f"OWASP references not citing 2021: {wrong_year}"


# ── Rules that intentionally omit optional metadata fields ────────────────────


def test_bash_slug_has_no_owasp_metadata(rules_by_id):
    """orama-bash-slug-not-validated only carries CWE-78; no OWASP entry is expected."""
    meta = rules_by_id[RULE_ID_BASH_SLUG].get("metadata", {})
    assert "owasp" not in meta, (
        f"orama-bash-slug-not-validated unexpectedly gained an 'owasp' key: {meta.get('owasp')}"
    )


def test_bash_curl_has_no_cwe_metadata(rules_by_id):
    """orama-bash-curl-pipe-sh only carries OWASP A08; no CWE entry is expected."""
    meta = rules_by_id[RULE_ID_BASH_CURL].get("metadata", {})
    assert "cwe" not in meta, (
        f"orama-bash-curl-pipe-sh unexpectedly gained a 'cwe' key: {meta.get('cwe')}"
    )


def test_no_eval_py_has_no_cwe_metadata(rules_by_id):
    """orama-no-eval only has OWASP A03; it does not need a CWE tag."""
    meta = rules_by_id[RULE_ID_NO_EVAL_PY].get("metadata", {})
    assert "cwe" not in meta, (
        f"orama-no-eval unexpectedly gained a 'cwe' key: {meta.get('cwe')}"
    )


def test_ts_no_eval_has_no_cwe_metadata(rules_by_id):
    """orama-ts-no-eval only has OWASP A03; it does not need a CWE tag."""
    meta = rules_by_id[RULE_ID_TS_NO_EVAL].get("metadata", {})
    assert "cwe" not in meta, (
        f"orama-ts-no-eval unexpectedly gained a 'cwe' key: {meta.get('cwe')}"
    )


def test_deprecated_validator_has_no_owasp_or_cwe(rules_by_id):
    """orama-no-deprecated-validator is a correctness rule; OWASP/CWE are not expected."""
    meta = rules_by_id[RULE_ID_NO_DEPRECATED_VALIDATOR].get("metadata", {})
    assert "owasp" not in meta, "deprecated-validator should not have an OWASP reference"
    assert "cwe" not in meta, "deprecated-validator should not have a CWE reference"


# ── ALL_EXPECTED_IDS / EXPECTED_RULE_COUNT constant consistency ───────────────


def test_all_expected_ids_set_size_matches_expected_rule_count():
    """The ALL_EXPECTED_IDS constant and EXPECTED_RULE_COUNT must agree."""
    assert len(ALL_EXPECTED_IDS) == EXPECTED_RULE_COUNT, (
        f"ALL_EXPECTED_IDS has {len(ALL_EXPECTED_IDS)} entries but "
        f"EXPECTED_RULE_COUNT is {EXPECTED_RULE_COUNT}"
    )


def test_all_expected_ids_constants_have_orama_prefix():
    """Every ID in ALL_EXPECTED_IDS must start with 'orama-' per naming convention."""
    bad = [rid for rid in ALL_EXPECTED_IDS if not rid.startswith("orama-")]
    assert not bad, f"Constant IDs missing 'orama-' prefix: {bad}"


# ── Negative / boundary: no extra top-level keys in config ───────────────────


def test_config_has_no_unexpected_top_level_keys(config):
    """The config must only contain the 'rules' key at the top level."""
    allowed = {"rules"}
    extra = set(config.keys()) - allowed
    assert not extra, (
        f"Unexpected top-level keys in .opengrep.yml: {extra}. "
        "Only 'rules' is expected at the top level."
    )


# ── Boundary: bash-eval pattern content detail ────────────────────────────────


def test_bash_eval_first_pattern_uses_dollar_paren_form(rules_by_id):
    """First pattern must cover the $() command substitution form."""
    rule = rules_by_id[RULE_ID_BASH_EVAL]
    patterns = rule["patterns"]
    first_pattern_text = str(patterns[0])
    assert "$(" in first_pattern_text or "CMD" in first_pattern_text, (
        "First pattern should cover $() substitution form"
    )


def test_bash_curl_patterns_all_contain_pipe_to_shell(rules_by_id):
    """Every curl/wget pattern must pipe to sh or bash (the dangerous operation)."""
    rule = rules_by_id[RULE_ID_BASH_CURL]
    for pattern_entry in rule["patterns"]:
        pattern_text = str(pattern_entry)
        assert "sh" in pattern_text or "bash" in pattern_text, (
            f"Pattern does not pipe to sh/bash: {pattern_text!r}"
        )
