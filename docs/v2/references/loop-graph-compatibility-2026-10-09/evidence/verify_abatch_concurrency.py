"""Bounded regression smoke against an explicitly selected Core source tree.

python -I verify_abatch_concurrency.py --core-src /checkout/perpetua-core/src
Exit zero only for the corrected contract. This does not prove upstream parity.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys


def main() -> None:
    """Resolve the intended source and fail on hangs or wrong exceptions."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-src", required=True, type=Path)
    args = parser.parse_args()
    source = args.core_src.resolve(strict=True)
    adapter_file = source / "perpetua_core/graph/adapters/langchain_adapter.py"
    if not adapter_file.is_file():
        parser.error("--core-src must contain perpetua_core/graph/adapters/langchain_adapter.py")
    sys.path.insert(0, str(source))
    from perpetua_core.graph.engine import MiniGraph, START, END
    from perpetua_core.graph.adapters.langchain_adapter import LangChainRunnableAdapter
    import perpetua_core.graph.adapters.langchain_adapter as module
    if Path(module.__file__).resolve() != adapter_file:
        raise RuntimeError("loaded Core does not match the requested source")
    graph = MiniGraph().add_node("a", lambda state: {})
    graph.add_edge(START, "a").add_edge("a", END)
    adapter = LangChainRunnableAdapter(graph)

    async def verify() -> None:
        for value in (0, -1, True, False, 1.5, "2"):
            try:
                await asyncio.wait_for(adapter.abatch(
                    [{"session_id": "evidence"}], {"max_concurrency": value},
                ), timeout=2)
            except ValueError as error:
                assert str(error) == "max_concurrency must be a positive integer"
            else:
                raise AssertionError(f"invalid limit accepted: {value!r}")
        result = await asyncio.wait_for(adapter.abatch(
            [{"session_id": "evidence"}], {"max_concurrency": 1},
        ), timeout=2)
        assert result[0].session_id == "evidence"

    asyncio.run(verify())
    print(json.dumps({"status": "pass", "checks": 7,
                      "adapter_sha256": hashlib.sha256(adapter_file.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
