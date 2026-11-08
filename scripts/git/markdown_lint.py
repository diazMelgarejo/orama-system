#!/usr/bin/env python3
"""Run the pinned Markdown linter on tracked first-party files."""

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.17.2"


def ignored(path, patterns):
    return path == "CHANGELOG.md" or any(
        fnmatch.fnmatchcase(path, pattern)
        or fnmatch.fnmatchcase("x/" + path, pattern)
        for pattern in patterns
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("changed", "debt"))
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    if args.mode == "changed" and not args.base:
        parser.error("changed mode requires --base")

    config = (ROOT / ".markdownlint-cli2.jsonc").read_text()
    config = re.sub(r"(?m)^\s*//.*$", "", config)
    patterns = json.loads(config)["ignores"]
    command = ["git", "ls-files", "-z", "--", "*.md"]
    if args.mode == "changed":
        command = ["git", "diff", "--name-only", "-z", "--diff-filter=ACMR",
                   args.base, args.head, "--", "*.md"]
    names = subprocess.check_output(command, cwd=ROOT).decode().split("\0")
    files = [name for name in names if name and not ignored(name, patterns)]
    if not files:
        if args.mode == "changed":
            print("No eligible Markdown files changed; lint skipped.")
            return 0
        print("ERROR: full debt scan selected zero Markdown files", file=sys.stderr)
        return 1

    package = ROOT / "node_modules/markdownlint-cli2/package.json"
    binary = ROOT / "node_modules/.bin/markdownlint-cli2"
    if not package.exists() or json.loads(package.read_text())["version"] != VERSION or not binary.exists():
        print(f"ERROR: install markdownlint-cli2@{VERSION} locally", file=sys.stderr)
        return 1
    # A tracked filename must not be interpreted as a glob or an option.
    globs = ["./" + re.sub(r"([*?\[\]{}!()\\])", r"\\\1", name) for name in files]
    result = subprocess.run([str(binary), *globs], cwd=ROOT, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(result.stdout, end="")
    count = re.search(r"(?m)^Linting: (\d+) file\(s\)\s*$", result.stdout)
    if not count or int(count.group(1)) != len(files):
        print(f"ERROR: expected {len(files)} files; linter count missing or different", file=sys.stderr)
        return 1
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
