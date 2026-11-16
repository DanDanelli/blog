# Editorial Plan — "Claude on Bedrock → AWS AI Framework"

> **Superseded 2026-11-13.** This series was dropped and its draft posts deleted. The project is now
> told by "Claude on AWS, the hard way" — see `../Claude on AWS v1.8/editorial-plan.md`.

*Language: English. Audience: layered (each post opens accessible, then goes deep). The deep
implementation lives in the companion repo; the blog tells the story and links to the code.*

> **Revision note.** This plan was deliberately shrunk from an earlier 13-post series. That
> version was technically complete but too long to write and too long to follow — a 13-part
> series risks being abandoned half-finished. The implementation detail already lives in the
> companion repo, so the blog doesn't need to re-document it. The shape below is a **6-post
> narrative arc**, designed to be finishable. (It also replaced an interim "flagship + deep
> dives" cut — see §2.)

---

## 1. The story

Two projects, **two acts of one story**:

- **Act I — the production deployment.** A proof-of-concept — *can we run Claude Code against
  Amazon Bedrock on managed fleet machines and wire it to internal systems?* — that survived
  contact with production. Two custom MCP servers (SharePoint via Microsoft Graph, Atlassian)
  and a fleet distribution pipeline, plus a pile of hard-won findings.
- **Act II — the framework.** Stepping back: *if I had to do this for many teams, what's the
  reusable platform?* The answer generalizes Act I but goes **AgentCore-native** (Gateway +
  Runtime), using Lambda only for the gaps managed services can't fill.

The spine: **what a real deployment taught us, and what we built once we knew.** Two threads
run through everything and are the editorial voice:

- **Docs vs. reality.** Almost every finding is a place where the documentation said one
  thing and the environment did another (admin consent, OBO under Conditional Access, the `$`
  rejected Bedrock-side, Nuitka's non-deterministic bundling). *Empirical, not theoretical.*
- **Standing on AWS's Guidance, improving where it hurt.** Act I is built on AWS's
  [`guidance-for-claude-code-with-amazon-bedrock`](https://github.com/aws-solutions-library-samples/guidance-for-claude-code-with-amazon-bedrock)
  — a published reference solution (the `ccwb` CLI + credential binary + infra). We didn't
  build that from scratch; we took it as a baseline and improved it (the credential shim, the
  Nuitka build fix). Being clear about that line — AWS's baseline vs. our additions — is part
  of the honesty of the series.

---

## 2. Structure: a 6-post narrative arc

Settled after iterating: a chronological, narrative series (more accessible than a
flagship + deep-dives hub), each post a theme rather than a single finding.

```
1. Why we run Claude Code on Amazon Bedrock          (motivation)
2. The architecture of Claude Code on Bedrock        (two pillars, AWS Guidance baseline)
3. Getting Claude Code onto a fleet machine          (Pillar 1: latency + packaging + shipping)
4. Working with App Registration and Entra ID        (Pillar 2 inbound: App Reg, admin consent, DCR)
5. Custom MCPs for Jira, Confluence and Office 365    (Pillar 2 servers: design, $ finding, outbound auth)
6. Why an AI framework is the better answer          (Act II — the framework)
```

**6 posts**, not 13. The order follows the story: why → architecture → the two pillars taken
apart → why it points to a framework. Each post is self-contained (a reader arriving from a
search gets full value) and keeps the searchable error-string anchors inside it. The repo
carries the deep detail (ADRs + component READMEs); posts link to it.

### What lives in the repo, not in a post
The narrow/niche findings become repo content (`docs/adr/` + component READMEs), not posts:
the `$`-schema mechanics in detail, Cedar policy, the framework's profile model, the full
ADRs. Posts *link* to these.

### Cadence
One post every 1–2 weeks, published in series order. All six are drafted as a batch so the
cross-references are coherent.

---

## 3. The posts

**1 — "Why we run Claude Code on Amazon Bedrock"** *(motivation)*
- Public API vs. Bedrock for an enterprise: governance, attribution, not standing up a
  parallel trust model. What's hard (the locked-down fleet machine). The three-act journey.

**2 — "The architecture of Claude Code on Bedrock"**
- The two pillars; the corrected diagram (Entra ID lives in Azure; direct Entra→STS
  federation, no Cognito); the AWS Guidance baseline + what we improved; the docs-vs-reality
  throughline. *Code:* `companion repo` root.

**3 — "Getting Claude Code onto a fleet machine"** *(Pillar 1)*
- The 11-second hello (per-request federation → a stdlib DPAPI-cached shim, ~11s→~3s); the
  Nuitka `cryptography._rust` trap (explicit includes, in two build paths); shipping via the
  `ccwb` lifecycle and our additions.
- *Searchable anchors:* `cryptography.hazmat.bindings._rust ImportError`; ~1.7s per
  `AssumeRoleWithWebIdentity`. *Code:* `credential-shim/`, `distribution/`.

**4 — "Working with App Registration and Entra ID"** *(Pillar 2, inbound)*
- The App Registration setting-by-setting; the "admin consent required: No" trap; the DCR
  problem (Entra doesn't implement DCR) and the shim that bridges it.
- *Searchable anchors:* the App Registration table; "Entra doesn't implement DCR". *Code:*
  `dcr-shim/`.

**5 — "Custom MCPs for Jira, Confluence and Office 365"** *(Pillar 2, servers)*
- Why custom (auth as the user, scope control, ours to run); the declarative YAML-over-REST
  design; the `$`-in-schema finding (Bedrock-side validation); outbound auth — OBO
  (same-tenant) vs a managed broker (cross-vendor).
- *Searchable anchors:* `Property keys should match pattern '^[a-zA-Z0-9_.-]{1,64}$'`.
  *Code:* `rest-mcp-proxy/`, `mcp-servers/examples/`.

**6 — "Why an AI framework is the better answer"** *(Act II)*
- From a project to a platform (framework plane vs. project plane); the monolith → gateway-
  native shift (Lambda only for the irreducible gaps); de-risk with live sandbox gates; safe
  defaults. The detail lives in the framework's ADRs in the repo.
- *Code:* `part-2-aws-ai-framework/` + `docs/adr/`.

---

## 4. How to write each post (the layered formula)

Four beats so a manager and a staff engineer both finish satisfied:

1. **The symptom (anyone).** Lead with the observable problem — a number, an error string.
2. **Why it matters (decision-makers).** A paragraph on the stakes/trade-off.
3. **The deep dive (engineers).** Mechanism, code, exact flags — under a clear heading
   ("How it actually works") so non-technical readers know they can stop.
4. **The lesson (everyone).** A short, transferable takeaway.

Style notes:
- **Show the measurement** — the probe, the before/after number, the exact error string
  (also SEO gold).
- **Consolidated, but keep the searchable anchors.** A merged post still needs the exact
  error strings and clear H2s, so a search for one finding lands on the right section.
- **Link to the repo for depth; don't re-document it.** The post carries the story and the
  lesson; the repo carries the runnable detail.
- **Name the AWS Guidance baseline** when a post builds on it, and be clear what we added.

---

## 5. Sanitization — decided, and enforced

Resolved (was an open question in the first draft):

- **Company is generic** — written as "an enterprise" / "we", never named. (Internal
  architecture posts usually still want sign-off — worth doing once for the set.)
- **Drafts ship as `draft: true`** with `REPO_URL` placeholder links until the companion repo
  is public; then it's a find-and-replace.
- **Automated guard.** The companion repo has a CI sanitization gate (a denylist for the org
  name, the AWS account number, internal repo slugs, tenant domains, plus a secret scanner)
  so nothing sensitive can land. Apply the same discipline to post drafts — a quick grep
  before publishing.

---

## 6. Status

**Companion repo (deployable reference):** Part 1 implemented and tested — credential shim,
the distribution patches, the declarative `rest-mcp-proxy`, the `dcr-shim`. Part 2 (Terraform
modules + Python package) scaffolded. CI sanitization + secret gates in place.

**Blog drafts:** all six posts are drafted (`draft: true`), in series order 1–6, with valid
cross-links and `REPO_URL` placeholders. Company kept generic; leak-checked clean.

**Next:** review/finalize the six drafts, then publish in order (1 → 6). When the companion
repo goes public, find-and-replace `REPO_URL`. Get employer sign-off before publishing.
