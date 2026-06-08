"""Compatibility wrapper for the renamed oramasys core contracts."""
from __future__ import annotations

try:
    from .oramasys_core import *  # noqa: F401,F403
except ImportError:
    from oramasys_core import *  # noqa: F401,F403
