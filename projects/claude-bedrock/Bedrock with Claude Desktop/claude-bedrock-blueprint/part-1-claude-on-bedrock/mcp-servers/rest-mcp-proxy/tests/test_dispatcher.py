"""Dispatcher: URL building, OData '$' round-trip, body shaping, required validation."""

from __future__ import annotations

import json

import pytest

from rest_mcp_proxy.dispatcher import (
    DispatchError,
    build_request,
    build_url,
)

BASE = "https://example.com/odata/v1"


def test_path_param_substitution_and_default_encoding():
    tool = {"method": "GET", "path": "/items/{id}", "path_params": {"id": {"required": True}}}
    url, remaining = build_url(tool, {"id": "a/b"}, BASE)
    assert url == "https://example.com/odata/v1/items/a%2Fb"  # '/' encoded by default
    assert remaining == {}


def test_quote_safe_preserves_addressing_chars():
    tool = {
        "method": "GET",
        "path": "/resolve/{hostPath}",
        "path_params": {"hostPath": {"required": True, "quote_safe": ":/"}},
    }
    url, _ = build_url(tool, {"hostPath": "host:/folder/name"}, BASE)
    assert url.endswith("/resolve/host:/folder/name")


def test_missing_required_path_param_raises():
    tool = {"method": "GET", "path": "/items/{id}", "path_params": {"id": {"required": True}}}
    with pytest.raises(DispatchError):
        build_url(tool, {}, BASE)


def test_odata_dollar_roundtrip_clean_name_in_dollar_name_on_wire():
    tool = {
        "method": "GET",
        "path": "/items",
        "query_params": {
            "$select": {"type": "string"},
            "$top": {"type": "integer", "default": 50},
        },
    }
    # Client sends the '$'-less name; wire must carry %24select / %24top.
    req = build_request(tool, {"select": "id,name"}, BASE)
    assert "%24select=id%2Cname" in req.full_url
    assert "%24top=50" in req.full_url  # default applied


def test_odata_tolerates_raw_dollar_name_inbound():
    tool = {"method": "GET", "path": "/items", "query_params": {"$top": {"type": "integer"}}}
    req = build_request(tool, {"$top": 5}, BASE)
    assert "%24top=5" in req.full_url


def test_post_body_is_json_from_remaining_params():
    tool = {
        "method": "POST",
        "path": "/posts",
        "body_params": {"title": {"required": True}, "userId": {"required": True}},
    }
    req = build_request(tool, {"title": "hi", "userId": 1}, BASE)
    assert json.loads(req.data) == {"title": "hi", "userId": 1}
    assert req.get_header("Content-type") == "application/json"
    assert req.get_method() == "POST"


def test_passthrough_param_is_whole_body():
    tool = {
        "method": "PATCH",
        "path": "/items/{id}/fields",
        "path_params": {"id": {"required": True}},
        "body_params": {"fields": {"required": True, "passthrough": True}},
    }
    req = build_request(tool, {"id": "1", "fields": {"Status": "Approved"}}, BASE)
    assert json.loads(req.data) == {"Status": "Approved"}  # not wrapped under "fields"


def test_body_template_with_prune_keeps_marker_when_disabled():
    tool = {
        "method": "POST",
        "path": "/folders",
        "prune_body": False,
        "body_template": '{"name": "{name}", "folder": {}}',
        "body_params": {"name": {"required": True}},
    }
    req = build_request(tool, {"name": "Docs"}, BASE)
    assert json.loads(req.data) == {"name": "Docs", "folder": {}}


def test_body_template_prunes_empty_optionals_by_default():
    tool = {
        "method": "POST",
        "path": "/x",
        "body_template": '{"name": "{name}", "note": "{note}"}',
        "body_params": {"name": {"required": True}, "note": {"required": False}},
    }
    req = build_request(tool, {"name": "a"}, BASE)  # note omitted
    assert json.loads(req.data) == {"name": "a"}


def test_bearer_token_header_when_provided():
    tool = {"method": "GET", "path": "/items"}
    req = build_request(tool, {}, BASE, token="abc")
    assert req.get_header("Authorization") == "Bearer abc"
    req2 = build_request(tool, {}, BASE)
    assert req2.get_header("Authorization") is None
