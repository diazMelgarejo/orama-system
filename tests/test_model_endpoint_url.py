"""Policy tests for utils.model_endpoint_url (Security Fix 5)."""
from __future__ import annotations

import pytest

from utils.model_endpoint_url import (
    ModelEndpointPolicyError,
    parse_model_endpoint_list,
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
