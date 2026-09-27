"""Read-only docs search exposed to people, MCP clients, and A2A peers."""
from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query, Request, Response

router = APIRouter()
_PROTOCOL = "2026-07-28"
_MAX_DOC_BYTES = 512_000
_WORD = re.compile(r"[a-z0-9][a-z0-9_.-]*", re.IGNORECASE)


def _docs_root() -> Path:
    configured = os.getenv("ORAMA_DOCS_ROOT", "").strip()
    return Path(configured).expanduser().resolve() if configured else Path(__file__).resolve().parents[2] / "docs"


def _search_docs(query: str, limit: int = 8) -> list[dict[str, Any]]:
    terms = tuple(dict.fromkeys(word.lower() for word in _WORD.findall(query)))
    if not terms:
        return []
    root = _docs_root().resolve()
    hits: list[tuple[int, dict[str, Any]]] = []
    for path in root.rglob("*.md"):
        try:
            resolved = path.resolve()
            resolved.relative_to(root)
            if not resolved.is_file() or resolved.stat().st_size > _MAX_DOC_BYTES:
                continue
            text = resolved.read_text(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            continue
        lowered = text.lower()
        title = next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("#")), path.stem)
        title_lower = title.lower()
        score = sum(lowered.count(term) + (5 if term in title_lower else 0) for term in terms)
        if not score:
            continue
        first = min((lowered.find(term) for term in terms if term in lowered), default=0)
        start = max(0, first - 120)
        excerpt = " ".join(text[start : first + 280].split())
        hits.append((score, {"title": title, "path": resolved.relative_to(root).as_posix(), "excerpt": excerpt, "score": score}))
    hits.sort(key=lambda item: (-item[0], item[1]["path"]))
    return [hit for _, hit in hits[:limit]]


def _rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _rpc_result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _text_from_a2a_message(params: Any) -> str:
    message = params.get("message", {}) if isinstance(params, dict) else {}
    parts = message.get("parts", []) if isinstance(message, dict) else []
    return " ".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict) and part.get("kind", part.get("type")) == "text"
    ).strip()


@router.get("/api/knowledge/search", tags=["knowledge"])
def knowledge_search(q: str = Query(..., min_length=2, max_length=200), limit: int = Query(8, ge=1, le=20)) -> dict[str, Any]:
    return {"query": q, "hits": _search_docs(q, limit), "read_only": True}


@router.post("/api/mcp", tags=["knowledge"])
async def mcp(request: Request):
    body = await request.json()
    if not isinstance(body, dict):
        return _rpc_error(None, -32600, "Invalid Request")
    request_id = body.get("id")
    method = body.get("method")
    if request.headers.get("Mcp-Protocol-Version") != _PROTOCOL:
        return _rpc_error(request_id, -32600, f"Mcp-Protocol-Version must be {_PROTOCOL}")
    if request.headers.get("Mcp-Method") != method:
        return _rpc_error(request_id, -32600, "Mcp-Method header must match the JSON-RPC method")
    if method == "notifications/initialized":
        return Response(status_code=202)
    if method == "initialize":
        return _rpc_result(
            request_id,
            {
                "protocolVersion": _PROTOCOL,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "orama-knowledge", "version": "1.0.0"},
            },
        )
    if method == "tools/list":
        return _rpc_result(
            request_id,
            {
                "tools": [
                    {
                        "name": "search_docs",
                        "description": "Search local Orama project documentation (read-only)",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"query": {"type": "string", "minLength": 2}},
                            "required": ["query"],
                            "additionalProperties": False,
                        },
                    }
                ]
            },
        )
    if method == "tools/call":
        params = body.get("params", {})
        if not isinstance(params, dict):
            return _rpc_error(request_id, -32602, "Invalid params")
        if request.headers.get("Mcp-Name") != params.get("name"):
            return _rpc_error(request_id, -32600, "Mcp-Name header must match params.name")
        if params.get("name") != "search_docs":
            return _rpc_error(request_id, -32601, "Unknown tool")
        arguments = params.get("arguments", {})
        query = arguments.get("query", "") if isinstance(arguments, dict) else ""
        if not isinstance(query, str) or len(query.strip()) < 2:
            return _rpc_error(request_id, -32602, "query must contain at least two characters")
        hits = _search_docs(query)
        return _rpc_result(
            request_id,
            {
                "content": [{"type": "text", "text": json.dumps(hits)}],
                "structuredContent": {"hits": hits},
                "isError": False,
            },
        )
    return _rpc_error(request_id, -32601, "Method not found")


@router.get("/.well-known/agent-card.json", tags=["knowledge"])
def agent_card(request: Request) -> dict[str, Any]:
    base = str(request.base_url).rstrip("/")
    return {
        "name": "Orama Knowledge Gateway",
        "description": "Read-only search over curated project documentation",
        "url": f"{base}/api/a2a",
        "version": "1.0.0",
        "protocolVersion": "0.3.0",
        "capabilities": {"streaming": False, "pushNotifications": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["application/json"],
        "skills": [
            {
                "id": "search-docs",
                "name": "Search documentation",
                "description": "Returns ranked excerpts from local Markdown documentation",
                "tags": ["docs", "search"],
                "examples": ["human approval gate"],
            }
        ],
    }


@router.post("/api/a2a", tags=["knowledge"])
async def a2a(request: Request) -> dict[str, Any]:
    body = await request.json()
    if not isinstance(body, dict):
        return _rpc_error(None, -32600, "Invalid Request")
    request_id = body.get("id")
    method = body.get("method")
    if method == "message/send":
        query = _text_from_a2a_message(body.get("params", {}))
        if len(query) < 2:
            return _rpc_error(request_id, -32602, "A text query is required")
        hits = _search_docs(query)
        return _rpc_result(
            request_id,
            {
                "kind": "message",
                "messageId": str(uuid.uuid4()),
                "role": "agent",
                "parts": [{"kind": "data", "data": {"hits": hits, "read_only": True}}],
            },
        )
    if method in {"tasks/get", "tasks/cancel"}:
        return _rpc_error(request_id, -32001, "No task exists: read-only searches return a direct Message")
    return _rpc_error(request_id, -32601, "Method not found")
