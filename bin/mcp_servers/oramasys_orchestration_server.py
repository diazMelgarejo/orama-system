#!/usr/bin/env python3
"""
oramasys_orchestration_server.py
====================================
MCP Server: oramasys Multi-Agent Orchestration
Version: 0.9.9.2 | License: Apache 2.0

Exposes the oramasys agent network as MCP tools.
Compatible with: Clawdbot, MoltBot, OpenClaw, Claude Code MCP client.

Usage:
    python oramasys_orchestration_server.py
    # or
    python oramasys_orchestration_server.py --port 8080

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
import json
import logging
import sys
from pathlib import Path

# Add shared to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))
from oramasys_core import TaskState, Stage, OptimizeFor
from state_manager import StateManager
from message_bus import MessageBus

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ── Tool schemas ─────────────────────────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "name": "oramasys_solve",
        "description": (
            "Apply the complete oramasys 5-stage process to a complex problem. "
            "Coordinates context gathering, architecture design, refinement, "
            "parallel execution, verification, and documentation."
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
        "description": "Delegate a specific oramasys stage to its specialist agent.",
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


# ── Server implementation ────────────────────────────────────────────────────

class OramasysMCPServer:
    """
    MCP server exposing oramasys agent network.
    Implements the MCP JSON-RPC protocol.
    """

    def __init__(self):
        self.state = StateManager()
        self.bus   = MessageBus()

    async def handle_request(self, request: dict) -> dict:
        """Dispatch MCP JSON-RPC request."""
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        try:
            if method == "initialize":
                result = await self._initialize(params)
            elif method == "tools/list":
                result = {"tools": TOOL_SCHEMAS}
            elif method == "tools/call":
                result = await self._call_tool(params["name"], params.get("arguments", {}))
            else:
                return self._error(req_id, -32601, f"Method not found: {method}")

            return {"jsonrpc": "2.0", "id": req_id, "result": result}

        except Exception as e:
            logger.exception("Error handling request: %s", e)
            return self._error(req_id, -32603, str(e))

    async def _initialize(self, params: dict) -> dict:
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "oramasys-orchestration-server",
                "version": "2.0.0"
            }
        }

    async def _call_tool(self, name: str, arguments: dict) -> dict:
        """Route tool call to appropriate handler."""
        if name == "oramasys_solve":
            return await self._solve(arguments)
        elif name == "oramasys_delegate":
            return await self._delegate(arguments)
        elif name == "oramasys_status":
            return await self._status(arguments)
        elif name == "oramasys_lessons":
            return await self._lessons(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

    async def _solve(self, args: dict) -> dict:
        """Kick off full oramasys pipeline."""
        import uuid
        task_id = str(uuid.uuid4())

        state = TaskState(
            task_id=task_id,
            task_description=args["task"],
            optimize_for=args.get("optimize_for", "reliability"),
        )
        await self.state.set_task_state(task_id, state.to_dict())

        logger.info("Starting oramasys task %s: %s", task_id, args["task"])

        # In production: publish to orchestrator agent
        # For now: return task_id for status polling
        return {
            "task_id": task_id,
            "status": "started",
            "message": f"oramasys task {task_id} initiated. Poll oramasys_status for updates."
        }

    async def _delegate(self, args: dict) -> dict:
        """Delegate to a specific stage agent."""
        stage = args["stage"]
        agent_map = {
            "context":        "context-agent",
            "architecture":   "architect-agent",
            "refinement":     "refiner-agent",
            "execution":      "executor-agent",
            "verification":   "verifier-agent",
            "crystallization":"crystallizer-agent"
        }
        target = agent_map.get(stage, "orchestrator")
        logger.info("Delegating stage '%s' to %s", stage, target)
        # STUB: In production, publish to message bus and await result
        return {"delegated_to": target, "stage": stage, "status": "queued"}

    async def _status(self, args: dict) -> dict:
        task_id = args["task_id"]
        state   = await self.state.get_task_state(task_id)
        if not state:
            return {"error": f"Task {task_id} not found"}
        return state

    async def _lessons(self, args: dict) -> dict:
        lessons = await self.state.get_lessons(args.get("domain"))
        limit   = args.get("limit", 10)
        return {"lessons": lessons[:limit], "total": len(lessons)}

    def _error(self, req_id, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


# ── Stdio transport (Claude Code / MCP standard) ─────────────────────────────

async def run_stdio_server():
    """Run server over stdin/stdout (standard MCP transport)."""
    server = OramasysMCPServer()
    logger.info("oramasys MCP server started (stdio)")

    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            request = json.loads(line.strip())
            response = await server.handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError:
            pass
        except EOFError:
            break


if __name__ == "__main__":
    asyncio.run(run_stdio_server())

