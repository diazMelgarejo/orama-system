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

from utils.endpoint_policy_core import TransportIdentity, parse_transport_identity
from utils.model_endpoint_url import ModelEndpointPolicyError, validate_model_endpoint_url

log = logging.getLogger("ultrathink.lan_peer")

HEARTBEAT_INTERVAL_S = 15
WS_OPEN_TIMEOUT_S = 5
RETRY_WAIT_S = 30
WS_FAIL_BEFORE_SSE = 2


def local_platform() -> str:
    """Return 'win' or 'mac' for this host, honouring ORAMA_PLATFORM."""
    explicit = __import__("os").environ.get("ORAMA_PLATFORM", "").strip().lower()
    if explicit in ("windows", "win"):
        return "win"
    if explicit in ("macos", "darwin", "mac"):
        return "mac"
    return "win" if platform.system().lower() == "windows" else "mac"


def read_discovery_peer_identity() -> TransportIdentity | None:
    """Return the validated transport identity for the discovered peer.

    The "ip" field is written by a separate process (scripts/discover.py);
    preserve its scheme, host, and optional port so the outbound client can
    authorize the backend target before selecting WS or SSE.
    """
    path = Path.home() / ".openclaw" / "state" / "last_discovery.json"
    role = local_platform()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    endpoints = data.get("endpoints") or {}
    peer = endpoints.get("mac" if role == "win" else "win") or {}
    raw_ip = str(peer.get("ip") or "").strip()
    if raw_ip in ("", "localhost", "127.0.0.1"):
        return None
    identity = parse_transport_identity(raw_ip)
    if identity is None:
        log.warning("lan_peer discovery: rejecting malformed peer endpoint")
    return identity


def read_discovery_peer_ip() -> str:
    """Return the legacy hostname projection used by portal/UI callers."""
    identity = read_discovery_peer_identity()
    return identity.hostname if identity is not None else ""


def build_peer_transport_url(
    identity: TransportIdentity,
    port: int,
    path: str,
    *,
    websocket: bool,
) -> str:
    """Authorize a backend target and select its HTTP or WS transport scheme."""
    if not path.startswith("/"):
        raise ValueError("peer transport path must start with '/'")
    base_url = validate_model_endpoint_url(identity.with_port(port))
    scheme, netloc = base_url.split("://", 1)
    if websocket:
        scheme = "wss" if scheme == "https" else "ws"
    return f"{scheme}://{netloc}{path}"


def ws_handshake_headers(token: str) -> dict[str, str] | None:
    """Return the WebSocket handshake headers carrying the bearer, or None when there is no token; the token is never placed in the URL."""
    return {"Authorization": f"Bearer {token}"} if token else None


def make_envelope(msg_type: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a peer message envelope dict for the given event."""
    return {
        "type": msg_type,
        "source": local_platform(),
        "ts": int(time.time()),
        "data": data or {},
    }


class LanPeerChannel:
    """Channel manager: inbound WS peers, outbound queue for SSE, optional peer client."""

    def __init__(self) -> None:
        """Initialise channel state for the local peer identity."""
        self.state: str = "idle"
        self._ws_peers: set[WebSocket] = set()
        self._out_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._inbound_handlers: list[Any] = []
        self._client_task: asyncio.Task[None] | None = None
        self._closed = False

    def register_inbound_handler(self, handler: Any) -> None:
        """Register a callback invoked for each inbound peer message."""
        self._inbound_handlers.append(handler)

    async def register_ws_peer(self, ws: WebSocket) -> None:
        """Track a connected WebSocket peer for outbound delivery."""
        self._ws_peers.add(ws)
        if self.state == "idle":
            self.state = "ws_connected"

    async def unregister_ws_peer(self, ws: WebSocket) -> None:
        """Forget a WebSocket peer once it disconnects."""
        self._ws_peers.discard(ws)
        if not self._ws_peers and self.state == "ws_connected":
            self.state = "idle"

    async def on_inbound(self, event: dict[str, Any]) -> dict[str, Any] | None:
        """Dispatch an inbound envelope to the registered handlers."""
        if event.get("type") == "probe":
            pong = make_envelope("probe-ack", {"ok": True})
            await self.send(pong)
            return
        if event.get("type") == "mesh_ip_migration_announcement":
            try:
                from mesh.discovery_trust import apply_migration_announcement, migration_digest
                payload = event.get("data")
                if not isinstance(payload, dict) or not payload:
                    payload = event
                accepted = apply_migration_announcement(payload)
                return {"ok": accepted, "migration_id": migration_digest(payload) if accepted else None}
            except Exception:
                log.exception("Failed to apply mesh IP migration announcement")
                return {"ok": False, "migration_id": None}
        for handler in self._inbound_handlers:
            try:
                await handler(event)
            except Exception:
                log.exception("lan_peer inbound handler failed")

    async def outbound_queue(self) -> AsyncIterator[dict[str, Any]]:
        """Yield queued outbound events for SSE consumers."""
        while not self._closed:
            event = await self._out_queue.get()
            yield event

    async def send(self, event: dict[str, Any]) -> None:
        """Send an envelope to the peer over the best available transport."""
        await self._out_queue.put(event)
        dead: list[WebSocket] = []
        for ws in list(self._ws_peers):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._ws_peers.discard(ws)

    async def connect(self, peer: str | TransportIdentity, port: int = 8002) -> None:
        """Start the background client loop that connects to the peer."""
        if self._client_task and not self._client_task.done():
            return
        identity = peer if isinstance(peer, TransportIdentity) else parse_transport_identity(peer)
        if identity is None:
            raise ValueError("peer transport identity is invalid")
        self._client_task = asyncio.create_task(self._client_loop(identity, port))

    async def close(self) -> None:
        """Stop the client loop and release transport resources."""
        self._closed = True
        if self._client_task and not self._client_task.done():
            self._client_task.cancel()
            try:
                await self._client_task
            except asyncio.CancelledError:
                pass

    async def _client_loop(self, identity: TransportIdentity, port: int) -> None:
        """Run the reconnecting client loop, falling back from WebSocket to SSE."""
        ws_fails = 0
        while not self._closed:
            self.state = "ws_connecting"
            try:
                await self._ws_client_session(identity, port)
                ws_fails = 0
            except ModelEndpointPolicyError:
                self.state = "disconnected"
                log.warning("lan_peer rejected peer endpoint by policy")
                return
            except Exception:
                ws_fails += 1
                log.warning("lan_peer ws client failed (%s)", ws_fails)
                if ws_fails >= WS_FAIL_BEFORE_SSE:
                    try:
                        await self._sse_client_session(identity, port)
                        ws_fails = 0
                    except ModelEndpointPolicyError:
                        self.state = "disconnected"
                        log.warning("lan_peer rejected peer endpoint by policy")
                        return
                    except Exception:
                        log.warning("lan_peer sse fallback failed")
            self.state = "disconnected"
            await asyncio.sleep(RETRY_WAIT_S)

    async def _ws_client_session(self, identity: TransportIdentity, port: int) -> None:
        """Connect to the peer WebSocket, sending the bearer only in the Authorization header over wss://.

        A token with a non-wss URL raises ModelEndpointPolicyError before any connection; the
        client loop treats that as terminal (no retry, no unauthenticated fallback).
        """
        from utils.control_plane_auth import outbound_control_plane_tokens

        tokens = outbound_control_plane_tokens()
        if not tokens:
            tokens = [""]
        last_exc: Exception | None = None
        import websockets

        endpoint = build_peer_transport_url(
            identity,
            port,
            "/ws/portal-peer",
            websocket=True,
        )

        for token in tokens:
            # SECURITY: the bearer travels only in the Authorization header of
            # the handshake. It is never placed in the URL, which access logs
            # (Caddy, uvicorn) record.
            headers = ws_handshake_headers(token)
            url = endpoint
            if token and not url.startswith("wss://"):
                # SECURITY: RFC 6750 s5.3 - never send a bearer over ws://, and
                # never silently downgrade to an unauthenticated connection.
                raise ModelEndpointPolicyError(
                    "refusing to send control-plane bearer over unencrypted ws://; wss:// is required"
                )
            try:
                async with websockets.connect(
                    url,
                    open_timeout=WS_OPEN_TIMEOUT_S,
                    additional_headers=headers,
                ) as ws:
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
        """Send periodic heartbeat frames on an open WebSocket."""
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL_S)
            await ws.send(json.dumps(make_envelope("heartbeat")))

    async def _sse_client_session(self, identity: TransportIdentity, port: int) -> None:
        """Stream peer events over SSE, sending auth headers only over https://.

        If auth headers would be sent to a non-https URL this raises ModelEndpointPolicyError
        before any request; the client loop treats that as terminal (no retry, no
        unauthenticated fallback).
        """
        from utils.control_plane_auth import auth_headers

        url = build_peer_transport_url(
            identity,
            port,
            "/events/peer-stream",
            websocket=False,
        )
        headers = auth_headers()
        if headers and not url.startswith("https://"):
            raise ModelEndpointPolicyError(
                "refusing to send control-plane credentials over unencrypted http://; https:// is required"
            )
        self.state = "sse_connected"
        async with httpx.AsyncClient(timeout=None, headers=headers) as client:
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
