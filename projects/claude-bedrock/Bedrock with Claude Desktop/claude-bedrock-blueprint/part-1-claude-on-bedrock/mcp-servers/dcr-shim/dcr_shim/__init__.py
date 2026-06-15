"""dcr-shim — a minimal OAuth/DCR bridge that fronts Microsoft Entra ID.

Entra does not implement Dynamic Client Registration (RFC 7591), which MCP clients like
Claude expect. This shim exposes the DCR-shaped surface (`/.well-known/...`, `/register`,
`/authorize`, `/token`) and bridges the real auth-code + PKCE flow to Entra. Handshake only:
it never sees a tool call.

See the package README for the full design and the blog post it backs.
"""

__version__ = "0.1.0"
