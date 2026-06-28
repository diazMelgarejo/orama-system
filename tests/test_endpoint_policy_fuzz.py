"""Randomized tests for endpoint policy boundary safety."""
from __future__ import annotations

import random
import string

import pytest

from utils.endpoint_policy_core import ModelEndpointPolicyError, validate_base_url


def _rand():
    chars = string.ascii_letters + string.digits + ":/@[]-_.*"
    return "".join(random.choice(chars) for _ in range(random.randint(0, 80)))


@pytest.mark.parametrize("_", range(50))
def test_no_crash_on_random_input(_):
    s = _rand()
    try:
        validate_base_url(s, allow_public=False)
    except ModelEndpointPolicyError:
        pass
    except Exception as exc:
        raise AssertionError(f"unexpected exception leaked: {type(exc)}") from exc
