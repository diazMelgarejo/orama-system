#!/usr/bin/env python3
"""
oramasys_orchestration_server.py
====================================
MCP Server: oramasys Multi-Agent Orchestration
Version: 1.1.1.0 | License: Apache 2.0

Exposes the oramasys agent network as MCP tools.
Compatible with: Clawdbot, MoltBot, OpenClaw, Claude Code MCP client.

Usage:
    python oramasys_orchestration_server.py        # stdio transport

Completion contract (fail closed):
    oramasys_solve and oramasys_delegate report "done" only after a configured
    StageExecutor actually ran the stage(s) and returned output. With no executor
    they return an MCP error result (isError=true, status="unavailable") and create
    no task record. They never report "started"/"queued" as if work were finished.
    Executors are injected (OramasysMCPServer(executor=...)) or loaded from
    ORAMASYS_STAGE_EXECUTOR="package.module:factory" (operator-controlled).

Tools exposed:
    - oramasys_solve    : Run full 5-stage process
    - oramasys_delegate : Delegate to a specific stage agent
    - oramasys_status   : Get task status from state store
    - oramasys_lessons  : Query the lessons database

Integration with OpenClaw (from openclaw.json):
    {
      "agents": [{
        "id": "oramasys-orchestrator",
        "mcp_url": "http://localhost:8080/mcp",
        "tools": ["oramasys_solve", "oramasys_delegate"]
      }]
    }
"""
import asyncio
import importlib
import json
import logging
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Optional, Protocol

# Add shared to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))
from oramasys_core import TaskState, Stage, OptimizeFor, Verdict, utc_now_iso
from state_manager import StateManager
from message_bus import MessageBus

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ── Tool schemas ─────────────────────────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "name": "oramasys_solve",
        "description": (
            "Run the complete oramasys 5-stage process to completion through the configured "
            "stage executor, or fail closed (isError, status unavailable/failed/timeout/"
            "rejected). Crystallization is blocked unless verification passes. Returns "
            "status 'done' only when real output exists."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The problem or task to solve"
                },
                "optimize_for": {
                    "type": "string",
                    "enum": ["reliability", "creativity", "speed"],
                    "default": "reliability"
                },
                "context": {
                    "type": "object",
                    "description": "Additional context (optional)",
                    "default": {}
                }
            },
            "required": ["task"]
        }
    },
    {
        "name": "oramasys_delegate",
        "description": (
            "Run one oramasys stage through the configured stage executor and return its "
            "real output, or fail closed. Never reports queued/started work as finished. "
            "Crystallization requires a task_id whose verification verdict is PASS."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "stage": {
                    "type": "string",
                    "enum": ["context", "architecture", "refinement",
                             "execution", "verification", "crystallization"]
                },
                "task_id": {"type": "string"},
                "input": {"type": "object"}
            },
            "required": ["stage", "input"]
        }
    },
    {
        "name": "oramasys_status",
        "description": "Get the current status of a running oramasys task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID returned by oramasys_solve"}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "oramasys_lessons",
        "description": "Query the self-improvement lessons database.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Filter by domain (optional)"},
                "limit":  {"type": "integer", "default": 10}
            }
        }
    }
]


# ── Stage execution contract ─────────────────────────────────────────────────

STAGE_BY_NAME = {
    "context":         Stage.CONTEXT,
    "architecture":    Stage.ARCHITECTURE,
    "refinement":      Stage.REFINEMENT,
    "execution":       Stage.EXECUTION,
    "verification":    Stage.VERIFICATION,
    "crystallization": Stage.CRYSTALLIZATION,
}
SOLVE_ORDER = ["context", "architecture", "refinement", "execution",
               "verification", "crystallization"]
SOLVE_ORDER_VALUES = [STAGE_BY_NAME[n].value for n in SOLVE_ORDER]
MAX_TASK_CHARS = 32_768
DEFAULT_STAGE_TIMEOUT_S = 600.0
_FACTORY = re.compile(r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$")


class StageExecutor(Protocol):
    """Runs one stage for real and returns its output.

    Return a dict with ``output`` (the stage result) and optionally ``model_used``.
    The verification stage must also return ``verdict`` ("PASS" approves crystallization).
    Raise to report failure; never return a placeholder.
    """

    async def run_stage(self, stage: Stage, task: dict, prior: dict) -> dict: ...


class ExecutorUnavailable(RuntimeError):
    """No stage executor is configured, so no work can be completed."""


def load_executor_from_env(environ=os.environ) -> Optional[StageExecutor]:
    """Load ORAMASYS_STAGE_EXECUTOR ("package.module:factory") or return None."""
    spec = environ.get("ORAMASYS_STAGE_EXECUTOR", "").strip()
    if not spec:
        return None
    if not _FACTORY.match(spec):
        raise ValueError("ORAMASYS_STAGE_EXECUTOR must look like package.module:factory")
    module_name, factory_name = spec.split(":")
    return getattr(importlib.import_module(module_name), factory_name)()


def _stage_timeout(environ=os.environ) -> float:
    try:
        value = float(environ.get("ORAMASYS_STAGE_TIMEOUT_S", DEFAULT_STAGE_TIMEOUT_S))
    except ValueError:
        return DEFAULT_STAGE_TIMEOUT_S
    return min(max(value, 1.0), 3600.0)


class InvalidParams(ValueError):
    """Caller error → JSON-RPC -32602."""


def _tool_result(payload: dict, is_error: bool) -> dict:
    """Wrap a payload as an MCP tool result, keeping its fields at top level.

    Perpetua-Tools' client reads ``status``/``result`` at the top level, so the
    payload stays flat alongside MCP ``content``/``structuredContent``.
    """
    return {
        **payload,
        "content": [{"type": "text", "text": json.dumps(payload, default=str)}],
        "structuredContent": payload,
        "isError": is_error,
    }


# ── Server implementation ────────────────────────────────────────────────────

class OramasysMCPServer:
    """MCP server exposing the oramasys agent network over JSON-RPC.

    Work only completes through a StageExecutor. Without one, solve/delegate fail
    closed instead of recording a task nobody will run.
    """

    def __init__(self, executor: Optional[StageExecutor] = None,
                 state: Optional[StateManager] = None,
                 stage_timeout_s: Optional[float] = None):
        self.state = state or StateManager()
        self.bus = MessageBus()
        self.executor = executor
        self.stage_timeout_s = stage_timeout_s or _stage_timeout()

    async def handle_request(self, request: Any) -> Optional[dict]:
        """Dispatch one JSON-RPC message. Notifications (no id) return None."""
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
            return self._error(None, -32600, "Invalid Request")
        method = request.get("method", "")
        params = request.get("params") or {}
        req_id = request.get("id")
        is_notification = "id" not in request
        if not isinstance(method, str) or not isinstance(params, dict):
            return None if is_notification else self._error(req_id, -32600, "Invalid Request")

        try:
            if method == "initialize":
                result = await self._initialize(params)
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": TOOL_SCHEMAS}
            elif method == "tools/call":
                if not isinstance(params.get("name"), str):
                    raise InvalidParams("tools/call requires a tool name")
                arguments = params.get("arguments") or {}
                if not isinstance(arguments, dict):
                    raise InvalidParams("arguments must be an object")
                result = await self._call_tool(params["name"], arguments)
            elif is_notification:
                return None  # e.g. notifications/initialized: no response, no side effect
            else:
                return self._error(req_id, -32601, f"Method not found: {method}")
            return None if is_notification else {"jsonrpc": "2.0", "id": req_id, "result": result}
        except InvalidParams as e:
            return None if is_notification else self._error(req_id, -32602, str(e))
        except Exception:
            logger.exception("Error handling %s", method)
            return None if is_notification else self._error(req_id, -32603, "Internal error")

    async def _initialize(self, params: dict) -> dict:
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "oramasys-orchestration-server", "version": "2.0.0"},
        }

    async def _call_tool(self, name: str, arguments: dict) -> dict:
        """Route a tool call. Tool failures are results (isError), not JSON-RPC errors."""
        handlers = {
            "oramasys_solve": self._solve,
            "oramasys_delegate": self._delegate,
            "oramasys_status": self._status,
            "oramasys_lessons": self._lessons,
        }
        if name not in handlers:
            raise InvalidParams(f"Unknown tool: {name}")
        return await handlers[name](arguments)

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _unavailable(self, tool: str) -> dict:
        return _tool_result({
            "status": "unavailable",
            "error": (f"{tool} cannot complete work: no stage executor is configured. "
                      "Nothing was started or queued. Set ORAMASYS_STAGE_EXECUTOR "
                      "(package.module:factory) or use the HTTP bridge."),
        }, True)

    async def _run_stage(self, stage_name: str, task: dict, prior: dict) -> dict:
        """Run one stage via the executor with a deadline; return validated output."""
        if self.executor is None:
            raise ExecutorUnavailable("no stage executor configured")
        stage = STAGE_BY_NAME[stage_name]
        result = await asyncio.wait_for(
            self.executor.run_stage(stage, task, prior), timeout=self.stage_timeout_s)
        if not isinstance(result, dict) or "output" not in result:
            raise RuntimeError("executor returned no output")
        if stage is Stage.VERIFICATION and result.get("verdict") not in {v.value for v in Verdict}:
            raise RuntimeError("verification stage returned no verdict")
        return result

    def _failure(self, status: str, stage_name: str, error: str, **extra: Any) -> dict:
        return _tool_result({"status": status, "stage": stage_name, "error": error, **extra}, True)

    async def _solve(self, args: dict) -> dict:
        """Run the full pipeline to completion, or fail closed. Never reports 'started'."""
        task = args.get("task")
        if not isinstance(task, str) or not task.strip() or len(task) > MAX_TASK_CHARS:
            raise InvalidParams(f"task must be a non-empty string of at most {MAX_TASK_CHARS} characters")
        optimize_for = args.get("optimize_for", "reliability")
        if optimize_for not in {o.value for o in OptimizeFor}:
            raise InvalidParams("optimize_for must be reliability, creativity or speed")
        context = args.get("context", {})
        if not isinstance(context, dict):
            raise InvalidParams("context must be an object")
        if self.executor is None:
            return self._unavailable("oramasys_solve")  # no task record is created

        started = time.monotonic()
        task_id = str(uuid.uuid4())
        state = TaskState(task_id=task_id, task_description=task,
                          optimize_for=OptimizeFor(optimize_for))
        envelope = {"task": task, "optimize_for": optimize_for, "context": context}

        async def persist(status: str) -> None:
            await self.state.set_task_state(task_id, {**state.to_dict(), "status": status})

        await persist("running")
        models: list[str] = []
        for name in SOLVE_ORDER:
            state.current_stage = STAGE_BY_NAME[name]
            await persist("running")
            try:
                result = await self._run_stage(name, envelope, dict(state.stage_outputs))
            except asyncio.TimeoutError:
                state.stage_outputs[name] = {"status": "timeout"}
                await persist("failed")
                return self._failure("timeout", name, f"stage exceeded {self.stage_timeout_s:g}s",
                                     task_id=task_id)
            except Exception as e:
                logger.warning("Stage %s failed for %s: %s", name, task_id, e)
                state.stage_outputs[name] = {"status": "failed", "error": type(e).__name__}
                await persist("failed")
                return self._failure("failed", name, f"{type(e).__name__}: {e}"[:500], task_id=task_id)
            state.stage_outputs[name] = {"status": "done", **result}
            if result.get("model_used"):
                models.append(str(result["model_used"]))
            # Verifier gate: crystallization is blocked without an approved verification.
            if name == "verification" and result["verdict"] != Verdict.PASS.value:
                await persist("failed")
                return self._failure("rejected", name, f"verification verdict {result['verdict']}",
                                     task_id=task_id)

        state.current_stage = Stage.DONE
        state.completed_at = utc_now_iso()
        await persist("done")
        crystallized = state.stage_outputs["crystallization"]["output"]
        return _tool_result({
            "task_id": task_id,
            "status": "done",
            "result": crystallized,
            "stages": {n: state.stage_outputs[n]["output"] for n in SOLVE_ORDER},
            "model_used": ",".join(dict.fromkeys(models)) or "unknown",
            "execution_time_ms": int((time.monotonic() - started) * 1000),
        }, False)

    @staticmethod
    def _verifier_gate(task_state: Optional[dict]) -> Optional[str]:
        """Return why crystallization is blocked, or None when verification PASSED.

        Single gate shared by solve and delegate: clients can call delegate directly, so
        the check cannot live only in the solve loop.
        """
        if not task_state:
            return "crystallization requires an existing task_id with a verification result"
        verification = (task_state.get("stage_outputs") or {}).get("verification")
        if not isinstance(verification, dict) or verification.get("status") != "done":
            return "crystallization blocked: no completed verification for this task"
        if verification.get("verdict") != Verdict.PASS.value:
            return f"crystallization blocked: verification verdict {verification.get('verdict')}"
        return None

    async def _delegate(self, args: dict) -> dict:
        """Run one stage via the executor and return its real output, or fail closed."""
        stage_name = args.get("stage")
        if stage_name not in STAGE_BY_NAME:
            raise InvalidParams(f"stage must be one of {sorted(STAGE_BY_NAME)}")
        payload = args.get("input")
        if not isinstance(payload, dict):
            raise InvalidParams("input must be an object")
        task_id = args.get("task_id")
        if task_id is not None and not isinstance(task_id, str):
            raise InvalidParams("task_id must be a string")
        existing = await self.state.get_task_state(task_id) if task_id else None
        if task_id and not existing:
            return self._failure("rejected", stage_name, f"Task {task_id} not found")
        if stage_name == "crystallization":
            reason = self._verifier_gate(existing)
            if reason:  # rejected before any executor call; nothing is persisted
                return self._failure("rejected", stage_name, reason, task_id=task_id)
        if self.executor is None:
            return self._unavailable("oramasys_delegate")

        prior = {k: v.get("output") for k, v in (existing or {}).get("stage_outputs", {}).items()
                 if isinstance(v, dict)}
        started = time.monotonic()
        try:
            result = await self._run_stage(stage_name, payload, prior)
        except asyncio.TimeoutError:
            return self._failure("timeout", stage_name,
                                 f"stage exceeded {self.stage_timeout_s:g}s", task_id=task_id)
        except Exception as e:
            logger.warning("Delegated stage %s failed: %s", stage_name, e)
            return self._failure("failed", stage_name, f"{type(e).__name__}: {e}"[:500], task_id=task_id)
        if task_id:
            # Keep one source of truth: the verifier gate reads task state, so a delegated
            # verification must land there (a later FAIL supersedes an earlier PASS).
            existing.setdefault("stage_outputs", {})[stage_name] = {"status": "done", **result}
            await self.state.set_task_state(task_id, existing)
            await self.state.set_stage_output(task_id, stage_name, {"status": "done", **result})
        return _tool_result({
            "status": "done",
            "stage": stage_name,
            "task_id": task_id,
            "output": result["output"],
            **({"verdict": result["verdict"]} if "verdict" in result else {}),
            "model_used": result.get("model_used", "unknown"),
            "execution_time_ms": int((time.monotonic() - started) * 1000),
        }, False)

    async def _status(self, args: dict) -> dict:
        task_id = args.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise InvalidParams("task_id must be a non-empty string")
        state = await self.state.get_task_state(task_id)
        if not state:
            return _tool_result({"status": "not_found", "error": f"Task {task_id} not found"}, True)
        return _tool_result(state, False)

    async def _lessons(self, args: dict) -> dict:
        limit = args.get("limit", 10)
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise InvalidParams("limit must be an integer 1..100")
        lessons = await self.state.get_lessons(args.get("domain"))
        return _tool_result({"lessons": lessons[:limit], "total": len(lessons)}, False)

    def _error(self, req_id, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


# ── Stdio transport (Claude Code / MCP standard) ─────────────────────────────

async def run_stdio_server(server: Optional[OramasysMCPServer] = None):
    """Run server over stdin/stdout. One task per request so long solves don't block status."""
    server = server or OramasysMCPServer(executor=load_executor_from_env())
    logger.info("oramasys MCP server started (stdio, executor=%s)",
                type(server.executor).__name__ if server.executor else "none")
    loop = asyncio.get_running_loop()
    pending: set[asyncio.Task] = set()

    def emit(response: Optional[dict]) -> None:
        if response is not None:
            print(json.dumps(response), flush=True)

    async def serve(request: Any) -> None:
        emit(await server.handle_request(request))

    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        if not line.strip():
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            emit(server._error(None, -32700, "Parse error"))
            continue
        task = asyncio.create_task(serve(request))
        pending.add(task)
        task.add_done_callback(pending.discard)
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(run_stdio_server())
