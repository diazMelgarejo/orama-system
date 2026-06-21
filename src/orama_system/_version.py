"""Single source of truth for orama-system version.

All runtime code must import from here:
    from orama_system._version import __version__

All documentation must reference pyproject.toml [project] version,
which hatch reads dynamically from this file.

Bump procedure:
    1. Edit __version__ here — nowhere else.
    2. Run: python3 scripts/sync_version.py
    3. Commit all changed files together (see docs/wiki/06-multi-agent-collab.md).
"""

__version__ = "1.1.0.0"
