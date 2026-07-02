"""Randomized tests for endpoint policy boundary safety.

Exercises the canonical Perpetua-Tools-owned parser (utils.model_endpoint_url)
per AGENTS.md "Endpoint transport policy" — orama does not fork this parser.
"""
from __future__ import annotations

import random
import string

import pytest

from utils.model_endpoint_url import ModelEndpointPolicyError, validate_model_endpoint_url


def _rand():
    chars = string.ascii_letters + string.digits + ":/@[]-_.*"
    return "".join(random.choice(chars) for _ in range(random.randint(0, 80)))


@pytest.mark.parametrize("_", range(50))
def test_no_crash_on_random_input(_):
    s = _rand()
    try:
        validate_model_endpoint_url(s, allow_public=False)
    except ModelEndpointPolicyError:
        pass
    except Exception as exc:
        raise AssertionError(f"unexpected exception leaked: {type(exc)}") from exc


# Regression vectors: each once denoted an accept/reject boundary decision.
# Kept explicit (rather than only random) so a future change that flips one
# of these outcomes fails loudly instead of relying on random seed luck.
_REGRESSION_VECTORS = [
    ("", False),  # empty endpoint URL
    ("ftp://localhost:1234", False),  # disallowed scheme
    ("http://user:pass@localhost:1234", False),  # credentials not allowed
    ("http://localhost:999999", False),  # port out of range -> ValueError -> wrapped
    ("http://169.254.169.254", False),  # link-local SSRF (cloud metadata) blocked
    ("http://[::ffff:127.0.0.1]:80", True),  # IPv4-mapped IPv6 loopback allowed
]


@pytest.mark.parametrize("url,should_pass", _REGRESSION_VECTORS)
def test_regression_vectors(url, should_pass):
    if should_pass:
        result = validate_model_endpoint_url(url, allow_public=False)
        assert isinstance(result, str) and result
    else:
        with pytest.raises(ModelEndpointPolicyError):
            validate_model_endpoint_url(url, allow_public=False)


@pytest.mark.parametrize("_", range(50))
def test_no_crash_on_random_input_allow_public(_):
    """Same fuzz coverage with allow_public=True to exercise the public-host branch."""
    s = _rand()
    try:
        validate_model_endpoint_url(s, allow_public=True)
    except ModelEndpointPolicyError:
        pass
    except Exception as exc:
        raise AssertionError(f"unexpected exception leaked: {type(exc)}") from exc
