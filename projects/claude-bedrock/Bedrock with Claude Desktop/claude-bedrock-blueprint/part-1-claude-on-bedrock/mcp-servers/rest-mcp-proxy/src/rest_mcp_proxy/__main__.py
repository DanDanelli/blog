"""Run rest-mcp-proxy as a local stdio MCP server.

Reads line-delimited JSON-RPC requests on stdin and writes responses on stdout — the
transport Claude Desktop and other local MCP clients use. For the serverless (API Gateway
+ Lambda) deployment, reuse ``protocol.handle`` from an HTTP handler instead.

Configuration (env vars):
  REGISTRY        path to the tool registry YAML (required)
  BASE_URL        override the registry's ``base_url`` (optional)
  ACCESS_TOKEN    bearer token sent to the upstream API (optional)
  SERVER_NAME     server name reported in ``initialize`` (optional)

Wire it into a client's MCP config, e.g.::

    {
      "command": "python",
      "args": ["-m", "rest_mcp_proxy"],
      "env": {"REGISTRY": "/path/to/registry.yaml", "ACCESS_TOKEN": "..."}
    }
"""

from __future__ import annotations

import json
import os
import sys

from .protocol import handle
from .registry import load_registry


def main() -> int:
    registry_path = os.environ.get("REGISTRY")
    if not registry_path:
        sys.stderr.write("rest-mcp-proxy: set REGISTRY to the tool registry YAML path\n")
        return 2

    registry = load_registry(registry_path)
    base_url = os.environ.get("BASE_URL") or registry.get("base_url")
    if not base_url:
        sys.stderr.write("rest-mcp-proxy: no base_url (set BASE_URL or add it to the registry)\n")
        return 2

    token = os.environ.get("ACCESS_TOKEN")
    server_info = {"name": os.environ.get("SERVER_NAME", "rest-mcp-proxy"), "version": "1.0.0"}

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            _write(_parse_error())
            continue

        response = handle(request, registry, base_url=base_url, token=token, server_info=server_info)
        if response is not None:
            _write(response)
    return 0


def _write(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _parse_error() -> dict:
    return {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}


if __name__ == "__main__":
    raise SystemExit(main())
