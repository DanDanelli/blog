---
title: "The client: one key instead of a package"
date: 2026-11-13T00:08:00Z
draft: false
description: "With Anthropic's Claude Apps Gateway in front of Bedrock, a device needs one setting instead of an installer. How Claude Desktop and Claude Code reach the gateway on managed and unmanaged devices, what you lose outside MDM, and the client behaviours that fail without a word."
summary: "From an installer per environment to a single bootstrap URL, the two routes onto a device, what the gateway enforces either way, and a catalogue of silent client failures."
series: ["Claude on AWS, the hard way"]
series_order: 8
categories: ["Work"]
tags: ["Claude Desktop", "Claude Code", "Claude Apps Gateway", "MDM", "Intune", "MCP"]
---

<!-- Sources: platform repo ADR 0039 and ADR 0038; docs/plans/2026-11-03-claude-apps-gateway-proof.md
     (proof branch). Client versions are the ones observed on the day. -->

Before the gateway, getting Claude onto a laptop meant shipping a package: a credential helper, an AWS profile, a configuration file, the model list and the connector entry, one per environment, through MDM. Every change meant a new package.

With the Claude Apps Gateway, a Claude Desktop device needs one setting:

```json
{ "bootstrapUrl": "https://<gateway-host>/user/bootstrap" }
```

The rest arrives at sign-in: the models the user may pick, the managed MCP connector and the client settings, decided by their Entra App Role ([post 6]({{< ref "token-governance-measure-before-you-believe" >}})).

There's a cost we wrote down before deciding. **The gateway now does part of what the device management tool used to do.** As the [previous post]({{< ref "from-public-to-private-in-a-week" >}}) showed, some of those settings run commands. The team that runs endpoint management has to accept that settings can change without going through them. That's an organisational decision, and it's theirs.

## Two routes onto a device

**Managed devices.** Claude Desktop reads `bootstrapUrl` from a machine-wide policy, opens in third-party mode and goes straight to sign-in, with no prompt and nothing the user can change. The CLI gets a managed settings file with `forceLoginMethod: "gateway"` and `forceLoginGatewayUrl`. Environments differ only in the URL, and both write the same key, so one machine holds one environment. We made that a rule instead of finding it out later.

**Unmanaged devices.** Some people with a corporate account work on devices MDM doesn't reach. I'm one of them. Before, that population needed its own installer. Now it needs a file: enable Developer Mode, open *Configure Third-Party Inference*, import the one-key JSON, relaunch, sign in and allow the organisation's settings. The CLI takes the same two keys in the user's `settings.json`. The file holds no secret.

On an unmanaged device the settings belong to the user, so any policy the **client** applies to itself can't be guaranteed. What the **gateway** enforces doesn't change: sign-in by App Role, and the model allow-list checked on every request. **Put the controls that matter where the user can't reach them.** A client setting is a convenience; a server-side check is a control.

I tried route two on my own Mac on 13 November, through the test VPN, and it worked end to end. The audit log showed the whole device sign-in within 15 seconds, Chat and Code answered, the pickers listed exactly my tier with no Opus, and the connector appeared connected.

## Silent client failures

Most of what cost us time had one thing in common: **the client failed silently.** No dialog, often no log line, just a connector that wasn't there.

- **A policy change needs a real restart.** Closing the window doesn't end the process; the tray icon keeps it running. The OAuth post ended on the same lesson. Support says *quit the app fully*, never *close it*.
- **An old build kept tokens for a URL that no longer existed,** held back its refresh token, got a `403` and never tried to sign in again. A newer build fixed it. Instead of finding which one, we decided **every cutover installs the latest Desktop on every machine.**
- **A connector entry without `"transport": "http"` simply vanishes.** Validate managed entries against the current schema, because the client won't tell you.
- **Relaunching during an outage leaves the app with no model at all.** Once the gateway was back, it recovered on the next retry without a relaunch. During an incident, *don't relaunch*.

### Seven tools that broke every request

This one surfaced through the gateway. With the connector on, requests failed with `400`, and the user saw only `upstream rejected the request`. Seven of 78 tools, all on Microsoft Graph, had property keys Bedrock refuses, such as `$top` and `@microsoft.graph.conflictBehavior`. Gateway deployments turn MCP tool search off by default, so every tool definition went into every request, and one bad key failed all of them.

We measured that Graph accepts the plain forms on those endpoints, renamed the keys and dropped the conflict field, and the `400`s stopped. Why the *old* schema passes when the client calls Bedrock directly is still unknown, and written down that way.

## Still open

- **The network path for unmanaged devices.** The gateway is private, so those devices need a way into the corporate network. Whether the corporate VPN admits them is the organisation's decision.
- **Claude Desktop's own metrics don't reach CloudWatch.** The CLI's do. We don't know yet which side drops them.

## The lesson

Moving configuration to the server shrank the client to an address, and made the unmanaged population, once a separate project, almost free. It also moved the source of truth, so the gateway is where the controls have to be.

- **Enforce on the server, configure on the client.** Anything the user can edit is a preference, not a policy.
- **Build the support runbook from silent failures.** None of these would show up as an error.
- **Pin the client forward, not backward.** "Latest at every cutover" is cheaper than finding which build fixed what.

Next: the working rules this project grew out of. Each one started as a mistake.
