"""Windows / Hermes co-orchestration portal skin."""
from __future__ import annotations

from orama_system.portals.co_orchestration_shared import render_co_orchestration_html

SKIN_ID = "windows"
ACTIVE_PATH = "/co-orchestration/windows"


def skin_dict() -> dict[str, str]:
    return {
        "page_title": "Co-orchestration inbox — Hermes (Windows)",
        "accent": "#06b6d4",
        "nav_brand": "Hermes co-orchestration",
        "active_path": ACTIVE_PATH,
        "platform_label": "Windows",
        "local_role": "win",
        "heading": "Win ↔ Mac file inbox",
        "platform_banner": (
            "<strong>Hermes-only</strong> harness on this host · "
            "<strong>LM Studio :1234</strong> (27B autoresearch-coder) · "
            "Subagents: <strong>autoresearcher</strong>, <strong>coder</strong>, cursor-agent · "
            "Inbound: <code>list</code> / <code>read --name</code> · "
            "Outbound: <code>drop --peer</code>"
        ),
    }


def render_co_orchestration_page(*, version: str, cp_fetch_bootstrap: str) -> str:
    return render_co_orchestration_html(
        skin_dict(),
        version=version,
        cp_fetch_bootstrap=cp_fetch_bootstrap,
    )
