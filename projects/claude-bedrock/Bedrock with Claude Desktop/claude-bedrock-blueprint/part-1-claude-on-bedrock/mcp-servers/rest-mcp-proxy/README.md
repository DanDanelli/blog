# rest-mcp-proxy — a declarative MCP server (backs posts A4 & A5)

> **Status:** implemented. `src/rest_mcp_proxy/` is the package, `registry/` holds runnable
> example registries, `tests/` the suite. Runs as a local stdio MCP server today; the same
> `protocol.handle` plugs into a serverless (API Gateway + Lambda) handler for production.

A generic MCP server that exposes any REST API to an MCP client. The design is a
**declarative YAML tool registry** over a **generic REST dispatcher** — adding a tool means
editing a YAML file and redeploying, not writing handler code.

## Design

```
MCP client ──(JWT)──▶ this server ──▶ REST dispatcher ──▶ downstream API
                          ▲
                          └── registry/*.yaml   (one entry per tool)
```

- [`registry/`](registry/) — tool definitions (path, method, params, scopes).
- [`src/`](src/) — the dispatcher, schema builder, and inbound JWT verification.
- [`tests/`](tests/) — regression tests, including the **"no `$` in property keys"** guard.

## The `$`-in-schema finding (A4)

Bedrock/Anthropic validates tool `input_schema` property keys against
`^[a-zA-Z0-9_.-]{1,64}$`. OData params like `$select` / `$top` are **rejected by the model,
server-side** — a raw `curl` to the API passes, but Claude Desktop fails. The proxy exposes
the **`$`-less** name to the client and translates back to the wire name in the dispatcher.
The registry YAML keeps the real `$`-name so it still documents the OData wire contract.
There's a test that asserts no schema property key contains a `$`.

## Run it locally (stdio)

```bash
pip install -e ".[dev]"
# point it at a registry; ACCESS_TOKEN is optional (the public example needs none)
REGISTRY=registry/jsonplaceholder.example.yaml python -m rest_mcp_proxy
```

Then send line-delimited JSON-RPC on stdin:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_post","arguments":{"id":1}}}
```

Wire it into a client's MCP config with `command: python`, `args: ["-m","rest_mcp_proxy"]`,
and the `REGISTRY` / `ACCESS_TOKEN` env vars.

## What to change for your environment

- Set `BASE_URL` (or the registry's `base_url`) to your downstream API.
- Set `ACCESS_TOKEN` to the bearer token for that API (for production, this is where the
  inbound JWT → downstream token exchange plugs in — see the [outbound-auth examples](../examples/)).
- Add your tools in `registry/`. See [`registry/odata.example.yaml`](registry/odata.example.yaml)
  for the `$`-param handling and `quote_safe`, and [`jsonplaceholder.example.yaml`](registry/jsonplaceholder.example.yaml)
  for a no-auth runnable starter.

## Develop / test

```bash
pip install -e ".[dev]"
pytest        # registry validation (incl. the no-'$' guarantee), dispatcher, protocol
ruff check src tests
```
