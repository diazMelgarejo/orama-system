"""Co-orchestration portal — platform router (macOS vs Windows skins)."""
from __future__ import annotations

from typing import Any

from orama_system.portals import co_orchestration_macos as macos_skin
from orama_system.portals import co_orchestration_windows as windows_skin
from orama_system.portals.co_orchestration_shared import (
    build_co_orchestration_summary as _build_summary,
    render_co_orchestration_html,
)

_SKINS = {
    macos_skin.SKIN_ID: macos_skin,
    windows_skin.SKIN_ID: windows_skin,
}


def resolve_skin_id(local_role: str, *, explicit: str | None = None) -> str:
    if explicit and explicit in _SKINS:
        return explicit
    return macos_skin.SKIN_ID if local_role == "mac" else windows_skin.SKIN_ID


def build_co_orchestration_summary(
    *,
    local_role: str,
    peer_ip: str,
    local_inbox: list[dict[str, Any]],
    peer_inbox: list[dict[str, Any]],
    peer_error: str = "",
    platform_skin: str | None = None,
) -> dict[str, Any]:
    skin_id = resolve_skin_id(local_role, explicit=platform_skin)
    return _build_summary(
        local_role=local_role,
        peer_ip=peer_ip,
        local_inbox=local_inbox,
        peer_inbox=peer_inbox,
        peer_error=peer_error,
        platform_skin=skin_id,
    )


def render_co_orchestration_page(
    *,
    version: str,
    cp_fetch_bootstrap: str,
    local_role: str,
    platform_skin: str | None = None,
) -> str:
    skin_id = resolve_skin_id(local_role, explicit=platform_skin)
    module = _SKINS[skin_id]
    return module.render_co_orchestration_page(
        version=version,
        cp_fetch_bootstrap=cp_fetch_bootstrap,
    )
