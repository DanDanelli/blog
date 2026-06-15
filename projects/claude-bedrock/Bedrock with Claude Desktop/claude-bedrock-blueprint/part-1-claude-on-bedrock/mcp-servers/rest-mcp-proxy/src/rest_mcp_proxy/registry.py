"""Load and validate the YAML tool registry, and project it to MCP tool schemas.

The registry is the whole point of this server: each tool is declarative data, so adding a
capability is a YAML edit. This module is pure (given a parsed dict) so it's easy to test.
"""

from __future__ import annotations

import re
from typing import Any, Optional

import yaml

_REQUIRED_TOOL_KEYS = {"description", "method", "path"}
_VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}

# Anthropic/Bedrock validate tool input_schema *property keys* against this pattern.
# A '$' (OData params like $select/$top) is rejected — by the model, server-side — even
# though the raw API accepts it. See post A4. We strip '$' for the schema and re-add it on
# the wire in the dispatcher; this regex lets the builder *enforce* legality up front.
SCHEMA_KEY_RE = re.compile(r"^[a-zA-Z0-9_.-]{1,64}$")


class RegistryError(ValueError):
    """Raised when a registry is structurally invalid or would emit an illegal schema."""


def load_registry(path: str) -> dict:
    """Parse and validate a registry YAML file."""
    with open(path, encoding="utf-8") as f:
        return validate_registry(yaml.safe_load(f))


def validate_registry(data: Any) -> dict:
    """Validate a parsed registry dict; return it unchanged if valid."""
    if not isinstance(data, dict):
        raise RegistryError("Registry root must be a mapping")
    if "tools" not in data or not isinstance(data["tools"], dict):
        raise RegistryError("Registry must contain a 'tools' mapping")
    for name, defn in data["tools"].items():
        missing = _REQUIRED_TOOL_KEYS - set(defn or {})
        if missing:
            raise RegistryError(f"Tool '{name}' missing required keys: {sorted(missing)}")
        if (defn.get("method") or "").upper() not in _VALID_METHODS:
            raise RegistryError(f"Tool '{name}' has invalid method '{defn.get('method')}'")
        # Fail fast on schema-illegal keys (post A4) rather than at model-call time.
        build_input_schema(defn)
    return data


def get_tool(registry: dict, name: str) -> Optional[dict]:
    return registry["tools"].get(name)


def mcp_param_name(name: str) -> str:
    """Map a registry param key to its MCP-exposed property name.

    OData query params are stored with their leading ``$`` ($select, $top, $expand) because
    that's the wire name. Bedrock/Anthropic reject ``$`` in schema property keys, so we drop
    it here and the dispatcher re-adds it when building the query string.
    """
    return name[1:] if name.startswith("$") else name


def build_input_schema(defn: dict) -> dict:
    """Derive a JSON Schema for a tool from its path/query/body params."""
    properties: dict = {}
    required: list = []
    for group in ("path_params", "query_params", "body_params"):
        for pname, pdef in (defn.get(group) or {}).items():
            key = mcp_param_name(pname)
            if not SCHEMA_KEY_RE.match(key):
                raise RegistryError(
                    f"Param '{pname}' produces schema-illegal key '{key}'. "
                    r"Keys must match ^[a-zA-Z0-9_.-]{1,64}$ — map a friendly name "
                    "to the wire name at both ends (schema build + request build)."
                )
            prop: dict = {
                "type": (pdef or {}).get("type", "string"),
                "description": (pdef or {}).get("description", ""),
            }
            if (pdef or {}).get("default") is not None:
                prop["default"] = pdef["default"]
            properties[key] = prop
            if (pdef or {}).get("required"):
                required.append(key)
    schema: dict = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def build_annotations(defn: dict) -> dict:
    """Derive MCP tool annotations so clients can reduce per-call approvals.

    ``readOnlyHint`` is derived from the HTTP method (GET → read-only). Writing tools default
    to ``destructiveHint: True``; a tool can override in its YAML ``annotations`` (e.g. an
    additive POST that only appends sets ``destructiveHint: false``).
    """
    read_only = defn["method"].upper() == "GET"
    annotations: dict = {"readOnlyHint": read_only}
    if not read_only:
        annotations["destructiveHint"] = True
    annotations.update(defn.get("annotations") or {})
    return annotations


def list_tools_mcp(registry: dict) -> list:
    """Project the registry to the MCP ``tools/list`` shape."""
    return [
        {
            "name": name,
            "description": defn["description"],
            "inputSchema": build_input_schema(defn),
            "annotations": build_annotations(defn),
        }
        for name, defn in registry["tools"].items()
    ]
