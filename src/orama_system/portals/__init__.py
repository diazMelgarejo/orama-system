"""Platform-specific portal views (macOS OpenClaw vs Windows Hermes)."""
from __future__ import annotations

from orama_system.portals.co_orchestration import (
    build_co_orchestration_summary,
    render_co_orchestration_page,
)

__all__ = [
    "build_co_orchestration_summary",
    "render_co_orchestration_page",
]
