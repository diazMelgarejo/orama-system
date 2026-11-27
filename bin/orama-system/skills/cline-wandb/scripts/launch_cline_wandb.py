#!/usr/bin/env python3
"""Launch Cline 3.0.74 on W&B Inference with the 2026-11-12 defaults, without touching ~/.cline.

Usage:
  launch_cline_wandb.py [--model ID] [--effort LEVEL] [--timeout-ms N]
                        [--implement] [--allow-tool-approval]
                        --max-requests N --max-total-output N -- <task text...>

Defaults (live-verified 2026-11-12, see docs/stale-reference-ledger-2026-11-12.md):
  model   deepseek-ai/DeepSeek-V4.1-Flash-1017
  effort  high   (W&B rejects `medium` on the V4.1 models with HTTP 400; V4-Flash-0731 accepts it)
  timeout 30000 ms (per-request upstream socket timeout)
  review  plan mode (`--plan`) with automatic tool approval off (`--auto-approve false`)
Rule (operator): effort is medium, else high, else low; never xhigh or max. Anything else is refused.
Model fallback order if one is rejected or missing: V4.1-Flash-1017 -> V4.1-Flash -> V4-Flash-0731
(pass --model). The bare deepseek-ai/DeepSeek-V4-Flash id is dead (404) and W&B serves no
`deepseek-flash` alias (404).

Launcher flags (explicit, mutually independent except plan vs implement):
  --implement            omit `--plan` (act/implementation mode). Default is review/plan mode.
  --allow-tool-approval  pass `--auto-approve true`. Default keeps `--auto-approve false`.
                         Never implied by `--implement`.
  --max-requests N       required positive request bound.
  --max-total-output N   required positive cumulative output-token bound.

Both bounds are mandatory. The launcher runs a stdlib loopback accounting proxy
intercepting Cline's OpenAI-compatible requests to enforce exact wire-level request counts
and cumulative usage.completion_tokens (injecting stream_options: {"include_usage": true} on
SSE streams). If either bound is exceeded or usage is missing, the child is terminated fail-closed
with exit code 124.

Passthrough after `--` is positional task text only. Tokens that start with `-`
(including a token that is exactly `-`) are refused before subprocess; reserved
launcher-owned settings cannot be overridden (`--config`, `--thinking`, `--plan`,
`--act`, `--auto-approve`, `--auto-approve-all`, `-P`, `-m`, `--model`, `--provider`,
and equals forms).

How it works: builds a throwaway 0600 config directory (0700) holding only the openai-compatible
entry pointing at the local loopback accounting proxy, runs `cline --config <dir> -P openai-compatible
-m <model> --thinking <effort>` then permission flags then positional task tokens, and deletes
the directory afterwards. The key must already be exported as DEEPSEEK_V4_FLASH_WANDB; this launcher
does not parse the env file. The key is never printed or put in argv; the operator's real Cline
directory is never touched.

Cline 3.0.74 is strict about the entry: tokenSource must be "manual" (or its own "oauth" or
"migration") and updatedAt must look like 2026-11-12T02:48:17.562Z (milliseconds, Z). Anything
else fails every request with the misleading `error: invalid model ID`.
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Sequence

KEYVAR = "DEEPSEEK_V4_FLASH_WANDB"
DEFAULT_ENV_FILE = "~/.openclaw/.env.wandb-deepseek"
BASE_URL = "https://api.inference.wandb.ai/v1"
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4.1-Flash-1017"
EFFORTS = ("medium", "high", "low")  # never xhigh or max
DEFAULT_TIMEOUT_MS = 30000
LOOPBACK_HOST = "127.0" + ".0.1"
# Evidence-backed capability flags, enforced launcher-side via loopback HTTP accounting proxy.
# The launcher supervises child execution and terminates fail-closed if either bound is reached.
BOUND_CONTRACT = {"max_requests": True, "max_total_output": True}
# Launcher-owned flags (short, long, and equals forms). Any option-like rest token is refused.
_RESERVED = frozenset({
    "--config", "--thinking", "--plan", "--act", "--auto-approve", "--auto-approve-all",
    "-P", "-m", "--model", "--provider",
})
_RESERVED_EQUALS = ("--config=", "--thinking=", "--auto-approve=", "-m=", "-P=")


def cline_timestamp() -> str:
    """Return the current time the way Cline writes it: UTC, milliseconds, trailing Z."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def read_key() -> str:
    """Return KEYVAR from the already-exported environment; never read or parse the env file."""
    key = os.environ.get(KEYVAR, "").strip()
    if not key:
        sys.exit(
            f"ERROR: {KEYVAR} is missing or empty. Shell-source the trusted env through the "
            f"approved wrapper ({DEFAULT_ENV_FILE}); this launcher does not parse the file."
        )
    return key


def build_config(
    key: str,
    model: str,
    effort: str,
    timeout_ms: int,
    base_url: str = BASE_URL,
) -> dict:
    """Return a providers.json document holding only the Cline-compatible openai-compatible entry."""
    return {
        "version": 1,
        "lastUsedProvider": "openai-compatible",
        "modes": {},
        "providers": {
            "openai-compatible": {
                "settings": {
                    "provider": "openai-compatible",
                    "apiKey": key,
                    "model": model,
                    "baseUrl": base_url,
                    "headers": {},
                    "timeout": timeout_ms,
                    "reasoning": {"enabled": True, "effort": effort},
                },
                "updatedAt": cline_timestamp(),
                "tokenSource": "manual",
            }
        },
    }


def _refuse_passthrough_token(token: str) -> None:
    """Raise SystemExit for a rest token that could override launcher-owned settings."""
    raise SystemExit(
        "ERROR: passthrough may only include positional task text; launcher-owned "
        f"settings cannot be overridden (refused {token!r})"
    )


def _overrides_launcher_setting(token: str) -> bool:
    """True for reserved flags (short/equals) and any option-like rest token, including '-'."""
    return (
        token in _RESERVED
        or token.startswith(_RESERVED_EQUALS)
        or token == "-"
        or token.startswith("-")
    )


def task_tokens(rest: Sequence[str]) -> list[str]:
    """Return non-option positional task text; refuse reserved flags and any dash token."""
    tokens: list[str] = []
    for token in rest:
        if _overrides_launcher_setting(token):
            _refuse_passthrough_token(token)
        tokens.append(token)
    return tokens


def is_positive_bound(value: object) -> bool:
    """True only for a positive integer; bools, floats, NaN and infinity are not bounds."""
    return type(value) is int and value > 0


def launcher_boundary_problem(max_requests: object, max_total_output: object) -> str | None:
    """Return a refusal until two valid bounds and both client capabilities are verified."""
    if not (is_positive_bound(max_requests) and is_positive_bound(max_total_output)):
        return "invalid-launcher-bounds"
    if not (BOUND_CONTRACT.get("max_requests") is True and BOUND_CONTRACT.get("max_total_output") is True):
        return "launcher-output-bound-unsupported"
    return None


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """Parse launcher options; everything after -- (or the first positional) is task text."""
    parser = argparse.ArgumentParser(description="Run Cline on W&B Inference with the 2026-11-12 defaults.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--effort", default="high", choices=EFFORTS)
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=DEFAULT_TIMEOUT_MS,
        help="per-request upstream socket timeout in milliseconds (default: 30000 ms)",
    )
    parser.add_argument(
        "--implement",
        action="store_true",
        help="implementation/act mode: omit --plan (default is review/plan mode)",
    )
    parser.add_argument(
        "--allow-tool-approval",
        action="store_true",
        help="pass --auto-approve true (default false; independent of --implement)",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        required=True,
        help="required maximum request count; must be a positive integer",
    )
    parser.add_argument(
        "--max-total-output",
        type=int,
        required=True,
        help="required maximum cumulative output tokens; must be a positive integer",
    )
    parser.add_argument("rest", nargs=argparse.REMAINDER, help="after --: positional task text only")
    args = parser.parse_args(list(argv))
    if args.max_requests is not None and args.max_requests <= 0:
        parser.error("--max-requests must be a positive integer")
    if args.max_total_output is not None and args.max_total_output <= 0:
        parser.error("--max-total-output must be a positive integer")
    args.rest = args.rest[1:] if args.rest[:1] == ["--"] else args.rest
    if not args.rest:
        parser.error("give a prompt or cline arguments after --")
    args.rest = task_tokens(args.rest)
    return args


def permission_flags(implement: bool, allow_tool_approval: bool) -> list[str]:
    """Return Cline permission flags: plan unless --implement; auto-approve only if requested."""
    flags: list[str] = []
    if not implement:
        flags.append("--plan")
    flags.extend(["--auto-approve", "true" if allow_tool_approval else "false"])
    return flags


class BoundaryExceededError(RuntimeError):
    """Raised when child process exceeds max_requests or max_total_output."""

    def __init__(self, bound: str, limit: int, actual: object) -> None:
        super().__init__(f"{bound} exceeded: limit={limit}, actual={actual}")
        self.bound = bound
        self.limit = limit
        self.actual = actual


def _terminate_proc(proc: subprocess.Popen) -> None:
    """Terminate child process fail-closed, escalating to kill after a short grace period."""
    try:
        proc.terminate()
    except (OSError, ProcessLookupError):
        return
    try:
        proc.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except (OSError, ProcessLookupError):
            pass
    except (OSError, ValueError):
        pass


def resolve_upstream_url(upstream_base: str, path: str) -> str:
    """Resolve incoming path against upstream base URL, avoiding duplicated /v1 segments."""
    base = upstream_base.rstrip("/")
    if base.endswith("/v1") and path.startswith("/v1/"):
        subpath = path[3:]
    elif not base.endswith("/v1") and not path.startswith("/"):
        subpath = f"/{path}"
    else:
        subpath = path
    return f"{base}{subpath}"


def extract_json_completion_tokens(body: bytes) -> int | None:
    """Extract completion_tokens from non-streaming JSON response."""
    try:
        data = json.loads(body.decode("utf-8"))
        if isinstance(data, dict):
            usage = data.get("usage")
            if isinstance(usage, dict):
                ct = usage.get("completion_tokens")
                if isinstance(ct, int) and not isinstance(ct, bool) and ct >= 0:
                    return ct
    except Exception:
        pass
    return None


def extract_sse_completion_tokens(body: bytes) -> int | None:
    """Extract completion_tokens from SSE payload (from final usage chunk)."""
    try:
        text = body.decode("utf-8", errors="replace")
        last_ct: int | None = None
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                continue
            try:
                chunk = json.loads(payload)
                if isinstance(chunk, dict):
                    usage = chunk.get("usage")
                    if isinstance(usage, dict):
                        ct = usage.get("completion_tokens")
                        if isinstance(ct, int) and not isinstance(ct, bool) and ct >= 0:
                            last_ct = ct
            except Exception:
                continue
        return last_ct
    except Exception:
        return None


class AccountingProxyHandler(http.server.BaseHTTPRequestHandler):
    """HTTP proxy handler enforcing request count and completion token limits."""

    server: AccountingProxyServer
    protocol_version = "HTTP/1.0"

    def log_message(self, format: str, *args: object) -> None:
        # Silence access logs to prevent API keys/prompts leaking to console
        pass

    def _reject(self, status: int, err_bytes: bytes) -> None:
        """Send a compact JSON error response and close the connection."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(err_bytes)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(err_bytes)
        self.wfile.flush()
        self.close_connection = True

    def do_GET(self) -> None:
        self._proxy_request()

    def do_POST(self) -> None:
        self._proxy_request()

    def do_PUT(self) -> None:
        self._proxy_request()

    def do_DELETE(self) -> None:
        self._proxy_request()

    def _proxy_request(self) -> None:
        self.server.begin_request()
        try:
            self._proxy_request_inner()
        finally:
            self.server.end_request()

    def _proxy_request_inner(self) -> None:
        path = self.path
        route = urllib.parse.urlsplit(path).path.rstrip("/")
        is_chat_completions = self.command == "POST" and route.endswith("/chat/completions")

        if self.command == "POST" and not is_chat_completions:
            self._reject(403, b'{"error": {"message": "unsupported POST route refused fail-closed"}}')
            return

        content_len = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_len) if content_len > 0 else b""

        if is_chat_completions:
            # Serialize /chat/completions so concurrent requests cannot race remaining token budget.
            with self.server.chat_gate:
                self._handle_chat_completions(path, body_bytes)
            return

        self._forward_request(path, body_bytes, is_chat_completions=False, is_streaming=False)

    def _handle_chat_completions(self, path: str, body_bytes: bytes) -> None:
        with self.server.lock:
            if self.server.boundary_error:
                self._reject(429, b'{"error": {"message": "bound already exceeded"}}')
                return
            self.server.request_count += 1
            if self.server.request_count > self.server.max_requests:
                self.server.boundary_error.append(
                    BoundaryExceededError(
                        "max_requests",
                        self.server.max_requests,
                        self.server.request_count,
                    )
                )
                self.server.terminate_child()
                self._reject(429, b'{"error": {"message": "max_requests exceeded", "type": "requests_exceeded"}}')
                return
            remaining_tokens = self.server.max_total_output - self.server.cumulative_output_tokens
            if remaining_tokens <= 0:
                self.server.boundary_error.append(
                    BoundaryExceededError(
                        "max_total_output",
                        self.server.max_total_output,
                        self.server.cumulative_output_tokens,
                    )
                )
                self.server.terminate_child()
                self._reject(429, b'{"error": {"message": "max_total_output exhausted", "type": "tokens_exceeded"}}')
                return

        req_json: dict | None = None
        if body_bytes:
            try:
                parsed = json.loads(body_bytes.decode("utf-8"))
                if isinstance(parsed, dict):
                    req_json = parsed
            except Exception:
                req_json = None

        if not isinstance(req_json, dict):
            with self.server.lock:
                self.server.boundary_error.append(
                    BoundaryExceededError("max_total_output", self.server.max_total_output, "invalid-request-json")
                )
            self.server.terminate_child()
            self._reject(400, b'{"error": {"message": "invalid JSON request body; refused fail-closed"}}')
            return

        # Enforce provider-side generation cap against remaining output budget before forwarding.
        existing_max = req_json.get("max_tokens")
        if isinstance(existing_max, int) and not isinstance(existing_max, bool) and existing_max > 0:
            req_json["max_tokens"] = min(existing_max, remaining_tokens)
        else:
            req_json["max_tokens"] = remaining_tokens
        if "max_completion_tokens" in req_json:
            existing_mct = req_json.get("max_completion_tokens")
            if isinstance(existing_mct, int) and not isinstance(existing_mct, bool) and existing_mct > 0:
                req_json["max_completion_tokens"] = min(existing_mct, remaining_tokens)
            else:
                req_json["max_completion_tokens"] = remaining_tokens

        is_streaming = req_json.get("stream") is True
        if is_streaming:
            stream_opts = req_json.get("stream_options")
            if not isinstance(stream_opts, dict):
                req_json["stream_options"] = {"include_usage": True}
            else:
                req_json["stream_options"]["include_usage"] = True
        body_bytes = json.dumps(req_json).encode("utf-8")

        self._forward_request(path, body_bytes, is_chat_completions=True, is_streaming=is_streaming)

    def _forward_request(
        self,
        path: str,
        body_bytes: bytes,
        *,
        is_chat_completions: bool,
        is_streaming: bool,
    ) -> None:
        headers = {}
        for k, v in self.headers.items():
            if k.lower() in ("host", "content-length", "connection"):
                continue
            headers[k] = v
        headers["Connection"] = "close"
        if body_bytes:
            headers["Content-Length"] = str(len(body_bytes))

        upstream_url = resolve_upstream_url(self.server.upstream_base_url, path)
        timeout_s = (self.server.timeout_ms / 1000.0) if self.server.timeout_ms else None
        req = urllib.request.Request(
            upstream_url,
            data=body_bytes if body_bytes else None,
            headers=headers,
            method=self.command,
        )

        try:
            resp = urllib.request.urlopen(req, timeout=timeout_s)
            status_code = resp.status
            resp_headers = resp.headers
            resp_body = resp.read()
            resp.close()
        except urllib.error.HTTPError as exc:
            status_code = exc.code
            resp_headers = exc.headers
            resp_body = exc.read()
            exc.close()
        except Exception as exc:
            status_code = 504 if isinstance(exc, (TimeoutError, socket.timeout)) else 502
            if is_chat_completions:
                # Request may have been billed upstream; fail closed with exit 124 so caller settles unknown.
                with self.server.lock:
                    self.server.boundary_error.append(
                        BoundaryExceededError("upstream_transport", self.server.max_total_output, status_code)
                    )
                self.server.terminate_child()
            self._reject(status_code, b'{"error": {"message": "upstream communication error"}}')
            return

        if is_chat_completions and 200 <= status_code < 300:
            if is_streaming:
                tokens = extract_sse_completion_tokens(resp_body)
            else:
                tokens = extract_json_completion_tokens(resp_body)

            if tokens is None:
                with self.server.lock:
                    self.server.boundary_error.append(
                        BoundaryExceededError("max_total_output", self.server.max_total_output, "missing")
                    )
                self.server.terminate_child()
                self._reject(502, b'{"error": {"message": "missing or invalid usage.completion_tokens"}}')
                return

            with self.server.lock:
                self.server.cumulative_output_tokens += tokens
                if self.server.cumulative_output_tokens > self.server.max_total_output:
                    self.server.boundary_error.append(
                        BoundaryExceededError(
                            "max_total_output",
                            self.server.max_total_output,
                            self.server.cumulative_output_tokens,
                        )
                    )
                    self.server.terminate_child()
                    self._reject(429, b'{"error": {"message": "max_total_output exceeded", "type": "tokens_exceeded"}}')
                    return

        self.send_response(status_code)
        for k, v in resp_headers.items():
            if k.lower() in ("transfer-encoding", "content-length", "connection"):
                continue
            self.send_header(k, v)
        self.send_header("Connection", "close")
        self.send_header("Content-Length", str(len(resp_body)))
        self.end_headers()
        self.wfile.write(resp_body)
        self.wfile.flush()
        self.close_connection = True


class AccountingProxyServer(http.server.ThreadingHTTPServer):
    """Threading HTTP server tracking request counts and output tokens."""

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
    ) -> None:
        super().__init__(server_address, RequestHandlerClass)
        self.lock = threading.RLock()
        self.chat_gate = threading.Lock()
        self._inflight_cond = threading.Condition(self.lock)
        self._inflight_requests = 0
        self.max_requests = max_requests
        self.max_total_output = max_total_output
        self.upstream_base_url = upstream_base_url
        self.timeout_ms = timeout_ms
        self.request_count = 0
        self.cumulative_output_tokens = 0
        self.boundary_error: list[BoundaryExceededError] = []
        self.child_proc: subprocess.Popen | None = None

    def begin_request(self) -> None:
        with self.lock:
            self._inflight_requests += 1

    def end_request(self) -> None:
        with self.lock:
            self._inflight_requests = max(0, self._inflight_requests - 1)
            if self._inflight_requests == 0:
                self._inflight_cond.notify_all()

    def wait_for_inflight(self, timeout_s: float = 5.0) -> bool:
        """Wait up to timeout_s for in-flight handlers to finish accounting. Returns True if drained."""
        with self.lock:
            return self._inflight_cond.wait_for(lambda: self._inflight_requests == 0, timeout=timeout_s)

    def set_child_proc(self, proc: subprocess.Popen) -> None:
        with self.lock:
            self.child_proc = proc
            if self.boundary_error:
                self._terminate_child_locked()

    def terminate_child(self) -> None:
        with self.lock:
            self._terminate_child_locked()

    def _terminate_child_locked(self) -> None:
        if self.child_proc is not None:
            _terminate_proc(self.child_proc)


def main(argv: Sequence[str] | None = None) -> int:
    """Run cline against a throwaway config and return its exit code."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    boundary_problem = launcher_boundary_problem(args.max_requests, args.max_total_output)
    if boundary_problem is not None:
        raise SystemExit(f"ERROR: {boundary_problem}; refusing to start Cline")
    key = read_key()
    config_dir = tempfile.mkdtemp(prefix="clinecfg-")
    os.chmod(config_dir, 0o700)
    proxy = AccountingProxyServer(
        (LOOPBACK_HOST, 0),
        AccountingProxyHandler,
        max_requests=args.max_requests,
        max_total_output=args.max_total_output,
        upstream_base_url=BASE_URL,
        timeout_ms=args.timeout_ms,
    )
    proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True)
    proxy_thread.start()
    proxy_port = proxy.server_address[1]
    proxy_base_url = f"http://{LOOPBACK_HOST}:{proxy_port}/v1"

    try:
        settings_dir = os.path.join(config_dir, "data", "settings")
        os.makedirs(settings_dir)
        fd = os.open(os.path.join(settings_dir, "providers.json"), os.O_WRONLY | os.O_CREAT, 0o600)
        with os.fdopen(fd, "w") as handle:
            json.dump(
                build_config(key, args.model, args.effort, args.timeout_ms, base_url=proxy_base_url),
                handle,
            )
        cline_bin = shutil.which("cline") or "cline"
        cmd = [
            cline_bin, "--config", config_dir, "-P", "openai-compatible", "-m", args.model,
            "--thinking", args.effort, *permission_flags(args.implement, args.allow_tool_approval),
        ]
        if args.max_requests is not None:
            cmd.extend(["--max-requests", str(args.max_requests)])
        if args.max_total_output is not None:
            cmd.extend(["--max-total-output", str(args.max_total_output)])
        cmd.extend(args.rest)

        proc = subprocess.Popen(cmd)
        proxy.set_child_proc(proc)
        rc = proc.wait()
        drained = proxy.wait_for_inflight(timeout_s=5.0)
        if not drained:
            sys.stderr.write("ERROR: proxy accounting did not drain within 5.0s; terminating fail-closed\n")
            return 124
        if proxy.boundary_error:
            exc = proxy.boundary_error[0]
            sys.stderr.write(f"ERROR: {exc}; terminating fail-closed\n")
            return 124
        return rc
    finally:
        try:
            proxy.shutdown()
            proxy.server_close()
        except Exception:
            pass
        shutil.rmtree(config_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
