# Architecture Decision Records

The non-obvious engineering decisions behind this reference — the *why*, so the reasoning
survives. Lightweight (Nygard-style): context → decision → consequences.

These are the sanitized, public versions of the decisions made during the real build. They
are the highest-value, lowest-risk thing in the repo — start here if you want the reasoning
before the code.

> **Status:** to be ported from the source projects (sanitized). Planned set:

| # | Decision | Backs post |
|---|----------|-----------|
| 0001 | Outbound auth: OAuth On-Behalf-Of vs a managed token vault | A3 |
| 0002 | Fast credential shim with an OS-encrypted cache | A1 |
| 0003 | Bundling the native `cryptography._rust` binding in the build | A2 |
| 0004 | No `$` in MCP tool schema property keys (OData params) | A4 |
| 0005 | Terraform (not CDK/CFN); `aws` default, `awscc` only for gateway + policy | B1 |
| 0006 | Framework repo isolated; one repo per project; lockstep artifacts | B1 |
| 0007 | Gateway-native composition; Lambda only for irreducible gaps | B3 |
| 0008 | DCR bridge only for clients that need it | B4 |
| 0009 | Cedar policy opt-in (permissive default = no enforced engine) | B5 |

Each ADR is rewritten to lead with the symptom and to drop internal references — generic
engineering reasoning a stranger can apply.
