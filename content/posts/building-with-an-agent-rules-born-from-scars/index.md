---
title: "Building with an agent: rules born from scars"
date: 2026-11-13T00:09:00Z
draft: false
description: "Most of this platform's investigation was done with Claude Code as a working partner. The four working rules that came out of it, each with the mistake that produced it: evidence is not truth, pre-flight every sink, try to break a design first, and leave organisational facts to humans."
summary: "Four working rules for building infrastructure with a coding agent, each written next to the mistake that produced it, and why the real problem they solve is speed, not AI."
series: ["Claude on AWS, the hard way"]
series_order: 9
categories: ["Work"]
tags: ["Claude Code", "AI Agents", "Engineering Practice", "Terraform", "Architecture Decisions"]
---

<!-- Sources: the platform repo's CLAUDE.md working rules; ADR 0022, 0025, 0031; the assumption
     register; the agent's project memory. -->

The repository behind this series has a short file at its root called *Working rules*. It's about **method**, not architecture, and its first line explains how it's built:

> Each rule exists because it was broken here first; the scar is named so the rule stays concrete.

Most of the hands-on work was done with Claude Code as a working partner: it ran the probes, read the responses, and drafted the Terraform and the decision records. The rules file is written for both of us, and it's the part of the project I'd most want another team to copy.

An agent produces evidence very fast. That's the value and the risk, because the step that goes wrong in infrastructure work is rarely gathering evidence. It's the step *after*: turning what a command printed into a sentence in a document. The rules slow that step down, in the few places where slowness pays.

## Rule 1: Evidence is not truth

> A command's output is a fact about one moment, one credential and one account. It is not a fact about the world.

The scars: a single-sign-on listing showed two accounts, and that became *"there is no access to production"* in our assumption register. The token was stale; the command never lied. A probe reported a container had no token; the deployed image predated the code. A CLI session reported two service principals didn't exist; behind it was an expired refresh token.

So before an observation becomes a conclusion, name what else could produce the same output: **a stale credential, a stale artefact, cached state, the wrong account or region.** Observations go into records as *what was observed and when*, not the inference. And `terraform validate` is never reported as proof, because it doesn't check attribute names against the provider schema; `plan` does.

The worst near-miss was in [the OAuth post]({{< ref "the-oauth-shim-we-could-not-delete" >}}): an error sentence *resembled* Microsoft Graph's wording, and a theory built on that was two days from going to AWS when a controlled test showed the gateway produces it by itself. The record says so: *a resemblance promoted to a fact.*

## Rule 2: Anything that receives data gets a pre-flight

> Before enabling a log delivery, a trace exporter, a bucket, a queue or any other sink, write down what will land in it — in full, including headers and request bodies.

The scar: AgentCore Gateway's vended logs wrote callers' **complete JWTs** into CloudWatch in clear text. Since then every proof starts with a table of each sink and what lands in it, as the [gateway proof]({{< ref "token-governance-measure-before-you-believe" >}}) did, and ends with an instruction to read the first real entries against it.

The second half: **match the shape of the secret, never its location.** The user's token has already moved once on this platform, and a rule anchored to where it lives today fails silently the next time.

## Rule 3: Try to break a design before proposing it

> For every component in a proposed design, state what breaks if it is removed. If the answer is "nothing", remove it.

The scar: a redaction pipeline of Firehose, Lambda and S3, where the bucket existed only because Firehose can't deliver to CloudWatch Logs. *"What is the S3 for?"* ended it, and three components became a data protection policy. Every decision record since has a *what breaks if each piece is removed* table, and it's where you find the component that's there out of habit.

The part I'd copy first: **two gates get an independent check whose only instruction is *refute this*, run before the action:** a `terraform apply` that touches authentication, policy, secrets or logging, and marking an assumption closed. In practice it's a separate agent session with no stake in the plan. It found an ordering defect in the gateway proof's applies before any ran, and that the first metrics fix would only be partial.

## Rule 4: Organisational facts belong to humans

> Some facts are not discoverable from this repository, from AWS, or from Entra by inspection. Ask; do not assert.

This is the most interesting rule, because inspection is exactly what an agent is good at. The scars:

- **A word was stripped from a server name** as if it were a codename. It was the scope. Later it came off again, correctly, because the organisation changed the scope and someone said so. The first removal was an inference; the second was a fact, and this kind of fact only arrives that way.
- **`AADSTS50105` was reported as "you are not assigned".** The assignment came through a group, under a different account.
- **A shared sandbox account was read as ours,** and an inventory produced a clean-up proposal. Never delete, or propose deleting, in a shared account on an inventory alone.

When a decision is a person's, it's recorded *as given*, with their words and the date. The rule ends with the line I'd put on the wall:

> Asking here is not a failure of autonomy. Asserting is.

## How the records are kept

- **Reversed decisions stay in full,** *"because the reasoning that produced it is the reasoning someone would repeat."*
- **The assumption register is read first.** One afternoon the agent spent six attempts rediscovering four things already written there. Its memory now opens with an instruction to read the register before any hypothesis.
- **Requests to other teams contain actions only.** One ran to 109 lines of reasoning; the recipient needed two steps.

The hardest correction to make stick wasn't technical. It was **altitude**: I need findings I can carry into a conversation, not a narration of every command. The agent's own memory puts it better than I do: *the depth of the investigation is not licence for the length of the report.*

## The lesson

None of these rules is really about AI. They're about **speed**. Each guards the gap between observing something and asserting it, and a capable agent closes that gap very fast unless something holds it open: before a conclusion, before a sink, before a design and before a claim about the organisation.

And writing the scar next to the rule matters more than the rule. "Verify your evidence" is advice everybody agrees with and nobody follows. "The token was stale, and the command never lied" is what you remember the next time a listing looks too clean.
