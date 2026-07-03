#!/usr/bin/env python3
"""Verify endpoint-policy scan roots exist.

Keep SCAN_ROOTS in sync with scripts/security/check_endpoint_policy_contract.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

SCAN_ROOTS = ["bin", "scripts", "src", "platform"]


def main() -> int:
    missing = [root for root in SCAN_ROOTS if not Path(root).is_dir()]
    if missing:
        print(f"FAIL: scan_roots references missing directories: {missing}")
        return 1
    print(f"OK: all scan_roots exist: {SCAN_ROOTS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
