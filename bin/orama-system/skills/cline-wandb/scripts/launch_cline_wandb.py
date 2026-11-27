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
  - Every upstream request carries `Accept-Encoding: identity` in place of the client's value, because
    the proxy does not decode replies.
  - Every forwarded chat request ends in exactly one outcome: ACCOUNTED (a 2xx response with
    verified `usage.completion_tokens`) or UNACCOUNTED. UNACCOUNTED covers a 2xx response without
    valid usage, a 2xx response encoded despite that request (never parsed), every non-2xx status
    (the launcher cannot prove a provider or gateway status means no billable work), and any
    transport or read failure. It is debited in full against the output budget.
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

This file holds the bound contract and the run sequence. The rest is in the sibling package
`cline_wandb_launcher/`, one responsibility per module; copy or link the two together.
"""
from __future__ import annotations

import importlib.util
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from typing import Sequence

_PARTS = "cline_wandb_launcher"


def _bind_parts() -> None:
    """Bind the package beside this file's real path, whatever loaded the file or what sys.path holds.

    Callers load this file by path and the skill directory may be a symlink, so sys.path is neither
    read nor changed. A same-named module from any other place is replaced, never imported from.
    """
    root = os.path.join(os.path.dirname(os.path.realpath(__file__)), _PARTS)
    loaded = sys.modules.get(_PARTS)
    if loaded is not None:
        if list(getattr(loaded, "__path__", [])) == [root]:
            return
        for name in [n for n in sys.modules if n == _PARTS or n.startswith(f"{_PARTS}.")]:
            sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(
        _PARTS, os.path.join(root, "__init__.py"), submodule_search_locations=[root])
    module = importlib.util.module_from_spec(spec)
    if sys.modules.setdefault(_PARTS, module) is module:
        spec.loader.exec_module(module)


_bind_parts()

# Names that callers and tests read from this file stay importable from it.
from cline_wandb_launcher import process_tree, signal_relay  # noqa: E402
from cline_wandb_launcher.accounting import BoundaryExceededError, extract_sse_completion_tokens  # noqa: E402,F401
from cline_wandb_launcher.cli import parse_args  # noqa: E402
from cline_wandb_launcher.cline_config import build_config, cline_timestamp  # noqa: E402,F401
from cline_wandb_launcher.cline_process import permission_flags  # noqa: E402
from cline_wandb_launcher.credentials import read_key  # noqa: E402
from cline_wandb_launcher.defaults import (BASE_URL, DEFAULT_ENV_FILE, DEFAULT_MODEL, EFFORTS,  # noqa: E402,F401
                                           KEYVAR, LOOPBACK_HOST)
from cline_wandb_launcher.proxy_handler import AccountingProxyHandler  # noqa: E402
from cline_wandb_launcher.proxy_server import PHASE_CLOSED, AccountingProxyServer  # noqa: E402,F401
from cline_wandb_launcher.upstream import hop_by_hop_names  # noqa: E402,F401

# Evidence-backed capability flags, enforced launcher-side via loopback HTTP accounting proxy.
# The launcher terminates fail-closed once a bound is exceeded or a dispatch cannot be accounted for.
BOUND_CONTRACT = {"max_requests": True, "max_total_output": True}


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
            previous_handlers = signal_relay.forward_signals(group, received, seen_tools)
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
                process_tree.terminate_group(proc, group, seen_tools)
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
