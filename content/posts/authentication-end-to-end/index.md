---
title: "Authentication end to end: getting Claude in, and acting as the user"
date: 2026-06-22
draft: true
description: "The full identity story for an MCP server behind Entra ID: the exact App Registration settings, why Claude's DCR bootstrap fails against Entra, the admin-consent trap, and choosing how the server calls a downstream API as the user."
summary: "Inbound (Entra App Registration + the DCR problem + admin consent) and outbound (On-Behalf-Of vs a managed token vault) — the whole auth path, and where the docs lie."
series: ["Claude on Bedrock"]
series_order: 3
categories: ["Engineering"]
tags: ["Entra ID", "Azure AD", "OAuth", "DCR", "MCP", "Identity", "Microsoft Graph"]
---

<!-- Replace REPO_URL with the public companion repo once it's published. -->

Authentication for an MCP server has two halves, and both bite. **Inbound:** Claude has to authenticate *to* your server (in an enterprise, via Microsoft Entra ID). **Outbound:** the server then has to call a downstream API — SharePoint, Jira — *as that user*, not as a shared service account. This post walks the whole path, because the gotchas are spread across all of it, and they're the kind that cost an afternoon each.

## Inbound, part 1 — the Entra App Registration

Each MCP server is fronted by one Entra App Registration. The settings are fiddly and interlocking; one wrong toggle produces a sign-in that fails opaquely. Here's what actually has to be true:

- **Expose an API.** Application ID URI `api://{client_id}`, plus a scope named `mcp`. That gives `api://{client_id}/mcp` — the scope the server validates.
- **Public client.** Add a *"Mobile and desktop applications"* platform and enable **"Allow public client flows."** Claude Desktop can't keep a secret, so it uses auth-code + PKCE, not a client secret.
- **Loopback redirect URIs.** e.g. `http://127.0.0.1:8400/callback`, `http://localhost:8400/callback`. These are where the PKCE login lands back in the desktop client. If the URI isn't registered exactly, Entra refuses the redirect.
- **Token audience and issuer.** The API Gateway's JWT authorizer expects audience `api://{client_id}` and issuer `https://sts.windows.net/{tenant_id}/` (the **v1** issuer). The trap is the token version: leave it at v1, or flip the authorizer to match v2 (`.../v2.0`). Mismatch = every token silently rejected.
- **Sign-in baseline permissions.** Microsoft Graph **delegated**: `openid`, `profile`, `email`, `offline_access`, `User.Read` — and grant admin consent (see the trap below).

## Inbound, part 2 — the admin-consent trap

Adding that permission baseline should be routine. Microsoft's docs even mark the relevant Graph permissions as **"admin consent required: No."** So no special approval needed, right?

A device-code sign-in returned the **"Need admin approval"** screen anyway.

The reason: the tenant has **user consent disabled tenant-wide.** When that's the case, the per-permission flag in the docs is irrelevant — *no* ordinary user can consent to anything. The Azure portal even warns, in small print, that the "admin consent required" column may not reflect your org's policy. Here it didn't. The implication is operational: treat admin consent as a **fixed lead-time dependency**, and **capture every scope up front** so you request consent once instead of waiting again the day you discover a second scope.

## Inbound, part 3 — the DCR problem

Here's the part that isn't in any setup table, and the one most likely to stop you cold.

MCP clients like Claude bootstrap auth with **Dynamic Client Registration** (DCR, [RFC 7591](https://datatracker.ietf.org/doc/html/rfc7591)). The flow Claude expects:

1. Fetch `/.well-known/oauth-authorization-server` to discover the OAuth endpoints.
2. **`POST /register`** to dynamically obtain a `client_id`.
3. Run `/authorize` + `/token` (auth-code + PKCE) with that `client_id`.

It's elegant, and it does not work against Entra — because **Entra ID does not implement DCR.** There's no `/register` to call. Point Claude straight at Entra's OAuth endpoints and the bootstrap dies at step 2.

### The workaround: an OAuth/DCR shim in front of Entra

Give Claude the DCR-shaped surface it's looking for. The MCP server's API Gateway exposes a few **public** routes the JWT authorizer doesn't guard:

```
/.well-known/*   ← OAuth discovery
/authorize       ← bridges to Entra's authorize endpoint
/token           ← bridges to Entra's token endpoint
/register        ← the DCR endpoint Entra is missing
```

`/register` answers the handshake by handing back the **pre-provisioned** `client_id` and the loopback redirect URIs, so Claude believes it registered dynamically. Discovery advertises the shim's *own* `/authorize` and `/token` (single origin for the client); those routes then bridge the real auth-code + PKCE flow to Entra, which *does* support that part. Two properties keep it honest: it's **handshake-only** (real tool traffic goes through the JWT-authorized route — the shim never sees a tool call), and `client_id` is **forced**, never trusted from the client. In the PoC each server carried its own copy of this shim; the framework later factors it into a standalone bridge, because Claude Desktop is only one client type.

## Outbound — On-Behalf-Of vs a managed token vault

Once Claude is authenticated *to* the server, the server has to call the downstream API as the user. Two mechanisms:

- **OAuth On-Behalf-Of (OBO):** exchange the inbound user token directly with the IdP for a downstream token (`grant_type=jwt-bearer`, `requested_token_use=on_behalf_of`). No extra infra.
- **A managed token vault / broker:** a managed service brokering 3-legged OAuth, storing refresh tokens, with its own consent callback.

The original plan assumed the broker for everything — the "enterprise-grade" instinct. Then we probed it. For the same-tenant case (the server and Microsoft Graph in the same tenant), the OBO exchange **succeeds server-side, returns 200, and isn't blocked by Conditional Access** — which was the very concern that had justified the broker. That invalidated the default. And OBO has a *better* posture here: no persisted refresh tokens at all — on a miss it re-exchanges from the always-fresh inbound token.

So the decision split by topology:

| Downstream | Mechanism | Why |
|---|---|---|
| Microsoft 365 / SharePoint (same tenant) | **OBO** | Works under Conditional Access; no infra; no stored refresh tokens |
| Atlassian (different vendor) | **Managed broker** | Cross-vendor 3-legged OAuth — OBO can't span IdPs, so the broker is genuinely required |

Both answers are right, for different downstreams. OBO isn't universally better; it's better when the downstream shares your tenant.

## The lesson

The whole identity path is one long exercise in **trusting the environment over the documentation.** A permission flag that the tenant overrode; a DCR standard the client speaks but the IdP doesn't implement; a Conditional Access fear that a probe disproved. In each case two sources that should agree didn't — and the running one won. Recognizing "these two systems disagree about the protocol" is half the work; the other half is a thin bridge (or a tested assumption) that closes the gap.

The DCR shim and runnable outbound-auth examples (OBO + brokered 3LO) are in the companion repo: [dcr-shim](REPO_URL/tree/main/part-1-claude-on-bedrock/mcp-servers/dcr-shim) and [mcp-servers/examples](REPO_URL/tree/main/part-1-claude-on-bedrock/mcp-servers/examples).

Next: [a declarative MCP server, and shipping it]({{< ref "declarative-mcp-server-and-shipping-it" >}}).
