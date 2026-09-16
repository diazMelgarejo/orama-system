"""orama-side client for PT's Tier-5 pipeline endpoint.

This module is the **only** approved way for orama to trigger PT's paid
pipeline.  It enforces the following invariants at the code level:

Anti-loop contract
------------------
orama MUST NOT call PT's ``/orchestrate`` endpoint.  That endpoint routes
``deep_reasoning`` / ``code_analysis`` tasks back through
``call_oramasys_mcp_or_bridge``, which posts to orama.  The resulting
PT → orama → PT cycle would (a) bypass PT's Tier-5 approval + budget gates,
(b) potentially recurse until timeout, and (c) produce stale intermediate
state.

This module therefore calls ONLY ``/pipelines/{recipe}/run`` (the explicit,
approval-gated Tier-5 path).  It intentionally imports nothing from
``orchestrator.orama_bridge``.

Approval contract
-----------------
The caller must register a ``PipelineApproval`` with PT
(``POST /pipelines/approvals``) before invoking ``run()``.  This client
passes the ``trace_id`` in the request body — PT validates it, checks
revocation, expiry, token budget, and cost budget before dispatching.
Orama never short-circuits those gates.

Environment variables
---------------------
``PT_PIPELINE_TOKEN``
    Bearer token accepted by PT's control-plane auth middleware.
    Defaults to empty (call will return 401 if auth is enforced on PT).
``PT_PIPELINE_BASE_URL``
    Base URL of the PT HTTP server.  Default: ``http://localhost:8000``.
    Must be scheme + host + port only (no path).
"""
from __future__ import annotations

import os
import uuid
from typing import Any

import httpx


class PipelineCallError(RuntimeError):
    """Raised when PT's pipeline endpoint returns an unexpected status code."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"PT pipeline call failed (HTTP {status}): {detail}")
        self.status = status
        self.detail = detail


class PipelineAuthError(PipelineCallError):
    """Raised when PT rejects the call with 401 (bad token) or 403
    (approval invalid / revoked / expired)."""


class PipelineBudgetError(PipelineCallError):
    """Raised when PT rejects the call with 402 (daily budget exhausted)."""


_SAFE_RESULT_KEYS = frozenset(
    {
        "status",
        "recipe",
        "output",
        "requested_tokens",
        "cost_reservation_usd",
        "held_microusd",
        "settled_microusd",
        "run_id",
    }
)


class Tier5PipelineClient:
    """Thin async HTTP client for PT's /pipelines/{recipe}/run endpoint.

    Usage::

        client = Tier5PipelineClient()
        result = await client.run(
            recipe="classify_then_generate",
            prompt="Analyze this …",
            trace_id="my-pre-registered-trace-id",
        )
        print(result["output"])

    Each ``Tier5PipelineClient`` instance owns one ``httpx.AsyncClient``
    session.  Call ``await client.aclose()`` when done, or use it as an
    async context manager.
    """

    def __init__(
        self,
        pt_base_url: str | None = None,
        token: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._base = (
            (pt_base_url or os.getenv("PT_PIPELINE_BASE_URL", "http://localhost:8000"))
            .rstrip("/")
        )
        self._token = token or os.getenv("PT_PIPELINE_TOKEN", "")
        self._timeout = timeout
        self._http = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "Tier5PipelineClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    def _build_headers(self, idempotency_key: str) -> dict[str, str]:
        headers: dict[str, str] = {"Idempotency-Key": idempotency_key}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def run(
        self,
        *,
        recipe: str,
        prompt: str,
        trace_id: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Execute one Tier-5 pipeline stage on PT and return the safe result.

        Parameters
        ----------
        recipe:
            Name of the pipeline recipe, e.g. ``"classify_then_generate"``.
            Must match a recipe registered in PT's ``config/pipelines.yml``.
        prompt:
            The input prompt for the pipeline.
        trace_id:
            Must be a pre-registered approval trace ID.  PT validates this
            before dispatching and will return 403 if it is unknown, expired,
            or revoked.
        idempotency_key:
            A UUIDv4 string used for idempotent replay.  Auto-generated when
            not supplied.

        Returns
        -------
        dict
            A subset of PT's response body: only ``_SAFE_RESULT_KEYS`` fields
            are forwarded.  Intermediate ``stage_outputs`` are deliberately
            dropped so that internal classification context cannot be re-used
            by the caller without a new approval cycle.

        Raises
        ------
        PipelineAuthError
            HTTP 401 (bad/missing token) or 403 (approval invalid).
        PipelineBudgetError
            HTTP 402 (daily budget exhausted).
        PipelineCallError
            Any other non-200 response.
        """
        key = idempotency_key or str(uuid.uuid4())
        url = f"{self._base}/pipelines/{recipe}/run"
        headers = self._build_headers(key)

        resp = await self._http.post(
            url,
            json={"prompt": prompt, "trace_id": trace_id},
            headers=headers,
        )

        if resp.status_code in (401, 403):
            detail = _extract_detail(resp)
            raise PipelineAuthError(resp.status_code, detail)
        if resp.status_code == 402:
            detail = _extract_detail(resp)
            raise PipelineBudgetError(resp.status_code, detail)
        if resp.status_code != 200:
            detail = _extract_detail(resp)
            raise PipelineCallError(resp.status_code, detail)

        body: dict[str, Any] = resp.json() if callable(resp.json) else resp.json
        # Drop stage_outputs and any other fields not in the safe set to
        # prevent forwarding of internal classification context.
        return {k: v for k, v in body.items() if k in _SAFE_RESULT_KEYS}


def _extract_detail(resp: httpx.Response) -> str:
    try:
        return str(resp.json().get("detail", ""))
    except Exception:
        return resp.text[:200]
