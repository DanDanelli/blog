---
title: "From public to private in a week"
date: 2026-11-13T00:07:00Z
draft: true
description: "We proved Anthropic's Claude Apps Gateway worked on an internet-facing endpoint, then moved it to a private one. What 'private' turned into: a Transit Gateway shared with a hundred other VPCs, NAT for Entra, internal DNS, a resident environment, and a dry run that proved nothing."
summary: "A gateway that worked in public and had to be private, the six decisions hiding inside the word 'private', and why a shared route table made one security group the only boundary."
series: ["Claude on AWS, the hard way"]
series_order: 7
categories: ["Work"]
tags: ["Claude Apps Gateway", "Networking", "Transit Gateway", "DNS", "AWS", "Security"]
---

<!-- Sources: platform repo ADR 0014 (amendment of 2026-11-11), ADR 0002 (exception of 2026-11-11),
     ADR 0038 §4, the gateway's rendered configuration, and the 2026-11-11 DNS requests. -->

On a Wednesday in November, the [token governance proof]({{< ref "token-governance-measure-before-you-believe" >}}) passed: Claude Desktop had signed in through the gateway, on an internet-facing load balancer, on two machines. That same day the answer came back from AWS: the endpoint had to be private.

A week later both environments were on the corporate network, the gateway had an internal name, and a user had signed in through it. This post is about how much was hiding inside the word *private*.

## Why we'd made it public, and why private is right

It wasn't carelessness. An isolated VPC depended on nobody else's network, needed no tickets, and worked from anywhere. The MCP endpoint from [the OAuth post]({{< ref "the-oauth-shim-we-could-not-delete" >}}) was public too. We knew the warning signs: Anthropic's documentation says to keep a gateway off the internet, and the Claude Code CLI refuses a public one. But nothing said Desktop refused one, and it didn't. We had measured that it worked, not whether it should be there.

The strongest reason for private came from the gateway itself. **It pushes managed settings to every client that signs in, and some of those settings can run commands on developer machines.** On the internet, that's a remote configuration channel to every laptop in the company, protected by a sign-in page. Put that way, "it works in public" stops sounding like good news.

## What "private" turned into

It sounded like one setting. It came to six decisions, most about infrastructure other teams own.

**1. One Transit Gateway, one route table.** Each environment's VPC attaches to the company's Transit Gateway, which carries Direct Connect. Reading the network account, I found it runs **a single route table** for about a hundred VPCs from other teams. That made our side easy, and had two consequences I had to accept:

- **Production and non-production can reach each other.** The separation is ours: a network ACL on each environment's subnets refuses the other in both directions. It has to be an ACL, because security groups can't deny.
- **Every attached VPC can route to ours,** with no firewall in between. The load balancer's security group is the **only** network boundary, so sign-in is the real barrier: Entra with assignment required, and a gateway that refuses anyone without a role.

**2. NAT, not the corporate proxy.** The gateway signs users in through Entra, which has no VPC endpoint, and the shared table has no default route. The corporate proxy needed four answers from its owners; a NAT gateway needed none. Everything else goes through VPC endpoints. So "private" means one precise thing: **nothing reaches the gateway from the internet.**

**3. Internal DNS.** The name lives in the company's internal DNS, a ticket to another team. It's a `CNAME` to the load balancer's DNS name, never an `A` record, because its IPs change. And it's **not** under the MCP endpoint's zone: an internal zone for that hostname would shadow the public one and break the MCP endpoint for everyone inside the network.

**4. Resident, not ephemeral.** Our non-production environment is meant to be destroyed and rebuilt with no manual step. But the `CNAME` points at the load balancer's name, which changes on every rebuild. So the gateway got its own Terraform root, written down as an exception rather than left to become the rule.

**5. A dry run that proved nothing.** Accepting the attachment happens in the network account, shared with every team. I gave Terraform a permission to accept *our* attachments and nothing else. The first version, scoped to the Transit Gateway owner's account, was refused on the real attachment: **an attachment's ARN carries the requesting account, not the owner's.** A `--dry-run` against an invented ID had passed the day before, because AWS built that ARN from the caller's own account. The permission also can't delete, which would reach every other team's attachments.

**6. Testing from outside.** I don't have the corporate VPN on my machine, so a temporary AWS Client VPN into the non-production VPC, in its own root, carries the test. It doesn't test Direct Connect, the internal DNS record or on-premises routing. Only a person on the corporate network can.

The gateway's own settings changed too: `trusted_proxies` names the load balancer's subnets so logs see the user's address; sign-in limits rose to 300 per address per ten minutes, because hundreds of people share an address behind VPN and virtual desktops; and a readiness grace period stops a database failover from replacing every replica at once.

## Where it stands

On day one both environments were attached, with the production MCP endpoint untouched. On day two the internal DNS records resolved correctly from a corporate machine, and I signed in through the test VPN: Chat and Code answered, the picker showed exactly my tier, and the connector appeared already connected. Whether people on unmanaged devices can reach the corporate network at all isn't something I can answer by inspection. That's post 8.

## The lesson

"Make it private" sounded like a checkbox and cost two DNS tickets, an exception to a design rule and a permission in another team's account. And the security we'd assumed came from the network came from one security group and a sign-in page.

- **A proof that something works doesn't tell you it belongs there.** Ask what the component can do to its clients.
- **Read the shared infrastructure before designing against it.** One route table across a hundred VPCs changes what "isolated" means.
- **A dry run against a resource that doesn't exist tests nothing.** If authorisation depends on the ARN, test the real one.

Next: the client, and what one setting instead of an installer changes.
