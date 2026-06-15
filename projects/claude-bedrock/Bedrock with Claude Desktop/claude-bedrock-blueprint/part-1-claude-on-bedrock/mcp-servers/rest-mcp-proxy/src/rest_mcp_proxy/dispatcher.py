"""Generic REST dispatcher: a YAML tool definition + params → an HTTP request.

No vendor specifics here — ``base_url`` comes from the registry, the bearer token (if any)
is injected per call. Three pieces of accumulated wisdom live in this file:

* **OData ``$`` round-trip (post A4):** the schema exposes ``top``/``select``; the wire wants
  ``$top``/``$select``. We accept either inbound and always emit the ``$`` form (urlencoded
  to ``%24``, which OData APIs accept).
* **``quote_safe`` per path param:** some path segments embed characters that must survive
  percent-encoding (e.g. an addressing path ``host:/sites/Name``). A param can relax the
  default ``quote(safe="")``.
* **Body shaping:** a ``body_template`` (with pruning of empty optionals) or a single
  ``passthrough`` param whose value *is* the whole body (dynamic-key payloads).
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

HTTP_TIMEOUT = 25


class DispatchError(ValueError):
    """Raised when a tool call is missing a required parameter, etc."""


def build_url(tool_def: dict, params: dict, base_url: str) -> tuple[str, dict]:
    """Substitute path params into the URL; return (url, remaining params)."""
    path = tool_def["path"]
    remaining = dict(params)
    for pname, pdef in (tool_def.get("path_params") or {}).items():
        if pname not in remaining:
            if (pdef or {}).get("required"):
                raise DispatchError(f"Required path param missing: '{pname}'")
            continue
        value = remaining.pop(pname)
        safe = (pdef or {}).get("quote_safe", "")
        path = path.replace(f"{{{pname}}}", urllib.parse.quote(str(value), safe=safe))
    return base_url.rstrip("/") + path, remaining


def build_request(
    tool_def: dict,
    params: dict,
    base_url: str,
    token: str | None = None,
) -> urllib.request.Request:
    """Build a urllib Request: path + query (GET) or body (non-GET), with auth header."""
    _validate_required_params(tool_def, params)
    url, remaining = build_url(tool_def, params, base_url)
    method = tool_def["method"].upper()

    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body_bytes: bytes | None = None

    if method == "GET":
        qs = _build_query(tool_def, remaining)
        if qs:
            # '$' in $select becomes %24, which OData APIs accept.
            url = f"{url}?{urllib.parse.urlencode(qs)}"
    else:
        body_bytes = _build_body(tool_def, params, remaining)
        if body_bytes:
            headers["Content-Type"] = "application/json"

    return urllib.request.Request(url, data=body_bytes, headers=headers, method=method)


def execute(tool_def: dict, params: dict, base_url: str, token: str | None = None) -> dict:
    """Run the call; return a normalized ``{"status", "body", "ok"}`` dict."""
    req = build_request(tool_def, params, base_url, token)
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            return {"status": r.status, "body": r.read().decode("utf-8", "replace"), "ok": True}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": e.read().decode("utf-8", "replace"), "ok": False}
    except Exception as e:  # network/DNS/timeout — surface as a gateway error
        return {"status": 502, "body": str(e), "ok": False}


# --------------------------------------------------------------------------------------
# Internals
# --------------------------------------------------------------------------------------
def _validate_required_params(tool_def: dict, params: dict) -> None:
    for group in ("path_params", "query_params", "body_params"):
        for pname, pdef in (tool_def.get(group) or {}).items():
            if (pdef or {}).get("required"):
                # Accept the schema-exposed ('$'-less) name too.
                clean = pname[1:] if pname.startswith("$") else pname
                if pname not in params and clean not in params:
                    raise DispatchError(f"Required parameter missing: '{pname}'")


def _build_query(tool_def: dict, remaining: dict) -> dict:
    qs: dict = {}
    for qname, qdef in (tool_def.get("query_params") or {}).items():
        clean = qname[1:] if qname.startswith("$") else qname
        if clean in remaining:
            qs[qname] = remaining[clean]
        elif qname in remaining:  # tolerate the raw '$top' form inbound
            qs[qname] = remaining[qname]
        elif (qdef or {}).get("default") is not None:
            qs[qname] = qdef["default"]
    return qs


def _build_body(tool_def: dict, params: dict, remaining: dict) -> bytes | None:
    template = tool_def.get("body_template")
    if template:
        rendered = _render_template(template, params, prune=tool_def.get("prune_body", True))
        return rendered.encode("utf-8")

    passthrough = _passthrough_key(tool_def)
    if passthrough is not None:
        if passthrough in remaining:
            return json.dumps(remaining[passthrough]).encode("utf-8")
        return None

    return json.dumps(remaining).encode("utf-8") if remaining else None


def _passthrough_key(tool_def: dict) -> str | None:
    """Return the body param marked ``passthrough: true`` (its value IS the whole body)."""
    for name, defn in (tool_def.get("body_params") or {}).items():
        if (defn or {}).get("passthrough"):
            return name
    return None


def _render_template(template: str, params: dict, prune: bool = True) -> str:
    """Substitute ``{name}`` placeholders in a body template.

    dict/list → JSON-encoded; str → JSON-escaped without outer quotes (use ``"{name}"``);
    None/missing → empty. Unfilled placeholders are dropped; if the result is valid JSON,
    empty optionals are pruned unless ``prune`` is False (keep markers like ``"x": {}``).
    """
    result = template
    for key, value in params.items():
        if isinstance(value, (dict, list)):
            replacement = json.dumps(value, ensure_ascii=False)
        elif isinstance(value, str):
            replacement = json.dumps(value, ensure_ascii=False)[1:-1]
        elif value is None:
            replacement = ""
        else:
            replacement = str(value)
        result = result.replace(f"{{{key}}}", replacement)

    result = re.sub(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}", "", result)
    if prune:
        try:
            result = json.dumps(_prune_empty(json.loads(result)), ensure_ascii=False)
        except (json.JSONDecodeError, ValueError):
            pass
    return result.strip()


def _prune_empty(obj):
    """Recursively drop empty strings/None/empty containers from a JSON-like structure."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            pruned = _prune_empty(v)
            if pruned in ("", None, {}, []):
                continue
            out[k] = pruned
        return out
    if isinstance(obj, list):
        return [_prune_empty(v) for v in obj if v not in ("", None)]
    return obj
