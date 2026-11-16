---
title: "Token governance: measure before you believe"
date: 2026-11-13T00:06:00Z
draft: false
description: "Putting per-person spend limits on Claude through Amazon Bedrock: an AWS-native option against Anthropic's Claude Apps Gateway, what a proof measured about spend caps, telemetry and the AWS bill, and how removing identity from metrics quietly undercounted tokens."
summary: "Two ways to cap what one person spends on Claude in Bedrock, a proof that measured both, a spend cap that turned out to be a brake, telemetry that misses the app's own calls, and an allow-list that silently dropped data."
series: ["Claude on AWS, the hard way"]
series_order: 6
categories: ["Work"]
tags: ["Claude Apps Gateway", "Bedrock", "FinOps", "OpenTelemetry", "CloudWatch", "Entra ID"]
---

<!-- Sources: platform repo ADR 0038; docs/plans/2026-11-03-claude-apps-gateway-proof.md (proof branch);
     "Token Governance - Gateway or AWS" note, 2026-10-09. Figures are from one user on one day
     unless the text says otherwise. -->

On this platform, tokens are almost the whole bill: 97 to 99 percent of it. We estimated between 2,200 and 9,200 dollars a month for 300 users, depending on how heavily people work. And nothing stopped any one person from spending as much as they liked.

This post is about a basic control every finance team expects and Bedrock doesn't give you per person: *this user may spend this much, and then they stop.* Bedrock knows which IAM session made each call. It doesn't know about people, budgets or months.

## Two options

In October we compared two ways to add the limit.

**The AWS-native option** adds no service. A daily job reads the cost report, which names each person's session, and attaches a deny rule to anyone over their limit until the 1st. In non-production the rule took effect **9 seconds** after being applied. It costs a few dollars a month.

**Anthropic's Claude Apps Gateway** sits in front of the model, knows each person's spend, and refuses requests over the limit. It's an always-on service with its own database, and every model request depends on it.

Measuring the AWS option turned up what the paper comparison missed. **The error message is misleading:** a blocked user sees `AWS authentication failed · refresh your AWS credentials…`, and signing in again won't help. And **the identity was self-asserted:** the laptop states the person's name, and at the time nothing checked it matched the corporate sign-in. Someone with the skills could charge their usage to a colleague.

A month later we chose the gateway, because it was the more seamless option. The AWS option needed a workaround at every step: a daily job, warning emails to make up for the error, an extra rule to close the bypass. The gateway needed none, and it blocks on the next request instead of the next day. As the proof showed, "the next request" needs a footnote.

## The proof

We wrote the proof as a list of questions, each with what result would decide what. The first was the network. The Claude Code CLI refuses a gateway on a public address, as documented. Claude Desktop signed in and worked in all three tabs on a Mac and a Windows VM. Shortly afterwards AWS told us it had to be private anyway, which is the next post. **"It works" and "it's supported" are different findings.**

## Spend caps: a brake, not a ceiling

**The meter is exact.** The gateway's counter matched Bedrock's token metrics to three decimal places in cents, at list price.

**The cap isn't.** The check runs *before* each request, so the request that crosses the cap still completes:

| Cap | Where spend ended |
|---|---|
| 44 cents | 45.01 cents, then refused |
| 100 cents | about 120 cents, then refused |

The cold session is the expensive one. Two Opus calls in Cowork and Code, each asked only to answer `OK`, cost 75 cents between them, almost all of it writing to the prompt cache. A warm chat message cost about 2 cents. A daily cap has to allow for the cost of *starting*.

Users see the gateway's `429` with our own text, raising a cap works in open sessions, and organisation and per-user caps layer correctly. Two caveats went into the design: the meter uses list price, so it can sit below the real bill; and **enforcement fails open** if the gateway's database is unreachable. So production sets an organisation-wide default cap *before* a single user is assigned.

## Telemetry isn't billing

FinOps wanted same-day dashboards, so we relayed the clients' OpenTelemetry metrics to CloudWatch and compared them against Bedrock. For Opus the match was exact. Overall, **six Haiku calls reached Bedrock and never reached telemetry.** They were **session titles**: Claude Desktop names each conversation with a Haiku call its own process sends, outside the engine that produces the metrics. No document we found mentions it.

Then we checked the bill. A CUR 2.0 export had **exactly Bedrock's token counts for that hour, title calls included**, under each person's session.

| Source | Title calls | By person | When |
|---|---|---|---|
| Client telemetry | No | Yes | Minutes |
| Bedrock metrics | Yes | No, by model only | Minutes |
| Billing export | Yes | Yes | Next day |

The gap is title tokens per person on the same day, and only model invocation logging closes it, which stays off (post 5). We accepted it. Two more findings: Chat reports itself as `cowork`, and the client publishes the OS login name (`process.owner`) on every data point.

## Designing it

With the measurements in hand, the production design was mostly what the documentation states quietly:

- **Tiers are Entra App Roles, not groups,** assigned directly, because nested groups aren't expanded.
- **`match: {}` matches everyone who signs in,** including someone with no role. The sign-in gate lists the roles explicitly.
- **A group's spend cap is a per-seat default, not a pool.**
- **No write key until something uses it.**

## The allow-list that ate our data

We didn't want identity in CloudWatch: the spend tables and the bill already answer *who*. So the collector keeps an **allow-list** of labels and drops everything else, so the next identity attribute a client adds is removed without anyone knowing its name.

On the first real session the collector logged `Duplicate metric found`, five times. Clients export *deltas*, and each attribute set carries its own start time. Two points that differ only in a stripped attribute leave the allow-list with identical labels but different start times, and the exporter keeps one and drops the other. **Removing identity had made the token and cost numbers too low**, and only a warning line said so.

The fix took three steps: a metric filter that counts every dropped point; adding the effort level to the allow-list, which helped only partly; and the upstream OpenTelemetry Collector Contrib, whose `transform` processor sets each delta point's start time to its own timestamp before the allow-list runs. The counter read zero, and it stays in place.

## The lesson

Every number here is from one user on one or two days, in non-production. But the pattern held: **the documentation was right about what the gateway does and quiet about what that means.** "Spend limits" meant a brake. "Usage telemetry" meant the engine's calls, not the app's. "Drop identity" changed the arithmetic.

- **Compare options on what users see.** The AWS option's error message decided more than its cost.
- **Reconcile telemetry against the bill before building a dashboard on it.**
- **When you remove data, check the totals afterwards.**

Next: the endpoint that had to go private, right after we'd shown it worked in public.
