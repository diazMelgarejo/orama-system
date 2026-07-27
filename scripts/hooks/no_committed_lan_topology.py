#!/usr/bin/env python3
"""Pre-commit gate: block committed private LAN IPs in config/registry JSON/YAML.

Hardware affinity slugs (win-rtx3080, win-rtx5080) belong in tracked config.
Endpoint URLs must use ${env:LM_STUDIO_*_ENDPOINTS} — autodetect locally, never commit.
"""
from __future__ import annotations

import importlib.util
import logging
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
HYGIENE_PATH = ROOT / "scripts" / "review" / "repo_hygiene.py"
logger = logging.getLogger(__name__)


def load_repo_hygiene() -> ModuleType:
    spec = importlib.util.spec_from_file_location("repo_hygiene", HYGIENE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tracked_files(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git ls-files failed")
    return [line for line in proc.stdout.splitlines() if line]


def _configure_logging() -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def main() -> int:
    _configure_logging()
    repo_hygiene = load_repo_hygiene()
    errors = repo_hygiene.scan_tracked_private_network_literals(
        ROOT,
        tracked_files(ROOT),
        use_git_index=True,
    )
    if errors:
        for err in errors:
            logger.error("ERROR: %s", err)
        logger.error(
            "FAIL: committed LAN topology — use ${env:LM_STUDIO_WIN_ENDPOINTS}, "
            "${env:LM_STUDIO_WIN_5080_ENDPOINTS}, or runtime discovery; "
            "affinity slugs (win-rtx3080/win-rtx5080) are OK"
        )
        return 1
    logger.info("OK: no private LAN literals in tracked config")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
