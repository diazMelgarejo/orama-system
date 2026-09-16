"""Stateless client for PT-owned, approval-gated tiered pipelines."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping

import httpx
import yaml

from utils.control_plane_auth import auth_headers
from utils.model_endpoint_url import ModelEndpointPolicyError, validate_model_endpoint_url


DEFAULT_CONFIG = Path(__file__).resolve().parent / "config" / "pipeline-routing.yml"
_ALLOWED_KEYS = frozenset({"version", "enabled", "pt_base_url", "recipes"})


class PTPipelineError(RuntimeError):
    """Raised when the guarded PT pipeline cannot complete."""


@dataclass(frozen=True)
class PTPipelineResult:
    output: str
    models_used: Mapping[str, str]
    replay: bool = False


@lru_cache(maxsize=16)
def _load_routing_config(config_path: str) -> dict:
    path = Path(config_path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise PTPipelineError("PT pipeline routing config is unavailable") from exc
    if not isinstance(raw, dict) or set(raw) - _ALLOWED_KEYS:
        raise PTPipelineError("PT pipeline routing config is invalid")
    if raw.get("enabled") is not True:
        raise PTPipelineError("PT pipeline routing is disabled")
    recipes = raw.get("recipes")
    if not isinstance(recipes, dict) or not recipes:
        raise PTPipelineError("PT pipeline recipe mapping is missing")
    return raw


class PTPipelineClient:
    """Call PT's pipeline route directly; never call its orchestrate route."""

    def __init__(
        self,
        *,
        config_path: str | Path | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        configured_path = os.getenv("ORAMASYS_PIPELINE_ROUTING_CONFIG", "").strip()
        self.config_path = (
            Path(config_path)
            if config_path
            else Path(configured_path)
            if configured_path
            else DEFAULT_CONFIG
        )
        self.transport = transport
        self._config = _load_routing_config(str(self.config_path.resolve()))

    def pipeline_url(self, task_type: str) -> str:
        recipes = self._config["recipes"]
        recipe = str(recipes.get(task_type, "")).strip()
        if not recipe or not recipe.replace("_", "").replace("-", "").isalnum():
            raise PTPipelineError("No guarded PT pipeline recipe is configured")
        configured_base = (
            os.getenv("ORAMASYS_PT_PIPELINE_BASE_URL", "").strip()
            or os.getenv("PT_PIPELINE_BASE_URL", "").strip()
            or str(self._config.get("pt_base_url", "")).strip()
        )
        try:
            base = validate_model_endpoint_url(configured_base, allow_public=False)
        except ModelEndpointPolicyError as exc:
            raise PTPipelineError("trusted PT pipeline endpoint is invalid") from exc
        return f"{base}/pipelines/{recipe}/run"

    async def run(
        self,
        *,
        task_type: str,
        prompt: str,
        trace_id: str,
        idempotency_key: str,
    ) -> PTPipelineResult:
        headers = {
            **auth_headers(),
            "Idempotency-Key": idempotency_key,
        }
        timeout = httpx.Timeout(120.0, connect=10.0)
        try:
            async with httpx.AsyncClient(
                transport=self.transport,
                timeout=timeout,
                follow_redirects=False,
            ) as client:
                response = await client.post(
                    self.pipeline_url(task_type),
                    headers=headers,
                    json={"prompt": prompt, "trace_id": trace_id},
                )
                response.raise_for_status()
                body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise PTPipelineError("PT pipeline request failed") from exc
        output = body.get("output") if isinstance(body, dict) else None
        models_used = body.get("models_used") if isinstance(body, dict) else None
        replay = body.get("replay") is True if isinstance(body, dict) else False
        if (
            not isinstance(output, str)
            or (not replay and not output.strip())
            or not isinstance(models_used, dict)
        ):
            raise PTPipelineError("PT pipeline returned an invalid response")
        return PTPipelineResult(
            output=output,
            models_used={
                str(stage): str(model)
                for stage, model in models_used.items()
                if str(stage).strip() and str(model).strip()
            },
            replay=replay,
        )
