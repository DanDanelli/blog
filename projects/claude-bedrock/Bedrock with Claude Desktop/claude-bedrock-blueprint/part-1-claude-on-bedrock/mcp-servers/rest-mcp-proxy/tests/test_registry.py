"""Registry validation + schema projection, including the post-A4 no-'$' guarantee."""

from __future__ import annotations

import glob
import os

import pytest

from rest_mcp_proxy.registry import (
    RegistryError,
    SCHEMA_KEY_RE,
    build_annotations,
    build_input_schema,
    list_tools_mcp,
    load_registry,
    mcp_param_name,
    validate_registry,
)

REGISTRY_DIR = os.path.join(os.path.dirname(__file__), "..", "registry")


def _odata_tool():
    return {
        "description": "list",
        "method": "GET",
        "path": "/items",
        "query_params": {
            "$select": {"type": "string", "required": False, "default": "id,name"},
            "$top": {"type": "integer", "required": False},
        },
    }


# --- validation ----------------------------------------------------------------------
def test_validate_rejects_non_mapping():
    with pytest.raises(RegistryError):
        validate_registry([])


def test_validate_requires_tools():
    with pytest.raises(RegistryError):
        validate_registry({"base_url": "x"})


def test_validate_rejects_missing_keys():
    with pytest.raises(RegistryError):
        validate_registry({"tools": {"t": {"description": "d"}}})


def test_validate_rejects_bad_method():
    with pytest.raises(RegistryError):
        validate_registry({"tools": {"t": {"description": "d", "method": "FETCH", "path": "/"}}})


# --- the A4 finding: no '$' in any schema property key -------------------------------
def test_mcp_param_name_strips_dollar():
    assert mcp_param_name("$select") == "select"
    assert mcp_param_name("top") == "top"


def test_schema_keys_are_dollar_free_and_legal():
    schema = build_input_schema(_odata_tool())
    assert set(schema["properties"]) == {"select", "top"}
    for key in schema["properties"]:
        assert "$" not in key
        assert SCHEMA_KEY_RE.match(key)


def test_builder_rejects_schema_illegal_key():
    bad = {
        "description": "d",
        "method": "GET",
        "path": "/x",
        "query_params": {"weird key!": {"type": "string"}},
    }
    with pytest.raises(RegistryError):
        build_input_schema(bad)


def test_default_and_required_propagate():
    schema = build_input_schema(
        {
            "description": "d",
            "method": "GET",
            "path": "/x",
            "path_params": {"id": {"type": "integer", "required": True}},
            "query_params": {"$top": {"type": "integer", "default": 50}},
        }
    )
    assert schema["properties"]["top"]["default"] == 50
    assert schema["required"] == ["id"]


# --- annotations ---------------------------------------------------------------------
def test_get_is_read_only():
    ann = build_annotations({"method": "GET"})
    assert ann == {"readOnlyHint": True}


def test_write_is_destructive_by_default_but_overridable():
    assert build_annotations({"method": "POST"})["destructiveHint"] is True
    ann = build_annotations({"method": "POST", "annotations": {"destructiveHint": False}})
    assert ann["destructiveHint"] is False


# --- the shipped example registries all load and stay '$'-free -----------------------
@pytest.mark.parametrize("path", sorted(glob.glob(os.path.join(REGISTRY_DIR, "*.yaml"))))
def test_example_registries_load_and_have_no_dollar_keys(path):
    registry = load_registry(path)
    for tool in list_tools_mcp(registry):
        for key in tool["inputSchema"]["properties"]:
            assert "$" not in key, f"{tool['name']} exposes a '$' key in {path}"
