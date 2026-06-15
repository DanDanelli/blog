# Editorial Plan — "Claude on Bedrock → AWS AI Framework"

*Language: English. Audience: layered (each post opens accessible, then goes deep). The deep
implementation lives in the companion repo; the blog tells the story and links to the code.*

> **Revision note.** This plan was deliberately shrunk from an earlier 13-post series. That
> version was technically complete but too long to write and too long to follow — a 13-part
> series risks being abandoned half-finished. The implementation detail already lives in the
> companion repo, so the blog doesn't need to re-document it. The shape below is **flagship +
> a few consolidated deep posts**, designed to be finishable.

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

## 2. Structure: flagship + consolidated deep posts

```
FLAGSHIP   ── 1 post  ── "What I learned taking Claude Code on Bedrock to production"
ACT I      ── 3 posts ── consolidated deep dives (the production findings)
ACT II     ── 1 post  ── "Generalizing it: going AgentCore-native"
```

**~5 posts**, not 13. Each deep post is self-contained (a reader arriving from a search gets
full value) and is a *theme*, not a single finding. The flagship is what most people read;
the deep posts are reference + SEO + proof of depth; the repo carries the rest.

### What lives in the repo, not in a post
The narrow/niche findings become repo content (`docs/adr/` + component READMEs), not posts:
the `$`-schema mechanics in detail, Cedar policy, the framework's profile model, the full
ADRs. Posts *link* to these.

### Cadence
One post every 1–2 weeks. The flagship and Act I are drafted as a batch so cross-references
are coherent; publish the flagship first, then the deep posts.

---

## 3. The posts

### FLAGSHIP — "What I learned taking Claude Code on Bedrock to production"
- *Audience:* broad. The journey and the lessons, light on mechanism.
- *Covers:* why Bedrock (governance, data residency, existing AWS footprint); the two-pillar
  architecture at a glance; the AWS Guidance baseline + what we improved; the docs-vs-reality
  throughline; a short tour of each lesson with a link to the deep post that unpacks it.
- *Ends:* pointer to the companion repo for runnable code.

### ACT I — deep dives (3)

**D1 — "Getting Claude Code onto a fleet machine: latency and a packaging trap"**
- *Theme:* the credential binary (Pillar 1, client side) — the two problems that hit only on
  the fleet, not on dev machines.
- *Merges:* the 11-second hello (per-request credential federation → a stdlib DPAPI-cached
  shim, ~11s→~3s) **+** the Nuitka war story (`cryptography._rust` non-deterministically
  dropped → explicit includes, in two build paths).
- *Searchable anchors to preserve:* `cryptography.hazmat.bindings._rust ImportError`; the
  "~1.7s per AssumeRoleWithWebIdentity" figure.
- *Code:* `credential-shim/`, `distribution/` (patches).

**D2 — "Authentication end to end: getting Claude in, and acting as the user"**
- *Theme:* the whole identity story — inbound (Claude → your MCP server) and outbound (server
  → downstream API as the user).
- *Merges:* the Entra App Registration settings + the **DCR problem** and shim (inbound) **+**
  the admin-consent gotcha **+** OBO vs a managed token vault, same-tenant vs cross-vendor
  (outbound).
- *Searchable anchors:* the App Registration setting table; "Entra doesn't implement DCR";
  the "admin consent required: No" trap.
- *Code:* `dcr-shim/`, `mcp-servers/examples/` (OBO + 3LO).

**D3 — "A declarative MCP server, and shipping it to a fleet"**
- *Theme:* the capability layer and how it reaches a laptop.
- *Merges:* the declarative YAML registry over a generic REST dispatcher **+** the `$`-in-
  schema finding (kept as a clearly-anchored section) **+** the `ccwb` distribution lifecycle
  (AWS Guidance) and our additions.
- *Searchable anchors:* `Property keys should match pattern '^[a-zA-Z0-9_.-]{1,64}$'`.
- *Code:* `rest-mcp-proxy/`.

### ACT II — "Generalizing it: going AgentCore-native" (1, to write)
- *Theme:* the mindset shift from one deployment to a reusable platform, and the single
  biggest architectural payoff: from a monolithic Lambda to a Gateway-native composition with
  Lambda only for the irreducible gaps (interceptor, DCR bridge).
- *Folds in lightly:* the three-axis model (profiles / archetypes / foundation), de-risking
  with live sandbox gates, and Cedar-policy-is-opt-in — each a paragraph, not a post. The
  detail lives in the framework's ADRs in the repo.
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

**Blog drafts:** the flagship + the 3 Act I deep posts are drafted (consolidated from the
earlier atomic drafts, which are archived). Act II's single narrative post is still to write.

**Next:** finalize the 4 drafts, write the Act II post, then publish flagship → D1 → D2 → D3.
