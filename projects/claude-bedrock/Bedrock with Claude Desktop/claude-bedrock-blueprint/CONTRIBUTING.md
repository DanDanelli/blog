# Contributing

Thanks for your interest. This is a reference repo that backs a blog series, so
contributions that improve clarity, fix bugs in the examples, or broaden portability
(other identity providers, other downstreams) are very welcome.

## Ground rules

1. **Never commit environment-specific values.** No real account IDs, tenant IDs, client
   IDs, ARNs, hostnames, or organization names. Use the documented placeholders. CI runs
   [`scripts/check-sanitization.sh`](scripts/check-sanitization.sh) and a secret scan on
   every PR — a hit fails the build.
2. **Config over forks.** New environment-specific behavior should be a variable or env var
   with an `*.example` showing its shape — not a hardcoded value someone has to edit out.
3. **Keep examples runnable.** If you add a module or server, add the minimal example and
   test that proves it composes/stands up.

## Workflow

1. Open an issue describing the change before a large PR.
2. Branch, commit with clear messages, and open a PR against `main`.
3. Make sure CI is green: `terraform validate` / `terraform test`, `pytest`, `ruff`, the
   secret scan, and the sanitization guard.

## Local checks

```bash
# Python
cd part-2-aws-ai-framework/python && pip install -e ".[dev]" && pytest && ruff check .

# Terraform (per module/example)
terraform init -backend=false && terraform validate && terraform test

# Sanitization guard
./scripts/check-sanitization.sh
```
