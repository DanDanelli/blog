"""Pure, platform-independent helpers for the credential shim.

These functions have no I/O and no side effects, so they're trivially unit-testable
(see ``tests/test_cache.py``). All the platform-specific behavior lives in ``stores.py``.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

# Reuse a cached credential only while it has at least this much life left. The skew
# protects against a credential expiring mid-request after we hand it back.
DEFAULT_SKEW = timedelta(minutes=5)


def parse_profile(argv: list[str]) -> str:
    """Return the ``--profile`` value AWS passes to ``credential_process``.

    Accepts both ``--profile NAME`` and ``--profile=NAME``. Falls back to ``"default"``.
    """
    for i, arg in enumerate(argv):
        if arg == "--profile" and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith("--profile="):
            return arg.split("=", 1)[1]
    return "default"


def is_fresh(
    creds: dict,
    *,
    now: datetime | None = None,
    skew: timedelta = DEFAULT_SKEW,
) -> bool:
    """True if ``creds`` carries an ``Expiration`` far enough in the future to reuse.

    Tolerates both ``...Z`` and explicit-offset ISO-8601 forms, and naive timestamps
    (assumed UTC). A missing or unparseable ``Expiration`` is treated as not fresh.
    """
    now = now or datetime.now(timezone.utc)
    raw = creds.get("Expiration")
    if not raw:
        return False
    try:
        expiry = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return False
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return expiry - now > skew


def credential_process_path() -> str:
    """Locate the real ``credential-process`` binary the shim falls through to.

    Resolution order:
      1. ``CREDENTIAL_PROCESS_BIN`` env var (explicit override — preferred for testing
         and non-standard layouts).
      2. The shipped sibling layout, discovered relative to this binary::

             <install>/credential-shim/credential-shim-<os>(.exe)
             <install>/credential-process/credential-process-<os>(.exe)

    The fixed relative layout is deliberate: the shim finds the real binary without any
    absolute paths baked in, so the bundle is relocatable.
    """
    override = os.environ.get("CREDENTIAL_PROCESS_BIN")
    if override:
        return override

    shim_dir = os.path.dirname(os.path.abspath(sys.executable))
    install_dir = os.path.dirname(shim_dir)
    if sys.platform.startswith("win"):
        name = "credential-process-windows.exe"
    elif sys.platform == "darwin":
        name = "credential-process-macos"
    else:
        name = "credential-process-linux"
    return os.path.join(install_dir, "credential-process", name)
