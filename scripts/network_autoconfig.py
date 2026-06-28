#!/usr/bin/env python3
"""
Network auto-configuration helper for orama-system.
This is a legacy wrapper. The canonical implementation now lives in
Perpetua-Tools (packages.net_utils.network_autoconfig).
"""

import sys
import os
from pathlib import Path

# Try to add PT path and import from there
pt_root = Path(os.environ.get("PERPETUA_TOOLS_ROOT", Path(__file__).resolve().parent.parent.parent / "perplexity-api" / "Perpetua-Tools"))
if pt_root.exists() and str(pt_root) not in sys.path:
    sys.path.insert(0, str(pt_root))

try:
    from packages.net_utils.network_autoconfig import NetworkAutoConfig, main
except ImportError as exc:
    print(f"Warning: Could not import NetworkAutoConfig from Perpetua-Tools: {exc}", file=sys.stderr)
    print(f"Looked in: {pt_root}/packages/net_utils", file=sys.stderr)
    sys.exit(1)

# Re-export
__all__ = ["NetworkAutoConfig", "main"]

if __name__ == "__main__":
    main()
