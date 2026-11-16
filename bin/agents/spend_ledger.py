"""A monthly spend ESTIMATE and guard for live provider requests. Not billing.

The provider's Billing page is the only truth. This module keeps a local, append-only estimate so a
loop can stop before it passes an operator budget. Sizes are characters (four per token); the rates
are the highest non-Pro DeepSeek per-million-token rates listed on the provider's pricing page on
2026-11-17, so the estimate leans high. Prompts and answers are never stored, only their sizes.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CHARS_PER_TOKEN = 4
INPUT_USD_PER_M = 0.50
OUTPUT_USD_PER_M = 1.50
# Projection before a request: 40k output tokens, which covers the reasoning stream that is billed.
ASSUMED_OUTPUT_CHARS = 160_000


def _size(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite number >= 0")
    return float(value)


def estimate_usd(input_chars: Any, output_chars: Any) -> float:
    """Estimated dollars for one request from its input and output sizes in characters."""
    tin = _size(input_chars, "input_chars") / CHARS_PER_TOKEN
    tout = _size(output_chars, "output_chars") / CHARS_PER_TOKEN
    return tin / 1e6 * INPUT_USD_PER_M + tout / 1e6 * OUTPUT_USD_PER_M


def _utc(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def append(path: Path, row: dict) -> None:
    """Append one validated row. The row needs an ISO `ts` and a finite `estimated_usd` >= 0."""
    _utc(row["ts"])
    _size(row["estimated_usd"], "estimated_usd")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def month_total(path: Path, now: datetime) -> float:
    """Sum of `estimated_usd` for rows in `now`'s UTC month. A bad row is an error, never skipped."""
    path = Path(path)
    if not path.exists():
        return 0.0
    month = (now.astimezone(timezone.utc).year, now.astimezone(timezone.utc).month)
    total = 0.0
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            when = _utc(row["ts"])
            usd = _size(row["estimated_usd"], "estimated_usd")
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError(f"invalid spend ledger row {number}: {exc}") from exc
        if (when.year, when.month) == month:
            total += usd
    return total


def check_budget(path: Path, budget_usd: Any, projected_usd: Any, now: datetime) -> dict:
    """ok False with reason budget-exhausted when this month's estimate plus the projection passes the budget."""
    if isinstance(budget_usd, bool) or not isinstance(budget_usd, (int, float)) or not math.isfinite(budget_usd) or budget_usd <= 0:
        raise ValueError("budget_usd must be a finite number > 0")
    projected = _size(projected_usd, "projected_usd")
    total = month_total(path, now)
    verdict = {
        "ok": total + projected <= budget_usd, "month_total_usd": total,
        "projected_usd": projected, "budget_usd": float(budget_usd),
    }
    if not verdict["ok"]:
        verdict["reason"] = "budget-exhausted"
    return verdict
