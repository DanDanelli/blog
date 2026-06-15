#!/usr/bin/env bash
#
# check-sanitization.sh — fail the build if any environment-specific / internal token
# leaks into the public repo. This is the seatbelt against an accidental paste from an
# internal source tree.
#
# Edit DENYLIST below to match the things that must NEVER appear publicly. Keep entries
# lowercase; the grep is case-insensitive.
#
# Usage:  ./scripts/check-sanitization.sh
# Exit:   0 = clean, 1 = a forbidden token was found.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# --- Forbidden literal tokens (case-insensitive) ----------------------------------------
# Add your real org name, internal domains, and any private repo slugs here.
DENYLIST=(
  "my employer"
  "your-org"
  "123456789012"          # a real AWS account number
  "123456789012"          # a real AWS account number (Bedrock federated role)
  ".onmicrosoft.com"      # real tenant vanity domains
  "<internal-repo>"   # internal repo slug
)

# --- Forbidden patterns (extended regex) ------------------------------------------------
# Catches the *shape* of real identifiers even when the exact value isn't known.
# The canonical AWS docs dummy account (123456789012) is allowed and excluded below.
PATTERNS=(
  '\barn:aws[a-z-]*:[a-z0-9-]*:[a-z0-9-]*:(?!123456789012)[0-9]{12}:'  # ARNs w/ a non-dummy account
  '\b(?!123456789012)[0-9]{12}\b'                                       # any other 12-digit AWS account id
)

# Paths we don't scan (binary/build/vendored noise).
EXCLUDES=(
  ":(exclude).git/*"
  ":(exclude)**/.terraform/*"
  ":(exclude)**/dist/*"
  ":(exclude)**/*.png"
  ":(exclude)**/*.svg"
  ":(exclude)scripts/check-sanitization.sh"   # this file documents the denylist itself
)

fail=0

echo "== sanitization: literal denylist =="
for token in "${DENYLIST[@]}"; do
  if git grep -I -n -i -- "$token" -- "${EXCLUDES[@]}" >/dev/null 2>&1; then
    echo "FORBIDDEN TOKEN: '$token'"
    git grep -I -n -i -- "$token" -- "${EXCLUDES[@]}" || true
    fail=1
  fi
done

echo "== sanitization: identifier patterns =="
for pat in "${PATTERNS[@]}"; do
  if git grep -I -n -P -- "$pat" -- "${EXCLUDES[@]}" >/dev/null 2>&1; then
    echo "FORBIDDEN PATTERN: '$pat'"
    git grep -I -n -P -- "$pat" -- "${EXCLUDES[@]}" || true
    fail=1
  fi
done

if [[ "$fail" -ne 0 ]]; then
  echo
  echo "Sanitization check FAILED. Replace the values above with documented placeholders"
  echo "(see README § 'A note on what's not here'). Dummy account 123456789012 is allowed."
  exit 1
fi

echo "Sanitization check passed."
