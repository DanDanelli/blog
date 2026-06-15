# `aws_ai_framework` (Python package)

> **Status:** placeholder — package lands with the Part 2 modules.

The Python side of the framework, published to a package registry in lockstep with the
Terraform modules. Holds the runtime code the managed services can't provide natively:

- `mcp/interceptor.py` — the REQUEST interceptor (e.g. plain text → Atlassian Document
  Format) that runs *before* gateway schema validation.
- `identity/` — token federation helpers for the profiles that need them.
- `agents/`, `common/` — runtime-agent scaffolding and shared utilities.

## Develop

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
```
