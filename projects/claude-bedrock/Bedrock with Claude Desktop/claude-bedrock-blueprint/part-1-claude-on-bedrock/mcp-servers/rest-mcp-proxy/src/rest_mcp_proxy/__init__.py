"""rest-mcp-proxy — a declarative MCP server over a generic REST dispatcher.

A tool is a YAML entry (path, method, params); the dispatcher turns a tool call into an
HTTP request. Adding a capability means editing YAML, not writing handler code.

See the package README for the design and the OData ``$`` finding (post A4).
"""

__version__ = "0.1.0"
