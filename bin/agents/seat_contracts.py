"""Seat contracts shared by Scout, the inner seat and Biafra (the outer seat).

Pure functions, no I/O beyond hashing named files, no model calls. The Python validators are
the authority; the JSON Schema under docs/v2/references/biafra/ is shape-only.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import unicodedata
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

TRACE_VERSION = 1
STALL_WINDOW = 3
# "metric" is the existing cycle and seat-wrapper default, retained for compatibility.
DECLARED_METRIC_NAMES = frozenset({
    "metric", "val_bpb", "val_bpb_heldout", "held_out_class_bc_comment_cases",
    "card_validity_and_grounding_failures", "failed_observed_defect_cases",
    "failed_prelaunch_cases", "failed_reviewer_cases", "failed_verified_defect_cases",
    "review_format_violations",
})
CARD_VERSION = 1
SEATS = ("inner", "inner-scout", "outer")
DECISIONS = ("keep", "revert")
CARD_STATUSES = ("candidate", "reviewed", "graduated")
CARD_FIELDS = (
    "version", "mechanism_id", "revision", "parent", "hypothesis", "evidence_ids",
    "inner_metric", "held_out_metric", "evaluator_digest", "dry_run_receipt",
    "delta", "reverted", "scope_record", "owner_slices", "status",
)
# Owners whose policy neither researcher seat may touch. Matched case-insensitively.
FIXED_WALLS = frozenset({"phylax", "telos", "agate"})
_OWNER_SHAPE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,63}")  # used with fullmatch
_HEX64 = re.compile(r"[0-9a-f]{64}")  # used with fullmatch: `$` would accept a trailing newline

# Model and effort policy (operator clarification 2026-11-17).
# The ladder is the default: it runs on free W&B turns with no human approval, and it is the
# fallback whenever no paid permission has been granted. xhigh and max are never selected.
EFFORT_LADDER = ("medium", "high", "low")
# W&B Inference defaults, live-verified 2026-11-12 (see docs/v2/76 section 8 for sources).
# Model order, first available wins; the V4.1 models reject medium with HTTP 400, so the ladder
# lands on high for them. V4-Flash-0731 accepts medium. Mirrors launch_cline_wandb.py (tested).
WANDB_MODEL_ORDER = (
    "deepseek-ai/DeepSeek-V4.1-Flash-1017",
    "deepseek-ai/DeepSeek-V4.1-Flash",
    "deepseek-ai/DeepSeek-V4-Flash-0731",
)
WANDB_EFFORTS: dict[str, tuple[str, ...]] = {
    "deepseek-ai/DeepSeek-V4.1-Flash-1017": ("high", "low"),
    "deepseek-ai/DeepSeek-V4.1-Flash": ("high", "low"),
    "deepseek-ai/DeepSeek-V4-Flash-0731": ("medium", "high", "low"),
}
# Preferred paid occupants are human-gated: they run only after explicit approval.
PREFERRED_PAID: dict[tuple[str, str], tuple[str, str]] = {
    ("outer", "anthropic"): ("Claude Fable 5.2", "high"),
    ("inner", "anthropic"): ("Claude Opus 5.5", "medium"),
    ("outer", "openai"): ("GPT-6 Astra", "high"),
    ("inner", "openai"): ("GPT-6.1 Sol", "medium"),
}


def _finite(value: Any) -> bool:
    """Accept finite floats and integers within the exact IEEE double integer range."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, int):
        return abs(value) <= 2**53
    return math.isfinite(value)


def is_declared_metric_name(value: Any) -> bool:
    """Return whether value names a metric in the closed contract registry."""
    return isinstance(value, str) and value in DECLARED_METRIC_NAMES


def _owner_folded(owner: str) -> str | None:
    """Fold an owner name for the fixed-wall check; None means it is not plain ASCII afterwards.

    NFKC folds compatibility look-alikes (fullwidth letters), format characters (zero-width
    spaces) are removed, NFKD then strips combining marks (accents), and the result is
    casefolded with every non-alphanumeric removed. Any character still outside ASCII
    (for example a Cyrillic look-alike) fails closed instead of being tokenized around.
    """
    folded = unicodedata.normalize("NFKC", owner)
    folded = "".join(c for c in folded if unicodedata.category(c) != "Cf")
    folded = unicodedata.normalize("NFKD", folded)
    folded = "".join(c for c in folded if unicodedata.category(c) != "Mn").casefold()
    folded = re.sub(r"[\W_]+", "", folded)
    return folded if folded.isascii() else None


def _owner_errors(owners: Any) -> list[str]:
    """Errors for a card's owner_slices; empty means acceptable. Pure; never raises.

    The fixed-wall check runs first, so a disguised wall name reports E_OWNER even when it also
    fails the identifier shape. Every remaining entry must be a repository identifier: letters,
    digits and . _ - / only, starting with a letter or digit, at most 64 characters, with no empty,
    dot, or dot-prefixed path segment and no trailing dot or slash.
    """
    if not isinstance(owners, list) or not owners:
        return ["owner_slices must be a non-empty list"]
    if any(not _text(o) for o in owners):
        return ["owner_slices entries must be non-empty text"]
    folded = [_owner_folded(o) for o in owners]
    walls = sorted({w for f in folded if f for w in FIXED_WALLS if w in f})
    if walls or any(f is None or f == "" for f in folded):
        reason = f"fixed-wall owner(s): {', '.join(walls)}" if walls else "non-ASCII or empty owner name"
        return [f"E_OWNER: a mechanism may not touch {reason}"]
    offenders = [
        o
        for o in owners
        if not (
            _OWNER_SHAPE.fullmatch(o)
            and all(part and not part.startswith(".") for part in o.split("/"))
            and not o.endswith(".")
        )
    ]
    if offenders:
        return [
            "owner_slices must be repository identifiers: "
            + ", ".join(repr(o[:72]) for o in offenders)
        ]
    return []


def is_finite_number(value: Any) -> bool:
    """Public form of the measurement test used by the cycle: no bool, str, None, NaN or inf."""
    return _finite(value)


def _text(value: Any) -> bool:
    """True for a string with a non-blank character."""
    return isinstance(value, str) and bool(value.strip())


def evaluator_digest(paths: Iterable[Path]) -> str:
    """Digest of the verifier files, bound to their names, so an edit changes the pin."""
    files = sorted(Path(p) for p in paths)
    if not files:
        raise ValueError("evaluator_digest needs at least one verifier file")
    not_files = [str(f) for f in files if not f.is_file()]
    if not_files:
        raise ValueError(f"not a verifier file: {', '.join(not_files)}")
    h = hashlib.sha256()
    for path in files:
        h.update(path.name.encode("utf-8") + b"\0")
        h.update(path.read_bytes() + b"\0")
    return h.hexdigest()


PIN_VERSION = 1


def _pin_body(digest: str, files: Sequence[Path]) -> dict[str, Any]:
    """The pin record: the digest and the sorted names of the verifier files it covers."""
    return {"version": PIN_VERSION, "evaluator_digest": digest, "covers": sorted(Path(f).name for f in files)}


def _read_pin_record(pin_path: Path) -> dict[str, Any]:
    """Parse and shape-check a pin file; ValueError on any defect, including a missing file."""
    try:
        record = json.loads(Path(pin_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # json.JSONDecodeError and UnicodeDecodeError are ValueErrors
        raise ValueError(f"evaluator pin unreadable: {type(exc).__name__}") from exc
    covers = record.get("covers") if isinstance(record, dict) else None
    if not (
        isinstance(record, dict)
        and set(record) == {"version", "evaluator_digest", "covers"}
        and record["version"] == PIN_VERSION
        and not isinstance(record["version"], bool)
        and isinstance(record["evaluator_digest"], str)
        and _HEX64.fullmatch(record["evaluator_digest"])
        and isinstance(covers, list)
        and covers
        and all(_text(name) for name in covers)
    ):
        raise ValueError("evaluator pin is malformed")
    return record


def read_pin(pin_path: Path) -> str:
    """Return the pinned evaluator digest; ValueError if the file is missing or malformed."""
    return _read_pin_record(pin_path)["evaluator_digest"]


def pin_evaluator(pin_path: Path, verifier_paths: Iterable[Path]) -> str:
    """Record the evaluator digest for this run, once, and return it.

    The pin covers exactly the files given (bound by name and bytes, as `evaluator_digest`). The
    file is created atomically and never rewritten. When it already exists the call succeeds only
    if the recomputed digest and covered names are the same; otherwise ValueError("evaluator
    changed"), so a verifier edited after the pin cannot be passed off as the pinned one.
    """
    files = [Path(p) for p in verifier_paths]
    body = _pin_body(evaluator_digest(files), files)
    pin_path = Path(pin_path)
    pin_path.parent.mkdir(parents=True, exist_ok=True)
    # A unique temp file in the pin's directory (same filesystem for the link), so threads and
    # processes pinning the same path never share or delete one another's temp.
    fd, tmp_name = tempfile.mkstemp(prefix=f".{pin_path.name}.", suffix=".tmp", dir=pin_path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(body, sort_keys=True) + "\n")
        os.link(tmp, pin_path)  # atomic and exclusive: fails when a pin already exists
    except FileExistsError:
        record = _read_pin_record(pin_path)
        if record["evaluator_digest"] != body["evaluator_digest"] or record["covers"] != body["covers"]:
            raise ValueError("evaluator changed since it was pinned") from None
    finally:
        tmp.unlink(missing_ok=True)
    return body["evaluator_digest"]


def validate_trace_entry(entry: Mapping[str, Any]) -> list[str]:
    """Return error strings; empty means valid. A lower metric is better."""
    if not isinstance(entry, Mapping):
        return ["entry must be an object"]
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
    for key in ("attempt_id", "hypothesis", "artifact"):
        if not _text(entry[key]):
            errors.append(f"{key} must be non-empty text")
    if not is_declared_metric_name(entry["metric_name"]):
        errors.append("metric_name must be a declared metric")
    for key in ("metric_before", "metric_after"):
        if not _finite(entry[key]):
            errors.append(f"{key} must be a finite number")
    if entry["decision"] not in DECISIONS:
        errors.append("decision must be keep or revert")
    if not (isinstance(entry["evaluator_digest"], str) and _HEX64.fullmatch(entry["evaluator_digest"])):
        errors.append("evaluator_digest must be 64 lowercase hex")
    if not errors:
        expected = "keep" if entry["metric_after"] < entry["metric_before"] else "revert"
        if entry["decision"] != expected:
            errors.append(f"decision {entry['decision']} disagrees with the metrics (expected {expected})")
    return errors


def stall_report(trace: Sequence[Mapping[str, Any]], window: int = STALL_WINDOW) -> dict[str, Any]:
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


def validate_mechanism_card(card: Mapping[str, Any], pinned_digest: str | None = None) -> list[str]:
    """Return error strings; empty means valid. Never mutates `card`.

    `pinned_digest` is the run's pin (`read_pin`). Given for any status, it must equal the card's
    evaluator_digest. A reviewed or graduated card needs a receipt that is a real dry run of this
    card: ok, no retries, no launch, and a valid `trace` carrying the card's evaluator_digest,
    and `card_checked` true with `card_id` naming this card (so a dry run that saw no card, or
    another one, cannot promote it). The receipt must bind the checked content fingerprint; old
    unbound receipts must be regenerated. Graduated also requires an independent `pinned_digest`.
    """
    if not isinstance(card, Mapping):
        return ["card must be an object"]
    errors: list[str] = []
    for key in CARD_FIELDS:
        if key not in card:
            errors.append(f"missing {key}")
    extra = sorted(str(k) for k in card if k not in CARD_FIELDS)
    if extra:
        errors.append(f"unknown field(s): {', '.join(extra)}")
    if errors:
        return errors
    try:
        card_fingerprint(card)
    except (TypeError, ValueError, RecursionError):
        errors.append("card content must be canonicalizable JSON with finite numbers and string keys")
    if card["version"] != CARD_VERSION:
        errors.append("version must be 1")
    if not _text(card["mechanism_id"]):
        errors.append("mechanism_id must be non-empty text")
    revision = card["revision"]
    if not (isinstance(revision, int) and not isinstance(revision, bool) and revision >= 1):
        errors.append("revision must be an integer >= 1")
    if card["parent"] is not None and not _text(card["parent"]):
        errors.append("parent must be null or non-empty text")
    if not _text(card["hypothesis"]):
        errors.append("hypothesis must be non-empty text")
    for key in ("inner_metric", "held_out_metric"):
        if not is_declared_metric_name(card[key]):
            errors.append(f"{key} must be a declared metric")
    ids = card["evidence_ids"]
    if not (isinstance(ids, list) and ids and all(_text(i) for i in ids)):
        errors.append("evidence_ids must be a non-empty list of ledger entry ids")
    if not (isinstance(card["evaluator_digest"], str) and _HEX64.fullmatch(card["evaluator_digest"])):
        errors.append("evaluator_digest must be 64 lowercase hex")
    if not _finite(card["delta"]):
        errors.append("delta must be a finite number")
    if not isinstance(card["reverted"], bool):
        errors.append("reverted must be a boolean")
    scope = card["scope_record"]
    if not (isinstance(scope, Mapping) and scope.get("authorizes") == "nothing"):
        errors.append("scope_record.authorizes must be 'nothing'")
    errors.extend(_owner_errors(card["owner_slices"]))
    if _finite(card["delta"]) and isinstance(card["reverted"], bool):
        # delta is metric_after - metric_before on a lower-is-better metric.
        if card["reverted"] and card["delta"] < 0:
            errors.append("reverted is true but delta shows an improvement")
        if not card["reverted"] and card["delta"] >= 0:
            errors.append("reverted is false but delta shows no improvement")
    status = card["status"]
    if status not in CARD_STATUSES:
        errors.append("status must be candidate, reviewed or graduated")
        return errors
    receipt = card["dry_run_receipt"]
    if not isinstance(receipt, Mapping):
        errors.append("dry_run_receipt must be an object")
    elif status in ("reviewed", "graduated") and not (
        receipt.get("ok") is True and receipt.get("retries") == 0 and receipt.get("launched") is False
    ):
        errors.append(f"dry_run_receipt must show ok, no retries and no launch before {status}")
    elif status in ("reviewed", "graduated"):
        errors.extend(_receipt_binding_errors(card, receipt))
    if pinned_digest is not None and pinned_digest != card["evaluator_digest"]:
        errors.append("pinned_digest does not equal the card's evaluator_digest")
    if status == "graduated" and pinned_digest is None:
        errors.append("a graduated card needs pinned_digest: the evaluator digest was never pinned")
    if status == "graduated" and card["reverted"] is True:
        errors.append("a reverted card cannot be graduated")
    return errors


def card_id(card: Mapping[str, Any]) -> str:
    """The identity a dry cycle reports for the card it checked: "<mechanism_id>@<revision>"."""
    return f"{card['mechanism_id']}@{card['revision']}"


def card_fingerprint(card: Mapping[str, Any]) -> str:
    """Hash canonical checked card content, excluding lifecycle state and its receipt."""
    content = {key: value for key, value in card.items() if key not in {"status", "reverted", "dry_run_receipt"}}
    def check_json(value: Any, active: set[int]) -> None:
        """Reject coercions, unsupported values and cycles before canonical serialization."""
        if value is None or type(value) in (str, bool, int):
            return
        if type(value) is float:
            if not math.isfinite(value):
                raise ValueError("non-finite JSON number")
            return
        if type(value) not in (dict, list):
            raise TypeError("unsupported JSON value")
        identity = id(value)
        if identity in active:
            raise ValueError("cyclic JSON value")
        active.add(identity)
        try:
            if type(value) is dict:
                for key, item in value.items():
                    if type(key) is not str:
                        raise TypeError("JSON object keys must be strings")
                    check_json(item, active)
            else:
                for item in value:
                    check_json(item, active)
        finally:
            active.remove(identity)

    check_json(content, set())
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _receipt_binding_errors(card: Mapping[str, Any], receipt: Mapping[str, Any]) -> list[str]:
    """Bind checked content, evaluator, trace decision and measured delta to this card."""
    errors: list[str] = []
    trace = receipt.get("trace")
    if not isinstance(trace, Mapping):
        errors.append("dry_run_receipt must carry the dry cycle's trace")
    elif validate_trace_entry(trace):
        errors.append("dry_run_receipt.trace is not a valid trace entry")
    elif trace["evaluator_digest"] != card["evaluator_digest"]:
        errors.append("dry_run_receipt.trace.evaluator_digest does not equal the card's evaluator_digest")
    elif not _finite(card["delta"]) or not math.isclose(
        card["delta"], trace["metric_after"] - trace["metric_before"], rel_tol=0.0, abs_tol=1e-9
    ):
        errors.append("card delta does not equal the receipt trace's metric_after - metric_before")
    if isinstance(trace, Mapping) and trace.get("decision") in DECISIONS and isinstance(card["reverted"], bool):
        if (trace["decision"] == "revert") != card["reverted"]:
            errors.append("dry_run_receipt.trace.decision does not agree with reverted")
    try:
        fingerprint = card_fingerprint(card)
    except (TypeError, ValueError, RecursionError):
        fingerprint = None
    if fingerprint is None or receipt.get("card_fingerprint") != fingerprint:
        errors.append("dry_run_receipt.card_fingerprint does not match checked card content")
    if receipt.get("card_checked") is not True:
        errors.append("dry_run_receipt must show card_checked true")
    elif receipt.get("card_id") != card_id(card):
        errors.append("dry_run_receipt.card_id does not name this card")
    return errors


def select_effort(supported: Iterable[str] = EFFORT_LADDER) -> str | None:
    """First of medium, high, low that the provider supports; None if none (never xhigh/max)."""
    offered = {supported} if isinstance(supported, str) else set(supported)
    return next((effort for effort in EFFORT_LADDER if effort in offered), None)


def default_wandb_turn(unavailable: Iterable[str] = ()) -> dict[str, Any]:
    """The free default turn: first available W&B model in order, effort from its own ladder."""
    skipped = set(unavailable)
    for model in WANDB_MODEL_ORDER:
        if model not in skipped:
            return {
                "tier": "default", "provider": "wandb", "model": model,
                "effort": select_effort(WANDB_EFFORTS[model]),
                "human_gated": False, "auto_run": True,
            }
    return {
        "tier": "default", "provider": "wandb", "model": None, "effort": None,
        "reason": "no-wandb-model-available", "human_gated": False, "auto_run": False,
    }


def plan_turn(
    seat: str,
    platform: str | None = None,
    paid_approved: Any = False,
    supported: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Choose the model tier and effort for one turn.

    A preferred paid model is returned only for a literal `paid_approved is True` and a known
    seat/platform pair, and it is marked human-gated and not auto-run. Everything else gets the
    free default: with no `supported` argument, the W&B default turn (model order, then that
    model's effort ladder); with an explicit `supported`, the plain ladder and no model pinned.
    """
    preferred = PREFERRED_PAID.get((seat, platform or ""))
    if paid_approved is True and preferred is not None:
        model, effort = preferred
        return {"tier": "preferred", "model": model, "effort": effort, "human_gated": True, "auto_run": False}
    if supported is None:
        return default_wandb_turn()
    return {
        "tier": "default",
        "model": None,
        "effort": select_effort(supported),
        "human_gated": False,
        "auto_run": True,
    }
