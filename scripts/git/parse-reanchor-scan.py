#!/usr/bin/env python3
"""Parse reanchor_scan.sh output into JSON branch actions.

Usage:
  bash scripts/git/reanchor_scan.sh . origin/main remotes | tee /tmp/scan.txt
  python3 scripts/git/parse-reanchor-scan.py /tmp/scan.txt

Stdout: {"merged": [...], "needs": [...], "no_twin": [...]}
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def parse_scan(text: str) -> dict:
    merged: list[str] = []
    needs: list[dict] = []
    no_twin: list[str] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"\s+origin/(\S+)\s+MERGED/in-main", line)
        if m:
            merged.append(m.group(1))
            i += 1
            continue
        m = re.match(
            r"\s+origin/(\S+)\s+NEEDS-REANCHOR:.*onto twin ([0-9a-f]+)", line
        )
        if m:
            branch, twin_short = m.group(1), m.group(2)
            cherry = lines[i + 1] if i + 1 < len(lines) else ""
            cm = re.search(
                r"git cherry -v origin/main ([0-9a-f]+) ([0-9a-f]+)", cherry
            )
            if cm:
                tip, base = cm.group(1), cm.group(2)
                needs.append(
                    {
                        "branch": branch,
                        "tip": tip,
                        "base": base,
                        "twin_short": twin_short,
                    }
                )
            i += 2
            continue
        m = re.match(r"\s+origin/(\S+)\s+NO-TWIN", line)
        if m:
            no_twin.append(m.group(1))
            i += 1
            continue
        i += 1
    return {"merged": merged, "needs": needs, "no_twin": no_twin}


def main() -> None:
    path = Path(sys.argv[1])
    data = parse_scan(path.read_text(encoding="utf-8"))
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
