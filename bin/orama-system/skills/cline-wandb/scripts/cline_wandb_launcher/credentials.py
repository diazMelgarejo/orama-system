"""Provider key lookup. The key is read from the environment and never written or printed."""
from __future__ import annotations

import os
import sys

from .defaults import DEFAULT_ENV_FILE, KEYVAR


def read_key() -> str:
    """Return KEYVAR from the already-exported environment; never read or parse the env file."""
    key = os.environ.get(KEYVAR, "").strip()
    if not key:
        sys.exit(
            f"ERROR: {KEYVAR} is missing or empty. Shell-source the trusted env through the "
            f"approved wrapper ({DEFAULT_ENV_FILE}); this launcher does not parse the file."
        )
    return key
