#!/usr/bin/env python3
"""Verify GOSSIP_SHARED_SECRET parity across repo-local env and JSON mirrors."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_MESH_DIR = Path(__file__).resolve().parent
if str(_MESH_DIR) not in sys.path:
    sys.path.insert(0, str(_MESH_DIR))
from dotenv_merge import read_dotenv_key

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env.local"
SECRETS_JSON = ROOT / ".local" / "mesh-secrets.json"


def _json_secret(path: Path) -> str:
    if not path.is_file():
        return ""
    data = json.loads(path.read_text(encoding="utf-8"))
    return (data.get("GOSSIP_SHARED_SECRET") or "").strip()


def _secret_stores() -> list[Path]:
    stores = [SECRETS_JSON]
    pt = os.environ.get("PERPETUA_TOOLS_PATH", "").strip()
    if pt:
        stores.append(Path(pt) / ".local" / "mesh-secrets.json")
    return stores


def main() -> int:
    env_val = (read_dotenv_key(ENV_FILE, "GOSSIP_SHARED_SECRET") or "").strip()
    if not env_val:
        print("FAIL: missing GOSSIP_SHARED_SECRET in repo-local env file", file=sys.stderr)
        return 1

    mismatch_count = 0
    for store in _secret_stores():
        if not store.is_file():
            continue
        json_val = _json_secret(store)
        if json_val and json_val != env_val:
            mismatch_count += 1

    if mismatch_count:
        print(
            "FAIL: GOSSIP_SHARED_SECRET env/JSON parity check failed "
            f"({mismatch_count} store(s))",
            file=sys.stderr,
        )
        return 1

    print("OK: GOSSIP_SHARED_SECRET matches all JSON stores")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
