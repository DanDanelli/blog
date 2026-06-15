# Distribution — patches against the AWS upstream (backs post A2)

> **Status:** patches shipped. Three `git apply`-able diffs in [`patches/`](patches/), an
> [`apply-patches.sh`](apply-patches.sh) helper, and the pin + details in
> [`patches/UPSTREAM.md`](patches/UPSTREAM.md).

This directory does **not** re-vendor AWS's solution. It ships only the changes, as
`git apply`-able patches against a pinned upstream commit, so credit and the diff stay
legible — and so you're not maintaining a fork of someone else's repo.

## Upstream

- **Repo:** [`aws-solutions-library-samples/guidance-for-claude-code-with-amazon-bedrock`](https://github.com/aws-solutions-library-samples/guidance-for-claude-code-with-amazon-bedrock)
- **License:** MIT-0 (redistribution permitted; we still prefer patches over re-vendoring)
- **Pinned base commit:** `d209253c029dbe7481a3d9f1403f02624e380185` (see [`patches/UPSTREAM.md`](patches/UPSTREAM.md))

## How to apply

One command — clones upstream at the pin, drops the shim into `source/credential_shim/`,
and applies all three patches:

```bash
./apply-patches.sh            # produces ./upstream, a buildable tree
```

Or by hand:

```bash
git clone https://github.com/aws-solutions-library-samples/guidance-for-claude-code-with-amazon-bedrock.git
cd guidance-for-claude-code-with-amazon-bedrock
git checkout d209253c029dbe7481a3d9f1403f02624e380185
# the shim is a NEW file the patches reference — copy the package in first:
cp -r /path/to/distribution/../credential-shim/credential_shim source/credential_shim
git apply /path/to/distribution/patches/*.patch
# then build per upstream's instructions (Nuitka — see patches/UPSTREAM.md)
```

> The patches *wire up* and *build* the shim, but the shim source itself lives in
> [`../credential-shim/`](../credential-shim/) (post A1). Copy it to `source/credential_shim/`
> before applying, or just use `apply-patches.sh`, which does it for you.

## What the patches do

- **Nuitka `cryptography._rust` fix (A2):** declare the native Rust binding explicitly in the
  build flags so the credential binary runs on **clean machines with no system Python**. The
  flags go in *two* places — the local packaging path and the Windows CodeBuild buildspec
  (the Windows binary is built there, not by the local packager).
- **Standalone `.dist` packaging** instead of one-file `.exe`.
- Wiring to invoke the [credential shim](../credential-shim/) as `credential_process`.
