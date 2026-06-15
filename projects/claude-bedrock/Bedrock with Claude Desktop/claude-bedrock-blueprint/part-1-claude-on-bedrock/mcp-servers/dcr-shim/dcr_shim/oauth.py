"""Pure OAuth/DCR builders — no I/O, so they're trivially testable.

The shim's whole job is translating between *the DCR flow Claude wants* and *the flow Entra
actually offers*. That translation is all here; ``server.py`` only does the HTTP plumbing.
"""

from __future__ import annotations

import urllib.parse
from typing import Iterable

from .config import Config

# Standard authorize params we forward from the client to Entra. ``client_id`` is forced to
# the pre-provisioned app (never trusted from the client), so it's not in this pass-through.
_AUTHORIZE_PASSTHROUGH = (
    "redirect_uri",
    "response_type",
    "scope",
    "state",
    "code_challenge",
    "code_challenge_method",
    "nonce",
    "prompt",
    "login_hint",
)


def entra_authorize_url(tenant_id: str, version: str = "v2") -> str:
    base = f"https://login.microsoftonline.com/{tenant_id}/oauth2"
    return f"{base}/v2.0/authorize" if version == "v2" else f"{base}/authorize"


def entra_token_url(tenant_id: str, version: str = "v2") -> str:
    base = f"https://login.microsoftonline.com/{tenant_id}/oauth2"
    return f"{base}/v2.0/token" if version == "v2" else f"{base}/token"


def discovery_document(cfg: Config) -> dict:
    """The `/.well-known/oauth-authorization-server` body.

    Issuer and endpoints point at the **shim** (single origin for the client); the shim then
    relays to Entra. ``registration_endpoint`` is the whole reason this exists — Entra has no
    such endpoint, so we advertise our own.
    """
    base = cfg.public_base_url
    return {
        "issuer": base,
        "authorization_endpoint": f"{base}/authorize",
        "token_endpoint": f"{base}/token",
        "registration_endpoint": f"{base}/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": list(cfg.scopes),
    }


def register_response(cfg: Config, requested_redirect_uris: Iterable[str] | None = None) -> dict:
    """Answer a DCR `POST /register`.

    Entra can't mint a client dynamically, so we return the **pre-provisioned** ``client_id``
    and the loopback redirect URIs the App Registration already allows. The client believes
    it registered dynamically; really it just learned the static id.
    """
    requested = [u for u in (requested_redirect_uris or []) if u in cfg.redirect_uris]
    return {
        "client_id": cfg.client_id,
        "redirect_uris": requested or list(cfg.redirect_uris),
        "token_endpoint_auth_method": "none",
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
    }


def authorize_location(cfg: Config, query_params: dict) -> str:
    """Build the Entra authorize URL to 302-redirect the client to.

    Forces our real ``client_id`` and passes through the standard PKCE/auth-code params.
    """
    out: dict[str, str] = {"client_id": cfg.client_id}
    for key in _AUTHORIZE_PASSTHROUGH:
        if key in query_params and query_params[key] not in (None, ""):
            out[key] = query_params[key]
    out.setdefault("response_type", "code")
    return f"{entra_authorize_url(cfg.tenant_id, cfg.auth_version)}?{urllib.parse.urlencode(out)}"


def token_target(cfg: Config) -> str:
    """The Entra token endpoint the shim forwards the `/token` form POST to."""
    return entra_token_url(cfg.tenant_id, cfg.auth_version)
