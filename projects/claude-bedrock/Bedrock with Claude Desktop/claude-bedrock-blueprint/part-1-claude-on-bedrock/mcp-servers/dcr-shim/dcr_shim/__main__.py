"""Run the DCR shim locally.

Config via env:
  TENANT_ID        Entra tenant id (required)
  CLIENT_ID        pre-provisioned App Registration client id (required)
  PUBLIC_BASE_URL  the shim's externally-reachable base URL (required)
  REDIRECT_URIS    comma-separated loopback callbacks (optional)
  SCOPES           comma-separated scopes for discovery (optional)
  AUTH_VERSION     v2 (default) or v1 — must match the API Gateway authorizer
  HOST / PORT      bind address (default 127.0.0.1:8401)

Example:
  TENANT_ID=YOUR_TENANT CLIENT_ID=YOUR_CLIENT PUBLIC_BASE_URL=https://example.com \
    python -m dcr_shim
"""

from __future__ import annotations

import os
import sys

from .config import Config
from .server import serve


def main() -> int:
    cfg = Config.from_env()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8401"))
    sys.stderr.write(f"dcr-shim listening on {host}:{port} (issuer {cfg.public_base_url})\n")
    serve(cfg, host=host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
