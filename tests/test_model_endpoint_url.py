"""Policy tests for utils.model_endpoint_url (Security Fix 5)."""
from __future__ import annotations

import pytest

from utils.model_endpoint_url import (
    ModelEndpointPolicyError,
    parse_model_endpoint_list,
    redact_endpoint_for_log,
    validate_model_endpoint_url,
)


@pytest.fixture(autouse=True)
def _clear_public_opt_in(monkeypatch):
    monkeypatch.delenv("ALLOW_PUBLIC_MODEL_ENDPOINTS", raising=False)


def test_loopback_allowed():
    assert validate_model_endpoint_url("http://127.0.0.1:1234") == "http://127.0.0.1:1234"


def test_bare_host_port_canonicalized():
    assert validate_model_endpoint_url("localhost:1234") == "http://localhost:1234"
    assert validate_model_endpoint_url("192.168.0.10:1234") == "http://192.168.0.10:1234"


def test_rfc1918_allowed():
    assert validate_model_endpoint_url("http://192.168.0.10:1234") == "http://192.168.0.10:1234"


def test_link_local_metadata_blocked():
    with pytest.raises(ModelEndpointPolicyError, match="RFC1918"):
        validate_model_endpoint_url("http://169.254.169.254")


def test_ipv4_mapped_link_local_metadata_blocked():
    with pytest.raises(ModelEndpointPolicyError, match="RFC1918"):
        validate_model_endpoint_url("http://[::ffff:169.254.169.254]:80")


def test_public_blocked_without_opt_in():
    with pytest.raises(ModelEndpointPolicyError):
        validate_model_endpoint_url("http://1.1.1.1:1234")


def test_127_prefix_hostname_not_treated_as_loopback():
    with pytest.raises(ModelEndpointPolicyError, match="RFC1918"):
        validate_model_endpoint_url("http://127.attacker.example:8000")


def test_127_prefix_hostname_blocked_with_require_tls_flag():
    with pytest.raises(ModelEndpointPolicyError, match="RFC1918"):
        validate_model_endpoint_url(
            "http://127.attacker.example:8000",
            require_tls_for_non_loopback=True,
        )


def test_public_allowed_with_opt_in(monkeypatch):
    monkeypatch.setenv("ALLOW_PUBLIC_MODEL_ENDPOINTS", "1")
    assert validate_model_endpoint_url("http://1.1.1.1:1234") == "http://1.1.1.1:1234"


def test_malformed_port_rejected_as_policy_error():
    with pytest.raises(ModelEndpointPolicyError, match="invalid endpoint URL"):
        validate_model_endpoint_url("http://127.0.0.1:notaport")


def test_out_of_range_port_rejected_as_policy_error():
    with pytest.raises(ModelEndpointPolicyError, match="invalid endpoint URL"):
        validate_model_endpoint_url("http://127.0.0.1:99999")


def test_parse_list_skip_invalid_handles_malformed_port():
    raw = "http://127.0.0.1:11434, http://127.0.0.1:notaport"
    assert parse_model_endpoint_list(raw, skip_invalid=True) == [
        "http://127.0.0.1:11434",
    ]


def test_parse_required_set_in_env_sentinel_skipped():
    raw = "REQUIRED_SET_IN_ENV, http://127.0.0.1:11434"
    assert parse_model_endpoint_list(raw, skip_invalid=True) == [
        "http://127.0.0.1:11434",
    ]


# CodeRabbit review 5234774766 (PR#363), Finding 2: require_tls_for_non_loopback
# is opt-in and default-off, so the PT pipeline client (the only caller that
# sends a bearer token on every call) can require HTTPS beyond loopback
# without changing behavior for LM Studio / Ollama / Windows-coder-pool
# endpoints, which stay plain-HTTP-on-trusted-LAN by design.


def test_default_still_allows_http_to_private_network_host():
    assert (
        validate_model_endpoint_url("http://192.168.1.50:8000")
        == "http://192.168.1.50:8000"
    )


def test_require_tls_flag_allows_the_documented_loopback_default():
    assert (
        validate_model_endpoint_url(
            "http://localhost:8000", require_tls_for_non_loopback=True
        )
        == "http://localhost:8000"
    )
    assert (
        validate_model_endpoint_url(
            "http://127.0.0.1:8000", require_tls_for_non_loopback=True
        )
        == "http://127.0.0.1:8000"
    )


def test_require_tls_flag_rejects_http_to_rfc1918_private_host():
    with pytest.raises(ModelEndpointPolicyError, match="https"):
        validate_model_endpoint_url(
            "http://192.168.1.50:8000", require_tls_for_non_loopback=True
        )


def test_require_tls_flag_rejects_http_to_10_range_private_host():
    with pytest.raises(ModelEndpointPolicyError, match="https"):
        validate_model_endpoint_url(
            "http://10.0.0.5:8000", require_tls_for_non_loopback=True
        )


def test_require_tls_flag_allows_https_to_private_network_host():
    assert (
        validate_model_endpoint_url(
            "https://192.168.1.50:8443", require_tls_for_non_loopback=True
        )
        == "https://192.168.1.50:8443"
    )


def test_file_scheme_rejected():
    """Task 5 union: PT's test_file_scheme_rejected. Genuinely new
    behavior coverage, not just a renamed duplicate -- orama's suite had
    no test for a non-http(s) scheme at all before this."""
    with pytest.raises(ModelEndpointPolicyError, match="scheme"):
        validate_model_endpoint_url("file:///etc/passwd")


def test_credentials_in_url_rejected():
    """Task 5 union: PT's test_credentials_rejected."""
    with pytest.raises(ModelEndpointPolicyError, match="credentials"):
        validate_model_endpoint_url("http://user:pass@127.0.3.1:1234")


def test_empty_url_rejected():
    """Task 5 union: PT's test_empty_rejected."""
    with pytest.raises(ModelEndpointPolicyError, match="empty"):
        validate_model_endpoint_url("   ")


def test_private_ip_redacted_for_log():
    """Task 5 union: redact_endpoint_for_log has zero coverage in this
    file before this addition, despite the function shipping in the
    byte-identical validator copy."""
    out = redact_endpoint_for_log("http://127.0.4.1:1234")
    assert "127.0.4.1" not in out
    assert "127.0.4.*" in out


def test_localhost_not_redacted_for_log():
    assert "localhost" in redact_endpoint_for_log("http://localhost:1234")
