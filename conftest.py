"""Guard for every test directory: no test process may reach a local model engine.

A test that talked to Ollama or LM Studio would load a model on the machine running the suite, with nobody's
approval. The audit hook below cannot be removed or monkeypatched away for the life of the process.
Perpetua-Tools carries the same guard; its one-model gate covers child processes.
"""
from __future__ import annotations

import errno
import sys

_ENGINE_PORTS = frozenset({11434, 1234})  # Ollama and LM Studio


def _refuse_engine_connections(event: str, args: tuple) -> None:
    if event != "socket.connect":
        return
    address = args[1]
    if isinstance(address, tuple) and len(address) >= 2 and address[1] in _ENGINE_PORTS:
        raise ConnectionRefusedError(errno.ECONNREFUSED, "tests may not reach a local model engine")


sys.addaudithook(_refuse_engine_connections)
