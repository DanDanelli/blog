# Portability notes

The cache *logic* (freshness check, fast/slow path, invalidate-on-failure) is identical
everywhere — only the **encryption backend** differs, because each OS exposes a different
secret store. The shim picks the right one automatically (`stores.get_store()`).

| Platform | Backend | At-rest protection | Requirement |
|----------|---------|--------------------|-------------|
| Windows | DPAPI file (`CryptProtectData`) | Bound to current **user + machine** | none (stdlib `ctypes`) |
| macOS | login **Keychain** (`security` CLI) | Keychain ACL | `security` (ships with macOS) |
| Linux | **libsecret** (`secret-tool`) | Secret Service / keyring | `secret-tool` installed |
| Linux (fallback) | `0600` file | **Not encrypted at rest** (warns) | none |

## Caveats worth knowing

- **macOS / Linux pass the secret as a CLI argument** (`security -w`, and `secret-tool`
  reads stdin — Linux avoids the issue; macOS does not). On a shared host the value can
  briefly appear in `ps`. For a single-user laptop (the target case) this is acceptable;
  for multi-user hosts, prefer the DPAPI/file backends or a hardened keyring.
- **DPAPI is the strongest of the three** because the ciphertext is unusable off the
  origin machine/user. The macOS/Linux keyrings protect via ACL, not by binding to
  hardware.
- **The fallback file store is opt-out, not silent:** it prints a one-time warning to
  stderr. Install `secret-tool` (e.g. `apt install libsecret-tools`) to get encryption.

## Adding a backend

Implement `SecureStore` (`load` / `save` / `delete`) in `stores.py` and add a branch to
`get_store()`. Keep `save`/`delete` best-effort (swallow errors) — a cache problem must
never break authentication; the shim just falls through to the real binary.
