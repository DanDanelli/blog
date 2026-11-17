---
title: "Claude on AWS"
description: "Claude for a whole company through Amazon Bedrock: Claude Desktop and Claude Code behind a private Claude Apps Gateway, tools behind AgentCore Gateway with a Cedar policy, and every tool call made as the user."
draft: false
weight: 10
status: "Deployed"
track: "Work"
series: ["Claude on AWS, the hard way"]
stack: ["Amazon Bedrock", "Claude Apps Gateway", "AgentCore Gateway", "AgentCore Identity", "Cedar", "Entra ID", "MCP", "Terraform"]
repo: ""
---

An enterprise platform that puts Claude in front of a whole company, with the model on Amazon Bedrock in the EU. People use Claude Desktop (Chat, Cowork and Code) and the Claude Code CLI as they normally would. Behind them, the platform decides which models each person may use and how much they may spend, which tools they may call, and makes sure every tool call reaches Microsoft 365, Jira, Confluence or SAP LeanIX **as the person who asked**.

## At a glance

| | |
|---|---|
| **Users** | The whole company, a few hundred people |
| **Clients** | Claude Desktop (Chat, Cowork, Code) and the Claude Code CLI |
| **Model** | Claude on Amazon Bedrock, EU inference profiles only |
| **Tools** | Microsoft 365 and SharePoint, Jira and Confluence, SAP LeanIX |
| **Identity** | Microsoft Entra ID, for the model and the tools |
| **Governance** | Model tiers and per-person spend limits at the Claude Apps Gateway; a Cedar policy per tool at AgentCore Gateway |
| **Environments** | Non-production and production, in separate AWS accounts, all in Terraform |
| **Conversation content stored in AWS** | None, by decision |

## The idea in one sentence

**The agent runs on the user's machine; AWS hosts only what it reaches for.** When someone asks Claude to find a document and summarise it, the loop that decides which tool to call runs in the app on their laptop. AWS hosts the model, the tools and the identity that lets each tool act as the user. Most of the platform is the governance around those three things.

## How a request travels

{{< diagram src="request-path.png" alt="How a request travels: the model path through the Claude Apps Gateway to Bedrock, and the tool path through the OAuth shim and AgentCore Gateway to Microsoft 365, Atlassian and SAP LeanIX" caption="The model path (top) and the tool path (bottom)" >}}

Two paths leave the laptop, and they share nothing except the identity provider.

**Path B, the model** (steps 1 to 4):

1. The app signs in to the gateway with a device code. The gateway sends back its configuration: the models this person may use, the managed tool connector and the client settings.
2. The gateway signs the user in with Entra ID through its own app registration. Entra App Roles decide the person's tier.
3. Every model request goes to the gateway, on a private address, over the corporate network.
4. The gateway checks the model against the person's tier and their spend against their limit, then calls Bedrock with SigV4 under a session named after the user. That session is what makes the bill, the CUR 2.0 export, attributable per person. The clients' usage metrics go the same way: the gateway relays them to an OpenTelemetry Collector beside it, which strips identity and writes them to CloudWatch.

**Path A, the tools** (steps 5 to 8):

5. The tool connector signs in to Entra ID separately (PKCE) and gets a token for the tool plane.
6. Tool calls go over MCP to an **OAuth shim**. It exists only because Claude's connector sign-in expects OAuth features that Entra doesn't provide. It handles sign-in and passes tool traffic straight through.
7. **AgentCore Gateway** validates the user's Entra token. Its **Cedar policy engine** decides whether this tool may run, and anything without a policy is denied. An interceptor Lambda on every call records which operation actually ran.
8. **AgentCore Identity** gets a token for *this person and this system*, and the call reaches the system as the user.

## How each person's identity reaches the tools

{{< diagram src="identity-to-tools.png" alt="How each user's identity reaches the tools: Entra sign-in, AgentCore Gateway, Cedar policies, AgentCore Identity and the downstream systems, with the three filters on every request" caption="Simplified: the OAuth shim and the interceptor are left out, because neither changes whose identity a call carries" >}}

Every tool request passes three filters, and each one belongs to a different owner:

| Filter | Where | Decides |
|---|---|---|
| **Entry** | Entra ID, per person | Whether this person can use the platform at all |
| **Tools** | Cedar, the same for everyone | What the agent can do in each system |
| **Data** | The destination system, per person | What this person can see and change |

The granularity lives in the third filter, and that's deliberate. Two people asking for a summary of the same document get different answers if only one of them can open it in SharePoint. **The platform opens nothing a person couldn't already open.**

How each system gets its token:

| System | How the token is obtained | What the agent may do |
|---|---|---|
| Microsoft 365 | On-behalf-of exchange with Entra, no extra consent | Read and write, including sharing links |
| Atlassian | The person's one-time consent, through a consent portal | Read and write; destructive actions withheld |
| SAP LeanIX | The person's one-time consent, through a consent portal | Read only |

The model has limits, and they're stated rather than discovered later. Broad permissions stay broad, and an agent makes what they expose easier to find. And an agent can act *within* a person's permissions but *against* their intent: a document it reads can try to induce a write. That's what the per-tool policy is for.

## The components, and why each one is there

Every component had to answer one question before it stayed: *what breaks if it's removed?*

| Component | What it does | What breaks without it |
|---|---|---|
| Claude Apps Gateway | Sign-in, model tiers, spend limits, client configuration | No per-person control over models or spend; a package per device again |
| PostgreSQL | Sessions, rate limits, spend counters | The gateway can't sign anyone in or count spend |
| Internal load balancer and DNS name | The gateway's private address | Clients can't reach the gateway |
| NAT gateway | Egress to Entra ID, which has no VPC endpoint | Nobody can sign in |
| OAuth shim | Fills the gap between Claude's connector sign-in and Entra ID | Claude Desktop can't sign in to the tools |
| AgentCore Gateway | The single entry point for every tool | No place to enforce policy |
| Cedar policy engine | Per-tool permit or deny | Every tool open to everyone |
| AgentCore Identity | The per-person token vault and token exchange | Tools would need their own identity, and see everything |
| Interceptor Lambda | Records which operation ran behind a vendor's generic tools | The audit trail says `executeWrite` and nothing more |
| OpenTelemetry Collector sidecar | Writes the clients' metrics to CloudWatch, keeping an allow-list of labels | No same-day usage metrics; a failure loses telemetry, never inference |
| CUR 2.0 export | The bill, per person, the next day | No billing-grade answer to *who spent what* |
| Account data protection policy | Masks JWTs, bearer tokens and secrets in every log group | Credentials readable in logs |

What's **not** there matters as much. There are no hosted agents, no vector index of company documents, no managed memory and no stored prompts. Each of those was declined on purpose, with what would reverse it written down.

## Governance

**Models and spend.** An Entra App Role puts each person in a tier, which decides the models they see. Spend limits are per person and act on the next request after a limit is crossed. In practice that makes a cap a brake, not a hard ceiling.

**Usage and cost.** Three sources answer three different questions, and none of them stores what anyone wrote:

| Source | What it holds | By person | When |
|---|---|---|---|
| The gateway's spend tables | Spend per person, at list price, as the caps see it | Yes | Same day |
| CloudWatch metrics, through the OpenTelemetry Collector | Tokens, cost, sessions and tool decisions, by model and token type | No, on purpose | Minutes |
| CUR 2.0 export | The bill, with each person's session name on every line | Yes | Next day |

The clients send OpenTelemetry metrics through the gateway to a collector running beside it. The collector keeps an **allow-list** of labels, so any identity attribute a client adds later is dropped without anyone needing to know its name. Removing labels changed the arithmetic: delta points that differed only in a removed label were discarded as duplicates, undercounting tokens. The collector now aligns their start times so they add up, and a metric counts any point that's still dropped.

The billing export matched Bedrock's own token counts exactly, on every model and token type. Telemetry didn't: Claude Desktop names each conversation with a small model call that never reaches the metrics, so CloudWatch is for trends and the bill is for money. Same-day attribution of those calls per person is a gap we accepted, because the only thing that closes it is storing every prompt.

**Tools.** Cedar decides which tools exist for whom, and a tool without a permit is hidden, not just refused. Where we own the read/write line, there's one permit per tool. Where a vendor exposes hundreds of operations behind a few generic tools, the policy can only govern those tools, and an audit line records the operation.

**Observability.** No prompt logging, by decision: the platform carries conversation content and doesn't store it. Tool parameter values are redacted and their names kept. An account-wide data protection policy masks anything shaped like a credential in every log group, and an alarm fires if one reaches a log again. Masking hides values from readers; it doesn't delete them, and the platform says exactly that when asked.

## The network

The gateway has no public address. Each environment's VPC is attached to the company's Transit Gateway, so clients reach it over Direct Connect and the corporate network, through an internal DNS name. Because the corporate network uses one shared route table, the separation between environments is ours to enforce, with network ACLs. Outbound, a NAT gateway carries sign-in traffic to Entra ID, and everything else goes through VPC endpoints.

## The client

A managed device needs **one setting**: the gateway's bootstrap URL. Models, the tool connector and client settings arrive at sign-in and change without touching the device. People on unmanaged devices import the same one-line file. What the gateway enforces doesn't depend on which route the user took, because the controls that matter are on the server.

## Design principles

- **Decide what not to build,** and write each "no" down with what would reverse it.
- **Every tool acts as the user.** No application identity against systems that hold user data.
- **No container that is only a proxy.** Our own MCP servers were retired; the tools are now an OpenAPI schema and the vendors' own servers.
- **Pre-flight every sink.** Before anything receives data, write down what will land in it. Redaction matches the shape of a secret, never its location.
- **Enforce on the server, configure on the client.**
- **Keep reversed decisions in full.** The reasoning that produced a wrong decision is the reasoning someone will repeat.

## The series

*Claude on AWS, the hard way* follows the platform one decision at a time, from the first attempt to the version that shipped, including the attempts that were reverted. It's about decisions and mishaps more than code.
