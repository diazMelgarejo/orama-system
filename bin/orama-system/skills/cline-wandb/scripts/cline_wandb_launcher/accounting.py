"""Token accounting: read reported usage, classify one chat outcome, clamp a request to the budget."""
from __future__ import annotations

import json

# No non-2xx status is trusted to mean "nothing billed": neither the provider nor a gateway in
# front of it documents that guarantee, so every non-2xx chat response is UNACCOUNTED.
ACCOUNTED, UNACCOUNTED = "accounted", "unaccounted"


class BoundaryExceededError(RuntimeError):
    """A spend bound was exceeded, or a dispatch could not be accounted for (limit is None)."""

    def __init__(self, bound: str, limit: int | None, actual: object) -> None:
        detail = f"exceeded: limit={limit}, actual={actual}" if limit is not None else f"actual={actual}"
        super().__init__(f"{bound} {detail}")
        self.bound = bound
        self.limit = limit
        self.actual = actual


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
