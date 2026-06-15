# Outbound-auth examples (backs post A3)

> **Status:** placeholder — examples land with post A3.

Each MCP server receives an inbound user JWT and must call a downstream API **as that user**.
There are two ways to get the downstream token, and the right one depends on whether the
downstream is in the same identity tenant or a different vendor.

| Example | When to use it | Mechanism |
|---------|----------------|-----------|
| [`graph-obo/`](graph-obo/) | Downstream is in the **same IdP tenant** (e.g. Microsoft Graph) | OAuth **On-Behalf-Of** (`jwt-bearer` / `on_behalf_of`) — no extra infra, no persisted refresh tokens |
| [`vendor-3lo/`](vendor-3lo/) | Downstream is a **different vendor** (e.g. Atlassian) | **3-legged OAuth** via a managed token vault (consent callback + refresh-token storage) |

## The finding (A3)

The "obviously correct" choice was a managed identity broker for everything. Probing proved
that for the same-tenant case **OBO works server-side, returns 200, and isn't blocked by
Conditional Access** — invalidating the original argument for the broker. So: OBO for
same-tenant, the managed vault only where OBO can't reach (cross-vendor 3LO).

Each example is runnable against a generic tenant — fill in the documented env vars.
