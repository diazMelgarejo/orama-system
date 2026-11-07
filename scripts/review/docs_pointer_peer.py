"""Resolve explicit immutable PT partners for cross-repository pointer checks."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re


def paired_ref(path: Path, pull_number: str) -> str:
    """Return a validated pinned partner, or empty for the legacy branch lookup."""
    pairs = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(pairs, dict):
        raise ValueError("pointer peer registry must be an object")
    for number, sha in pairs.items():
        if not re.fullmatch(r"[1-9][0-9]*", number):
            raise ValueError("invalid pull request number")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise ValueError("pointer peer must be an immutable commit")
    return pairs.get(pull_number, "")


def main() -> None:
    """Emit only validated non-secret checkout metadata to GitHub Actions."""
    pin = paired_ref(
        Path(__file__).resolve().parents[2] / "config/docs-pointer-peers.json",
        os.environ.get("POINTER_PULL_NUMBER", ""),
    )
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"ref={pin}\n")


if __name__ == "__main__":
    main()
