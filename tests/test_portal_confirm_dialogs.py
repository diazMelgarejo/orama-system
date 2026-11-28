#!/usr/bin/env python3
"""Regression tests for the legacy portal's destructive-control confirm dialogs.

The legacy dashboard (``portal_server._render_html``) keeps Stop All, the three
per-service restarts and Re-discover on the glass, but every one of them must be
routed through one native confirm dialog instead of a wired-up click.
"""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

import orama_system.portal_server as portal_server

pytestmark = pytest.mark.unit

# Labels the task treats as destructive. Matched as substrings because the
# rendered label still carries its leading icon entity (&#9632; / &#8635;).
_DESTRUCTIVE_LABELS = (
    "Stop All",
    "Restart PT",
    "Restart orama",
    "Restart Portal",
    "Re-discover",
)

_BUTTON_RE = re.compile(r"<button\b([^>]*)>(.*?)</button>", re.DOTALL)
_OPS_RE = re.compile(r"_CONFIRM_OPS = \{(.*?)\n\};", re.DOTALL)
_OP_KEY_RE = re.compile(r"'([a-z-]+)':\s*function")


@pytest.fixture()
def legacy_page(monkeypatch, tmp_path) -> str:
    """Render the legacy dashboard the way tests/test_control_plane_auth.py does.

    ``_WEB_DIST`` is redirected at an empty tmp folder so ``index()`` cannot take
    the React FileResponse path, and ``api_status`` is faked so no probe runs.
    """
    monkeypatch.setenv("ORAMA_INSECURE_DEV", "1")
    monkeypatch.setattr(portal_server, "_WEB_DIST", tmp_path)

    async def _fake_status():
        """Minimal status payload: no services, no routing, no activity."""
        return {"services": {}, "routing": None, "activity": [], "agents": []}

    monkeypatch.setattr(portal_server, "api_status", _fake_status)

    with TestClient(portal_server.app, raise_server_exceptions=True) as client:
        response = client.get("/")

    assert response.status_code == 200
    return response.text


def _destructive_buttons(html: str) -> list[tuple[str, str]]:
    """(label, opening-tag attributes) for every destructive control on the page."""
    found = []
    for attributes, inner in _BUTTON_RE.findall(html):
        label = re.sub(r"<[^>]+>", "", inner).strip()
        if any(name in label for name in _DESTRUCTIVE_LABELS):
            found.append((label, attributes))
    return found


def _consequence(attributes: str) -> str:
    """The data-confirm text of one rendered control."""
    match = re.search(r'data-confirm="([^"]+)"', attributes)
    assert match is not None, attributes
    return match.group(1)


def _script(html: str) -> str:
    """The inline dashboard script, i.e. everything after the single <script>."""
    return html.split("<script>", 1)[1]


def test_every_destructive_control_carries_a_one_line_consequence(legacy_page: str) -> None:
    buttons = _destructive_buttons(legacy_page)
    assert len(buttons) == len(_DESTRUCTIVE_LABELS)

    for label, attributes in buttons:
        assert "onclick" not in attributes, label
        assert "data-confirm-op=" in attributes, label
        consequence = _consequence(attributes)
        assert "\n" not in consequence, label
        assert len(consequence) >= 40, label
        assert consequence.endswith("."), label


def test_destructive_controls_name_ops_the_helper_registers(legacy_page: str) -> None:
    registry = _OPS_RE.search(_script(legacy_page))
    assert registry is not None
    registered = set(_OP_KEY_RE.findall(registry.group(1)))
    assert "stop" in registered
    assert "rediscover" in registered

    declared = set()
    for label, attributes in _destructive_buttons(legacy_page):
        match = re.search(r'data-confirm-op="([^"]+)"', attributes)
        assert match is not None, label
        declared.add(match.group(1))

    assert len(declared) == len(_DESTRUCTIVE_LABELS)
    assert declared <= registered


def test_confirm_dialog_exists_and_is_aria_labelled(legacy_page: str) -> None:
    assert legacy_page.count("<dialog") == 1
    opening_tag = re.search(r"<dialog\b[^>]*>", legacy_page)
    assert opening_tag is not None
    tag = opening_tag.group(0)
    assert 'id="confirm-dialog"' in tag
    assert 'aria-labelledby="confirm-dialog-title"' in tag
    assert 'aria-describedby="confirm-dialog-body"' in tag
    assert re.search(r'<h2[^>]*id="confirm-dialog-title"[^>]*>\s*\S', legacy_page)
    assert re.search(r'<p[^>]*id="confirm-dialog-body"[^>]*>', legacy_page)


def test_cancel_is_the_default_focus_and_confirm_is_danger_coloured(legacy_page: str) -> None:
    cancel = re.search(r'<button\b[^>]*id="confirm-dialog-cancel"[^>]*>', legacy_page)
    confirm = re.search(r'<button\b[^>]*id="confirm-dialog-ok"[^>]*>', legacy_page)
    assert cancel is not None and confirm is not None
    assert "autofocus" in cancel.group(0)
    assert "danger" in confirm.group(0)
    assert "danger" not in cancel.group(0)
    assert cancel.start() < confirm.start()


def test_no_destructive_fetch_runs_before_confirm(legacy_page: str) -> None:
    assert 'onclick="svcAction' not in legacy_page
    assert 'onclick="rediscover' not in legacy_page
    # Only the two helpers behind _CONFIRM_OPS may name these routes.
    assert legacy_page.count("'/api/stop'") == 1
    assert legacy_page.count("'/api/restart/'") == 1
    assert legacy_page.count("'/api/rediscover'") == 1

    js = _script(legacy_page)
    # runConfirmed is defined once and referenced once: from the Confirm button only.
    assert js.count("runConfirmed") == 2
    # 1 declaration + 4 registered svcAction calls; 1 declaration + 1 registry call.
    assert len(re.findall(r"svcAction\(", js)) == 5
    assert len(re.findall(r"rediscover\(\)", js)) == 2
    # The single entry point is the delegated data-confirm click handler.
    assert "closest('[data-confirm]')" in js
    assert "e.preventDefault();" in js
    assert ".showModal()" in js


def test_focus_returns_to_the_trigger_when_the_dialog_closes(legacy_page: str) -> None:
    js = _script(legacy_page)
    assert "_confirmTrigger = trigger;" in js
    assert "addEventListener('close', function () {" in js
    assert "trigger.focus();" in js


def test_page_states_the_stop_is_a_confirmed_emergency_override(legacy_page: str) -> None:
    stop = [attrs for label, attrs in _destructive_buttons(legacy_page) if "Stop All" in label]
    assert len(stop) == 1
    consequence = _consequence(stop[0])
    assert "emergency override" in consequence
    assert "no approval gate" in consequence
    assert "confirmation dialog first" in legacy_page
