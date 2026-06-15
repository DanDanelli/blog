# Claude on Bedrock — Blueprint

Reference implementations for running **Claude on Amazon Bedrock** in an enterprise, and
for the **AgentCore-native AI framework** that generalizes it. This repo is the runnable
companion to a blog series — the posts tell the *story and the why*; this repo holds the
*deployable how*.

Everything here is **config-driven, not fork-driven**: you should never edit source to make
it yours. Copy an `*.example.tfvars` / `.env.example`, fill in your own identifiers, and
deploy into your own AWS account against your own identity provider.

> **Status:** scaffolding. Directories are landing alongside the blog posts they back —
> see the map below for what's live.

---

## Start here

1. Read the architecture overview in [`docs/architecture/`](docs/architecture/).
2. Pick the part that matches what you're trying to do (below).
3. Follow that directory's README — each one is self-contained (prerequisites → run it →
   what to change for your environment).

This repo is built in two acts:

- **Part 1 — [`part-1-claude-on-bedrock/`](part-1-claude-on-bedrock/):** the production
  findings, generalized — credential brokering for fleet machines and custom MCP servers.
- **Part 2 — [`part-2-aws-ai-framework/`](part-2-aws-ai-framework/):** the reusable,
  AgentCore-native platform (Gateway + Runtime), with Lambda only for the irreducible gaps.

---

## Blog post → code map

| Post | What it covers | Code |
|------|----------------|------|
| P0 — Why Claude on Bedrock | Architecture overview, the two pillars | [`docs/architecture/`](docs/architecture/) |
| A1 — The 11-second hello | Credential federation latency + the DPAPI cache shim | [`part-1-.../credential-shim/`](part-1-claude-on-bedrock/credential-shim/) |
| A2 — The Nuitka war story | Bundling `cryptography._rust` on clean machines | [`part-1-.../distribution/`](part-1-claude-on-bedrock/distribution/) |
| Entra ID & the DCR problem | App Registration settings + the DCR bridge in front of Entra | [`part-1-.../mcp-servers/dcr-shim/`](part-1-claude-on-bedrock/mcp-servers/dcr-shim/) |
| A3 — OBO vs a token vault | Outbound auth: On-Behalf-Of vs a managed broker | [`part-1-.../mcp-servers/examples/`](part-1-claude-on-bedrock/mcp-servers/examples/) |
| A4 — Admin consent & the `$` | Two "the docs lied" findings | [`part-1-.../mcp-servers/rest-mcp-proxy/`](part-1-claude-on-bedrock/mcp-servers/rest-mcp-proxy/) |
| A5 — Shipping it | Declarative MCP server + fleet distribution | [`part-1-.../mcp-servers/`](part-1-claude-on-bedrock/mcp-servers/) |
| B1 — From one repo to a platform | The three-axis model, repo isolation, versioning | [`part-2-.../`](part-2-aws-ai-framework/) |
| B2 — De-risk before you design | Sandbox validation gates | [`docs/adr/`](docs/adr/) |
| B3 — Gateway-native, Lambda for the gaps | Gateway + interceptor + DCR bridge | [`part-2-.../terraform/modules/archetypes/`](part-2-aws-ai-framework/terraform/modules/archetypes/) |
| B4 — DCR for the clients that need it | The profile model | [`part-2-.../terraform/modules/profiles/`](part-2-aws-ai-framework/terraform/modules/profiles/) |
| B5 — Default-deny is a footgun | Cedar policy, opt-in | [`part-2-.../terraform/modules/shared/`](part-2-aws-ai-framework/terraform/modules/shared/) |

*(Links to the published posts will be added here as they go live.)*

---

## Repository layout

```
docs/                       architecture diagrams, ADRs, per-post notes
part-1-claude-on-bedrock/   Act I — credential shim, distribution, MCP servers
part-2-aws-ai-framework/    Act II — Terraform modules + Python package
examples/end-to-end/        one composition that wires the whole stack together
scripts/                    scaffolding + the sanitization CI guard
```

---

## A note on what's *not* here

This is a clean-room reference, not an export of any employer's internal repo. There are no
real account IDs, tenant IDs, ARNs, hostnames, or private repo paths anywhere — only
documented placeholders. CI enforces this (see [`scripts/check-sanitization.sh`](scripts/check-sanitization.sh)).

## License

[Apache-2.0](LICENSE). Part 1's distribution tooling builds on AWS's
[`guidance-for-claude-code-with-amazon-bedrock`](https://github.com/aws-solutions-library-samples/guidance-for-claude-code-with-amazon-bedrock)
(MIT-0); this repo ships patches against it rather than re-vendoring it — see
[`part-1-claude-on-bedrock/distribution/`](part-1-claude-on-bedrock/distribution/).
