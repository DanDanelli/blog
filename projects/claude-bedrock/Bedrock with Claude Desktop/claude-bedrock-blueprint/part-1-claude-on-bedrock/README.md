# Part 1 — Claude on Bedrock (the production findings, generalized)

Act I of the story: getting Claude Code to run against Amazon Bedrock on managed fleet
machines, and wiring it to internal systems through custom MCP servers. This part holds the
generalized, deployable versions of the findings from a real production deployment.

## What's in here

| Directory | Backs post | What it is |
|-----------|-----------|------------|
| [`credential-shim/`](credential-shim/) | A1 | A fast, DPAPI-cached `credential_process` shim that cuts federation latency (~11s → ~3s). |
| [`distribution/`](distribution/) | A2 | Patches + build notes against AWS's upstream solution (the Nuitka `cryptography._rust` fix). |
| [`mcp-servers/rest-mcp-proxy/`](mcp-servers/rest-mcp-proxy/) | A4, A5 | A generic MCP server: a YAML tool registry over a REST dispatcher. |
| [`mcp-servers/dcr-shim/`](mcp-servers/dcr-shim/) | Entra/DCR | An OAuth/DCR bridge that fronts Entra ID so Claude's DCR bootstrap works. |
| [`mcp-servers/examples/`](mcp-servers/examples/) | A3 | Outbound-auth examples: OBO (same-tenant) and 3LO via a managed token vault (cross-vendor). |

## Prerequisites

- An AWS account and an OIDC identity provider (Entra ID / Okta / Cognito).
- Python 3.12. (The credential shim is stdlib-only; the MCP server needs a venv.)

Start with [`credential-shim/`](credential-shim/) — it's the most self-contained piece and
the one that produces the most visible win.
