"""Configuration for the DCR shim — everything environment-specific, no secrets baked in."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Runtime configuration.

    Attributes:
        tenant_id: Entra (Azure AD) tenant id.
        client_id: the pre-provisioned App Registration client id the shim hands back from
            ``/register`` (Entra can't mint one dynamically, so we return this fixed one).
        redirect_uris: the loopback callbacks registered on the App Registration.
        public_base_url: the shim's own externally-reachable base URL (what the discovery
            document advertises as issuer / endpoints).
        scopes: default scopes advertised in discovery (e.g. ``["openid", "api://<id>/mcp"]``).
        auth_version: ``"v2"`` (default) or ``"v1"``. MUST match what the MCP server's JWT
            authorizer expects — see the blog post on the v1/v2 issuer trap.
    """

    tenant_id: str
    client_id: str
    redirect_uris: tuple[str, ...]
    public_base_url: str
    scopes: tuple[str, ...] = ("openid", "profile", "email", "offline_access")
    auth_version: str = "v2"

    @classmethod
    def from_env(cls) -> "Config":
        missing = [k for k in ("TENANT_ID", "CLIENT_ID", "PUBLIC_BASE_URL") if not os.environ.get(k)]
        if missing:
            raise SystemExit(f"dcr-shim: missing required env vars: {', '.join(missing)}")
        redirects = tuple(filter(None, os.environ.get("REDIRECT_URIS", "").split(",")))
        scopes = tuple(filter(None, os.environ.get("SCOPES", "").split(","))) or (
            "openid", "profile", "email", "offline_access",
        )
        return cls(
            tenant_id=os.environ["TENANT_ID"],
            client_id=os.environ["CLIENT_ID"],
            redirect_uris=redirects,
            public_base_url=os.environ["PUBLIC_BASE_URL"].rstrip("/"),
            scopes=scopes,
            auth_version=os.environ.get("AUTH_VERSION", "v2"),
        )
