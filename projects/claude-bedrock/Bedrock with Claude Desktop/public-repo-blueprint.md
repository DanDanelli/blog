# Public Companion Repo — Blueprint

*A single public monorepo with **real, deployable** reference implementations that back the blog series and guide others to implement the same thing. Sanitized of all employer/tenant specifics, parameterized so a stranger can `clone → configure → deploy`.*

---

## 1. What this repo is (and isn't)

**Is:** a reference platform. Someone lands here from a blog post, reads the directory's README, fills in a `*.tfvars` / `.env` from a documented example, and stands the thing up in *their own* AWS account against *their own* identity provider. The code is the same shape as what you ran in production — just generic.

**Isn't:** a copy of your internal repos. Every employer name, account ID, tenant ID, ARN, internal hostname, and private repo path is gone, replaced by clearly-named placeholders with example values. Nothing deploys "to my employer" — it deploys to *whoever clones it*.

The guiding principle for "deployable but generic": **config-driven, not fork-driven.** A user should never have to edit source to make it theirs — only variables, tfvars, and a documented OpenAPI/scope set.

---

## 2. Naming

Pick one umbrella name; it'll be the GitHub repo and the thing you link from every post. Some options that read well publicly:

- `claude-bedrock-blueprint`
- `agentcore-mcp-reference`
- `ai-on-aws-fieldnotes` (matches the "findings" voice of the blog)

The doc below assumes the placeholder `<repo>`.

---

## 3. Top-level layout

The two acts of the blog become two top-level parts, plus shared docs and one end-to-end example that ties them together.

```
<repo>/
├── README.md                  # the map: what this is, link to the blog, "start here"
├── LICENSE                    # MIT or Apache-2.0 (see §6)
├── CONTRIBUTING.md
├── SECURITY.md                # how to report; "no secrets in issues"
├── .github/workflows/         # CI: terraform validate/test, pytest, ruff, secret-scan
├── .gitignore                 # tfvars, .env, *.bin caches, dist/, __pycache__
│
├── docs/
│   ├── architecture/          # SVG diagrams: per-part + the before/after (monolith→gateway)
│   ├── adr/                    # the sanitized ADRs — these are the crown jewels, publish them
│   └── posts/                 # one short note per blog post linking prose ↔ the code path
│
├── part-1-claude-on-bedrock/  # ACT I — the production findings, generalized
│   ├── README.md              # what runs here, prerequisites, the ccwb flow
│   ├── credential-shim/       # A1 — the fast DPAPI-cached shim (+ a portable note for mac/linux)
│   ├── distribution/          # A5 — patches + scripts against the AWS upstream (see §5)
│   │   ├── patches/           #   your git-apply-able diffs vs the upstream base commit
│   │   └── README.md          #   "clone upstream @ <commit>, apply these, build"
│   └── mcp-servers/
│       ├── rest-mcp-proxy/    # A5 — the generic YAML tool-registry over a REST dispatcher
│       │   ├── src/
│       │   ├── registry/      #   example YAML tool definitions (the $-less OData mapping, A4)
│       │   └── tests/         #   regression tests incl. "no $ in property keys"
│       └── examples/
│           ├── graph-obo/     # A3 — OBO outbound (M365/Graph-style), against a generic tenant
│           └── vendor-3lo/    # A3 — 3LO via a managed token vault (Atlassian-style)
│
├── part-2-aws-ai-framework/   # ACT II — the AgentCore-native framework
│   ├── README.md
│   ├── terraform/
│   │   ├── modules/{foundation,profiles,archetypes,shared}
│   │   └── examples/          # B-series: reference compositions that actually deploy
│   ├── python/                # the framework package (interceptor, identity, mcp, agents)
│   └── docs/                  # per-profile / per-archetype usage
│
├── examples/
│   └── end-to-end/            # the one composition that wires a gateway + target + interceptor
│                              #   + DCR bridge against a public/stub downstream — "see it run"
└── scripts/
    ├── new_project.py         # B1 — scaffolds a consumer project skeleton with version pins
    └── check-sanitization.sh  # CI guard: greps for forbidden tokens (see §4)
```

Each leaf directory has its own README so a reader who arrives deep (from a search result) is never lost. The READMEs are where "guide people to implement" actually lives — the four-beat blog formula applies here too: what this is → prerequisites → run it → what to change for your environment.

---

## 4. Sanitization — the rule that makes this safe to publish

Treat sanitization as a build gate, not a vibe. Concretely:

**Replace, with documented placeholders:**

| Internal thing | Public placeholder |
|---|---|
| Company name (my employer) | `your-org` / "an enterprise tenant" |
| AWS account `123456789012` | `123456789012` (the canonical AWS docs dummy) |
| Internal repo `your-org/<repo>` | `<repo>` / `your-org/...` |
| Entra tenant / client IDs | `YOUR_TENANT_ID`, `YOUR_CLIENT_ID` env vars |
| Real ARNs, hostnames, S3 buckets | `example.com`, `arn:aws:...:123456789012:...` |
| SharePoint sites / Jira cloud IDs | example/stub values in `*.example.tfvars` |

**Mechanics:**
- Every environment-specific value is a **Terraform variable** or **env var** with an `*.example.tfvars` / `.env.example` showing the shape. The real ones live only on the user's disk and are `.gitignore`d.
- Add `scripts/check-sanitization.sh` to CI: a denylist grep for `my employer`, the account number, internal domains, etc. The build **fails** if any reappear. This is your seatbelt against an accidental paste.
- Add a secret scanner to CI (gitleaks / `detect-secrets`) — you already use `.secrets.baseline` internally, so port that habit.
- Where a real downstream API would be needed to demo (Graph, Jira), ship either a **stub server** in `examples/` or document pointing it at a free-tier/public OData endpoint, so "deployable" doesn't mean "you must have an enterprise tenant to try it."

---

## 5. Two IP nuances worth getting right up front

**(a) Don't re-vendor the AWS solution — ship your patches.** Pillar 1 is a vendored copy of AWS's `guidance-for-claude-code-with-amazon-bedrock`. Its license is **MIT-0 (MIT No Attribution)**, so redistribution *is* permitted — but re-publishing the whole AWS tree means you own the maintenance of someone else's repo. Cleaner: in `part-1/distribution/`, publish only **your** artifacts (the credential-shim source + your `patches/` diffs) plus a README that says "clone upstream at commit `d209253…`, `git apply` these patches, build." You already keep exactly these patches internally, so this is mostly a copy + a README. It also makes your *contribution* legible, which is better for a personal portfolio repo.

**(b) Get employer sign-off before publishing internal-derived work.** Even fully sanitized, code and ADRs derived from an internal production project usually need an OK from your employer (and possibly a quick legal/security skim). Worth doing once, up front, for the whole repo rather than per post. The ADRs are the highest-value, lowest-risk thing to clear first — they're already written as generic engineering reasoning.

---

## 6. License & repo hygiene

- **License:** `Apache-2.0` (patent grant + widely trusted for infra/IaC) or `MIT` (simplest). Since you're consuming MIT-0 upstream, both are compatible. Apache-2.0 is the conventional choice for Terraform-module repos.
- **README "start here":** lead with the architecture diagram and a table mapping **blog post → directory**. That table is the whole point of a companion repo — make it the first thing people see.
- **Versioning / releases:** tag the repo so blog posts can link a stable ref (`?ref=v0.1.0`) and not break when you refactor. Mirrors the lockstep-versioning idea from your framework (ADR 0002) — practice what the posts preach.
- **CONTRIBUTING + issues:** even if you don't expect PRs, a short CONTRIBUTING and issue templates signal "this is maintained," which is what makes a reference repo trustworthy.

---

## 7. How the repo and the blog reinforce each other

- **Every post ends with "Run it yourself → `<repo>/part-X/...`".** The post tells the *story and the why*; the repo holds the *runnable how*. Don't duplicate — link.
- **The repo's `docs/posts/` does the reverse link:** each code directory points back to the post that explains it. A reader who finds the code via GitHub search gets the narrative; a reader who finds the post gets the code.
- **Ship code slightly ahead of the post.** Have the directory for post A1 in the repo (even minimal) before A1 publishes, so the "run it yourself" link is never dead.

---

## 8. Suggested build order for the repo

Mirror the blog's first batch so they ship together:

1. **Scaffold the skeleton** — top-level README with the post↔dir map, LICENSE, CI with the sanitization + secret gates. (Do this first; it's the safety net.)
2. **`part-1/credential-shim/`** — backs post A1, fully self-contained, easiest to make generic.
3. **`part-1/distribution/patches/`** — backs A2, mostly a copy of your existing patches + a build README.
4. **`part-1/mcp-servers/rest-mcp-proxy/`** — backs A4/A5, the reusable core; include the "no `$` in keys" regression test as a teaching artifact.
5. Then grow `part-2/` alongside the B-series.

Doing 1 first means the sanitization guard exists *before* any real code lands — so nothing internal can slip in even on the first commit.
