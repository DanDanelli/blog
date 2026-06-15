# Security Policy

## Reporting a vulnerability

If you find a security issue in this reference code, please **do not open a public issue**.
Email the maintainer (see the GitHub profile) with a description and reproduction steps.
You'll get an acknowledgement within a few days.

## Scope and expectations

This is **reference / educational** infrastructure. It is meant to teach a pattern, not to
be dropped into production unreviewed. Before deploying anything here:

- Review the IAM, network, and identity configuration against your own threat model.
- Turn on the hardening that's opt-in by default — notably the Cedar authorization policy
  (it ships **off** so a fresh gateway is usable; see Part 2). A production deployment
  should run with an explicit `permit` policy, not the permissive default.
- Supply your own secrets via your secret manager / write-only Terraform arguments. Never
  commit secrets, and never paste them into issues or PRs.

## What we guard against in this repo

- **No secrets in git:** every PR runs a secret scanner and a sanitization denylist
  ([`scripts/check-sanitization.sh`](scripts/check-sanitization.sh)).
- **No environment-specific identifiers:** account IDs, tenant IDs, ARNs, and hostnames are
  placeholders only.
