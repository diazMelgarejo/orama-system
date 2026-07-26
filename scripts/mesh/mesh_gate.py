#!/usr/bin/env python3
"""Shared LAN mesh bind guards (GOSSIP secret presence)."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def gossip_secret_configured(repo_root: Path) -> bool:
    """True when GOSSIP_SHARED_SECRET is set in env or .env.local (last wins)."""
    if os.environ.get("GOSSIP_SHARED_SECRET", "").strip():
        return True
    mesh_dir = repo_root / "scripts" / "mesh"
    if str(mesh_dir) not in sys.path:
        sys.path.insert(0, str(mesh_dir))
    from dotenv_merge import read_dotenv_key

    return bool(read_dotenv_key(repo_root / ".env.local", "GOSSIP_SHARED_SECRET"))


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    return 0 if gossip_secret_configured(root) else 1


if __name__ == "__main__":
    raise SystemExit(main())
