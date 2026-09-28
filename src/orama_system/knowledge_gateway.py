"""Read-only docs search exposed to people, MCP clients, and A2A peers."""
from __future__ import annotations

import asyncio
import json
import os
import re
import unicodedata
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from starlette.responses import JSONResponse

# MCP Streamable HTTP protocol date from https://modelcontextprotocol.io/specification/2026-07-28
_PROTOCOL = "2026-07-28"
_MAX_DOC_BYTES = 512_000
_EXCERPT_CHARS = 280
_QUERY_MAX = 200
_WORD = re.compile(r"[0-9a-z][0-9a-z_.-]*", re.IGNORECASE)
_SERVER_INFO = {"name": "orama-knowledge", "version": "1.0.0"}
_SERVER_INFO_META = "io.modelcontextprotocol/serverInfo"
_QUERY_INVALID = "query must be a string of 2 to 200 characters"
_TEXT_PARTS_INVALID = "text parts must be strings"
def _max_files_scan() -> int:
    return max(1, int(os.getenv("ORAMA_KNOWLEDGE_MAX_FILES_SCAN", "2000")))


def _max_concurrent_searches() -> int:
    return max(1, int(os.getenv("ORAMA_KNOWLEDGE_MAX_CONCURRENT_SEARCHES", "4")))


def _search_timeout_s() -> float:
    return max(0.5, float(os.getenv("ORAMA_KNOWLEDGE_SEARCH_TIMEOUT_S", "8")))
_SEARCH_TIMEOUT_DETAIL = "documentation search timed out; retry with a narrower query"

_search_sem: asyncio.Semaphore | None = None


def _search_semaphore() -> asyncio.Semaphore:
    global _search_sem
    if _search_sem is None:
        _search_sem = asyncio.Semaphore(_max_concurrent_searches())
    return _search_sem


async def _bounded_search(query: str, limit: int = 8) -> list[dict[str, Any]]:
    """Run Markdown scan off the event loop with concurrency and time limits."""
    async with _search_semaphore():
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_search_docs, query, limit),
                timeout=_search_timeout_s(),
            )
        except TimeoutError:
            raise HTTPException(status_code=503, detail=_SEARCH_TIMEOUT_DETAIL) from None


router = APIRouter()


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _fold_align(text: str) -> tuple[str, list[int]]:
    """NFKD-fold text and map each folded index back to an original character index."""
    chars: list[str] = []
    origins: list[int] = []
    for index, char in enumerate(text):
        folded = "".join(
            piece for piece in unicodedata.normalize("NFKD", char) if not unicodedata.combining(piece)
        )
        for piece in folded:
            chars.append(piece)
            origins.append(index)
    return "".join(chars), origins


def _excerpt(text: str, terms: tuple[str, ...]) -> str:
    folded, origins = _fold_align(text)
    folded = folded.lower()
    starts = [folded.find(term) for term in terms]
    starts = [start for start in starts if start >= 0]
    if not starts or len(folded) != len(origins):
        return " ".join(text.split())[:_EXCERPT_CHARS]
    folded_at = min(starts)
    orig_at = origins[folded_at]
    half = _EXCERPT_CHARS // 2
    start = max(0, orig_at - half)
    end = min(len(text), start + _EXCERPT_CHARS)
    if end - start < _EXCERPT_CHARS:
        start = max(0, end - _EXCERPT_CHARS)
    snippet = " ".join(text[start:end].split())
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{snippet}{suffix}"


def _docs_root() -> Path:
    configured = os.getenv("ORAMA_DOCS_ROOT", "").strip()
    return Path(configured).expanduser().resolve() if configured else Path(__file__).resolve().parents[2] / "docs"


def _search_docs(query: str, limit: int = 8) -> list[dict[str, Any]]:
    terms = tuple(dict.fromkeys(word.lower() for word in _WORD.findall(_fold(query))))
    if not terms:
        return []
    root = _docs_root().resolve()
    hits: list[tuple[int, dict[str, Any]]] = []
    scanned = 0
    for path in root.rglob("*.md"):
        scanned += 1
        if scanned > _max_files_scan():
            break
        try:
            resolved = path.resolve()
            resolved.relative_to(root)
            if not resolved.is_file() or resolved.stat().st_size > _MAX_DOC_BYTES:
                continue
            text = resolved.read_text(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            continue
        folded = _fold(text).lower()
        title = next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("#")), path.stem)
        title_lower = _fold(title).lower()
        score = sum(folded.count(term) + (5 if term in title_lower else 0) for term in terms)
        if not score:
            continue
        hits.append(
            (
                score,
                {
                    "title": title,
                    "path": resolved.relative_to(root).as_posix(),
                    "excerpt": _excerpt(text, terms),
                    "score": score,
                },
            )
        )
    hits.sort(key=lambda item: (-item[0], item[1]["path"]))
    return [hit for _, hit in hits[:limit]]


def _mcp_hello() -> dict[str, Any]:
    return {
        "protocolVersion": _PROTOCOL,
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": dict(_SERVER_INFO),
    }


def _rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _rpc_result(request_id: Any, result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        meta = dict(result.get("_meta") or {})
        meta.setdefault(_SERVER_INFO_META, _SERVER_INFO)
        result = {**result, "_meta": meta}
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_response(payload: dict[str, Any], status_code: int = 200) -> JSONResponse:
    return JSONResponse(content=payload, status_code=status_code)


async def _rpc_body(request: Request) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
        return None, _rpc_error(None, -32700, "Parse error")
    if not isinstance(body, dict):
        return None, _rpc_error(None, -32600, "Invalid Request")
    return body, None


def _bounded_query(query: Any, *, already_stripped: bool = False) -> str:
    if not isinstance(query, str):
        raise ValueError(_QUERY_INVALID)
    candidate = query.strip() if not already_stripped else query
    if len(candidate) < 2 or len(query) > _QUERY_MAX:
        raise ValueError(_QUERY_INVALID)
    return query


def _text_from_a2a_message(params: Any) -> str:
    message = params.get("message", {}) if isinstance(params, dict) else {}
    parts = message.get("parts", []) if isinstance(message, dict) else []
    texts: list[str] = []
    for part in parts:
        if not isinstance(part, dict) or part.get("kind", part.get("type")) != "text":
            continue
        text = part.get("text", "")
        if not isinstance(text, str):
            raise ValueError(_TEXT_PARTS_INVALID)
        texts.append(text)
    return " ".join(texts).strip()


@router.get("/api/knowledge/search", tags=["knowledge"])
async def knowledge_search(
    q: str = Query(..., min_length=2, max_length=_QUERY_MAX),
    limit: int = Query(8, ge=1, le=20),
) -> dict[str, Any]:
    hits = await _bounded_search(q, limit)
    return {"query": q, "hits": hits, "read_only": True}


@router.post("/api/mcp", tags=["knowledge"], response_class=Response)
async def mcp(request: Request) -> Response:
    body, error = await _rpc_body(request)
    if error is not None or body is None:
        return _rpc_response(error or _rpc_error(None, -32600, "Invalid Request"))
    request_id = body.get("id")
    method = body.get("method")
    if request.headers.get("Mcp-Protocol-Version") != _PROTOCOL:
        return _rpc_response(_rpc_error(request_id, -32600, f"Mcp-Protocol-Version must be {_PROTOCOL}"))
    if request.headers.get("Mcp-Method") != method:
        return _rpc_response(_rpc_error(request_id, -32600, "Mcp-Method header must match the JSON-RPC method"))
    if method == "notifications/initialized":
        return Response(status_code=202)
    if method == "server/discover":
        return _rpc_response(_rpc_result(request_id, _mcp_hello()))
    if method == "initialize":
        return _rpc_response(_rpc_result(request_id, _mcp_hello()))
    if method == "tools/list":
        return _rpc_response(
            _rpc_result(
                request_id,
                {
                    "tools": [
                        {
                            "name": "search_docs",
                            "description": "Search local Orama project documentation (read-only)",
                            "annotations": {"readOnlyHint": True},
                            "inputSchema": {
                                "type": "object",
                                "properties": {"query": {"type": "string", "minLength": 2, "maxLength": 200}},
                                "required": ["query"],
                                "additionalProperties": False,
                            },
                        }
                    ]
                },
            )
        )
    if method == "tools/call":
        params = body.get("params", {})
        if not isinstance(params, dict):
            return _rpc_response(_rpc_error(request_id, -32602, "Invalid params"))
        if request.headers.get("Mcp-Name") != params.get("name"):
            return _rpc_response(_rpc_error(request_id, -32600, "Mcp-Name header must match params.name"))
        if params.get("name") != "search_docs":
            return _rpc_response(_rpc_error(request_id, -32601, "Unknown tool"))
        arguments = params.get("arguments", {})
        query = arguments.get("query", "") if isinstance(arguments, dict) else ""
        try:
            query = _bounded_query(query)
        except ValueError:
            return _rpc_response(_rpc_error(request_id, -32602, _QUERY_INVALID))
        try:
            hits = await _bounded_search(query)
        except HTTPException as exc:
            if exc.status_code == 503:
                detail = exc.detail if isinstance(exc.detail, str) else _SEARCH_TIMEOUT_DETAIL
                return _rpc_response(_rpc_error(request_id, -32000, detail))
            raise
        return _rpc_response(
            _rpc_result(
                request_id,
                {
                    "content": [{"type": "text", "text": json.dumps(hits)}],
                    "structuredContent": {"hits": hits},
                    "isError": False,
                },
            )
        )
    return _rpc_response(_rpc_error(request_id, -32601, "Method not found"))


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
    body, error = await _rpc_body(request)
    if error is not None or body is None:
        return error or _rpc_error(None, -32600, "Invalid Request")
    request_id = body.get("id")
    method = body.get("method")
    if method == "message/send":
        try:
            query = _text_from_a2a_message(body.get("params", {}))
        except ValueError:
            return _rpc_error(request_id, -32602, _TEXT_PARTS_INVALID)
        try:
            query = _bounded_query(query, already_stripped=True)
        except ValueError:
            return _rpc_error(request_id, -32602, _QUERY_INVALID)
        try:
            hits = await _bounded_search(query)
        except HTTPException as exc:
            if exc.status_code == 503:
                detail = exc.detail if isinstance(exc.detail, str) else _SEARCH_TIMEOUT_DETAIL
                return _rpc_error(request_id, -32000, detail)
            raise
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
