#!/usr/bin/env python3
"""Sync the vendored copy of the OpenClaw defaults from the live Perpetua-Tools file (stdlib only).

The vendored copy is a stamped duplicate (JSON plus the PT module) that orama falls back to when Perpetua-Tools is not
reachable. A wrong copy would bring back stale routes, so syncing is a HUMAN act:

  --check   read-only: reports "in sync" or shows the diff (exit 0 in sync, 1 differs, 2 cannot compare)
  --apply   needs a real terminal for both input and output, shows the diff, and writes only after the person types
            the exact phrase it prints. Without a terminal it refuses (exit 3); a wrong phrase aborts (exit 4).

There is deliberately no flag, environment variable or option that skips the confirmation. Start-up never calls this
script; it only reports the status through scripts/lib/openclaw_defaults_resolver.py.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _resolver():
    spec = importlib.util.spec_from_file_location("openclaw_defaults_resolver_sync", HERE / "lib" / "openclaw_defaults_resolver.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["openclaw_defaults_resolver_sync"] = mod
    spec.loader.exec_module(mod)
    return mod


def _payload(text: str) -> str:
    obj = json.loads(text)
    obj.pop("_vendor", None)
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _diff(label: str, old: str, new: str, limit: int = 120) -> list[str]:
    lines = list(difflib.unified_diff(old.splitlines(), new.splitlines(), "vendored " + label, "live " + label, lineterm="", n=2))
    return lines[:limit] + (["... (%d more diff lines)" % (len(lines) - limit)] if len(lines) > limit else [])


def _write_bundle(vendored_dir: Path, json_text: str, module_text: str, resolver) -> str:
    """Write both files via a sibling folder, verify them there, then move them into place. Returns '' or a problem."""
    work = vendored_dir.parent / (".openclaw-defaults-sync-%d" % os.getpid())
    work.mkdir(parents=True, exist_ok=True)
    try:
        (work / resolver.JSON_NAME).write_text(json_text, encoding="utf-8")
        (work / resolver.MODULE_NAME).write_text(module_text, encoding="utf-8")
        problem = resolver._gate_vendored(work)[3]
        if problem:
            return problem
        vendored_dir.mkdir(parents=True, exist_ok=True)
        for name in (resolver.MODULE_NAME, resolver.JSON_NAME):
            os.replace(work / name, vendored_dir / name)
        return ""
    finally:
        for leftover in work.glob("*"):
            leftover.unlink()
        work.rmdir()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync the vendored OpenClaw defaults (human-confirmed).")
    parser.add_argument("--pt-root", help="Perpetua-Tools root (default: environment, then known siblings)")
    parser.add_argument("--vendored-dir", help="vendored copy folder")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    resolver = _resolver()
    vendored_dir = Path(args.vendored_dir) if args.vendored_dir else resolver.VENDORED_DIR
    pt_root = Path(args.pt_root).expanduser() if args.pt_root else resolver.find_pt_root()
    live = resolver._live(pt_root)
    if live is None:
        print("cannot sync: Perpetua-Tools is not reachable, so there is nothing to compare with")
        return 2
    live_json, live_module = live
    module = resolver._import(live_module, "perpetua_tools_openclaw_defaults_sync")
    data = module.load(live_json)
    problems = module.validate(data)
    if problems:
        print("refusing: the live Perpetua-Tools defaults are invalid:\n  " + "\n  ".join(problems))
        return 2
    module_text = live_module.read_text(encoding="utf-8")
    new_json = module.vendored_copy(data, now=datetime.now(timezone.utc), module_source=module_text)
    fingerprint = module.fingerprint(data)

    old_json_path, old_module_path = vendored_dir / resolver.JSON_NAME, vendored_dir / resolver.MODULE_NAME
    old_json = old_json_path.read_text(encoding="utf-8") if old_json_path.is_file() else ""
    old_module = old_module_path.read_text(encoding="utf-8") if old_module_path.is_file() else ""
    in_sync = False
    if old_json and old_module == module_text:
        try:
            stamp = json.loads(old_json)["_vendor"]
            in_sync = stamp.get("source_sha256") == fingerprint and stamp.get("module_sha256") == hashlib.sha256(module_text.encode("utf-8")).hexdigest()
        except (ValueError, KeyError, TypeError):
            in_sync = False
    if in_sync:
        print("in sync (fingerprint %s)" % fingerprint[:8])
        return 0

    print("the vendored OpenClaw defaults differ from the live Perpetua-Tools file (live fingerprint %s)" % fingerprint[:8])
    shown = _diff("openclaw-defaults.json", _payload(old_json) if old_json else "", _payload(new_json))
    shown += _diff("openclaw_defaults.py", old_module, module_text)
    print("\n".join(shown) if shown else "(only the stamp differs)")
    if args.check:
        return 1

    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("refusing: syncing the vendored OpenClaw defaults needs a human at a terminal to confirm; use --check to see the diff")
        return 3
    phrase = "SYNC OPENCLAW DEFAULTS %s" % fingerprint[:8]
    print("\nType the phrase `%s` to apply this change; anything else aborts." % phrase)
    try:
        answer = input("> ").strip()
    except EOFError:
        answer = ""
    if answer != phrase:
        print("aborted: nothing was written")
        return 4
    problem = _write_bundle(vendored_dir, new_json, module_text, resolver)
    if problem:
        print("failed: the new copy did not verify (%s); nothing was replaced" % problem)
        return 5
    print("synced: the vendored OpenClaw defaults now match the live file (fingerprint %s)" % fingerprint[:8])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
