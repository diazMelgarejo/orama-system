"""macOS / OpenClaw co-orchestration portal skin."""
from __future__ import annotations

from orama_system.portals.co_orchestration_shared import render_co_orchestration_html

SKIN_ID = "macos"
ACTIVE_PATH = "/co-orchestration/macos"


def skin_dict() -> dict[str, str]:
    return {
        "page_title": "Co-orchestration inbox — OpenClaw (macOS)",
        "accent": "#38bdf8",
        "nav_brand": "OpenClaw co-orchestration",
        "active_path": ACTIVE_PATH,
        "platform_label": "macOS",
        "local_role": "mac",
        "heading": "Mac ↔ Win file inbox",
        "platform_banner": (
            "<strong>OpenClaw + AlphaClaw</strong> on this host · "
            "<strong>Ollama :11434</strong> warm (primary inference) · "
            "LM Studio :1234 passive · "
            "Subagents: <strong>mac-researcher</strong>, <strong>orchestrator</strong>, cursor-agent · "
            "Coordination: <code>lan_peer_assign.py</code> file drops (no remote RPC)"
        ),
    }


def render_co_orchestration_page(*, version: str, cp_fetch_bootstrap: str) -> str:
    return render_co_orchestration_html(
        skin_dict(),
        version=version,
        cp_fetch_bootstrap=cp_fetch_bootstrap,
    )
