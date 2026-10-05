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


# ── Verifier gate on direct delegate (clients can skip solve) ────────────────

def _task_with(server, stage_outputs):
    """Persist a task whose stage_outputs we control, bypassing solve."""
    state = {"task_id": "t1", "status": "running", "stage_outputs": stage_outputs}
    asyncio.run(server.state.set_task_state("t1", state))
    return "t1"


def _crystallize(server, task_id=None):
    args = {"stage": "crystallization", "input": {}}
    if task_id:
        args["task_id"] = task_id
    return call(server, "oramasys_delegate", args)["result"]


def test_delegate_crystallization_without_task_id_is_rejected_and_executor_not_called():
    executor = FakeExecutor()
    server = OramasysMCPServer(executor=executor)
    result = _crystallize(server)
    assert result["status"] == "rejected" and result["isError"] is True
    assert executor.calls == []
    assert asyncio.run(server.state.list_keys("task:")) == []


def test_delegate_crystallization_with_missing_verification_is_rejected():
    executor = FakeExecutor()
    server = OramasysMCPServer(executor=executor)
    task_id = _task_with(server, {"context": {"status": "done", "output": "c"}})
    result = _crystallize(server, task_id)
    assert result["status"] == "rejected" and "no completed verification" in result["error"]
    assert executor.calls == []
    assert "crystallization" not in asyncio.run(server.state.get_task_state(task_id))["stage_outputs"]


@pytest.mark.parametrize("verdict", ["FAIL", "WARNING", None])
def test_delegate_crystallization_with_non_pass_verdict_is_rejected(verdict):
    executor = FakeExecutor()
    server = OramasysMCPServer(executor=executor)
    task_id = _task_with(server, {"verification": {"status": "done", "output": "v", "verdict": verdict}})
    result = _crystallize(server, task_id)
    assert result["status"] == "rejected" and result["isError"] is True
    assert executor.calls == []


def test_delegate_crystallization_rejects_unknown_task_and_unfinished_verification():
    server = OramasysMCPServer(executor=FakeExecutor())
    assert _crystallize(server, "nope")["status"] == "rejected"
    task_id = _task_with(server, {"verification": {"status": "failed", "error": "RuntimeError"}})
    assert _crystallize(server, task_id)["status"] == "rejected"


def test_delegate_crystallization_runs_after_pass_including_delegated_verification():
    executor = FakeExecutor(verdict="PASS")
    server = OramasysMCPServer(executor=executor)
    task_id = _task_with(server, {})
    # Verification delegated directly must land in the state the gate reads.
    assert call(server, "oramasys_delegate",
                {"stage": "verification", "task_id": task_id, "input": {}})["result"]["status"] == "done"
    result = _crystallize(server, task_id)
    assert result["status"] == "done" and result["isError"] is False
    assert [c[0] for c in executor.calls] == ["verification", "crystallization"]


def test_later_failing_verification_supersedes_an_earlier_pass():
    server = OramasysMCPServer(executor=FakeExecutor(verdict="FAIL"))
    task_id = _task_with(server, {"verification": {"status": "done", "output": "v", "verdict": "PASS"}})
    call(server, "oramasys_delegate", {"stage": "verification", "task_id": task_id, "input": {}})
    assert _crystallize(server, task_id)["status"] == "rejected"


def test_rerunning_an_upstream_stage_invalidates_a_stale_pass():
    """A PASS verifies specific outputs; replacing one of them must revoke the PASS."""
    executor = FakeExecutor(verdict="PASS")
    server = OramasysMCPServer(executor=executor)
    task_id = _task_with(server, {"verification": {"status": "done", "output": "v", "verdict": "PASS"}})
    call(server, "oramasys_delegate", {"stage": "execution", "task_id": task_id, "input": {}})
    outputs = asyncio.run(server.state.get_task_state(task_id))["stage_outputs"]
    assert "verification" not in outputs and outputs["execution"]["status"] == "done"
    assert _crystallize(server, task_id)["status"] == "rejected"
    assert "crystallization" not in [c[0] for c in executor.calls]


def test_solve_and_delegate_share_one_gate():
    """solve rejects through the same gate (stage reported is the blocked crystallization)."""
    result = call(OramasysMCPServer(executor=FakeExecutor(verdict="WARNING")),
                  "oramasys_solve", {"task": "t"})["result"]
    assert result["status"] == "rejected" and result["stage"] == "crystallization"
    assert "verification verdict WARNING" in result["error"]


class SequencedExecutor:
    """Per-stage delays and a call counter, so overlapping calls interleave deterministically."""

    def __init__(self, delays):
        self.delays, self.count = delays, 0

    async def run_stage(self, stage, task, prior):
        self.count += 1
        n = self.count
        await asyncio.sleep(self.delays.get(stage.value, 0))
        out = {"output": f"{stage.value}-{n}", "model_used": "fake"}
        if stage.value == "verification":
            out["verdict"] = "PASS"
        return out


def test_overlapping_delegates_on_one_task_never_lose_a_result():
    """A slow verification must not write back a stale snapshot over a newer execution output."""

    async def scenario():
        server = OramasysMCPServer(executor=SequencedExecutor({"verification": 0.05}))
        await server.state.set_task_state(
            "t1", {"task_id": "t1", "stage_outputs": {"execution": {"status": "done", "output": "old"}}})

        def delegate(stage, req_id):
            return server.handle_request({"jsonrpc": "2.0", "id": req_id, "method": "tools/call",
                                          "params": {"name": "oramasys_delegate", "arguments": {
                                              "stage": stage, "task_id": "t1", "input": {}}}})

        verify, execute = await asyncio.gather(delegate("verification", 1), delegate("execution", 2))
        assert verify["result"]["status"] == "done" and execute["result"]["status"] == "done"
        outputs = (await server.state.get_task_state("t1"))["stage_outputs"]
        # Execution reported done, so its output must be what is stored.
        assert outputs["execution"]["output"] == execute["result"]["output"] != "old"
        # Execution ran after verification, so that PASS no longer applies.
        assert "verification" not in outputs

    asyncio.run(scenario())


def test_task_locks_do_not_accumulate():
    server = OramasysMCPServer(executor=FakeExecutor())
    for _ in range(5):
        call(server, "oramasys_solve", {"task": "t"})
    assert len(server._task_locks) == 0
