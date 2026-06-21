#!/usr/bin/env python3
"""sync_version.py — propagate the version from src/orama_system/_version.py
to every canonical doc/config surface.

Usage:
    python3 scripts/sync_version.py           # writes all surfaces
    python3 scripts/sync_version.py --dry-run # prints diff, writes nothing
    python3 scripts/sync_version.py --check   # exits 1 if any surface is stale

Historical docs (CHANGELOG, LESSONS, docs/plans/, docs/superpowers/specs/) are
never touched. AlphaClaw / third-party runtime versions are never touched.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

ROOT  = Path(__file__).parent.parent
VFILE = ROOT / "src" / "orama_system" / "_version.py"

def _load_version() -> str:
    ns: dict = {}
    exec(VFILE.read_text(encoding="utf-8"), ns)
    return ns["__version__"]

VERSION = _load_version()

# ── Canonical surfaces ──────────────────────────────────────────────────────
# Each entry: (path, transform_fn)
# transform_fn(text, ver) → new_text

def _re_replace(pattern: str, repl_template: str):
    """Factory: regex replace with {ver} in repl_template."""
    def fn(text: str, ver: str) -> str:
        return re.sub(pattern, repl_template.replace("{ver}", ver), text)
    return fn

def _json_key(key: str):
    def fn(text: str, ver: str) -> str:
        data = json.loads(text)
        data[key] = ver
        return json.dumps(data, indent=2) + "\n"
    return fn

SURFACES: list[tuple[Path, ...]] = [
    # (path, transform_fn)
    (
        ROOT / "bin" / "orama-system" / "SKILL.md",
        _re_replace(r'^(version:\s*)[\d.]+', r'\g<1>{ver}', ),
    ),
    (
        ROOT / "CLAUDE.md",
        _re_replace(r'@diazmelgarejo/orama-system@[\d.]+', r'@diazmelgarejo/orama-system@{ver}'),
    ),
    (
        ROOT / "README.md",
        _re_replace(r'version-[\d.]+-orange', r'version-{ver}-orange'),
    ),
    (
        ROOT / "SKILL.md",
        _re_replace(
            r'Version registry: \*\*current version is `[\d.]+`\*\*\.',
            r'Version registry: **current version is `{ver}`**.',
        ),
    ),
    (
        ROOT / "docs" / "PERPLEXITY_BRIDGE.md",
        _re_replace(r'^## Version [\d.]+', r'## Version {ver}'),
    ),
    (
        ROOT / "docs" / "SYNC_ANALYSIS.md",
        lambda t, v: (
            t.replace(
                re.search(r'orama-system v[\d.]+ · PT v[\d.]+', t).group() if re.search(r'orama-system v[\d.]+ · PT v[\d.]+', t) else '__NOMATCH__',
                f'orama-system v{v} · PT v{v}'
            )
            .replace(
                re.search(r'Both at v[\d.]+', t).group() if re.search(r'Both at v[\d.]+', t) else '__NOMATCH__',
                f'Both at v{v}'
            )
            .replace(
                re.search(r'PERPLEXITY_BRIDGE\.md aligned to v[\d.]+', t).group() if re.search(r'PERPLEXITY_BRIDGE\.md aligned to v[\d.]+', t) else '__NOMATCH__',
                f'PERPLEXITY_BRIDGE.md aligned to v{v}'
            )
        ),
    ),
    (
        ROOT / "src" / "orama_system" / "portal_server.py",
        _re_replace(r'^(VERSION\s*=\s*)"[\d.]+"', r'\g<1>"{ver}"'),
    ),
    (
        ROOT / "bin" / "config" / "agent_registry.json",
        _json_key("version"),
    ),
    (
        ROOT / "bin" / "orama-system" / "config" / "agent_registry.json",
        _json_key("version"),
    ),
    (
        ROOT / "bin" / "orama-system" / "config" / "routing_rules.json",
        _json_key("version"),
    ),
    (
        ROOT / "agent" / "install.json",
        lambda t, v: re.sub(r'"agentic_stack_version":\s*"[\d.]+"',
                            f'"agentic_stack_version": "{v}"', t),
    ),
    (
        ROOT / "platform" / "windows" / "install.ps1",
        _re_replace(r"(version\s*=\s*')[^']+(')", r"\g<1>{ver}\g<2>"),
    ),
    (
        ROOT / "docs" / "wiki" / "06-multi-agent-collab.md",
        lambda t, v: re.sub(
            r'(\*\*Current version:\s*`)[\d.]+(`\*\*)',
            lambda m: f'{m.group(1)}{v}{m.group(2)}', t
        ),
    ),
    (
        ROOT / "bin" / "orama-system" / "afrp" / "README.md",
        _re_replace(r'(\*\*Version:\*\*\s*)[\d.]+', r'\g<1>{ver}'),
    ),
    (
        ROOT / "bin" / "orama-system" / "skills" / "self-discovery" / "SKILL.md",
        _re_replace(r'^(version:\s*)[\d.]+', r'\g<1>{ver}'),
    ),
]

# Per-agent agent.md files
for agent_dir in (ROOT / "bin" / "agents").iterdir():
    agent_md = agent_dir / "agent.md"
    if agent_md.exists():
        SURFACES.append((
            agent_md,
            _re_replace(r'^(version:\s*)[\d.]+', r'\g<1>{ver}'),
        ))

# Python module docstrings (Version: X.Y.Z.W)
for py_file in list((ROOT / "bin" / "mcp_servers").glob("*.py")) + \
               list((ROOT / "bin" / "shared").glob("*.py")):
    SURFACES.append((
        py_file,
        _re_replace(r'(Version:\s*)[\d.]+(\s*\|)', r'\g<1>{ver}\g<2>'),
    ))

# ── Main ──────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check",   action="store_true")
    args = ap.parse_args()

    stale, changed = [], []
    for entry in SURFACES:
        path, transform = entry
        if not path.exists():
            print(f"  SKIP (missing): {path.relative_to(ROOT)}")
            continue
        old = path.read_text(encoding="utf-8")
        new = transform(old, VERSION)
        if new == old:
            continue
        stale.append(path)
        if args.dry_run or args.check:
            print(f"  STALE: {path.relative_to(ROOT)}")
        else:
            path.write_text(new, encoding="utf-8")
            changed.append(path)
            print(f"  updated: {path.relative_to(ROOT)}")

    print(f"\nVersion: {VERSION}  |  stale={len(stale)}  updated={len(changed)}")
    if args.check and stale:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
