---
title: "A declarative MCP server, and shipping it to a fleet"
date: 2026-06-26
draft: true
description: "Making 'add a tool' a one-line YAML change, a schema gotcha that's enforced Bedrock-side (the $ that curl accepts but the model rejects), and the distribution layer that decides whether anyone uses the thing."
summary: "A declarative YAML registry over a generic REST dispatcher, the $-in-schema finding, and the ccwb fleet-distribution lifecycle we extended."
series: ["Claude on Bedrock"]
series_order: 4
categories: ["Engineering"]
tags: ["MCP", "AWS", "Architecture", "Bedrock", "Distribution"]
---

<!-- Replace REPO_URL with the public companion repo once it's published. -->

The last piece is the capability layer — the MCP servers that let Claude see SharePoint and Jira — and the unglamorous machinery that gets the whole thing onto a laptop. Two properties matter more than cleverness here: adding a tool should be cheap, and installing should be boring. Both are design problems, and there's one sharp gotcha in the middle that only fails *through Claude*.

## A declarative MCP server

Both MCP servers share one design: a **declarative YAML tool registry** over a **generic REST dispatcher**. A tool isn't hand-written code — it's a YAML entry describing an HTTP call:

```yaml
get_post:
  description: "Get a single post by id."
  method: GET
  path: "/posts/{id}"
  path_params:
    id:
      type: integer
      required: true
```

The registry loader turns each entry into the MCP tool schema Claude sees; the dispatcher turns a tool call into the actual HTTP request — substituting path params, attaching query params, building the body, injecting the per-user token. Adding a capability is then *editing a YAML file and redeploying* — no new handler, no new tests beyond the data. The two servers differ only in outbound auth; everything else is shared machinery.

A couple of touches that pay off: **read-only hints derived from the HTTP method** (a `GET` tool is annotated read-only so the client can auto-approve it instead of prompting every call), and a **transport-agnostic protocol handler** that can run behind a local stdio transport (for development) or API Gateway + Lambda (in production) — one code path, two front doors. (Production ran on Lambda; the stdio runner is in the companion repo, handy for wiring the server into a desktop client locally.)

## The `$` that only Bedrock rejected

Here's the gotcha. The SharePoint MCP exposes Microsoft Graph's OData query params — `$select`, `$top`, `$expand` — and we first declared them as tool schema properties using their real names, dollar signs and all. Listing the tools worked. Then the model call failed:

```
API Error: 400 tools.N.custom.input_schema.properties:
Property keys should match pattern '^[a-zA-Z0-9_.-]{1,64}$'
```

Why it's sneaky: the validation is **Bedrock-side**, on the tool schema, enforced by the model — not by the downstream API. So the most natural test passes: a raw `curl` to Graph with `$select` works perfectly. Only the path *through Claude* fails, because that's the only place the schema is checked against `^[a-zA-Z0-9_.-]{1,64}$`, and `$` isn't in that set. You go hunting in your API integration; the bug is in a schema the model rejected before any API call happened.

The fix: expose a `$`-less property name to the client and translate back to the wire name when building the request. The schema builder strips the leading `$` (so `$select` becomes `select`); the dispatcher maps it back and emits `%24select`, which Graph accepts. A regression test asserts **no schema property key contains a `$`**, so a future tool can't reintroduce it. The general rule: any param whose wire name has a character outside `[a-zA-Z0-9_.-]` needs a friendly-name ↔ wire-name mapping at *both* ends.

## Shipping it to the fleet

A clever server that's painful to install doesn't get used. Pillar 1 — authenticated Bedrock access on a fleet machine — runs through the four-step lifecycle that [AWS's Guidance solution](https://github.com/aws-solutions-library-samples/guidance-for-claude-code-with-amazon-bedrock) provides (its `ccwb` CLI):

```
init       interactive setup; writes the local profile/config
deploy     provision the AWS infra (IdP, IAM, Bedrock access)
package    build the per-OS binaries + install scripts
distribute assemble the fleet installer (zip / S3) from the artifacts
```

We didn't reinvent it — we **extended** it, baking our [credential shim and Nuitka fix]({{< ref "getting-claude-code-onto-a-fleet-machine" >}}) into the `package` and `distribute` steps. The install script wires `credential_process` to point at the shim, with a fallback to the full binary if the shim is absent. The result is a single artifact a managed-device tool can push to the fleet, and an installer that configures `~/.aws/config` and the client settings without the user touching anything.

## The lesson

The interesting architecture is rarely the hard part of shipping. The hard part is making extension cheap — so the system grows without rotting — and making installation boring, so it actually lands on machines. A declarative registry turns "add a tool" into a data change; a scripted lifecycle turns "deploy to the fleet" into four commands. And the `$` finding is the same docs-vs-reality lesson in miniature: when two things that should agree (`curl` and the model) disagree, the running one is telling you the truth.

The declarative server — with the `$` translation and the no-`$` regression test — is in the companion repo at [rest-mcp-proxy](REPO_URL/tree/main/part-1-claude-on-bedrock/mcp-servers/rest-mcp-proxy).

That closes the first act — the proof-of-concept that went to production. Next, the second: stepping back to ask what the reusable *platform* looks like, going AgentCore-native.
