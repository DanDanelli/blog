"""Pure OAuth/DCR builder tests + an end-to-end check of the local server's routes."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from dcr_shim.config import Config
from dcr_shim.oauth import (
    authorize_location,
    discovery_document,
    entra_authorize_url,
    entra_token_url,
    register_response,
)
from dcr_shim.server import make_handler

CFG = Config(
    tenant_id="tenant-123",
    client_id="client-abc",
    redirect_uris=("http://127.0.0.1:8400/callback", "http://localhost:8400/callback"),
    public_base_url="https://shim.example.com",
    scopes=("openid", "api://client-abc/mcp"),
    auth_version="v2",
)


# --- pure builders -------------------------------------------------------------------
def test_entra_endpoints_v2_and_v1():
    assert entra_authorize_url("t", "v2").endswith("/oauth2/v2.0/authorize")
    assert entra_token_url("t", "v2").endswith("/oauth2/v2.0/token")
    assert entra_authorize_url("t", "v1").endswith("/oauth2/authorize")
    assert entra_token_url("t", "v1").endswith("/oauth2/token")


def test_discovery_points_at_shim_and_advertises_registration():
    doc = discovery_document(CFG)
    assert doc["issuer"] == "https://shim.example.com"
    assert doc["registration_endpoint"] == "https://shim.example.com/register"
    assert doc["authorization_endpoint"] == "https://shim.example.com/authorize"
    assert doc["code_challenge_methods_supported"] == ["S256"]


def test_register_returns_static_client_id():
    body = register_response(CFG, ["http://127.0.0.1:8400/callback"])
    assert body["client_id"] == "client-abc"
    assert body["redirect_uris"] == ["http://127.0.0.1:8400/callback"]
    assert body["token_endpoint_auth_method"] == "none"


def test_register_filters_unknown_redirects():
    body = register_response(CFG, ["http://evil.example/callback"])
    # Unknown redirect is dropped; falls back to the configured allow-list.
    assert body["redirect_uris"] == list(CFG.redirect_uris)


def test_authorize_forces_client_id_and_preserves_pkce():
    loc = authorize_location(
        CFG,
        {
            "client_id": "attacker-supplied",  # must be overridden
            "redirect_uri": "http://127.0.0.1:8400/callback",
            "code_challenge": "abc123",
            "code_challenge_method": "S256",
            "state": "xyz",
        },
    )
    q = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query)
    assert q["client_id"] == ["client-abc"]  # forced, not the attacker value
    assert q["code_challenge"] == ["abc123"]
    assert q["state"] == ["xyz"]
    assert loc.startswith("https://login.microsoftonline.com/tenant-123/oauth2/v2.0/authorize")


# --- live server routes --------------------------------------------------------------
@pytest.fixture
def base_url():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(CFG))
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    host, port = httpd.server_address
    yield f"http://{host}:{port}"
    httpd.shutdown()


def test_discovery_route(base_url):
    with urllib.request.urlopen(f"{base_url}/.well-known/oauth-authorization-server") as r:
        doc = json.loads(r.read())
    assert doc["registration_endpoint"].endswith("/register")


def test_register_route(base_url):
    req = urllib.request.Request(
        f"{base_url}/register",
        data=json.dumps({"redirect_uris": ["http://localhost:8400/callback"]}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 201
        body = json.loads(r.read())
    assert body["client_id"] == "client-abc"


def test_authorize_route_redirects(base_url):
    # Don't follow the redirect (it would hit Entra); just inspect the 302.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    try:
        opener.open(f"{base_url}/authorize?redirect_uri=http://127.0.0.1:8400/callback&code_challenge=x&code_challenge_method=S256")
        raise AssertionError("expected a redirect, not a 200")
    except urllib.error.HTTPError as e:
        assert e.code == 302
        assert e.headers["Location"].startswith("https://login.microsoftonline.com/tenant-123/")


def test_unknown_route_404(base_url):
    try:
        urllib.request.urlopen(f"{base_url}/nope")
        raise AssertionError("expected 404")
    except urllib.error.HTTPError as e:
        assert e.code == 404
