"""Seat contracts shared by Scout, the inner seat and Biafra (the outer seat).

Pure functions, no I/O beyond hashing named files, no model calls. The Python validators are
the authority; the JSON Schema under docs/v2/references/biafra/ is shape-only.
"""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

TRACE_VERSION = 1
CARD_VERSION = 1
SEATS = ("inner", "outer")
DECISIONS = ("keep", "revert")
CARD_STATUSES = ("candidate", "reviewed", "graduated")
# Owners whose policy neither researcher seat may touch. Matched case-insensitively.
FIXED_WALLS = frozenset({"phylax", "telos", "agate"})
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _finite(value: Any) -> bool:
    """True for a real finite number; bool, str, NaN and inf are not measurements."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def evaluator_digest(paths: Iterable[Path]) -> str:
    """Digest of the verifier files, bound to their names, so an edit changes the pin."""
    h = hashlib.sha256()
    for path in sorted(Path(p) for p in paths):
        h.update(path.name.encode("utf-8") + b"\0")
        h.update(path.read_bytes() + b"\0")
    return h.hexdigest()


def validate_trace_entry(entry: Mapping[str, Any]) -> list[str]:
    """Return error strings; empty means valid. A lower metric is better."""
    errors: list[str] = []
    required = (
        "version", "seat", "attempt_id", "hypothesis", "artifact",
        "metric_name", "metric_before", "metric_after", "decision", "evaluator_digest",
    )
    for key in required:
        if key not in entry:
            errors.append(f"missing {key}")
    if errors:
        return errors
    if entry["version"] != TRACE_VERSION:
        errors.append("version must be 1")
    if entry["seat"] not in SEATS:
        errors.append("seat must be inner or outer")
    for key in ("attempt_id", "hypothesis", "artifact", "metric_name"):
        if not _text(entry[key]):
            errors.append(f"{key} must be non-empty text")
    for key in ("metric_before", "metric_after"):
        if not _finite(entry[key]):
            errors.append(f"{key} must be a finite number")
    if entry["decision"] not in DECISIONS:
        errors.append("decision must be keep or revert")
    if not (isinstance(entry["evaluator_digest"], str) and _HEX64.match(entry["evaluator_digest"])):
        errors.append("evaluator_digest must be 64 lowercase hex")
    if not errors:
        expected = "keep" if entry["metric_after"] < entry["metric_before"] else "revert"
        if entry["decision"] != expected:
            errors.append(f"decision {entry['decision']} disagrees with the metrics (expected {expected})")
    return errors


def stall_report(trace: Sequence[Mapping[str, Any]], window: int = 3) -> dict[str, Any]:
    """A stall is `window` consecutive valid reverts at the end of the trace.

    Invalid entries never count toward a stall; they are counted and reported.
    """
    valid = [e for e in trace if not validate_trace_entry(e)]
    invalid = len(trace) - len(valid)
    tail = valid[-window:] if window > 0 else []
    stalled = len(tail) == window > 0 and all(e["decision"] == "revert" for e in tail)
    return {
        "stalled": stalled,
        "window": window,
        "entry_ids": [e["attempt_id"] for e in tail] if stalled else [],
        "invalid": invalid,
    }


def validate_mechanism_card(card: Mapping[str, Any]) -> list[str]:
    """Return error strings; empty means valid. Never mutates `card`."""
    errors: list[str] = []
    required = (
        "version", "mechanism_id", "revision", "parent", "hypothesis", "evidence_ids",
        "inner_metric", "held_out_metric", "evaluator_digest", "dry_run_receipt",
        "delta", "reverted", "scope_record", "owner_slices", "status",
    )
    for key in required:
        if key not in card:
            errors.append(f"missing {key}")
    if errors:
        return errors
    if card["version"] != CARD_VERSION:
        errors.append("version must be 1")
    if not _text(card["mechanism_id"]):
        errors.append("mechanism_id must be non-empty text")
    revision = card["revision"]
    if not (isinstance(revision, int) and not isinstance(revision, bool) and revision >= 1):
        errors.append("revision must be an integer >= 1")
    if card["parent"] is not None and not _text(card["parent"]):
        errors.append("parent must be null or non-empty text")
    for key in ("hypothesis", "inner_metric", "held_out_metric"):
        if not _text(card[key]):
            errors.append(f"{key} must be non-empty text")
    ids = card["evidence_ids"]
    if not (isinstance(ids, list) and ids and all(_text(i) for i in ids)):
        errors.append("evidence_ids must be a non-empty list of ledger entry ids")
    if not (isinstance(card["evaluator_digest"], str) and _HEX64.match(card["evaluator_digest"])):
        errors.append("evaluator_digest must be 64 lowercase hex")
    if not _finite(card["delta"]):
        errors.append("delta must be a finite number")
    if not isinstance(card["reverted"], bool):
        errors.append("reverted must be a boolean")
    scope = card["scope_record"]
    if not (isinstance(scope, Mapping) and scope.get("authorizes") == "nothing"):
        errors.append("scope_record.authorizes must be 'nothing'")
    owners = card["owner_slices"]
    if not (isinstance(owners, list) and owners and all(_text(o) for o in owners)):
        errors.append("owner_slices must be a non-empty list")
    else:
        walls = sorted({o.strip().lower() for o in owners} & FIXED_WALLS)
        if walls:
            errors.append(f"E_OWNER: a mechanism may not touch fixed-wall owner(s): {', '.join(walls)}")
    if card["status"] not in CARD_STATUSES:
        errors.append("status must be candidate, reviewed or graduated")
    elif card["status"] == "graduated":
        receipt = card["dry_run_receipt"]
        if not (
            isinstance(receipt, Mapping)
            and receipt.get("ok") is True
            and receipt.get("retries") == 0
            and receipt.get("launched") is False
        ):
            errors.append("dry_run_receipt must show ok, no retries and no launch before graduation")
    elif not isinstance(card["dry_run_receipt"], Mapping):
        errors.append("dry_run_receipt must be an object")
    return errors
