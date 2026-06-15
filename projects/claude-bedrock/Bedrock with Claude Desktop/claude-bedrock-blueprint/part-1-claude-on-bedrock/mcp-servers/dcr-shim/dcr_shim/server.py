"""HTTP plumbing for the DCR shim — wires the four public routes to the pure builders.

This is a stdlib ``http.server`` reference. In the serverless deployment these same four
routes live on the MCP server's API Gateway as public (un-authorized) routes; the logic in
``oauth.py`` is identical.

Routes:
  GET  /.well-known/oauth-authorization-server  → discovery document
  GET  /.well-known/openid-configuration        → discovery document (alias)
  POST /register                                 → DCR handshake (returns the static client_id)
  GET  /authorize                                → 302 redirect to Entra authorize
  POST /token                                    → forward the token form to Entra, relay JSON
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import Config
from .oauth import authorize_location, discovery_document, register_response, token_target

_DISCOVERY_PATHS = (
    "/.well-known/oauth-authorization-server",
    "/.well-known/openid-configuration",
)


def make_handler(cfg: Config):
    class Handler(BaseHTTPRequestHandler):
        server_version = "dcr-shim/0.1"

        # -- helpers ----------------------------------------------------------------
        def _json(self, status: int, body: dict) -> None:
            payload = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _path(self) -> str:
            return urllib.parse.urlparse(self.path).path

        def _query(self) -> dict:
            qs = urllib.parse.urlparse(self.path).query
            return {k: v[0] for k, v in urllib.parse.parse_qs(qs).items()}

        def _read_body(self) -> bytes:
            length = int(self.headers.get("Content-Length", 0) or 0)
            return self.rfile.read(length) if length else b""

        # -- routes -----------------------------------------------------------------
        def do_GET(self):  # noqa: N802 (http.server API)
            path = self._path()
            if path in _DISCOVERY_PATHS:
                return self._json(200, discovery_document(cfg))
            if path == "/authorize":
                location = authorize_location(cfg, self._query())
                self.send_response(302)
                self.send_header("Location", location)
                self.end_headers()
                return None
            return self._json(404, {"error": "not_found"})

        def do_POST(self):  # noqa: N802
            path = self._path()
            if path == "/register":
                try:
                    parsed = json.loads(self._read_body() or b"{}")
                except json.JSONDecodeError:
                    return self._json(400, {"error": "invalid_client_metadata"})
                requested = parsed.get("redirect_uris") if isinstance(parsed, dict) else None
                return self._json(201, register_response(cfg, requested))
            if path == "/token":
                return self._forward_token(self._read_body())
            return self._json(404, {"error": "not_found"})

        def _forward_token(self, body: bytes) -> None:
            """Relay the token form POST to Entra and pass the response straight back."""
            req = urllib.request.Request(
                token_target(cfg),
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=25) as r:
                    payload = r.read()
                    status = r.status
            except urllib.error.HTTPError as e:
                payload, status = e.read(), e.code
            except Exception as e:  # network failure
                return self._json(502, {"error": "token_endpoint_unreachable", "detail": str(e)})
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):  # keep test output quiet
            pass

    return Handler


def serve(cfg: Config, host: str = "127.0.0.1", port: int = 8401) -> None:
    httpd = ThreadingHTTPServer((host, port), make_handler(cfg))
    httpd.serve_forever()
