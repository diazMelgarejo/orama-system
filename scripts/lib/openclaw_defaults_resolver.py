#!/usr/bin/env python3
"""Resolve the OpenClaw defaults for orama scripts (stdlib only; never writes a config).

Order: (1) the live Perpetua-Tools file (the owner); (2) a stamped vendored copy; (3) only then fail closed.

A vendored copy is a stamped duplicate (JSON plus the PT module), so it can go stale. Protections:
  * the stamp holds the source fingerprint, the source date, the copy date and the module hash;
  * the module and the JSON are verified BEFORE the vendored module is imported: a hand-edited copy is never executed;
  * a copy that differs from the live file, or is old while the live file is unreachable, is reported loudly;
  * syncing the copy is a separate script that needs a human to confirm; this module can only report.

    python3 scripts/lib/openclaw_defaults_resolver.py --status            # start-up report; exit 0 / 1 warnings / 2 closed
    python3 scripts/lib/openclaw_defaults_resolver.py --render-patch --shape entries
    python3 scripts/lib/openclaw_defaults_resolver.py --check ~/.openclaw/openclaw.json
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
VENDORED_DIR = REPO_ROOT / "config" / "vendored" / "openclaw-defaults"
JSON_NAME = "openclaw-defaults.json"
MODULE_NAME = "openclaw_defaults.py"
LIVE_JSON = Path("config") / JSON_NAME
LIVE_MODULE = Path("src") / "perpetua_tools" / MODULE_NAME
PREFIX = "[openclaw-defaults]"


class DefaultsUnavailable(RuntimeError):
    """Neither the live Perpetua-Tools file nor a trustworthy vendored copy is available: fail closed."""


@dataclass(frozen=True)
class Resolution:
    source: str  # "live" or "vendored"
    data: dict[str, Any]
    module: ModuleType
    warnings: tuple[str, ...]
    pt_root: Path | None


def canonical_fingerprint(data: Mapping[str, Any]) -> str:
    """Same canonical form as the PT module, so a vendored copy can be checked BEFORE its module is imported."""
    body = {k: v for k, v in data.items() if k != "_vendor"}
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def find_pt_root(env: Mapping[str, str] | None = None) -> Path | None:
    """Perpetua-Tools root: PERPETUATOOLSROOT, PERPETUA_TOOLS_ROOT, legacy PERPETUA_TOOLS_PATH, then known siblings."""
    env = os.environ if env is None else env
    for name in ("PERPETUATOOLSROOT", "PERPETUA_TOOLS_ROOT", "PERPETUA_TOOLS_PATH"):
        raw = (env.get(name) or "").strip()
        if raw:
            return Path(raw).expanduser()
    for candidate in (
        REPO_ROOT.parent / "perplexity-api" / "Perpetua-Tools",
        REPO_ROOT.parent / "Perpetua-Tools",
        Path.home() / "Perpetua-Tools",
    ):
        if (candidate / LIVE_JSON).is_file():
            return candidate
    return None


def _import(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DefaultsUnavailable("cannot import %s" % path.name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _live(pt_root: Path | None) -> tuple[Path, Path] | None:
    if pt_root is None:
        return None
    json_path, module_path = pt_root / LIVE_JSON, pt_root / LIVE_MODULE
    return (json_path, module_path) if json_path.is_file() and module_path.is_file() else None


def _gate_vendored(vendored_dir: Path) -> tuple[str | None, str | None, dict[str, Any] | None, str]:
    """Verify the vendored files WITHOUT importing the module. Returns (module_text, json_text, data, problem)."""
    json_path, module_path = vendored_dir / JSON_NAME, vendored_dir / MODULE_NAME
    if not json_path.is_file() or not module_path.is_file():
        return None, None, None, "no vendored copy"
    json_text = json_path.read_text(encoding="utf-8")
    module_text = module_path.read_text(encoding="utf-8")
    try:
        data = json.loads(json_text)
        stamp = data["_vendor"]
    except (ValueError, KeyError, TypeError):
        return None, None, None, "the vendored copy has no readable stamp"
    if canonical_fingerprint(data) != stamp.get("source_sha256"):
        return None, None, None, "the vendored OpenClaw defaults were edited by hand (fingerprint mismatch)"
    if hashlib.sha256(module_text.encode("utf-8")).hexdigest() != stamp.get("module_sha256"):
        return None, None, None, "the vendored OpenClaw defaults module was edited by hand (hash mismatch)"
    return module_text, json_text, data, ""


def resolve(
    pt_root: Path | None = None,
    vendored_dir: Path | None = None,
    now: datetime | None = None,
    max_age_days: int = 30,
    env: Mapping[str, str] | None = None,
) -> Resolution:
    now = now or datetime.now(timezone.utc)
    vendored_dir = Path(vendored_dir) if vendored_dir else VENDORED_DIR
    if pt_root is None:
        pt_root = find_pt_root(env)
    warnings: list[str] = []
    gate = _gate_vendored(vendored_dir)
    vendored_ok = not gate[3]

    live = _live(pt_root)
    if live is not None:
        module = _import(live[1], "perpetua_tools_openclaw_defaults_live")
        data = module.load(live[0])
        problems = module.validate(data)
        if not problems:
            if vendored_ok:
                verdict = module.verify_vendored(gate[1], live_fingerprint=module.fingerprint(data), now=now, module_source=gate[0])
                if verdict["status"] != "ok":
                    warnings.append(verdict["message"])
            elif gate[3] != "no vendored copy":
                warnings.append("%s; do not use it, and sync it after a human confirms" % gate[3])
            return Resolution("live", data, module, tuple(warnings), pt_root)
        warnings.append("the live Perpetua-Tools defaults are invalid (%s); falling back to the vendored copy" % problems[0])

    if not vendored_ok:
        why = gate[3]
        raise DefaultsUnavailable(
            "fail closed: no live Perpetua-Tools defaults and %s" % (why if why != "no vendored copy" else "no vendored copy either")
        )
    module = _import(vendored_dir / MODULE_NAME, "openclaw_defaults_vendored")
    verdict = module.verify_vendored(gate[1], live_fingerprint=None, now=now, max_age_days=max_age_days, module_source=gate[0])
    if verdict["status"] not in ("ok",):
        if verdict["status"] == "old":
            warnings.append(verdict["message"])
        else:
            raise DefaultsUnavailable("fail closed: " + verdict["message"])
    return Resolution("vendored", gate[2], module, tuple(warnings), None)


# ------------------------------------------------------------------------------------------------- CLI


def _status(r: Resolution) -> int:
    where = "Perpetua-Tools (live)" if r.source == "live" else "vendored copy (Perpetua-Tools not found)"
    print("%s source=%s %s fingerprint=%s" % (PREFIX, r.source, where, r.module.fingerprint(r.data)[:8]))
    for w in r.warnings:
        print("%s WARN: %s" % (PREFIX, w))
    return 1 if r.warnings else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve the OpenClaw defaults (read-only).")
    parser.add_argument("--pt-root", help="Perpetua-Tools root (default: environment, then known siblings)")
    parser.add_argument("--vendored-dir", help="vendored copy folder (default: config/vendored/openclaw-defaults)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--status", action="store_true")
    mode.add_argument("--render-patch", action="store_true")
    mode.add_argument("--check", metavar="CONFIG")
    parser.add_argument("--shape", choices=("entries", "list"), default="entries")
    args = parser.parse_args(argv)
    try:
        r = resolve(Path(args.pt_root).expanduser() if args.pt_root else None, Path(args.vendored_dir) if args.vendored_dir else None)
    except DefaultsUnavailable as exc:
        print("%s FAIL CLOSED: %s" % (PREFIX, exc))
        return 2
    if args.status:
        return _status(r)
    for w in r.warnings:
        print("%s WARN: %s" % (PREFIX, w), file=sys.stderr)
    if args.render_patch:
        print(json.dumps(r.module.render_patch(r.data, shape=args.shape), indent=2))
        return 0
    with open(args.check, encoding="utf-8") as fh:
        found = r.module.drift(r.data, json.load(fh))
    for item in found:
        print("drift %s: expected %s, actual %s" % (item["path"], json.dumps(item["expected"]), json.dumps(item["actual"])))
    print("no drift" if not found else "%d drift item(s)" % len(found))
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
