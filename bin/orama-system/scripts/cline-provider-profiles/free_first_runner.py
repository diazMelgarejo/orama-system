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


def classify_outcome(http_status: int | None, structured_code: Any = None) -> str:
    """1113 is a billing stop. A plain 429 is a throttle, not that stop."""
    code = str(structured_code) if structured_code is not None else ""
    if http_status == 429 and code == "1113":
        return "billing_or_entitlement_blocked"
    if http_status == 429:
        return "throttled"
    if http_status == 200:
        return "success"
    return "rejected"


def next_model(
    profile: Mapping[str, Any],
    ledger: Sequence[Mapping[str, Any]] | None = None,
) -> str | None:
    """Return the next free model, or None when the chain must stop.

    `free_only` never returns a paid id. Billing code 1113 stops the chain
    even if free models remain.
    """
    if profile.get("financial_mode") != "free_only":
        raise ValueError("free-first runner requires financial_mode free_only")
    models = list(profile.get("resolution", {}).get("models") or [])
    if _PAID_STOP in models or profile.get("settings", {}).get("model") == _PAID_STOP:
        raise ValueError("free_only profile selected a paid model")
    for row in ledger or []:
        if classify_outcome(row.get("http_status"), row.get("code")) == "billing_or_entitlement_blocked":
            return None
    settled = {row.get("model_id") for row in (ledger or [])}
    for model_id in models:
        if model_id not in settled:
            return model_id
    return None
