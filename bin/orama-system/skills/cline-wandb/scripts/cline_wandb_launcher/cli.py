"""Command-line parsing and validation: launcher flags in, positional task text only."""
from __future__ import annotations

import argparse
from typing import Sequence

from .defaults import DEFAULT_MODEL, DEFAULT_TIMEOUT_MS, EFFORTS

# Launcher-owned flags (short, long, and equals forms). Any option-like rest token is refused.
_RESERVED = frozenset({
    "--config", "--thinking", "--plan", "--act", "--auto-approve", "--auto-approve-all",
    "-P", "-m", "--model", "--provider",
})
_RESERVED_EQUALS = ("--config=", "--thinking=", "--auto-approve=", "-m=", "-P=")


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
