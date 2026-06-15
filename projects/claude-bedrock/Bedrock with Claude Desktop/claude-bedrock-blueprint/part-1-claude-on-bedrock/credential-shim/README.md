# Credential Shim — fast cached `credential_process` (backs post A1)

> **Status:** implemented. Stdlib-only, cross-platform. `credential_shim/` is the package,
> `tests/` the test suite, [`PORTABILITY.md`](PORTABILITY.md) the per-OS backend notes.

## The problem this solves

A simple Claude query on Windows took ~11 seconds. The cause isn't the model — it's
credentials. The `credential-process` binary federates your IdP → AWS STS via
`AssumeRoleWithWebIdentity` (~1.7s each), and the client creates a **new session per Bedrock
request**, ignoring the credential `Expiration` field. One query → ~6 credential calls ≈
10.2s spent purely on auth.

## The fix

A thin **shim** that sits where `credential_process` points and serves a local cache when
the cached credentials are still valid (> 5 min to expiry), only falling through to the real
binary on a miss.

- **Fast:** warm cache ~130ms vs ~1.7s (~13×); end-to-end "hello" ~11s → ~3s.
- **Safe on Windows:** the cache is encrypted with **DPAPI** (`CryptProtectData`), binding the
  blob to the current user + machine — copying the `.bin` elsewhere is useless.
- **Cheap to start:** stdlib + `ctypes` only — no `boto3`, no `cryptography` — for a ~50ms
  cold start.

## How to use it

```ini
# ~/.aws/config
[profile my-profile]
credential_process = /path/to/credential-shim --profile my-profile
```

Point the shim at the real binary with `CREDENTIAL_PROCESS_BIN`, or rely on the shipped
sibling-directory layout (see `credential_shim/cache.py::credential_process_path`). The
first call populates the cache; subsequent calls are served warm until ~5 min before
expiry. Run it directly with `python -m credential_shim --profile my-profile`.

## Develop / test

```bash
pip install -e ".[dev]"
pytest          # pure helpers + file-store round-trip + fast/slow/invalidate paths
ruff check .
```

## What to change for your environment

Nothing in the source — the shim is identity-provider agnostic. Only your `~/.aws/config`
profile and the on-disk binary layout are environment-specific (both documented here).

## Portability note

DPAPI is Windows-only. A macOS/Linux variant using the OS keychain / an age-encrypted file
is sketched in [`PORTABILITY.md`](PORTABILITY.md) *(to come)* — the cache logic is identical;
only the encryption backend differs.
