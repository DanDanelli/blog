---
title: "Getting Claude Code onto a fleet machine: latency and a packaging trap"
date: 2026-06-18
draft: true
description: "Two problems that hit only on the fleet, not on dev machines: an 11-second 'hello' caused by credential federation, and a credential binary that failed on every clean PC."
summary: "A per-request credential storm fixed with a cached shim (~11s→~3s), and a Nuitka build that non-deterministically dropped cryptography._rust — both about the same binary."
series: ["Claude on Bedrock"]
series_order: 2
categories: ["Engineering"]
tags: ["AWS", "Bedrock", "Performance", "Windows", "Python", "Nuitka"]
---

<!-- Replace REPO_URL with the public companion repo once it's published. -->

Pillar 1 of running Claude Code on Bedrock is a small binary — the `credential_process` that turns a corporate OIDC login into short-lived AWS credentials. It comes from [AWS's Guidance solution](https://github.com/aws-solutions-library-samples/guidance-for-claude-code-with-amazon-bedrock), and on a developer's machine it works fine. Then it meets the fleet, and two problems show up that you'd never catch in dev. This post is both, because they're the same binary and the same lesson: **test on a machine as clean and as constrained as the target.**

## Problem 1 — the 11-second hello

The first complaint after rollout wasn't about answers. It was speed. A trivial "hello" took about **eleven seconds** on Windows before anything came back. That's the kind of latency that makes people quietly stop using a tool.

The model wasn't the problem. Credentials were.

### Why it matters

Latency is a tax on adoption. A tool that's correct but sluggish gets abandoned for the faster, worse option. "Make hello fast" wasn't polish — it was the difference between the rollout landing or not.

### How it actually works

Each time the `credential_process` binary runs, it federates the corporate IdP to AWS STS via `AssumeRoleWithWebIdentity` and gets short-lived credentials. That federation is **inherently slow — about 1.7 seconds per call.** Not a bug; a real round-trip to STS.

One 1.7s call would be fine. The trouble is the count. The client creates a **new credential session per Bedrock HTTP request** and ignores the `Expiration` field that would let the SDK cache and reuse them. So a single "hello" fans out into roughly six credential-process invocations:

```
6 calls × ~1.7s ≈ 10.2s   ← spent entirely on credentials, before the model does anything
```

There's the eleven seconds.

The federation cost is fixed and the per-request behavior wasn't configurable, so instead of speeding up AWS's binary — or forking it — we avoided *repeating* the call, by interposing a small **shim** of our own where `credential_process` points. On each call it:

1. Checks a local cache. Valid credentials with >5 min of life left are returned immediately (~130 ms).
2. Otherwise it calls the real, slow binary, stores the result, and returns it.

Warm hits drop from ~1.7s to ~130 ms (~13×); the six-call "hello" goes ~10.2s → ~1.8s, and end to end the query goes from ~11s to about **3 seconds**.

Caching credentials on disk is a security question too. On Windows the shim encrypts the cache with **DPAPI**, which binds the ciphertext to the current user on the current machine — copying the file elsewhere yields nothing. Two more deliberate choices: it's **stdlib-only** (no SDK, no crypto lib) so its own cold start is ~50 ms and doesn't reintroduce the latency it's removing; and it **fails to correctness** — any cache problem is treated as a miss and falls through to the real binary, and an auth failure invalidates the cache. A cache must never be able to *break* auth, only speed it up.

## Problem 2 — it worked on my machine because my machine had Python

The same binary had a second issue, and this one didn't show up as slowness — it showed up as a flat refusal to start. It ran for every developer who tested it, and failed on every clean fleet PC with a bare `ImportError`. The classic "works on my machine," inverted: it worked on *ours* for a reason that had nothing to do with the code.

### Why it matters

This is the bug that ships. It passes every developer's test because dev machines are contaminated with the very thing that's missing — a system Python with the right libraries. Clean machines fail. If you don't reproduce the clean environment, the fleet finds the bug for you.

### How it actually works

The binary is a Python program compiled to a standalone executable with [Nuitka](https://nuitka.net/). At startup it imports PyJWT, which pulls a chain you don't see:

```
__main__  →  import jwt  →  jwt.utils  →  cryptography.hazmat.primitives.asymmetric.ec
          →  cryptography/exceptions.py  →  from cryptography.hazmat.bindings._rust import ...
```

That last import is a **native Rust extension** (`_rust.pyd`) that `cryptography` ships as a compiled binary. For the executable to run on a machine with no Python, that `.pyd` has to be inside the bundle.

It wasn't — reliably. Nuitka follows imports automatically, but its following is **non-deterministic for lazily-loaded native bindings**. `_rust` is imported dynamically, deep inside `cryptography`, so some builds pulled `_rust.pyd` in and others didn't. The ones that did worked everywhere; the ones that didn't worked only where a *system* `cryptography` was installed to satisfy the import at runtime — i.e. on developer machines. Clean PCs raised the `cryptography.hazmat.bindings._rust ImportError`.

The fix is to stop relying on auto-following and declare it:

```
--include-package=cryptography
--include-package-data=cryptography
--include-module=cryptography.hazmat.bindings._rust
```

Verify it landed at `credential-process-windows.dist/cryptography/hazmat/bindings/_rust.pyd`.

The part that cost extra time: **the fix goes in two places.** There are two build paths — the local packaging path, and the Windows build, which runs through a CodeBuild buildspec, *not* the local packager. The fleet's Windows binary is built by CodeBuild, so putting the flags only in the local path looks correct when you test and still ships a broken binary. And you have to redeploy the CodeBuild stack before a rebuild, or the live buildspec reverts to the old behavior.

## The lesson

Both problems share a root: **the fleet is not your laptop.** The slow path ran six times because of behavior you only notice under real request volume; the import failed only where no system Python masked it. The fixes were a cache that stops repeating an expensive call, and an explicit "include this exact module" that replaces a non-deterministic guess. When automation is unpredictable, declare what you need; when there's more than one build path, fix the one that ships.

The cross-platform shim (DPAPI on Windows, Keychain on macOS, libsecret on Linux) and the build patches against the AWS upstream are in the companion repo: [credential-shim](REPO_URL/tree/main/part-1-claude-on-bedrock/credential-shim) and [distribution](REPO_URL/tree/main/part-1-claude-on-bedrock/distribution).

Next: [authentication, end to end]({{< ref "authentication-end-to-end" >}}) — getting Claude *in*, and letting it act as the user.
