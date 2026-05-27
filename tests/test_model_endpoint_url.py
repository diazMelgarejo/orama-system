"""Policy tests for utils.model_endpoint_url (Security Fix 5)."""
from __future__ import annotations

import pytest

from utils.model_endpoint_url import (
    ModelEndpointPolicyError,
    validate_model_endpoint_url,
)


@pytest.fixture(autouse=True)
def _clear_public_opt_in(monkeypatch):
    monkeypatch.delenv("ALLOW_PUBLIC_MODEL_ENDPOINTS", raising=False)


def test_loopback_allowed():
    assert validate_model_endpoint_url("http://127.0.0.1:1234") == "http://127.0.0.1:1234"


def test_rfc1918_allowed():
    assert validate_model_endpoint_url("http://192.168.0.10:1234") == "http://192.168.0.10:1234"


def test_public_blocked_without_opt_in():
    with pytest.raises(ModelEndpointPolicyError):
        validate_model_endpoint_url("http://1.1.1.1:1234")


def test_public_allowed_with_opt_in(monkeypatch):
    monkeypatch.setenv("ALLOW_PUBLIC_MODEL_ENDPOINTS", "1")
    assert validate_model_endpoint_url("http://1.1.1.1:1234") == "http://1.1.1.1:1234"
