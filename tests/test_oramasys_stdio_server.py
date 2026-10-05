"""Fail-closed completion contract for the oramasys stdio MCP server.

solve/delegate must report "done" only after a StageExecutor produced real output; with no
executor they return an error result and persist nothing.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from bin.mcp_servers import oramasys_orchestration_server as srv  # noqa: E402
from bin.mcp_servers.oramasys_orchestration_server import (  # noqa: E402
    OramasysMCPServer,
    load_executor_from_env,
)


class FakeExecutor:
    """Deterministic test double that records calls; verdict/failure injectable."""

    def __init__(self, verdict="PASS", fail_stage=None, delay=0.0):
        self.verdict, self.fail_stage, self.delay, self.calls = verdict, fail_stage, delay, []

    async def run_stage(self, stage, task, prior):
        self.calls.append((stage.value, dict(prior)))
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail_stage == stage.value:
            raise RuntimeError("boom")
        out = {"output": f"{stage.value}-out", "model_used": "fake-model"}
        if stage.value == "verification":
            out["verdict"] = self.verdict
        return out


def call(server, name, arguments, req_id=1):
    request = {"jsonrpc": "2.0", "id": req_id, "method": "tools/call",
               "params": {"name": name, "arguments": arguments}}
    return asyncio.run(server.handle_request(request))


def test_solve_without_executor_fails_closed_and_persists_nothing():
    server = OramasysMCPServer()
    result = call(server, "oramasys_solve", {"task": "do it"})["result"]
    assert result["isError"] is True
    assert result["status"] == "unavailable"
    assert result["status"] not in {"started", "queued", "done"}
    assert asyncio.run(server.state.list_keys("task:")) == []


def test_delegate_without_executor_fails_closed():
    result = call(OramasysMCPServer(), "oramasys_delegate",
                  {"stage": "context", "input": {}})["result"]
    assert result["isError"] is True and result["status"] == "unavailable"


def test_solve_completes_all_stages_and_keeps_pt_client_contract():
    executor = FakeExecutor()
    server = OramasysMCPServer(executor=executor)
    result = call(server, "oramasys_solve", {"task": "do it"})["result"]
    # Perpetua-Tools orama_mcp_client.call_solve reads these top-level fields.
    assert result["status"] == "done" and result["result"] == "crystallization-out"
    assert result["model_used"] == "fake-model" and result["isError"] is False
    assert [c[0] for c in executor.calls] == srv.SOLVE_ORDER_VALUES
    assert result["content"][0]["type"] == "text"
    state = call(server, "oramasys_status", {"task_id": result["task_id"]})["result"]
    assert state["status"] == "done" and state["current_stage"] == "done"
    assert "verification" in state["stage_outputs"]


def test_unapproved_verification_blocks_crystallization():
    executor = FakeExecutor(verdict="FAIL")
    server = OramasysMCPServer(executor=executor)
    result = call(server, "oramasys_solve", {"task": "t"})["result"]
    assert result["isError"] is True and result["status"] == "rejected"
    assert "crystallization" not in [c[0] for c in executor.calls]
    state = call(server, "oramasys_status", {"task_id": result["task_id"]})["result"]
    assert state["status"] == "failed"


def test_stage_failure_and_timeout_are_reported_not_hidden():
    failed = call(OramasysMCPServer(executor=FakeExecutor(fail_stage="execution")),
                  "oramasys_solve", {"task": "t"})["result"]
    assert failed["status"] == "failed" and failed["stage"] == "execution" and failed["isError"]
    slow = call(OramasysMCPServer(executor=FakeExecutor(delay=0.5), stage_timeout_s=0.05),
                "oramasys_solve", {"task": "t"})["result"]
    assert slow["status"] == "timeout" and slow["isError"]


def test_delegate_returns_real_output_and_persists_it():
    server = OramasysMCPServer(executor=FakeExecutor())
    solved = call(server, "oramasys_solve", {"task": "t"})["result"]
    result = call(server, "oramasys_delegate",
                  {"stage": "context", "task_id": solved["task_id"], "input": {"q": 1}})["result"]
    assert result["status"] == "done" and result["output"] == "context_immersion-out"
    missing = call(server, "oramasys_delegate",
                   {"stage": "context", "task_id": "nope", "input": {}})["result"]
    assert missing["status"] == "rejected" and missing["isError"]


def test_invalid_params_are_jsonrpc_errors():
    server = OramasysMCPServer(executor=FakeExecutor())
    assert call(server, "oramasys_solve", {"task": ""})["error"]["code"] == -32602
    assert call(server, "oramasys_solve", {"task": "t", "optimize_for": "x"})["error"]["code"] == -32602
    assert call(server, "oramasys_delegate", {"stage": "bogus", "input": {}})["error"]["code"] == -32602
    assert call(server, "no_such_tool", {})["error"]["code"] == -32602
    status = call(server, "oramasys_status", {"task_id": "missing"})["result"]
    assert status["isError"] is True and status["status"] == "not_found"


def test_notifications_get_no_response_and_unknown_methods_error():
    server = OramasysMCPServer()
    assert asyncio.run(server.handle_request(
        {"jsonrpc": "2.0", "method": "notifications/initialized"})) is None
    assert asyncio.run(server.handle_request({"jsonrpc": "2.0", "id": 3, "method": "nope"}))[
        "error"]["code"] == -32601
    assert asyncio.run(server.handle_request({"jsonrpc": "2.0", "id": 4, "method": "ping"}))[
        "result"] == {}


def test_executor_env_loader_rejects_malformed_specs_and_defaults_to_none():
    assert load_executor_from_env({}) is None
    with pytest.raises(ValueError):
        load_executor_from_env({"ORAMASYS_STAGE_EXECUTOR": "os.system:exit; rm -rf"})


def test_stdio_process_is_clean_and_fails_closed_end_to_end():
    lines = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "oramasys_solve", "arguments": {"task": "x"}}},
    ]
    proc = subprocess.run(
        [sys.executable, "-m", "bin.mcp_servers.oramasys_orchestration_server"],
        input="\n".join(json.dumps(m) for m in lines) + "\nnot-json\n",
        capture_output=True, text=True, cwd=_ROOT, timeout=30,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(_ROOT)},
    )
    out = [json.loads(line) for line in proc.stdout.splitlines()]  # stdout is pure JSON-RPC
    by_id = {m["id"]: m for m in out}
    assert by_id[1]["result"]["capabilities"] == {"tools": {}}
    assert by_id[2]["result"]["status"] == "unavailable" and by_id[2]["result"]["isError"]
    assert by_id[None]["error"]["code"] == -32700
    assert len(out) == 3  # the notification produced no response
