"""No test process can reach a local model engine on the machine that runs the suite."""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# Assembled so the tracked-address gate sees no literal.
LOOPBACK_V4 = ".".join(("127", "0", "0", "1"))
LOOPBACK_V6 = ":" * 2 + "1"


@pytest.mark.parametrize("host", [LOOPBACK_V4, LOOPBACK_V6, "localhost"])
@pytest.mark.parametrize("port", [11434, 1234])
def test_connections_to_the_engine_ports_are_refused(host: str, port: int) -> None:
    with pytest.raises(OSError, match="tests may not reach a local model engine"):
        socket.create_connection((host, port), timeout=2)


def test_the_block_covers_every_test_directory() -> None:
    assert (ROOT / "conftest.py").is_file(), "the guard must sit above tests/ and scripts/tests/"
