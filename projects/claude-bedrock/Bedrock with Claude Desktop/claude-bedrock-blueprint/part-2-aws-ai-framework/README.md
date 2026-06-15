# Part 2 — AWS AI Framework (AgentCore-native)

Act II: the reusable platform that generalizes Part 1's findings, but built
**gateway/runtime-native** on Bedrock AgentCore — Lambda only for the irreducible gaps.

## Core model (three axes)

```
PROFILES (inbound)   mcp-dcr · m2m-api · web-user · agent-a2a
ARCHETYPES           gateway-integration (Gateway + targets) · runtime-agent (Runner)
FOUNDATION           identity (Entra · AgentCore Identity) · observability · network/IAM · state
DATA-PATH SERVICES   Cedar policy (opt-in) · evaluations (runtime-agent only)
```

## What's in here

| Path | Backs post | What it is |
|------|-----------|------------|
| [`terraform/modules/foundation/`](terraform/modules/foundation/) | B1 | Shared identity, observability, network/IAM, state. |
| [`terraform/modules/profiles/`](terraform/modules/profiles/) | B4 | Inbound client classes; the DCR bridge is one profile, not a core requirement. |
| [`terraform/modules/archetypes/`](terraform/modules/archetypes/) | B3 | `gateway-integration` (Gateway + OpenAPI target + interceptor) and `runtime-agent`. |
| [`terraform/modules/shared/`](terraform/modules/shared/) | B5 | Cross-cutting bits incl. the opt-in Cedar policy engine. |
| [`terraform/examples/`](terraform/examples/) | B1–B5 | Reference compositions that actually deploy. |
| [`python/`](python/) | B3 | The `aws_ai_framework` package (interceptor, identity, mcp, agents). |

## Design principles (the ADRs)

- **Terraform**, `hashicorp/aws` default, `awscc` only for the Gateway + Cedar policy.
- **Repo isolation:** framework in its own repo; each consumer project in its own repo,
  pinning the modules by git ref and the package by version (lockstep).
- **Gateway-native:** the Gateway owns MCP protocol, JWT verification, the REST target, and
  native per-user 3LO; Lambda does only the REQUEST interceptor (text → ADF) and the DCR
  bridge (Entra lacks DCR).
- **Cedar policy is opt-in:** a fresh gateway is usable; default-deny is a deliberate
  hardening switch, not the out-of-the-box state.

See [`../docs/adr/`](../docs/adr/) for the full reasoning.

## Prerequisites

- Terraform `>= 1.11`, an AWS account with AgentCore access, and an Entra (Azure AD) app
  registration. Each example's README lists exactly what to supply.
