"""MCP JSON-RPC protocol: initialize / tools/list / tools/call / errors / auth-required."""

from __future__ import annotations

from rest_mcp_proxy import protocol
from rest_mcp_proxy.registry import validate_registry

REGISTRY = validate_registry(
    {
        "base_url": "https://example.com",
        "tools": {
            "get_item": {
                "description": "Get an item",
                "method": "GET",
                "path": "/items/{id}",
                "path_params": {"id": {"required": True}},
            }
        },
    }
)
BASE = "https://example.com"


def test_initialize_returns_capabilities():
    resp = protocol.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"}, REGISTRY, base_url=BASE)
    assert resp["result"]["serverInfo"]["name"] == "rest-mcp-proxy"
    assert "tools" in resp["result"]["capabilities"]


def test_notification_returns_none():
    resp = protocol.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}, REGISTRY, base_url=BASE)
    assert resp is None


def test_tools_list_shape():
    resp = protocol.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, REGISTRY, base_url=BASE)
    names = [t["name"] for t in resp["result"]["tools"]]
    assert names == ["get_item"]
    assert resp["result"]["tools"][0]["annotations"]["readOnlyHint"] is True


def test_unknown_method():
    resp = protocol.handle({"jsonrpc": "2.0", "id": 3, "method": "bogus"}, REGISTRY, base_url=BASE)
    assert resp["error"]["code"] == -32601


def test_tools_call_success(monkeypatch):
    monkeypatch.setattr(
        protocol, "execute", lambda *a, **k: {"ok": True, "status": 200, "body": '{"id": 7}'}
    )
    resp = protocol.handle(
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "get_item", "arguments": {"id": 7}}},
        REGISTRY, base_url=BASE,
    )
    assert "7" in resp["result"]["content"][0]["text"]
    assert "isError" not in resp["result"]


def test_tools_call_unknown_tool():
    resp = protocol.handle(
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "nope"}},
        REGISTRY, base_url=BASE,
    )
    assert resp["result"]["isError"] is True


def test_tools_call_upstream_error(monkeypatch):
    monkeypatch.setattr(
        protocol, "execute", lambda *a, **k: {"ok": False, "status": 404, "body": "not found"}
    )
    resp = protocol.handle(
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call",
         "params": {"name": "get_item", "arguments": {"id": 1}}},
        REGISTRY, base_url=BASE,
    )
    assert resp["result"]["isError"] is True
    assert "404" in resp["result"]["content"][0]["text"]


def test_auth_required_synthetic_tool():
    resp = protocol.handle(
        {"jsonrpc": "2.0", "id": 7, "method": "tools/list"},
        REGISTRY, base_url=BASE, token=None, auth_message="Please authorize",
    )
    assert resp["result"]["tools"][0]["name"] == "authorize"
