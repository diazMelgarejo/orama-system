"""The accounting proxy server: counters, the drain lifecycle, the child it may stop, start and close."""
from __future__ import annotations

import http.server
import socket
import subprocess
import threading

from . import process_tree
from .accounting import BoundaryExceededError
from .defaults import BASE_URL, DEFAULT_TIMEOUT_MS, LOOPBACK_HOST

PHASE_RUNNING, PHASE_DRAINING, PHASE_CLOSED = "running", "draining", "closed"


class AccountingProxyServer(http.server.ThreadingHTTPServer):
    """Threading HTTP server tracking request counts and output tokens.

    Lifecycle: RUNNING -> DRAINING (no new connections; admitted work may finish) -> CLOSED (set only
    when the drain deadline passes; no admitted worker may start a new upstream dispatch).
    """

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: type[http.server.BaseHTTPRequestHandler],
        max_requests: int,
        max_total_output: int,
        upstream_base_url: str = BASE_URL,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        *,
        session_token: str,
        upstream_key: str | None = None,
    ) -> None:
        super().__init__(server_address, RequestHandlerClass)
        self.lock = threading.RLock()
        self.chat_gate = threading.Lock()
        self._inflight_cond = threading.Condition(self.lock)
        self._inflight_requests = 0
        self._phase = PHASE_RUNNING
        self.dispatches_claimed = 0
        self.dispatches_claimed_at_close: int | None = None
        self.session_token = session_token
        self.upstream_key = upstream_key
        self.max_requests = max_requests
        self.max_total_output = max_total_output
        self.upstream_base_url = upstream_base_url
        self.timeout_ms = timeout_ms
        self.request_count = 0
        self.cumulative_output_tokens = 0
        self.boundary_error: list[BoundaryExceededError] = []
        self.child_proc: subprocess.Popen | None = None
        self.child_group: int | None = None

    @property
    def phase(self) -> str:
        with self.lock:
            return self._phase

    def is_accepting(self) -> bool:
        return self.phase == PHASE_RUNNING

    def process_request(self, request: socket.socket, client_address: tuple[str, int]) -> None:
        """Admit and count a connection synchronously BEFORE spawning its worker thread."""
        with self.lock:
            if self._phase != PHASE_RUNNING:
                self.shutdown_request(request)
                return
            self._inflight_requests += 1
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._decrement_inflight()
            raise

    def process_request_thread(self, request: socket.socket, client_address: tuple[str, int]) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._decrement_inflight()

    def claim_dispatch(self) -> bool:
        """Atomically refuse once CLOSED, or claim one upstream dispatch slot.

        The phase check and the claim share the lock that stop_and_drain holds when it sets CLOSED,
        so every dispatch is ordered strictly before or after the close: a claim made before it may
        proceed (its I/O never blocks the drain deadline), and no claim can succeed after it.
        """
        with self.lock:
            if self._phase == PHASE_CLOSED:
                return False
            self.dispatches_claimed += 1
            return True

    def _decrement_inflight(self) -> None:
        with self.lock:
            self._inflight_requests = max(0, self._inflight_requests - 1)
            if self._inflight_requests == 0:
                self._inflight_cond.notify_all()

    def stop_and_drain(self, timeout_s: float = 5.0) -> bool:
        """Stop accepting, shut down the accept loop, and drain admitted handlers.

        On timeout the phase becomes CLOSED under the lock, so a worker still queued behind
        chat_gate is refused instead of starting a new upstream dispatch.
        """
        with self.lock:
            self._phase = PHASE_DRAINING
        self.shutdown()
        with self.lock:
            drained = self._inflight_cond.wait_for(lambda: self._inflight_requests == 0, timeout=timeout_s)
            if not drained:
                self._phase = PHASE_CLOSED
                self.dispatches_claimed_at_close = self.dispatches_claimed
            return drained

    def set_child_proc(self, proc: subprocess.Popen, process_group: int | None = None) -> None:
        with self.lock:
            self.child_proc = proc
            self.child_group = process_group
            if self.boundary_error:
                self._terminate_child_locked()

    def terminate_child(self) -> None:
        with self.lock:
            self._terminate_child_locked()

    def _terminate_child_locked(self) -> None:
        if self.child_proc is not None:
            process_tree.terminate_proc(self.child_proc, self.child_group)


def serve_in_background(proxy: AccountingProxyServer) -> str:
    """Run the accept loop on a daemon thread; return the base URL the local client must use."""
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    return f"http://{LOOPBACK_HOST}:{proxy.server_address[1]}/v1"


def close_proxy(proxy: AccountingProxyServer) -> None:
    """Stop serving and close the socket. An ordinary error is ignored so that later cleanup still runs."""
    try:
        proxy.shutdown()
        proxy.server_close()
    except Exception:
        pass
