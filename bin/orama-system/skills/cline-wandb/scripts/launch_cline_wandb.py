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

Both bounds are mandatory. The launcher runs a stdlib loopback accounting proxy between Cline and
the provider. Cline authenticates to the proxy with a random per-launch session token; the provider
key stays in launcher memory and is never written to disk. Contract, one rule per line:
  - Only `POST` requests whose URL path (query string ignored) ends in `/chat/completions` are
    forwarded and counted; every other `POST` is refused with HTTP 403.
  - Before forwarding, `max_tokens` (and `max_completion_tokens` when present) is clamped to the
    remaining output budget, and `stream_options.include_usage` is forced on for streaming calls.
  - Every forwarded chat request ends in exactly one outcome: ACCOUNTED (a 2xx response with
    verified `usage.completion_tokens`) or UNACCOUNTED. UNACCOUNTED covers a 2xx response without
    valid usage, every non-2xx status (the launcher cannot prove a provider or gateway status means
    no billable work), and any transport or read failure. It is debited in full against the output
    budget.
  - Cline's process group is terminated and the launcher exits 124 when `request_count` exceeds
    `max_requests`, when the next chat request finds no output budget left, when cumulative output exceeds
    `max_total_output`, when a dispatch is UNACCOUNTED, or when admitted handlers do not drain in time.
  - Exit 124 means spend is breached or not fully accounted: callers settle it as unknown spend.
  - Transport errors on non-chat routes return HTTP 502/504 and do not change the exit code.
  - Every upstream dispatch, chat or not, first claims a dispatch slot under the server lock. Once
    the drain deadline sets CLOSED, no claim succeeds, so no dispatch can start after CLOSED.

Child process (POSIX): Cline starts with stdin closed, in its own session and process group. The
bounds are not passed to it. A fail-closed stop ends the group and the processes below it, including
tool commands that Cline runs in sessions of their own. INT, TERM and HUP sent to the launcher are
relayed to the group (a second one kills the group and those processes) and the launcher then exits
128 plus the signal number. Not covered: Cline's shared hub daemon, which is left running; a process
already reparented away from Cline when the stop begins; and the launcher itself being SIGKILLed.
On Windows only the direct child is signalled.

Passthrough after `--` is positional task text only. Tokens that start with `-`
(including a token that is exactly `-`) are refused before subprocess; reserved
launcher-owned settings cannot be overridden (`--config`, `--thinking`, `--plan`,
`--act`, `--auto-approve`, `--auto-approve-all`, `-P`, `-m`, `--model`, `--provider`,
and equals forms).

How it works: builds a throwaway 0600 config directory (0700) holding only the openai-compatible
entry pointing at the local loopback accounting proxy, runs `cline --config <dir> -P openai-compatible
-m <model> --thinking <effort>` then permission flags then positional task tokens, and deletes
the directory afterwards. The key must already be exported as DEEPSEEK_V4_FLASH_WANDB; this launcher
does not parse the env file. The key is never printed, put in argv or written to disk; the operator's
real Cline directory is never touched.

Cline 3.0.74 is strict about the entry: tokenSource must be "manual" (or its own "oauth" or
"migration") and updatedAt must look like 2026-11-12T02:48:17.562Z (milliseconds, Z). Anything
else fails every request with the misleading `error: invalid model ID`.
"""
from __future__ import annotations

import argparse
import hmac
import http.server
import json
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Sequence

KEYVAR = "DEEPSEEK_V4_FLASH_WANDB"
DEFAULT_ENV_FILE = "~/.openclaw/.env.wandb-deepseek"
BASE_URL = "https://api.inference.wandb.ai/v1"
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4.1-Flash-1017"
EFFORTS = ("medium", "high", "low")  # never xhigh or max
DEFAULT_TIMEOUT_MS = 30000
LOOPBACK_HOST = "127.0" + ".0.1"
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
TERMINATE_GRACE_S = 2.0
# No non-2xx status is trusted to mean "nothing billed": neither the provider nor a gateway in
# front of it documents that guarantee, so every non-2xx chat response is UNACCOUNTED.
ACCOUNTED, UNACCOUNTED = "accounted", "unaccounted"
PHASE_RUNNING, PHASE_DRAINING, PHASE_CLOSED = "running", "draining", "closed"
# Evidence-backed capability flags, enforced launcher-side via loopback HTTP accounting proxy.
# The launcher terminates fail-closed once a bound is exceeded or a dispatch cannot be accounted for.
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
    """Return a providers.json document with only the openai-compatible entry.

    `key` is the credential Cline presents. The launcher passes its per-launch session token, never the
    provider key, which stays in launcher memory.
    """
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
    """A spend bound was exceeded, or a dispatch could not be accounted for (limit is None)."""

    def __init__(self, bound: str, limit: int | None, actual: object) -> None:
        detail = f"exceeded: limit={limit}, actual={actual}" if limit is not None else f"actual={actual}"
        super().__init__(f"{bound} {detail}")
        self.bound = bound
        self.limit = limit
        self.actual = actual


def _signal_group(group: int, signum: int) -> bool:
    """Send `signum` to a process group; False once no member is left to receive it."""
    try:
        os.killpg(group, signum)
    except OSError:
        return False
    return True


def _descendants(root: int) -> set[int]:
    """Processes below `root` right now, except Cline's shared hub daemon and what it started.

    Cline runs each tool command in a new session, outside the child's group, and once the parent dies the
    command can no longer be traced to it. So take this list before signalling. Empty if `ps` fails.
    """
    try:
        listing = subprocess.run(["ps", "-Ao", "pid=,ppid=,command="], capture_output=True, text=True,
                                 errors="replace", timeout=5, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return set()
    children: dict[int, list[int]] = {}
    for line in listing.splitlines():
        fields = line.split(None, 2)
        if len(fields) >= 2 and "--cline-hub-daemon" not in (fields[2] if len(fields) > 2 else ""):
            children.setdefault(int(fields[1]), []).append(int(fields[0]))
    found: set[int] = set()
    queue = [root]
    while queue:
        for pid in children.get(queue.pop(), []):
            if pid not in found:
                found.add(pid)
                queue.append(pid)
    return found


def _signal_pid(pid: int, signum: int) -> bool:
    """Send `signum` to one process; False once it is gone."""
    try:
        os.kill(pid, signum)
    except OSError:
        return False
    return True


def _terminate_group(proc: subprocess.Popen, group: int, tools: set[int] | None = None) -> None:
    """Terminate the child's group and the tool processes below it, escalating to SIGKILL.

    `cline` is a wrapper that starts the real program as its own child, so signalling only `proc`
    would leave the program that does the work running. `tools` adds processes already seen below it.
    """
    below = _descendants(group) | (tools or set())
    signalled = _signal_group(group, signal.SIGTERM)
    if not signalled and not below:
        return
    deadline = time.monotonic() + TERMINATE_GRACE_S
    while time.monotonic() < deadline:
        proc.poll()  # reap the leader, otherwise its zombie keeps the group alive
        if not _signal_group(group, 0) and not any(_signal_pid(pid, 0) for pid in below):
            return
        time.sleep(0.05)
    _signal_group(group, signal.SIGKILL)
    for pid in below:
        _signal_pid(pid, signal.SIGKILL)
    proc.poll()


def _terminate_proc(proc: subprocess.Popen, group: int | None = None) -> None:
    """Terminate child process fail-closed, escalating to kill after a short grace period.

    With `group` (the child leads its own process group) the whole group is terminated.
    """
    if group is not None:
        _terminate_group(proc, group)
        return
    try:
        proc.terminate()
    except (OSError, ProcessLookupError):
        return
    try:
        proc.wait(timeout=TERMINATE_GRACE_S)
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


def _valid_completion_tokens(usage: object) -> int | None:
    if isinstance(usage, dict):
        ct = usage.get("completion_tokens")
        if isinstance(ct, int) and not isinstance(ct, bool) and ct >= 0:
            return ct
    return None


def extract_sse_completion_tokens(body: bytes) -> int | None:
    """Extract completion_tokens from the SSE usage reports; None (unaccounted) when any is malformed.

    Events whose `usage` is absent or null are skipped (intermediate chunks). A `usage` value that is
    present but malformed is never treated as absent, so it can not fall back to an earlier report.
    """
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
            except ValueError:
                if "usage" in payload:
                    return None
                continue
            if not isinstance(chunk, dict) or chunk.get("usage") is None:
                continue
            ct = _valid_completion_tokens(chunk["usage"])
            if ct is None:
                return None
            last_ct = ct
        return last_ct
    except Exception:
        return None


def classify_chat_outcome(status: int, tokens: int | None) -> str:
    """Return the single outcome of one forwarded chat request."""
    return ACCOUNTED if 200 <= status < 300 and tokens is not None else UNACCOUNTED


def clamp_output_caps(req_json: dict, remaining_tokens: int) -> dict:
    """Clamp max_tokens (always) and max_completion_tokens (when present) to the remaining budget."""
    for field in ("max_tokens", "max_completion_tokens"):
        if field == "max_tokens" or field in req_json:
            val = req_json.get(field)
            req_json[field] = min(val, remaining_tokens) if (type(val) is int and val > 0) else remaining_tokens
    return req_json


class OversizeResponseError(RuntimeError):
    """The upstream response exceeded MAX_RESPONSE_BYTES."""


class TruncatedResponseError(RuntimeError):
    """The upstream response ended before its declared Content-Length."""


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect: the provider key must not travel to another origin."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


_UPSTREAM_OPENER = urllib.request.build_opener(_NoRedirectHandler)

HOP_BY_HOP = frozenset({
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "proxy-connection", "te", "trailer", "transfer-encoding", "upgrade",
})


def hop_by_hop_names(headers: Any, *extra: str) -> frozenset[str]:
    """Lower-cased names to drop: fixed hop-by-hop fields, every field nominated by any Connection
    value, and any `extra` names the caller replaces itself."""
    names = set(HOP_BY_HOP) | {name.lower() for name in extra}
    for value in headers.get_all("Connection") or []:
        names.update(token.strip().lower() for token in str(value).split(",") if token.strip())
    return frozenset(names)


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
        drop = hop_by_hop_names(self.headers, "host", "content-length", "authorization")
        headers = {k: v for k, v in self.headers.items() if k.lower() not in drop}
        headers["Connection"] = "close"
        if self.server.upstream_key:
            headers["Authorization"] = f"Bearer {self.server.upstream_key}"
        if body_bytes:
            headers["Content-Length"] = str(len(body_bytes))
        return urllib.request.Request(
            resolve_upstream_url(self.server.upstream_base_url, self.path),
            data=body_bytes or None, headers=headers, method=self.command,
        )

    @staticmethod
    def _read_bounded(stream: Any) -> bytes:
        data = stream.read(MAX_RESPONSE_BYTES + 1)
        if len(data) > MAX_RESPONSE_BYTES:
            raise OversizeResponseError(f"upstream response exceeds {MAX_RESPONSE_BYTES} bytes")
        declared = stream.headers.get("Content-Length")
        if declared is not None and declared.strip().isdigit() and len(data) < int(declared.strip()):
            raise TruncatedResponseError(f"upstream response ended at {len(data)} of {declared.strip()} bytes")
        return data

    def _fetch_upstream(self, req: urllib.request.Request) -> tuple[int, Any, bytes]:
        """One upstream round trip; a failure while reading ANY body (2xx or HTTPError) raises."""
        timeout_s = (self.server.timeout_ms / 1000.0) if self.server.timeout_ms else None
        try:
            with _UPSTREAM_OPENER.open(req, timeout=timeout_s) as resp:
                return resp.status, resp.headers, self._read_bounded(resp)
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, exc.headers, self._read_bounded(exc)
            finally:
                exc.close()

    def _settle_chat(self, status: int, body: bytes, is_streaming: bool, budget: int) -> bool:
        """Apply the two-outcome rule to a chat response. False when the request was rejected here."""
        tokens = None
        if 200 <= status < 300:
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
            status, headers, body = self._fetch_upstream(self._build_upstream_request(body_bytes))
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
        if chat_budget is not None and not self._settle_chat(status, body, is_streaming, chat_budget):
            return
        self._relay(status, headers, body)


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
            _terminate_proc(self.child_proc, self.child_group)


def _forward_signals(group: int, received: list[int], tools: set[int]) -> dict:
    """Relay the launcher's INT, TERM and HUP to the child's group; return the replaced handlers.

    The child runs in its own session, so a terminal Ctrl-C or a supervisor's TERM reaches only the
    launcher. A second signal means the child did not stop, so the group is killed.
    """

    def relay(signum: int, frame: object) -> None:
        tools.update(_descendants(group))  # while their parent is still alive
        if received:
            _signal_group(group, signal.SIGKILL)
            for pid in tools:
                _signal_pid(pid, signal.SIGKILL)
        else:
            _signal_group(group, signum)
        received.append(signum)

    previous: dict = {}
    if threading.current_thread() is threading.main_thread():
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            previous[signum] = signal.signal(signum, relay)
    return previous


def main(argv: Sequence[str] | None = None) -> int:
    """Run cline against a throwaway config and return its exit code."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    boundary_problem = launcher_boundary_problem(args.max_requests, args.max_total_output)
    if boundary_problem is not None:
        raise SystemExit(f"ERROR: {boundary_problem}; refusing to start Cline")
    provider_key = read_key()
    session_token = secrets.token_urlsafe(32)
    config_dir = tempfile.mkdtemp(prefix="clinecfg-")
    os.chmod(config_dir, 0o700)
    proxy = AccountingProxyServer(
        (LOOPBACK_HOST, 0),
        AccountingProxyHandler,
        max_requests=args.max_requests,
        max_total_output=args.max_total_output,
        upstream_base_url=BASE_URL,
        timeout_ms=args.timeout_ms,
        session_token=session_token,
        upstream_key=provider_key,
    )
    proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True)
    proxy_thread.start()
    proxy_port = proxy.server_address[1]
    proxy_base_url = f"http://{LOOPBACK_HOST}:{proxy_port}/v1"

    proc: subprocess.Popen | None = None
    received: list[int] = []
    seen_tools: set[int] = set()
    previous_handlers: dict = {}
    try:
        settings_dir = os.path.join(config_dir, "data", "settings")
        os.makedirs(settings_dir)
        fd = os.open(os.path.join(settings_dir, "providers.json"), os.O_WRONLY | os.O_CREAT, 0o600)
        with os.fdopen(fd, "w") as handle:
            json.dump(
                build_config(session_token, args.model, args.effort, args.timeout_ms, base_url=proxy_base_url),
                handle,
            )
        cline_bin = shutil.which("cline") or "cline"
        cmd = [
            cline_bin, "--config", config_dir, "-P", "openai-compatible", "-m", args.model,
            "--thinking", args.effort, *permission_flags(args.implement, args.allow_tool_approval),
        ]
        cmd.extend(args.rest)  # the bounds stay here: Cline has no such options, the proxy enforces them

        child_env = {k: v for k, v in os.environ.items() if k != KEYVAR}
        own_group = hasattr(os, "killpg")  # POSIX; elsewhere only the direct child can be signalled
        proc = subprocess.Popen(cmd, env=child_env, stdin=subprocess.DEVNULL, start_new_session=own_group)
        group = proc.pid if own_group else None
        if group is not None:
            previous_handlers = _forward_signals(group, received, seen_tools)
        proxy.set_child_proc(proc, group)
        rc = proc.wait()
        drained = proxy.stop_and_drain(timeout_s=5.0)
        if not drained:
            sys.stderr.write("ERROR: proxy accounting did not drain within 5.0s; exiting 124 (spend not fully accounted)\n")
            proxy.terminate_child()
            return 124
        if proxy.boundary_error:
            exc = proxy.boundary_error[0]
            sys.stderr.write(f"ERROR: {exc}; terminating fail-closed\n")
            # The handler thread that started the termination dies with this process, so finish it here.
            proxy.terminate_child()
            return 124
        if received:
            if group is not None:
                _terminate_group(proc, group, seen_tools)
            return 128 + received[0]
        return rc
    finally:
        if proc is not None and proc.poll() is None:
            proxy.terminate_child()  # an unexpected error must not leave Cline running
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
        try:
            proxy.shutdown()
            proxy.server_close()
        except Exception:
            pass
        shutil.rmtree(config_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
