#!/usr/bin/env python3
"""/api/restart: Windows Portal restarts go through start.ps1; restarts never bind IPv6-only localhost."""
from __future__ import annotations

import asyncio
import ipaddress
import socket
import subprocess
from typing import Any

import pytest

from orama_system import portal_server

IPV4_LOOPBACK = str(ipaddress.IPv4Address(socket.INADDR_LOOPBACK))


def test_localhost_is_pinned_to_ipv4_loopback_and_other_hosts_are_kept() -> None:
    """The word localhost (any case or padding) becomes the IPv4 loopback; explicit hosts pass through."""
    assert portal_server._restart_bind_host("localhost") == IPV4_LOOPBACK
    assert portal_server._restart_bind_host(" LocalHost ") == IPV4_LOOPBACK
    assert portal_server._restart_bind_host("0.0.0.0") == "0.0.0.0"
    assert portal_server._restart_bind_host("192.0.2.5") == "192.0.2.5"


def test_windows_portal_restart_is_delegated_to_start_ps1() -> None:
    """On Windows the Portal is restarted with its TLS front end by start.ps1 --restart-portal, detached."""
    plan = portal_server._restart_plan("portal", windows=True)
    assert plan["delegated"] is True
    assert plan["cmd"][0] == "powershell.exe"
    assert plan["cmd"][-1] == "--restart-portal"
    assert plan["cmd"][-2].replace("\\", "/").endswith("platform/windows/start.ps1")
    assert plan["popen_kwargs"]["creationflags"] & 0x00000200  # CREATE_NEW_PROCESS_GROUP
    assert plan["popen_kwargs"]["creationflags"] & 0x08000000  # CREATE_NO_WINDOW


@pytest.mark.parametrize("service", ["pt", "orama"])
def test_windows_service_restart_binds_ipv4_loopback_not_localhost(monkeypatch: pytest.MonkeyPatch, service: str) -> None:
    """A direct uvicorn restart on Windows never passes --host localhost."""
    monkeypatch.setitem(portal_server._SERVICE_BIND_HOSTS, service, "localhost")
    plan = portal_server._restart_plan(service, windows=True)
    assert plan["delegated"] is False
    host = plan["cmd"][plan["cmd"].index("--host") + 1]
    assert host == IPV4_LOOPBACK
    assert "start_new_session" not in plan["popen_kwargs"]


def test_posix_portal_restart_runs_uvicorn_in_a_new_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """Off Windows the Portal restarts directly, in its own session, on IPv4 loopback for localhost."""
    monkeypatch.setitem(portal_server._SERVICE_BIND_HOSTS, "portal", "localhost")
    plan = portal_server._restart_plan("portal", windows=False)
    assert plan["delegated"] is False
    assert plan["popen_kwargs"] == {"start_new_session": True}
    assert plan["cmd"][plan["cmd"].index("--host") + 1] == IPV4_LOOPBACK


def test_delegated_restart_does_not_kill_the_portal_itself(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """When start.ps1 owns the restart, the route launches it and leaves stopping to it."""
    launched: list[list[str]] = []

    def fake_popen(cmd: list[str], **kwargs: Any) -> object:
        """Record the launch instead of starting a process."""
        launched.append(cmd)
        return object()

    def no_kill(port: int) -> int:
        """Fail the test if the route looks up a PID to kill."""
        raise AssertionError("delegated restart must not kill the listener itself")

    plan = {"delegated": True, "cmd": ["launcher", "--restart-portal"], "cwd": str(tmp_path),
            "env": {}, "popen_kwargs": {}}
    monkeypatch.setattr(portal_server, "verify_lifecycle_origin", lambda request: None)
    monkeypatch.setattr(portal_server, "_restart_plan", lambda service, windows: plan)
    monkeypatch.setattr(portal_server, "_pid_on_port", no_kill)
    monkeypatch.setattr(portal_server, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    result = asyncio.run(portal_server.api_restart("portal", request=None))  # type: ignore[arg-type]

    assert result["ok"] is True
    assert launched == [["launcher", "--restart-portal"]]
