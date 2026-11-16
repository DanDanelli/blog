---
title: "Observability without leaking"
date: 2026-11-13T00:05:00Z
draft: false
description: "Turning on one log delivery wrote every caller's JWT into CloudWatch in clear text. How the platform's observability was rebuilt around that: prompt logging off by decision, redaction that matches the shape of a secret, a pre-flight for every sink, a log field that stored company content, and an alarm that could never fire."
summary: "The token that landed in CloudWatch, the record that proves who did what and leaks how they proved it, and what a written pre-flight for every sink found that the controls didn't."
series: ["Claude on AWS, the hard way"]
series_order: 5
categories: ["Work"]
tags: ["Observability", "CloudWatch", "AgentCore", "Data Protection", "Security", "GDPR"]
---

<!-- Sources: platform repo ADR 0020, ADR 0028, and the observability pre-flight investigation
     (2026-08-24 to 2026-09-24). No support case contents. -->

In August I turned on AgentCore Gateway's application logs to have something to look at during a client test. They immediately wrote **every caller's complete JWT, in clear text,** into CloudWatch, once per request. I deleted the log stream within minutes and nothing came of it. But it changed how every sink on this platform has been turned on since.

## The record that proves who did what

Shipping fewer fields didn't help: the token and the policy decision live in the same field, `body`. Dropping one meant dropping the audit trail that made logging worth turning on. As we wrote at the time:

> The record that proves who did what is the same record that leaks how they proved who they were.

The first plan was a pipeline: Firehose, a redaction Lambda, an S3 bucket. Then someone asked what the bucket was for. The answer was that Firehose can't deliver to CloudWatch Logs. The plan died on that question. **CloudWatch Logs data protection** masks matching data as it arrives: the token comes out as asterisks and the decision beside it is untouched. Zero new resources.

The identifier matches **what a JWT looks like**, an `eyJ…` triple, not a header or field path. As [post 2]({{< ref "every-tool-acts-as-the-user" >}}) described, the token had already moved once, from `Authorization` into `params._meta`. A rule anchored to its location would have failed silently the next time it moved.

## Two decisions about content

Two questions had been left open on purpose, because in both the default was the permissive one.

**Model invocation logging stays off.** It would turn the platform from *carrying* content to *storing* it, with a lawful basis, a retention schedule and a place in every data-subject request. And it doesn't answer the question we need, *what did the agent do, and on whose behalf*, which is a tool-plane question.

**Tool parameters are redacted, not retained briefly.** Short retention still writes personal data into telemetry. We redact **values** and keep parameter **names and types**.

## A pre-flight for every sink

After the incident, the project got a rule: *anything that receives data gets a pre-flight, written before the apply.* The first big test was tracing:

| Sink | What it would hold | Decision |
|---|---|---|
| Identity token-exchange spans | The caller's subject claim and issuer, no credentials | Enable. **Don't redact the subject claim** |
| Identity application logs | The user's assertion and the downstream access token | **Never enable** |
| Our containers' log groups | Spans, in groups with **no data protection policy** | Protect at account level first |
| Gateway spans | Tool, target, Cedar decision, latency | Enable |

**The subject claim is the point, not the leak.** It's the *on whose behalf*. A loose redaction rule would erase the one field the exercise was meant to keep. And because AWS's documentation didn't say which log group our spans would land in, the policy went at **account level**, covering whichever one it turned out to be.

### Masking hides; it doesn't delete

Our own record said redaction *stops data being written*. It doesn't. CloudWatch masks at every **read**, and anyone with `logs:Unmask` sees the original, which in our account meant every administrator. *"Credentials in logs are masked from every reader except account administrators"* is the supportable claim, and we corrected the record. A narrowly scoped `logs:Unmask` policy exists, and I left it unattached, with the consequence written down first.

## The field that stored company content

Reading the gateway's logs during the tracing work, I found **the `body` field held the complete request and response of every tool call.** One SharePoint search had written 15,000 characters of site names, URLs and display names. About eleven days of it was at rest.

Every control missed it: **the policies match the shape of a credential, and business content has no shape.** It also contradicted the platform overview, which said it kept no copy of anything. We corrected that in place, with a dated note, and I dropped `body` the same day. Then the cheapest check showed what remained: the gateway publishes `AllowDecisions` and `DenyDecisions` metrics per tool. What was lost was the part that needs a person, and metrics shouldn't carry that.

## The alarm that could never fire

The account policy publishes `LogEventsWithFindings`, the cheapest alarm on *a credential reached a log again*. When we came to prove it, the findings destination was empty, and the metric is only published when one is set. A comment in our Terraform said otherwise. Eleven days of zero datapoints were a silent alarm, not a quiet log. We set the destination and proved it with a synthetic JWT-shaped string.

## Spans that didn't arrive, then did

With every precondition in place, the gateway produced no spans. We eliminated eight hypotheses and took it to AWS. Weeks later, spans were simply there: tool invocation, policy decision, token exchange, target call. We still don't know why, and it's written down that way. None of the spans we inspected carries **the calling user**, so *on whose behalf* still has no trace.

On cost, scanning was about a fifth of a cent a month. The lever was volume: 22% came from log groups of runtimes that no longer existed, which were deleted after a person confirmed it.

## The lesson

The JWT in CloudWatch was a five-minute incident. What it bought was a habit: before anything receives data, write down what will land in it, and read the first real entries against what you wrote. Almost everything here was found that way.

- **Match the shape of a secret, never its location.** Tokens move.
- **Masking is a read control, not a deletion.** Say exactly that, and decide who holds `logs:Unmask`.
- **Shape-based redaction can't protect content.** For business data, the only control is not writing it.

Next: governing token spend per person, a cap that turned out to be a brake, and telemetry that isn't billing.
