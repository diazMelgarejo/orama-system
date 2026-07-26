#!/usr/bin/env python3
"""Ensure gitignored local mesh secrets exist (never committed).

Writes to .env.local (orama + optional Perpetua) and .local/mesh-secrets.json:
  - GOSSIP_SHARED_SECRET — shared across all fleet peers for gossip + discovery handshake

Integrative: harmonizes missing/empty keys only — never replaces operator values.
"""
from __future__ import annotations

import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

_MESH_DIR = Path(__file__).resolve().parent
if str(_MESH_DIR) not in sys.path:
    sys.path.insert(0, str(_MESH_DIR))
from dotenv_merge import harmonize_dotenv_keys

ROOT = Path(__file__).resolve().parents[2]
LOCAL_DIR = ROOT / ".local"
SECRETS_JSON = LOCAL_DIR / "mesh-secrets.json"
ENV_KEYS = frozenset({"GOSSIP_SHARED_SECRET"})
ENV_HEADER = (
    "# Local mesh secrets — never commit (harmonized by ensure_local_mesh_secrets.py)"
)


def _repo_env_paths() -> list[Path]:
    paths = [ROOT / ".env.local"]
    pt = os.environ.get("PERPETUA_TOOLS_PATH", "").strip()
    if pt:
        paths.append(Path(pt) / ".env.local")
    return paths


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _merge_env(path: Path, values: dict[str, str]) -> None:
    harmonize_dotenv_keys(
        path,
        values,
        managed_keys=ENV_KEYS,
        header_comment=ENV_HEADER,
    )
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def ensure_gossip_secret(*, force: bool = False) -> str:
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    store = _load_json(SECRETS_JSON)
    secret = (store.get("GOSSIP_SHARED_SECRET") or "").strip()
    if not secret or force:
        secret = secrets.token_urlsafe(32)
        store["GOSSIP_SHARED_SECRET"] = secret
        store["updated_at"] = datetime.now(timezone.utc).isoformat()
        SECRETS_JSON.write_text(json.dumps(store, indent=2) + "\n", encoding="utf-8")
        try:
            os.chmod(SECRETS_JSON, 0o600)
        except OSError:
            pass
    for path in _repo_env_paths():
        if path.parent.exists() or path == ROOT / ".env.local":
            path.parent.mkdir(parents=True, exist_ok=True)
            _merge_env(path, {"GOSSIP_SHARED_SECRET": secret})
    os.environ["GOSSIP_SHARED_SECRET"] = secret
    return secret


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Ensure local-only mesh secrets.")
    parser.add_argument("--force", action="store_true", help="Rotate GOSSIP_SHARED_SECRET")
    args = parser.parse_args()
    ensure_gossip_secret(force=args.force)
    print("OK: GOSSIP_SHARED_SECRET present in .env.local (value not printed)")
    print(f"     archive: {SECRETS_JSON.relative_to(ROOT)}")
    print("     distribute this secret to all mesh peers out-of-band — never commit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
