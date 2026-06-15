"""MCP JSON-RPC protocol handler (initialize / tools/list / tools/call).

Transport-agnostic: ``handle()`` takes a parsed request dict and returns a response dict
(or ``None`` for notifications). The stdio runner in ``__main__`` is one transport; an HTTP
Lambda would be another.
"""

from __future__ import annotations

import json
from typing import Optional

from .dispatcher import DispatchError, execute
from .registry import get_tool, list_tools_mcp

PROTOCOL_VERSION = "2024-11-05"


def handle(
    body: dict,
    registry: dict,
    *,
    base_url: str,
    token: str | None = None,
    server_info: Optional[dict] = None,
    auth_message: str | None = None,
) -> Optional[dict]:
    """Dispatch one JSON-RPC MCP request. Returns a response dict, or None for notifications.

    If ``token`` is None and ``auth_message`` is set, ``initialize`` still succeeds (so the
    client can proceed), ``tools/list`` returns a single synthetic "authorize" tool, and any
    other call returns the message as content.
    """
    server_info = server_info or {"name": "rest-mcp-proxy", "version": "1.0.0"}
    rpc_id = body.get("id")
    method = body.get("method", "")

    # Notifications (no id, e.g. "notifications/initialized") get no response.
    if rpc_id is None and method != "initialize":
        return None

    if method == "initialize":
        return _ok(rpc_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": server_info,
        })

    if token is None and auth_message is not None:
        return _auth_required(rpc_id, method, auth_message)

    if method == "tools/list":
        return _ok(rpc_id, {"tools": list_tools_mcp(registry)})

    if method == "tools/call":
        return _tools_call(rpc_id, body.get("params", {}), registry, base_url, token)

    return _error(rpc_id, -32601, f"Method not found: {method}")


def _tools_call(rpc_id, params, registry, base_url, token):
    name = params.get("name") or params.get("tool")
    arguments = params.get("arguments") or params.get("input") or {}
    if not name:
        return _error(rpc_id, -32602, "Missing 'name' in tools/call params")

    tool_def = get_tool(registry, name)
    if tool_def is None:
        return _tool_error(rpc_id, f"Unknown tool: '{name}'")

    try:
        result = execute(tool_def, arguments, base_url, token)
    except DispatchError as e:
        return _tool_error(rpc_id, str(e))

    if result["ok"]:
        try:
            text = json.dumps(json.loads(result["body"]), ensure_ascii=False, indent=2)
        except Exception:
            text = result["body"]
        return _ok(rpc_id, {"content": [{"type": "text", "text": text}]})

    return _tool_error(rpc_id, f"Upstream API error {result['status']}: {result['body'][:300]}")


def _auth_required(rpc_id, method, auth_message):
    if method == "tools/list":
        return _ok(rpc_id, {"tools": [{
            "name": "authorize",
            "description": auth_message,
            "inputSchema": {"type": "object", "properties": {}},
        }]})
    return _ok(rpc_id, {"content": [{"type": "text", "text": auth_message}]})


# --- JSON-RPC envelope helpers --------------------------------------------------------
def _ok(rpc_id, result):
    return {"jsonrpc": "2.0", "id": rpc_id, "result": result}


def _error(rpc_id, code, message):
    return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}


def _tool_error(rpc_id, message):
    return _ok(rpc_id, {"content": [{"type": "text", "text": message}], "isError": True})
