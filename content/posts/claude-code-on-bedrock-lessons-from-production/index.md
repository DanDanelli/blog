---
title: "What I learned taking Claude Code on Bedrock to production"
date: 2026-06-16
draft: true
description: "Running Claude Code against Amazon Bedrock on managed fleet machines — why you'd do it, the two pillars it takes, and the production findings that only show up once you ship."
summary: "The journey from proof-of-concept to production: why Bedrock, the architecture, the AWS Guidance baseline we improved on, and a tour of the hard-won lessons."
series: ["Claude on Bedrock"]
series_order: 1
categories: ["Engineering"]
tags: ["AWS", "Bedrock", "Claude", "MCP", "Architecture"]
---

<!-- Replace REPO_URL with the public companion repo once it's published. -->

I spent a chunk of this year taking something from "let's see if this works" to "the whole team uses it daily": **Claude Code running against Amazon Bedrock** on a fleet of managed enterprise machines, wired to internal systems through custom MCP servers. This post is the overview — why you'd build this, what it takes, and the lessons that only surfaced once it met real machines and real users. The deep dives that follow each unpack one theme; the runnable code lives in a [companion repo](REPO_URL).

## Why Bedrock at all?

If you can call Claude through the public API, why put Amazon Bedrock in front of it? For an individual, you wouldn't. For an enterprise, the answer is **governance**. Routing model traffic through Bedrock means it rides on the same AWS account, IAM, networking, logging and data-residency guarantees the rest of the company already lives under. Access is brokered by the corporate identity provider, every call is attributable, and nothing leaves the boundary the security team already reasons about. When you want hundreds of engineers using Claude Code without standing up a parallel trust model, Bedrock is the path of least resistance.

That decision is the easy part. Making it pleasant to *use* on a locked-down corporate laptop is where the interesting problems live.

## The two pillars

The work splits cleanly in two, versioned and shipped separately:

**Pillar 1 — authenticated Bedrock access on the machine.** Claude Code authenticates to AWS using a `credential_process`: a small binary that exchanges an OIDC login (via the corporate IdP) for short-lived AWS credentials. That binary is built per OS and shipped to the fleet — a whole build/package/install pipeline behind the scenes.

**Pillar 2 — connecting Claude to internal systems.** Out of the box Claude can reason but can't see your SharePoint or your Jira. MCP (the Model Context Protocol) is how you give it eyes: small servers that expose internal APIs as tools. We built two — Microsoft 365 / SharePoint and Atlassian — sharing one design, differing only in how they authenticate to the downstream system.

```
 Developer machine        Microsoft Entra ID         AWS account
┌─────────────────────┐   ┌──────────────────┐      ┌──────────────────────────────┐
│ Claude Code/Desktop  │   │  corporate IdP    │      │  Amazon Bedrock                │
│  • credential_process│   │  (OIDC, in Azure) │      │  API Gateway ─▶ Lambda (MCP)   │
│  • MCP client        │   └──────────────────┘      │    ├─ SharePoint (MS Graph)    │
└─────────────────────┘                              │    └─ Atlassian (Jira/Conf.)   │
                                                      └──────────────────────────────┘

 Bedrock auth:  credential_process ──OIDC login──▶ Entra ID ──id token──▶ AWS STS
                (AssumeRoleWithWebIdentity — direct federation, no Cognito)
                ──▶ short-lived AWS creds ──▶ Amazon Bedrock
 MCP calls:     MCP client ──HTTPS + Entra JWT──▶ API Gateway ──▶ Lambda
```

The identity anchor for *both* paths is Microsoft Entra ID, living in Azure — not in the AWS account. Bedrock access is a direct STS federation of an Entra login (no Cognito in the middle); the MCP calls carry an Entra-issued JWT that API Gateway validates.

## We didn't build Pillar 1 from scratch

Worth being clear up front: AWS publishes a **Guidance** for exactly this — [`guidance-for-claude-code-with-amazon-bedrock`](https://github.com/aws-solutions-library-samples/guidance-for-claude-code-with-amazon-bedrock). (A *Guidance* in the [AWS Solutions Library](https://aws.amazon.com/solutions/) is a published, opinionated reference implementation — real deployable code, not a whitepaper.) It ships a CLI (`ccwb`) that drives the whole lifecycle: configure a profile, deploy the AWS infra, build the per-OS credential binaries, package an installer. We took that as our foundation and **improved it where production hurt**. So when I describe a fix below, the honest framing is: AWS's solid baseline, plus the changes we had to make once it met our fleet.

## The throughline: docs vs. reality

If there's one theme, it's this: **almost every finding worth writing down was a place where the documentation said one thing and the environment did another.** A permission Microsoft marks "no admin consent required" that the tenant blocked anyway. A schema that `curl` accepted and the model rejected. A binary that ran on every dev machine and failed on every clean one. The tell, every time, was two sources that *should* agree disagreeing — and the one that's actually running wins. That's the editorial voice of this whole series: empirical, not theoretical.

## The lessons, in brief

Each of these is its own deep dive:

- **[Getting Claude onto a fleet machine]({{< ref "getting-claude-code-onto-a-fleet-machine" >}})** — a "hello" took 11 seconds because credential federation ran ~6× per query; the fix was a cached shim. And the credential binary ran for every developer but failed on every clean PC, because a packaged dependency was bundled non-deterministically. Both are about the same binary, and both only showed up on the fleet.

- **[Authentication, end to end]({{< ref "authentication-end-to-end" >}})** — the fiddly Entra ID App Registration, the fact that Claude expects Dynamic Client Registration and Entra doesn't implement it, and the choice of how a server calls a downstream API *as the user* (where the "obvious" managed option turned out wrong for one case).

- **[A declarative MCP server, and shipping it]({{< ref "declarative-mcp-server-and-shipping-it" >}})** — making "add a tool" a one-line YAML change, a schema gotcha that's enforced *Bedrock-side*, and the unglamorous distribution layer that decides whether anyone actually uses the thing.

And then the second act, which I'll pick up separately: stepping back from one deployment and asking what the reusable *platform* looks like — an AgentCore-native AI framework.

If you're building something similar, start with the [companion repo](REPO_URL) — it has generic, deployable versions of everything here. The posts tell you *why*; the repo shows you *how*.
