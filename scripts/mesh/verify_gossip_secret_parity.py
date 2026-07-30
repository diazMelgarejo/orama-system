#!/usr/bin/env python3
"""Verify GOSSIP_SHARED_SECRET parity across repo-local env and JSON mirrors.

Run after ``ensure_local_mesh_secrets.py`` harmonizes mirrors. By default, missing
JSON stores are skipped (env-only bootstrap). Pass ``--require-stores`` to fail
closed when an expected ``.local/mesh-secrets.json`` mirror is absent.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_MESH_DIR = Path(__file__).resolve().parent
if str(_MESH_DIR) not in sys.path:
    sys.path.insert(0, str(_MESH_DIR))
from dotenv_merge import read_dotenv_key
from mesh_logging import get_mesh_logger

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env.local"
SECRETS_JSON = ROOT / ".local" / "mesh-secrets.json"
log = get_mesh_logger("orama.mesh.parity", repo_root=ROOT)


def _usable_secret(value: object) -> str | None:
    if value is None or not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in "\"'":
        inner = stripped[1:-1].strip()
        return inner or None
    return stripped


def _json_secret(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return _usable_secret(data.get("GOSSIP_SHARED_SECRET"))


def _secret_stores() -> list[Path]:
    stores = [SECRETS_JSON]
    pt = os.environ.get("PERPETUA_TOOLS_PATH", "").strip()
    if pt:
        stores.append(Path(pt) / ".local" / "mesh-secrets.json")
    return stores


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify GOSSIP_SHARED_SECRET parity across env and JSON mirrors.",
    )
    parser.add_argument(
        "--require-stores",
        action="store_true",
        help="Fail when an expected .local/mesh-secrets.json mirror is missing.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    env_val = _usable_secret(read_dotenv_key(ENV_FILE, "GOSSIP_SHARED_SECRET"))
    if not env_val:
        log.error("FAIL: missing GOSSIP_SHARED_SECRET in repo-local env file")
        return 1

    mismatch_count = 0
    missing_count = 0
    for store in _secret_stores():
        if not store.is_file():
            if args.require_stores:
                missing_count += 1
            continue
        json_val = _json_secret(store)
        if json_val is None or json_val != env_val:
            mismatch_count += 1

    if missing_count:
        log.error(
            "FAIL: expected JSON mirror store(s) missing (%d store(s))",
            missing_count,
        )
        return 1

    if mismatch_count:
        log.error(
            "FAIL: GOSSIP_SHARED_SECRET env/JSON parity check failed (%d store(s))",
            mismatch_count,
        )
        return 1

    print("OK: GOSSIP_SHARED_SECRET matches all JSON stores")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
