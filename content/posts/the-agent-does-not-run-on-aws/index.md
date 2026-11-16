---
title: "The agent doesn't run on AWS"
date: 2026-11-13T00:01:00Z
draft: true
description: "The opening of a series on running Claude through Amazon Bedrock for an enterprise. The first decisions were mostly about what not to build: no hosted agents, no vector index, no autonomous phase, no value baseline, each written down with what would reverse it."
summary: "What the platform is, why the agent loop stays on the user's machine, the AgentCore services we took and the ones we didn't, and the debts we chose to carry in writing."
series: ["Claude on AWS, the hard way"]
series_order: 1
categories: ["Work"]
tags: ["Claude", "Bedrock", "AgentCore", "Architecture", "MCP", "Governance"]
---

<!-- Sources: platform repo ADR 0001, 0006, 0007, 0011, 0013, 0028 and 0038.
     No ref links to later posts here: a published post cannot link to a draft. -->

Sketch "enterprise AI on AWS" on a whiteboard and you get agents hosted on AWS, a vector index of the company's documents, a managed memory service, maybe a fleet of autonomous agents writing reports overnight.

The platform this series is about has none of those, on purpose. The first decisions were mostly about **what not to build**, and each "no" was written down with what would turn it into a "yes". The series follows the platform one decision at a time, including the attempts that were reverted.

## The brief

- **Claude for the whole company:** Claude Desktop (Chat and Cowork) and Claude Code.
- **The model on Amazon Bedrock, in the EU.**
- **Wired to the systems people work in:** Microsoft 365 and SharePoint, Jira and Confluence, SAP LeanIX.
- **Every action taken as the user,** with an organisational policy on top and an audit trail.

## Decision 1: the agent loop stays on the user's machine

When someone asks Claude Desktop to find a document and summarise it, the loop that decides which tool to call runs in the app, on their laptop. We decided not to move it to AWS.

AWS hosts what the loop *reaches for*: **the model** on Bedrock, **the tools** behind AgentCore Gateway with a policy engine, and **the identity** that lets each tool act as the user. Designing as if AWS hosted the agent would have pulled in agent hosting and its operations, for a loop that already ran somewhere else. So the core of the platform became governance.

We accepted one consequence explicitly: **portability is limited by the client.** Claude Desktop and Claude Code are Anthropic's clients, and we didn't claim a model-agnostic architecture we couldn't honour.

## Decision 2: take AgentCore services by what breaks without them

| Service | Decision | Why |
|---|---|---|
| Gateway | Adopt | The only interception point the policy engine can use |
| Policy | Adopt | Write operations were already live with no authorisation of our own |
| Identity | Adopt | The path that lets each tool act as the user |
| Observability | Adopt first | You can't govern what you can't see |
| Memory | Defer | The client manages its own context |
| Registry | Defer | A handful of tools don't need a governed catalogue |
| Browser, Payments | Exclude | No use case |

The pricing made the decision for us. At about 100,000 tool calls a month for 300 users, the whole governance layer cost **less than the non-production environment**, and token spend was roughly three orders of magnitude larger. Every deferral carried its trigger: Registry when a second team publishes tools, Memory when an agent needs it. "Later" without a condition tends to mean never.

## Decision 3: no vector index

Retrieval already happens through the tools. The SharePoint tool searches through Microsoft Graph **with the user's own token**, so results are filtered by SharePoint's permissions, per user and per request, at no cost to us.

A separate index breaks that. Content copied into a vector store leaves SharePoint's access control behind, and the index has to reimplement it and keep it current. That's the tenant-wide exposure "every action as the user" exists to prevent, back in through a side door. What we gave up is cross-site semantic search. If it ever becomes a hard requirement, it's a project of its own, a *permission-trimmed* index with its own security review.

## Decision 4: pause the autonomous agents

The plan had a second phase of autonomous agents. When discovery opened, nobody had a use case. Every candidate failed one test:

> If a saved filter, a retention policy, a native notification or a workflow tool does the job, an agent isn't needed. It's an expensive cron job.

Stale tickets were a saved Jira filter; unreviewed documents, a retention policy; a weekly digest, native notifications. An autonomous agent earns its cost when a task needs **judgement across systems that no query can express**, and nobody had asked for one. So the phase is paused, with its triggers written down.

The pause left a finding worth more than the phase: **identity decides the architecture.** The platform's rule is that every tool acts as the user, and an autonomous agent has no user. Resuming means either an exception to the rule or rewriting it, and we wrote that down so nobody discovers it halfway through a build.

## Decision 5: ship without a value baseline, and say so

The platform had a quality baseline, a set of tasks that catches regressions. It didn't have a **value** baseline: what a task costs without the assistant, to compare with what it costs with it. That needed a business owner to choose the tasks, and none was identified. So we shipped without one and registered it as **debt**: the platform won't be able to answer *"how much time did this save?"* with a measured number.

Two things kept that from being reckless. The economics survive heavy discounting: a few cents per interaction against minutes of a knowledge worker's time. And the record says how to reverse it: **any cohort not yet onboarded is still a valid control group**, so the rollout schedule is also when that option expires.

## The platform today

```
 User's machine (the agent loop)
 Claude Desktop: Chat, Cowork, Code  ·  Claude Code CLI
        │                                   │
        │ model                             │ tools
        ▼                                   ▼
 Claude Apps Gateway (private)        OAuth shim (sign-in only)
   tiers by Entra App Role                  │
   spend limits per person                  ▼
        │                             AgentCore Gateway + Cedar policy
        ▼                               ├─ Microsoft Graph (as the user)
 Amazon Bedrock, EU profiles            ├─ Atlassian's MCP server (as the user)
                                        └─ SAP LeanIX's MCP server (as the user)

 Identity everywhere: Microsoft Entra ID
```

Two paths leave the laptop. The **model path** goes through Anthropic's Claude Apps Gateway, which decides which models each person may use and how much they may spend. The **tool path** goes through AgentCore Gateway, where a Cedar policy decides which tools each person may call, and every call reaches the downstream system as the user.

## What's in the series

1. The agent doesn't run on AWS (this post)
2. Every tool acts as the user, and what that costs
3. The OAuth shim we couldn't delete
4. Retiring our own MCP servers
5. Observability without leaking
6. Token governance: measure before you believe
7. From public to private in a week
8. The client: one key instead of a package
9. Building with an agent: rules born from scars

## The lesson

Most of the architecture of an enterprise AI platform is what you decide **not** to build. The pressure points the other way, because hosted agents, vector indexes and managed memory all show up in reference diagrams. A "no" is only as good as the reasoning written with it: what it costs, what would reverse it, and who has to say so. Without that, a deferral quietly becomes permanent.

Next: the rule that shaped everything, every tool acts as the user, and what it cost.
