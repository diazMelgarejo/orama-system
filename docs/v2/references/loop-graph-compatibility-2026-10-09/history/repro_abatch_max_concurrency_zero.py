"""Repro: LangChainRunnableAdapter.abatch hangs when config max_concurrency == 0.
Run from a perpetua-core checkout:  python -I repro_abatch_max_concurrency_zero.py
Observed 2026-10-09 on perpetua-core main c0795bc: prints HANG for 0; ValueError for -1."""
import sys, asyncio; sys.path.insert(0, "src")
from perpetua_core.graph.engine import MiniGraph, START, END
from perpetua_core.graph.adapters.langchain_adapter import LangChainRunnableAdapter
g = MiniGraph(); g.add_node("a", lambda s: {}); g.add_edge(START, "a"); g.add_edge("a", END)
r = LangChainRunnableAdapter(g)
async def main():
    try:
        await asyncio.wait_for(r.abatch([{"session_id": "x"}], config={"max_concurrency": 0}), 2)
        print("completed")
    except asyncio.TimeoutError:
        print("HANG with max_concurrency=0")
    try:
        await r.abatch([{"session_id": "x"}], config={"max_concurrency": -1}); print("neg ok")
    except Exception as e:
        print("neg:", type(e).__name__, e)
asyncio.run(main())
