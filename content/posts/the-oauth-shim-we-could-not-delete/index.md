---
title: "The OAuth shim we couldn't delete"
date: 2026-11-13T00:03:00Z
draft: false
description: "Why Claude Desktop can't sign in to an AgentCore Gateway MCP endpoint with Microsoft Entra ID (AADSTS9010010), the three workarounds we tried, and why the small OAuth shim we built to bridge the gap became the one component we can't remove."
summary: "AADSTS9010010, three workarounds, two reverted cutovers, and a one-character difference that turned a temporary OAuth shim into a load-bearing part of the platform."
series: ["Claude on AWS, the hard way"]
series_order: 3
categories: ["Work"]
tags: ["Entra ID", "OAuth", "MCP", "AgentCore", "Claude Desktop", "Identity"]
---

<!-- Sources: platform repo ADR 0024, 0025, 0031 and docs/investigations/forcing-a-403.md.
     Verify every external link before publishing. -->

The connector showed up in Claude Desktop exactly as configured. Clicking **Connect** opened a browser, the browser went to Microsoft Entra ID, and Entra answered:

```
AADSTS9010010: The resource parameter provided in the request doesn't match with the
requested scopes.
```

The AgentCore Gateway logged `Missing Bearer token`. It never saw a credential. Everything after sign-in already worked: a token minted by hand with a device-code flow got `HTTP 200` and the full tool list. The only thing failing was **the client getting that token by itself**.

This post is about the fix: a small OAuth shim built as a temporary workaround, which we then spent a month trying to delete.

## What was going on

The MCP authorization spec expects a client to discover everything from the server. Claude Desktop reads the gateway's protected-resource metadata and sends its `resource` value to Entra as a resource indicator ([RFC 8707](https://datatracker.ietf.org/doc/html/rfc8707)), next to the scope:

```
resource = https://<gateway-id>.gateway.bedrock-agentcore.<region>.amazonaws.com/mcp
scope    = api://<client-id>/mcp
```

Those are two identities, and Entra refuses to mix them. Every piece was fixed. The gateway advertises its `amazonaws.com` hostname and can't be told otherwise. Entra only registers identifier URIs on verified domains, and nobody verifies `amazonaws.com`. Entra publishes no dynamic registration endpoint ([RFC 7591](https://datatracker.ietf.org/doc/html/rfc7591)).

It's a gap between products, not a bug in one. The same error was open against at least six other projects, two of them Microsoft's own MCP servers.

## Three attempts

**Inject the header ourselves.** Claude Desktop supports a `headersHelper`, a local program that prints an `Authorization` header before each request. On paper it was the safest option. We spent days clearing its preconditions, and in the same hour we cleared the last one, we found an open issue: `headersHelper` is never invoked for HTTP `managedMcpServers` in Claude Desktop. The reporter's error was `Missing Bearer token`, the exact string our gateway logged. We'd have shipped a different failure with the same symptom.

**Front the gateway with our own domain.** We built it on API Gateway **REST**, and it failed twice: a stage prefix breaks the well-known path, and REST renames `WWW-Authenticate` on the way out. We concluded *a custom domain is unavoidable, and expensive.* That conclusion was wrong, and it took a month to notice. Both failures were specific to REST.

**The controlled experiment.** Our proof of concept, in production for months, served its own OAuth endpoints, and its connectors signed in fine. Same VM, same client, same tenant, two connectors side by side: ours failed, the proof of concept's listed 26 tools. The only variable was the server, and in its `/authorize` and `/token` handlers it did one thing that mattered:

```python
params.pop("resource", None)
```

## What shipped

We put the same idea in front of AgentCore Gateway, with one change we cared about: **only the OAuth routes reach our code.**

```
                 ┌─ /.well-known/*, /authorize, /token, /register ─▶ Lambda (sign-in only)
Claude Desktop ──┤
                 └─ /mcp ─────────────────────────────────────────▶ HTTP_PROXY ─▶ AgentCore Gateway
```

Tool traffic never touches a Lambda. The shim removes one query parameter from a sign-in request; identity, token validation, Cedar and the audit trail stay where they were. Before the first deploy we wrote down what would land in its logs, because `/token` carries codes and tokens: it logs only route, method and outcome.

## The second hour

Two weeks later it broke. The shim pinned the scope on `/authorize` but passed whatever the client asked for on `/token`. On a **refresh**, the client asked for a narrower scope, and the new token came back without the MCP scope.

The fix was one line and shipped that evening. The user stayed broken for **21 hours** anyway, because the client kept retrying a token it already held. Only quitting Claude Desktop completely, tray icon included, cleared it. That's now the first line of our support runbook.

An earlier version had left out `offline_access`. Both bugs sat on a path nobody tests at deploy time and everybody hits within hours. With OAuth code, the useful question is *"what happens in the second hour?"*

## Trying to delete it

A month later we came back to the custom domain, on the substrate we'd actually chosen. Entra accepted a second identifier URI and issued tokens with our hostname as audience, and the gateway accepted them. The plan was to delete `/authorize` and `/token` entirely.

That's where it failed, on one character:

```
resource=https://mcp.example.com/mcp    →  accepted
resource=https://mcp.example.com/mcp/   →  AADSTS9010010
```

A client pointed straight at Entra normalises the URL to the second form, and with nobody in the path, nothing corrects it. So the shim stayed, and its job flipped: instead of **removing** `resource`, it now **pins** it to the exact canonical value.

Getting there cost two reverted cutovers and a set of failures with one thing in common: **each step reported success and left the wrong state behind.** Changing a response mapping on an existing API Gateway integration silently deleted it, three times. An explicit route returned an error document under `HTTP 200`. A path in the resource identifier moved the well-known URL ([RFC 9728 §3.1](https://datatracker.ietf.org/doc/html/rfc9728#section-3.1)), and we'd dismissed that exact request in the logs an hour earlier. One more thing: **the connect URL is an identity, not an address.** It lives in managed device policy, so changing the advertised identity means changing what you ship to every machine.

## The lesson

We built the shim as a liability: our code in the token path caused two outages, one of 21 hours. What we missed is that the same position is the **only place a defect in someone else's client can be fixed**. It goes away when the client stops mangling the resource, or when the gateway lets you set what it advertises, and not before.

- **A failed attempt tells you about that attempt.** "Custom domains don't work" meant "don't work on API Gateway REST". Write the substrate into the conclusion.
- **Ask what happens in the second hour.** Refresh, expiry and a stale token are where OAuth code breaks.
- **Measure after every apply, especially the ones you think are inert.** Every expensive failure here came from a step that reported success.

Next: retiring our own MCP servers in favour of the vendors', and the vendor defects that came with them.
