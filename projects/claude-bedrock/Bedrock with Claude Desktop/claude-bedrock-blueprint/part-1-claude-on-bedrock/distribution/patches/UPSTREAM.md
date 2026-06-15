# Upstream pin

These patches apply on top of AWS's solution, at a known-good base commit.

- **Origin:** `https://github.com/aws-solutions-library-samples/guidance-for-claude-code-with-amazon-bedrock.git`
- **Base commit:** `d209253c029dbe7481a3d9f1403f02624e380185` (branch `main`)
- **License:** MIT-0 (redistribution permitted; we ship patches rather than re-vendor)

## What each patch does

| Patch | File it modifies | Change |
|-------|------------------|--------|
| `codebuild-windows.yaml.patch` | `deployment/infrastructure/codebuild-windows.yaml` | The **Windows binary is built here, not by `package.py`.** Adds the `cryptography._rust` Nuitka includes, drops `--onefile` for standalone `.dist` folders, and adds the credential-shim build. |
| `package.py.patch` | `source/.../cli/commands/package.py` | Same Nuitka includes for the local/native path, resolves the otel-helper inside its `.dist`, and rewrites `install.bat` to copy `.dist` folders and wire the shim as `credential_process` (with a fallback). |
| `distribute.py.patch` | `source/.../cli/commands/distribute.py` | Ships `.dist` folders (not `.exe`), includes the shim, and zips/copies directories recursively. |

## The `_rust` finding in one line

`cryptography._rust` is loaded **dynamically** (via PyJWT → cryptography), so Nuitka's
auto-following bundles it **non-deterministically** — some builds include `_rust.pyd`,
others don't, and the latter fail with a bare `ImportError` only on clean machines with no
system Python. The fix is to declare it explicitly:

```
--include-package=cryptography
--include-package-data=cryptography
--include-module=cryptography.hazmat.bindings._rust
```

…in **both** build paths. The Windows one (the CodeBuild buildspec) is the one that actually
ships the fleet binary — putting the flags only in `package.py` looks correct locally and
still fails in production.

## Verify after building

`_rust.pyd` must appear under
`credential-process-windows.dist/cryptography/hazmat/bindings/_rust.pyd`.
