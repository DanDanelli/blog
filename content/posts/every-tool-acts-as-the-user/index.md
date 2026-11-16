---
title: "Every tool acts as the user, and what that costs"
date: 2026-11-13T00:02:00Z
draft: true
description: "The rule that shaped the whole platform: no tool acts with its own identity. What it cost to make AgentCore Gateway forward the user's token and still authorise per tool: three reversals in two days, a token in the request body, and a Lambda that can't be removed."
summary: "Why every tool acts with the user's identity, the gateway that at first refused to forward it, the three reversals it took to get both identity and per-tool policy, and what the workaround cost until it could be retired."
series: ["Claude on AWS, the hard way"]
series_order: 2
categories: ["Work"]
tags: ["AgentCore", "Identity", "Entra ID", "Cedar", "MCP", "Security"]
---

<!-- Sources: platform repo ADR 0004, 0005, 0022 (with its amendment, resolution, correction and
     closing note), 0035 gate 6. -->

One rule on this platform bends every other decision: **no tool acts with its own identity.** When Claude searches SharePoint or reads a Jira ticket, the call reaches Microsoft or Atlassian as the person who asked, with that person's permissions.

It sounds like a configuration choice. Making it hold behind a policy gateway took three reversals in two days, a token carried somewhere tokens don't usually go, and a Lambda in the path of every tool call.

## Why the rule

With its own identity, a tool holding Graph `Sites.Read.All` lets **any user who can invoke it reach every SharePoint site in the tenant**, and the destination logs the application, not the person. With the user's identity, permissions come from the destination system per person, and the logs name the right person.

The rule has a price, and we wrote it down. Removing over-privilege promotes **indirect prompt injection** to the top risk: a document the agent reads can induce a write *within the user's own legitimate privileges*, and no IAM or Entra control notices. Identity can't defend against that. A policy that decides, **per tool**, what may run can.

In AgentCore, policy attaches to a **gateway**, so every tool had to sit behind one. Two rules, then: every tool acts as the user, and every tool sits behind a policy gateway. Together they collided.

## The collision

Our tool servers were containers on AgentCore Runtime, and the gateway offered two ways to front them. Each kept only one rule:

| | `mcpServer` targets | Runtime targets |
|---|---|---|
| The user's token reaches the tool | **No** | **Yes**, by passthrough |
| One consolidated tool list | Yes | No |

**Reversal one.** We chose Runtime targets: identity is what the platform exists for. It didn't last the day. The policy engine derives Cedar actions from the target type, and a Runtime target gets one action **per server**, not per tool. Our third attempt at a policy came back:

> Overly Permissive: Policy Engine will allow every request for the specified principal, action and resource combination

With one action per server, any permit means "everything on this server", and the engine won't store it. The prompt-injection defence needed *this* write denied by name. Our trade-off table had named aggregation as the price; the real price, per-tool authorisation, wasn't in it.

**Reversal two.** The option we'd dismissed that morning was `mcpServer` targets with a **request interceptor**, a Lambda the gateway calls before each request. It can receive the caller's headers and return an `Authorization` header to forward. A ten-line Lambda handing the token back would give us both properties. Within hours, a permit on `sharepoint_search_sites` and a forbid on `excel_set_range` were `ACTIVE`.

**Reversal three.** The next day, nothing worked. The gateway signs its call to a Runtime with **SigV4**, and the signature *is* the `Authorization` header. Our token overwrote it, and the Runtime rejected the request before the container saw anything. A custom header didn't survive the hop. The request **body** did. So the user's token moved into the MCP request's `params._meta`, under a namespaced key, and `Authorization` was left to SigV4. It looks like a hack, but it was the only option that conceded nothing on identity or on policy.

Then the governed path walked, with a real user token. Search returned the company's sites as the calling user, and `excel_set_range` returned `Tool Execution Denied: Tool call not allowed due to policy enforcement`. Denied by name, per tool. That line is what the three reversals were for.

## What the interceptor cost

AWS's documentation settled that it was structural: passthrough exists only for HTTP and Runtime targets, and only `mcpServer` targets give one action per tool. So we measured it:

- **Latency:** p50 1.68 ms and p95 7.9 ms warm, 73 to 89 ms cold.
- **Failure:** throttled to zero, it **failed closed** (`HTTP 500`, nothing forwarded) and took the whole tool plane with it, `tools/list` included. Reserved concurrency protects it.
- **Silent sync:** the engine only recognises tools the gateway has indexed. Add a tool and forget to synchronise the target, and the policy fails with *unrecognized action*.
- **A bearer token in the body**, which is exactly what traces record. Redaction had to cover `_meta`. Post 5 is about that.

## How it ended

Later our own tool servers went away (post 4), and the passthrough was due to go with the last container. The gate that removed it found the point of this post. The interceptor wrote the user's token into `_meta` on **every** request, whatever the target, because interceptors belong to the gateway and AgentCore offers no per-target form. Deleting the container would have removed the only consumer of the token and left the line that wrote it, sending the token in the body of every call to the vendors' servers.

So three things went in one apply: the container, the passthrough code, and the setting that hands headers to the interceptor, so it no longer even *receives* the token. We verified on real traffic that the gateway still calls it. The interceptor survived doing one job, an audit line per call.

## The lesson

The rule was right, and I'd make it again: nothing else gives you the user's permissions and the right name in the audit log. What I underestimated was making it hold *together with* per-tool policy.

- **A trade-off table lists only the costs you already know.** Write the first real policy before deciding, not just the comparison.
- **A workaround that moves a secret needs its removal planned with it.** Remove the consumer, the code that writes the secret and the setting that delivers it, in the same change.

Next: the client that couldn't sign in to the tool gateway at all, and the OAuth shim we built, then couldn't delete.
