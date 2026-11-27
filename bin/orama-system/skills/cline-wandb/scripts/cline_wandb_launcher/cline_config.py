"""The throwaway Cline configuration: the one openai-compatible entry Cline accepts, written privately."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone

from .defaults import BASE_URL


def cline_timestamp() -> str:
    """Return the current time the way Cline writes it: UTC, milliseconds, trailing Z."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def build_config(
    key: str,
    model: str,
    effort: str,
    timeout_ms: int,
    base_url: str = BASE_URL,
) -> dict:
    """Return a providers.json document with only the openai-compatible entry.

    `key` is the credential Cline presents. The launcher passes its per-launch session token, never the
    provider key, which stays in launcher memory.
    """
    return {
        "version": 1,
        "lastUsedProvider": "openai-compatible",
        "modes": {},
        "providers": {
            "openai-compatible": {
                "settings": {
                    "provider": "openai-compatible",
                    "apiKey": key,
                    "model": model,
                    "baseUrl": base_url,
                    "headers": {},
                    "timeout": timeout_ms,
                    "reasoning": {"enabled": True, "effort": effort},
                },
                "updatedAt": cline_timestamp(),
                "tokenSource": "manual",
            }
        },
    }


def create_config_dir() -> str:
    """Create the throwaway config directory, open to this user only."""
    config_dir = tempfile.mkdtemp(prefix="clinecfg-")
    os.chmod(config_dir, 0o700)
    return config_dir


def write_config(config_dir: str, document: dict) -> None:
    """Write providers.json where Cline looks for it, readable by this user only."""
    settings_dir = os.path.join(config_dir, "data", "settings")
    os.makedirs(settings_dir)
    fd = os.open(os.path.join(settings_dir, "providers.json"), os.O_WRONLY | os.O_CREAT, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(document, handle)
