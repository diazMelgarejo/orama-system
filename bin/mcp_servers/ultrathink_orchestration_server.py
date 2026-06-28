#!/usr/bin/env python3
"""Compatibility wrapper for the renamed oramasys MCP server module."""
from __future__ import annotations

from bin.mcp_servers.oramasys_orchestration_server import *  # noqa: F401,F403


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_stdio_server())
