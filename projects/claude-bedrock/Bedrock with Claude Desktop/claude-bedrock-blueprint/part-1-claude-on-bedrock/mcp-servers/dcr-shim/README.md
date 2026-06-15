# dcr-shim — an OAuth/DCR bridge in front of Entra ID (backs the Entra/DCR post)

> **Status:** implemented (reference). `dcr_shim/` is the package, `tests/` the suite. Runs
> as a local stdlib server; in production the same four routes live as **public** routes on
> the MCP server's API Gateway.

## The problem

MCP clients like Claude bootstrap auth with **Dynamic Client Registration** (DCR,
[RFC 7591](https://datatracker.ietf.org/doc/html/rfc7591)): discover `/.well-known/...`,
`POST /register` to get a `client_id`, then run auth-code + PKCE. **Microsoft Entra ID does
not implement DCR** — there's no `/register` — so pointing Claude straight at Entra fails at
the registration step.

## What this does

Presents the DCR-shaped surface Claude expects, and bridges the real flow to Entra:

```
GET  /.well-known/oauth-authorization-server   discovery (issuer = this shim)
GET  /.well-known/openid-configuration         discovery (alias)
POST /register                                  returns the PRE-PROVISIONED client_id
GET  /authorize                                 302 → Entra authorize (client_id forced)
POST /token                                     forwards the form to Entra, relays the JSON
```

The client thinks it registered dynamically; really it learned the static `client_id` from
your App Registration. The actual login is plain auth-code + PKCE against Entra.

## Design notes / security

- **Handshake only.** These routes exist to mint a token. Real tool traffic goes through the
  JWT-authorized route, which the shim never touches. This is also the *only* public
  (un-authorized) surface, so it stays minimal.
- **`client_id` is forced, never trusted from the client.** `/authorize` overrides any
  client-supplied `client_id` with the configured one; `/register` only echoes redirect URIs
  that are on the App Registration's allow-list.
- **The v1/v2 trap.** `AUTH_VERSION` must match what the MCP server's JWT authorizer expects
  (issuer `sts.windows.net/{tenant}/` for v1 vs `login.microsoftonline.com/{tenant}/v2.0`
  for v2). Mismatch = every token silently rejected.

## Run it locally

```bash
pip install -e ".[dev]"
TENANT_ID=YOUR_TENANT \
CLIENT_ID=YOUR_APP_REG_CLIENT_ID \
PUBLIC_BASE_URL=https://your-shim.example.com \
REDIRECT_URIS=http://127.0.0.1:8400/callback,http://localhost:8400/callback \
AUTH_VERSION=v2 \
python -m dcr_shim
```

## Develop / test

```bash
pip install -e ".[dev]"
pytest        # pure builders + live-server route checks (no network needed)
ruff check .
```

## Relationship to the framework

In the PoC each MCP server carried its own copy of this shim. The framework (Part 2)
factors it out into a standalone **DCR bridge** and treats DCR as a *profile* — because
Claude Desktop is only one client type and not every client needs DCR. See
[`part-2-aws-ai-framework`](../../../part-2-aws-ai-framework/) → profiles.
