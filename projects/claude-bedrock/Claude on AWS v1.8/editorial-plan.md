# Editorial Plan — "Claude on AWS, the hard way" (platform v1.8)

*Language: English. Audience: cloud architects and platform teams evaluating Claude on Amazon
Bedrock in an enterprise. Same layered formula and sanitization rules as the first series
(`../Bedrock with Claude Desktop/editorial-plan.md` §4 and §5).*

## 1. What this series is, and how it differs from the first

The first series ("Claude on Bedrock") tells the proof-of-concept story, built on AWS's `ccwb`
Guidance. This one leaves `ccwb` out entirely and tells the story of the platform as it stands at
**version 1.8**: every Claude client (Desktop, Cowork, Code) behind a private Claude Apps Gateway
in front of Bedrock, every tool behind AgentCore Gateway, every call made as the user.

It is about **decisions and mishaps, not code.** Each post follows one decision from the first
attempt to the version that shipped, including the attempts that were reverted.

**Through-line:** the agent runs on the user's machine. AWS hosts three things only — the model,
the tools, the identity. The series is how each of those was decided, got wrong, and corrected.

## 2. Format of every post

1. **The symptom** — the observable failure, with the exact error string.
2. **Why it matters** — the stakes, in one or two paragraphs.
3. **What we tried** — each attempt, what it cost, what killed it.
4. **What shipped** — the decision, and what breaks if each piece is removed.
5. **The scar** — one transferable rule that came out of the mistake.

Minimal code. Error strings, a measured request/response pair, one diagram at most.

## 3. The posts

| # | Working title | Source in the platform repo | Status |
|---|---|---|---|
| 1 | The agent doesn't run on AWS | ADR 0001, 0006, 0007, 0011, 0013, 0028 | **Draft** |
| 2 | Every tool acts as the user, and what that costs | ADR 0004, 0005, 0022, 0035 gate 6 | **Draft** |
| 3 | The OAuth shim we couldn't delete | ADR 0024, 0025, 0031 | **Draft** |
| 4 | Retiring our own MCP servers | ADR 0030, 0032, 0034, 0035; vendor-defects investigation | **Draft** |
| 5 | Observability without leaking | ADR 0020, 0028; observability pre-flight | **Draft** |
| 6 | Token governance: measure before you believe | ADR 0038; gateway proof plan (2026-11-03); token governance note (2026-10-09) | **Draft** |
| 7 | From public to private in a week | ADR 0014 amendment, ADR 0002 exception | **Draft** |
| 8 | The client: one key instead of a package | ADR 0039, ADR 0038; gateway proof plan | **Draft** |
| 9 | Building with an agent: rules born from scars | `CLAUDE.md` working rules; agent project memory | **Draft** |

Posts 3 and 6 first: they carry the most complete arcs and the least-documented material.

**Publish in series order.** Posts link backwards with Hugo `ref` (7 → 3, 6; 8 → 6, 7; 9 → 3, 6),
and a published post that refs a draft fails the production build. Post 1 lists the series in
plain text for the same reason; turn those entries into links as each post goes live.

## 4. Overlap with the first series

Decided 2026-11-13: the first series' six draft posts are deleted; this series replaces them.
The project page `content/projects/claude-on-bedrock` was rewritten for this series the same day
(title "Claude on AWS", slug kept), and the first editorial plan is marked superseded.

## 5. Sanitization

Same rules as the first series: company generic, no tenant or account IDs, no GUIDs, no CIDRs or
prefix sizes, no platform version numbers ("today", not "1.8"), no internal hostnames (`mcp.example.com` stands in), no colleagues' names, no AWS support case contents —
only what we measured. Grep every draft before publishing. Verify every external link at
publication time.
