"""LAN peer channel — WS-primary transport with SSE/POST fallback (Phase 1–2).

Shared JSON envelope on all wires; only this module branches on transport state.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import platform
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
from fastapi import WebSocket

log = logging.getLogger("ultrathink.lan_peer")

HEARTBEAT_INTERVAL_S = 15
WS_OPEN_TIMEOUT_S = 5
RETRY_WAIT_S = 30
WS_FAIL_BEFORE_SSE = 2


def local_platform() -> str:
    explicit = __import__("os").environ.get("ORAMA_PLATFORM", "").strip().lower()
    if explicit in ("windows", "win"):
        return "win"
    if explicit in ("macos", "darwin", "mac"):
        return "mac"
    return "win" if platform.system().lower() == "windows" else "mac"


def read_discovery_peer_ip() -> str:
    """Peer IP from ~/.openclaw/state/last_discovery.json (never hardcode DHCP)."""
    path = Path.home() / ".openclaw" / "state" / "last_discovery.json"
    role = local_platform()
    if not path.is_file():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    endpoints = data.get("endpoints") or {}
    peer = endpoints.get("mac" if role == "win" else "win") or {}
    ip = str(peer.get("ip") or "").strip()
    if ip in ("", "localhost", "127.0.0.1"):
        return ""
    return ip


def make_envelope(msg_type: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "type": msg_type,
        "source": local_platform(),
        "ts": int(time.time()),
        "data": data or {},
    }


class LanPeerChannel:
    """Channel manager: inbound WS peers, outbound queue for SSE, optional peer client."""

    def __init__(self) -> None:
        self.state: str = "idle"
        self._ws_peers: set[WebSocket] = set()
        self._out_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._inbound_handlers: list[Any] = []
        self._client_task: asyncio.Task[None] | None = None
        self._closed = False

    def register_inbound_handler(self, handler: Any) -> None:
        self._inbound_handlers.append(handler)

    async def register_ws_peer(self, ws: WebSocket) -> None:
        self._ws_peers.add(ws)
        if self.state == "idle":
            self.state = "ws_connected"

    async def unregister_ws_peer(self, ws: WebSocket) -> None:
        self._ws_peers.discard(ws)
        if not self._ws_peers and self.state == "ws_connected":
            self.state = "idle"

    async def on_inbound(self, event: dict[str, Any]) -> None:
        if event.get("type") == "probe":
            pong = make_envelope("probe-ack", {"ok": True})
            await self.send(pong)
            return
        for handler in self._inbound_handlers:
            try:
                await handler(event)
            except Exception:
                log.exception("lan_peer inbound handler failed")

    async def outbound_queue(self) -> AsyncIterator[dict[str, Any]]:
        while not self._closed:
            event = await self._out_queue.get()
            yield event

    async def send(self, event: dict[str, Any]) -> None:
        await self._out_queue.put(event)
        dead: list[WebSocket] = []
        for ws in list(self._ws_peers):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._ws_peers.discard(ws)

    async def connect(self, peer_ip: str, port: int = 8002) -> None:
        if self._client_task and not self._client_task.done():
            return
        self._client_task = asyncio.create_task(self._client_loop(peer_ip, port))

    async def close(self) -> None:
        self._closed = True
        if self._client_task and not self._client_task.done():
            self._client_task.cancel()
            try:
                await self._client_task
            except asyncio.CancelledError:
                pass

    async def _client_loop(self, peer_ip: str, port: int) -> None:
        ws_fails = 0
        while not self._closed:
            self.state = "ws_connecting"
            try:
                await self._ws_client_session(peer_ip, port)
                ws_fails = 0
            except Exception as exc:
                ws_fails += 1
                log.warning("lan_peer ws client failed (%s): %s", ws_fails, exc)
                if ws_fails >= WS_FAIL_BEFORE_SSE:
                    try:
                        await self._sse_client_session(peer_ip, port)
                        ws_fails = 0
                    except Exception as sse_exc:
                        log.warning("lan_peer sse fallback failed: %s", sse_exc)
            self.state = "disconnected"
            await asyncio.sleep(RETRY_WAIT_S)

    async def _ws_client_session(self, peer_ip: str, port: int) -> None:
        from utils.control_plane_auth import outbound_control_plane_tokens

        tokens = outbound_control_plane_tokens()
        if not tokens:
            tokens = [""]
        last_exc: Exception | None = None
        import websockets

        for token in tokens:
            qs = f"?token={token}" if token else ""
            url = f"ws://{peer_ip}:{port}/ws/portal-peer{qs}"
            try:
                async with websockets.connect(url, open_timeout=WS_OPEN_TIMEOUT_S) as ws:
                    self.state = "ws_connected"
                    heartbeat = asyncio.create_task(self._heartbeat_ws(ws))
                    try:
                        async for raw in ws:
                            try:
                                event = json.loads(raw)
                            except json.JSONDecodeError:
                                continue
                            await self.on_inbound(event)
                    finally:
                        heartbeat.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await heartbeat
                    return
            except Exception as exc:
                last_exc = exc
                continue
        if last_exc:
            raise last_exc

    async def _heartbeat_ws(self, ws: Any) -> None:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL_S)
            await ws.send(json.dumps(make_envelope("heartbeat")))

    async def _sse_client_session(self, peer_ip: str, port: int) -> None:
        from utils.control_plane_auth import auth_headers

        url = f"http://{peer_ip}:{port}/events/peer-stream"
        self.state = "sse_connected"
        async with httpx.AsyncClient(timeout=None, headers=auth_headers()) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if not payload:
                        continue
                    try:
                        event = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    await self.on_inbound(event)
