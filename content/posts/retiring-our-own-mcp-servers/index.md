---
title: "Retiring our own MCP servers"
date: 2026-11-13T00:04:00Z
draft: false
description: "We started with two MCP servers of our own and ended with none. How SAP LeanIX, Microsoft 365 and Atlassian each reached AgentCore Gateway without a container: a pinned catalogue we wrote and deleted, an OpenAPI schema, a vendor server, and the vendor defects that came with it."
summary: "Three tool integrations, three different routes to no container, the rule that decided each one, and what a vendor's MCP server costs in policy granularity and in defects you work around instead of chasing."
series: ["Claude on AWS, the hard way"]
series_order: 4
categories: ["Work"]
tags: ["MCP", "AgentCore", "Cedar", "Atlassian", "Microsoft Graph", "SAP LeanIX"]
---

<!-- Sources: platform repo ADR 0030 (not adopted), 0032, 0034, 0035 (with its §9 amendment),
     and the vendor-defects investigation of 2026-09-29. -->

The proof of concept came with two MCP servers we'd written ourselves, for Microsoft 365 and for Jira and Confluence. Behind AgentCore Gateway they became containers on AgentCore Runtime, and [the previous post]({{< ref "every-tool-acts-as-the-user" >}}) was about what it cost to get the user's token to them.

By the end of September there were no containers left. Each of the three systems got there differently, and each left a rule behind.

## SAP LeanIX: the adapter we wrote and deleted

The request was to build an MCP server for SAP LeanIX. SAP already publishes one. The vendor's endpoint is its own OAuth server, with no client-credentials grant, which ruled out the lazy option: a technical user's API key would have been an application identity against per-person data.

The first design was a container that exposed a **pinned catalogue** of three read-only tools instead of relaying SAP's. It was written, reviewed and deleted, on my objection: **pinning a copy of the vendor's catalogue defeats the point of using the vendor's server.** Without the pin the container had nothing left to do, so the gateway now reaches the vendor directly, gets each user's token through AgentCore Identity, and Cedar decides what's reachable.

That became a standing rule: **the vendor owns the tool catalogue.** If keeping up with it has an operational cost, we fix the cost, not the catalogue.

### A target is an action group

Our repository said, in four files, that Cedar has no action wildcards, so every tool must be named. The first half is true; the second doesn't follow. A gateway target *is* a Cedar action group, and `action in` takes one. We measured it with a control: a `forbid` on the real target reached `ACTIVE`, and the same statement on a non-existent target failed. Repetition across four files had looked like corroboration.

One statement permitted all 49 tools SAP exposed. Our records from nine days earlier said 47: **two had arrived and nobody had been told.** That's the argument for the action group and against it. An hour later I narrowed it to the 43 read-only tools, because the read/write line is ours to draw. `execute_code` is withheld too: it runs JavaScript that calls other tools, which the gateway never sees.

| Form | When to use it |
|---|---|
| One statement per target (`action in`) | The vendor owns the catalogue and every tool in it is acceptable |
| One permit per tool | The read/write line is ours, and we want it readable in the policy |

## Microsoft 365: a schema instead of a container

Our Microsoft 365 server was mostly a translator, MCP in and Graph REST out. AgentCore Gateway can call a REST API from an **OpenAPI schema** and do the on-behalf-of exchange itself. We measured it against the real tenant in a day: the exchange works, Cedar gets one action per `operationId`, and the call carries the user's identity. `GET /me/followedSites` returned `200`, and Graph refuses every `/me` path to an application token. That check was added by the refutation step (post 9), which found the probe couldn't otherwise tell a delegated token from an application one.

The case for keeping the container was traceability. It failed on its own terms: the container's tracing had no exporter, so **no span had ever left the account.** It was buying the *option* to build traceability, not traceability.

The costs were written down before the cutover:

- **Pagination stops.** A schema can't follow `@odata.nextLink`.
- **Error translation is lost.** Users see Entra's raw response instead of *"an administrator must grant consent"*.
- **Tool annotations are lost**, so the client may not ask before a write. Cedar, the actual control, is unchanged.
- **The target type can't change in place,** so all 26 tools vanished from `tools/list` for a window, failing closed.

The rule this left: **the test isn't "no containers", it's "no container that is only a proxy".** A container that resolves a per-user route, translates errors or follows pagination does work a schema can't describe. For Microsoft 365, the answer to *what breaks if it's removed* was close enough to nothing.

## Atlassian: the one a schema couldn't take

Every Jira and Confluence path includes a `cloudId` the model doesn't supply, and our container resolved it per user. An OpenAPI target has nowhere to run that lookup. But Atlassian's own remote MCP server resolves it from the caller's token.

Its catalogue is **deferred**: `tools/list` returns 10 tools, and about 300 operations sit behind three of them, `executeRead`, `executeWrite` and `executeDestructive`, addressed by name. Cedar sees `executeRead` as one action. So knowing which operation ran became a **gate**: the interceptor from post 2 writes one line per call with the **operation name, never the arguments**.

```
deferred-dispatch action=mcp-atlassian-cloud___executeRead operation=getJiraIssue id=1
```

Getting there cost two mistakes of our own. The deployed interceptor was **seven weeks older** than the code we thought was running, found by reading a timestamp in a plan. And we'd removed a scope from a working configuration on an inference, which cost a day.

### Two vendor defects, worked around and not chased

The target then failed with `Method not found`. Probed directly, Atlassian's `initialize` advertises **`resources`**, and `resources/list` answers `-32601`. AgentCore syncs every advertised capability, so it failed the whole target, though `tools/list` had succeeded.

AWS documents a route for this: hand the gateway the tool schema instead of letting it fetch it. A script reads the live `tools/list` and writes the file, and re-running it refreshes it. That's not us owning the catalogue; the 300 operations stay Atlassian's. We wrote the defects down with the evidence and chose not to chase them, so the workaround is never mistaken for a design choice.

## The lesson

Two servers we owned became none, by three routes: a deleted adapter, a schema and a vendor server.

- **The vendor owns the catalogue.** A copy in your configuration is wrong within days, as two tools in nine days showed. Govern it with policy.
- **Keep a container only for work a schema can't describe.** If its only job is translation, it's a proxy, and the gateway can do that.
- **A vendor's server sets your policy granularity.** Where 300 operations hide behind three tools, the audit line is all you have left. Know that before promising per-operation control.

Next: what all of this writes to the logs, and the token that landed in CloudWatch in clear text.
