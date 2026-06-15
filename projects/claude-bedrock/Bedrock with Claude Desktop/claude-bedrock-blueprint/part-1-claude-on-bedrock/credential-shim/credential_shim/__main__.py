"""Credential cache shim — a drop-in for the AWS ``credential_process`` interface.

Why this exists
---------------
The real credential binary federates your identity provider → AWS STS
(``AssumeRoleWithWebIdentity``, ~1.7s) on **every** invocation, and some clients create a
new session per request — so a single query can spend ~10s purely on credentials. This
shim serves a locally cached, OS-protected credential blob when it's still valid (warm
calls drop to tens of milliseconds) and only falls through to the real binary on a miss.

Contract
--------
``credential_process`` programs must print a JSON document to stdout with at least
``Version``, ``AccessKeyId``, ``SecretAccessKey``, ``SessionToken`` and ``Expiration``.
This shim is format-agnostic: it caches whatever the real binary prints and only inspects
``Expiration`` to decide freshness.

Wire it up in ``~/.aws/config``::

    [profile my-profile]
    credential_process = /path/to/credential-shim --profile my-profile

Set ``CREDENTIAL_PROCESS_BIN`` to point at the real binary, or rely on the shipped
sibling-directory layout (see ``cache.credential_process_path``).
"""

from __future__ import annotations

import json
import subprocess
import sys

from .cache import credential_process_path, is_fresh, parse_profile
from .stores import get_store


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    profile = parse_profile(argv)
    store = get_store()

    # --- Fast path: a valid cached credential ---------------------------------------
    cached = store.load(profile)
    if cached:
        try:
            creds = json.loads(cached)
            if is_fresh(creds):
                sys.stdout.write(json.dumps(creds))
                return 0
        except (ValueError, TypeError):
            pass  # corrupt cache → fall through to a fresh fetch

    # --- Slow path: invoke the real credential-process and repopulate the cache ------
    binary = credential_process_path()
    try:
        result = subprocess.run([binary, *argv], capture_output=True, text=True)
    except OSError as exc:
        sys.stderr.write(f"credential-shim: cannot run {binary}: {exc}\n")
        return 1

    if result.returncode != 0:
        # Auth failed (e.g. the federated account was revoked) — drop any stale cache so
        # we never serve credentials the IdP has since rejected.
        store.delete(profile)
        if result.stderr:
            sys.stderr.write(result.stderr)
        return result.returncode

    output = result.stdout.strip()
    store.save(profile, output)
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
