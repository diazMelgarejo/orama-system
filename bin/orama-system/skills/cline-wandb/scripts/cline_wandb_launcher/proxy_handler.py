"""One proxied request: authenticate, admit, clamp, forward, then settle its spend."""
from __future__ import annotations

import hmac
import http.server
import json
import socket
import urllib.parse
import urllib.request
from typing import Any

from .accounting import (UNACCOUNTED, BoundaryExceededError, clamp_output_caps, classify_chat_outcome,
                         extract_json_completion_tokens, extract_sse_completion_tokens)
from .proxy_server import PHASE_CLOSED, AccountingProxyServer
from .upstream import fetch, hop_by_hop_names, is_identity_encoded, resolve_upstream_url


class AccountingProxyHandler(http.server.BaseHTTPRequestHandler):
    """HTTP proxy handler enforcing request count and completion token limits."""

    server: AccountingProxyServer
    protocol_version = "HTTP/1.0"

    def log_message(self, format: str, *args: object) -> None:
        # Silence access logs to prevent API keys/prompts leaking to console
        pass

    def _send(self, status: int, header_items: list[tuple[str, str]], body: bytes) -> None:
        """Write one response and close. A client that already went away (for example the child we
        just terminated) is expected: the outcome was recorded before this write, so it is not an error."""
        self.close_connection = True
        try:
            self.send_response(status)
            for key, value in header_items:
                self.send_header(key, value)
            self.send_header("Connection", "close")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _reject(self, status: int, err_bytes: bytes) -> None:
        """Send a compact JSON error response and close the connection."""
        self._send(status, [("Content-Type", "application/json")], err_bytes)

    def _fail_closed(self, cause: str, limit: int | None, actual: object, status: int, message: bytes) -> None:
        """Record the breach, terminate the child fail-closed, and reject the request."""
        with self.server.lock:
            self.server.boundary_error.append(BoundaryExceededError(cause, limit, actual))
        self.server.terminate_child()
        self._reject(status, message)

    def _is_authorized(self) -> bool:
        supplied = self.headers.get("Authorization", "").encode("utf-8")
        expected = f"Bearer {self.server.session_token}".encode("utf-8")
        return hmac.compare_digest(supplied, expected)

    def _is_chat_completions_route(self) -> bool:
        route = urllib.parse.urlsplit(self.path).path.rstrip("/")
        return self.command == "POST" and route.endswith("/chat/completions")

    def do_GET(self) -> None:
        self._proxy_request()

    def do_POST(self) -> None:
        self._proxy_request()

    def do_PUT(self) -> None:
        self._proxy_request()

    def do_DELETE(self) -> None:
        self._proxy_request()

    def _proxy_request(self) -> None:
        if not self._is_authorized():
            self._reject(401, b'{"error": {"message": "missing or invalid launcher session credential"}}')
            return
        is_chat = self._is_chat_completions_route()
        if self.command == "POST" and not is_chat:
            self._reject(403, b'{"error": {"message": "unsupported POST route refused fail-closed"}}')
            return
        content_len = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_len) if content_len > 0 else b""
        if not is_chat:
            self._forward(body_bytes, chat_budget=None, is_streaming=False)
            return
        # Serialize chat completions so concurrent requests cannot race the remaining output budget.
        with self.server.chat_gate:
            self._handle_chat(body_bytes)

    def _admit_chat_request(self) -> int | None:
        """Gate one chat request; return the remaining output budget, or None after rejecting it."""
        with self.server.lock:
            if self.server.phase == PHASE_CLOSED:
                self._reject(503, b'{"error": {"message": "proxy closed; dispatch refused"}}')
                return None
            if self.server.boundary_error:
                self._reject(429, b'{"error": {"message": "bound already exceeded"}}')
                return None
            self.server.request_count += 1
            if self.server.request_count > self.server.max_requests:
                breach = ("max_requests", self.server.max_requests, self.server.request_count,
                          b'{"error": {"message": "max_requests exceeded", "type": "requests_exceeded"}}')
            else:
                remaining = self.server.max_total_output - self.server.cumulative_output_tokens
                if remaining > 0:
                    return remaining
                breach = ("max_total_output", self.server.max_total_output, self.server.cumulative_output_tokens,
                          b'{"error": {"message": "max_total_output exhausted", "type": "tokens_exceeded"}}')
        cause, limit, actual, message = breach
        self._fail_closed(cause, limit, actual, 429, message)
        return None

    def _prepare_chat_payload(self, body_bytes: bytes, remaining_tokens: int) -> tuple[bytes, bool] | None:
        """Parse the body, clamp output caps, and force include_usage on streams."""
        try:
            req_json = json.loads(body_bytes.decode("utf-8")) if body_bytes else None
        except (UnicodeDecodeError, ValueError):
            req_json = None
        if not isinstance(req_json, dict):
            self._fail_closed(
                "invalid_request", None, "non-object JSON body", 400,
                b'{"error": {"message": "invalid JSON request body; refused fail-closed"}}',
            )
            return None
        clamp_output_caps(req_json, remaining_tokens)
        is_streaming = req_json.get("stream") is True
        if is_streaming:
            opts = req_json.get("stream_options")
            req_json["stream_options"] = {**(opts if isinstance(opts, dict) else {}), "include_usage": True}
        return json.dumps(req_json).encode("utf-8"), is_streaming

    def _handle_chat(self, body_bytes: bytes) -> None:
        remaining = self._admit_chat_request()
        if remaining is None:
            return
        prepared = self._prepare_chat_payload(body_bytes, remaining)
        if prepared is None:
            return
        payload, is_streaming = prepared
        self._forward(payload, chat_budget=remaining, is_streaming=is_streaming)

    def _build_upstream_request(self, body_bytes: bytes) -> urllib.request.Request:
        drop = hop_by_hop_names(self.headers, "host", "content-length", "authorization", "accept-encoding")
        headers = {k: v for k, v in self.headers.items() if k.lower() not in drop}
        headers["Connection"] = "close"
        headers["Accept-Encoding"] = "identity"  # the usage parsers read plain bodies only
        if self.server.upstream_key:
            headers["Authorization"] = f"Bearer {self.server.upstream_key}"
        if body_bytes:
            headers["Content-Length"] = str(len(body_bytes))
        return urllib.request.Request(
            resolve_upstream_url(self.server.upstream_base_url, self.path),
            data=body_bytes or None, headers=headers, method=self.command,
        )

    def _settle_chat(self, status: int, headers: Any, body: bytes, is_streaming: bool, budget: int) -> bool:
        """Apply the two-outcome rule to a chat response. False when the request was rejected here."""
        tokens = None
        # A reply encoded despite `identity` is never parsed: any usage visible in its bytes is unverified.
        if 200 <= status < 300 and is_identity_encoded(headers):
            tokens = extract_sse_completion_tokens(body) if is_streaming else extract_json_completion_tokens(body)
        if classify_chat_outcome(status, tokens) == UNACCOUNTED:
            return self._reject_unaccounted(status if status >= 400 else 502, budget)
        with self.server.lock:
            self.server.cumulative_output_tokens += tokens
            total = self.server.cumulative_output_tokens
        if total > self.server.max_total_output:
            self._fail_closed(
                "max_total_output", self.server.max_total_output, total, 429,
                b'{"error": {"message": "max_total_output exceeded", "type": "tokens_exceeded"}}',
            )
            return False
        return True

    def _reject_unaccounted(self, status: int, budget: int) -> bool:
        """Debit the whole clamp (worst case) so no later request reuses it, then fail closed."""
        with self.server.lock:
            self.server.cumulative_output_tokens += budget
            total = self.server.cumulative_output_tokens
        self._fail_closed(
            "unaccounted_dispatch", None, f"status={status}, debited={budget}, total={total}", status,
            b'{"error": {"message": "dispatch could not be accounted for; failing closed"}}',
        )
        return False

    def _relay(self, status: int, headers: Any, body: bytes) -> None:
        drop = hop_by_hop_names(headers, "content-length")
        kept = [(k, v) for k, v in headers.items() if k.lower() not in drop]
        self._send(status, kept, body)

    def _forward(self, body_bytes: bytes, *, chat_budget: int | None, is_streaming: bool) -> None:
        """Forward one request. chat_budget is the clamp for a chat request, None for any other route."""
        if not self.server.claim_dispatch():
            # CLOSED was set before this worker claimed a slot: nothing was sent, so nothing is debited.
            self._reject(503, b'{"error": {"message": "proxy closed; dispatch refused"}}')
            return
        try:
            status, headers, body = fetch(self._build_upstream_request(body_bytes), self.server.timeout_ms)
        except Exception as exc:
            status = 504 if isinstance(exc, (TimeoutError, socket.timeout)) else 502
            if chat_budget is not None:
                self._reject_unaccounted(status, chat_budget)
            else:
                self._reject(status, b'{"error": {"message": "upstream communication error"}}')
            return
        if chat_budget is None and 300 <= status < 400:
            self._reject(502, b'{"error": {"message": "upstream redirect refused"}}')
            return
        if chat_budget is not None and not self._settle_chat(status, headers, body, is_streaming, chat_budget):
            return
        self._relay(status, headers, body)
