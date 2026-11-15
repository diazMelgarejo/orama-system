"""Walk the free-first Cline profile. Paid models and billing code 1113 stop it."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

_PROFILE = Path(__file__).with_name("bigmodel-free-first.json.tmpl")
_PAID_STOP = "glm-5.3-flash"


def load_profile(path: Path | None = None) -> dict[str, Any]:
    """Return the checked-in free-first profile."""
    return json.loads((path or _PROFILE).read_text(encoding="utf-8"))


_CONTINUABLE = frozenset({"model_unavailable", "capability_ineligible", "rejected"})


def classify_outcome(
    http_status: int | None,
    structured_code: Any = None,
    execution_state: str | None = None,
    outcome: str | None = None,
) -> str:
    """Map one result to a class. 1113 is a billing stop, not a throttle."""
    if isinstance(outcome, str) and outcome:
        return outcome
    state = (execution_state or "").lower()
    if state in {"recovery", "partial", "tool_effects", "cancelled"}:
        return "recovery_required"
    if state in {"safety", "policy_rejection"}:
        return "safety_blocked"
    if state in {"timeout", "network", "interrupted"}:
        return "outcome_unknown"
    code = str(structured_code) if structured_code is not None else ""
    if http_status == 429 and code == "1113":
        return "billing_or_entitlement_blocked"
    if http_status in {401, 403}:
        return "credentials_blocked"
    if http_status == 429:
        return "throttled"
    if http_status == 200:
        return "success"
    if http_status == 404:
        return "model_unavailable"
    if http_status == 422:
        return "rejected"
    if http_status is not None and http_status >= 500:
        return "outcome_unknown"
    return "outcome_unknown"


def next_model(
    profile: Mapping[str, Any],
    ledger: Sequence[Mapping[str, Any]] | None = None,
) -> str | None:
    """Return the next free model, or None when the chain must stop.

    `free_only` never returns a paid id. Success, billing, credentials,
    throttle, and uncertain execution stop the chain. A proven miss of one
    model is the only reason to try the next free id. `glm-4.7-flash` stays
    first when the ledger is empty.
    """
    if profile.get("financial_mode") != "free_only":
        raise ValueError("free-first runner requires financial_mode free_only")
    models = list(profile.get("resolution", {}).get("models") or [])
    if _PAID_STOP in models or profile.get("settings", {}).get("model") == _PAID_STOP:
        raise ValueError("free_only profile selected a paid model")
    settled: set[Any] = set()
    for row in ledger or []:
        klass = classify_outcome(
            row.get("http_status"),
            row.get("code"),
            row.get("execution_state"),
            row.get("outcome"),
        )
        if klass not in _CONTINUABLE:
            return None
        if row.get("model_id"):
            settled.add(row.get("model_id"))
    for model_id in models:
        if model_id not in settled:
            return model_id
    return None
