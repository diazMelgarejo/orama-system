#!/usr/bin/env python3
"""Pre-commit gate: block committed private LAN IPs in config/registry JSON/YAML.

Hardware affinity slugs (win-rtx3080, win-rtx5080) belong in tracked config.
Endpoint URLs must use ${env:LM_STUDIO_*_ENDPOINTS} — autodetect locally, never commit.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HYGIENE_PATH = ROOT / "scripts" / "review" / "repo_hygiene.py"


def load_repo_hygiene():
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


def main() -> int:
    repo_hygiene = load_repo_hygiene()
    errors = repo_hygiene.scan_tracked_private_network_literals(ROOT, tracked_files(ROOT))
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        print(
            "FAIL: committed LAN topology — use ${env:LM_STUDIO_WIN_ENDPOINTS}, "
            "${env:LM_STUDIO_WIN_5080_ENDPOINTS}, or runtime discovery; "
            "affinity slugs (win-rtx3080/win-rtx5080) are OK",
            file=sys.stderr,
        )
        return 1
    print("OK: no private LAN literals in tracked config")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
