#!/usr/bin/env bash
# Replace a pull request's description with the contents of a markdown file.
#
# Usage: pr_body_patch.sh <pr-number> <body-markdown-file>
#
# Uses the hosting CLI (`gh`) and `jq`. When a token environment variable is
# set but rejected, retries once with the CLI's stored login and says which
# authentication was used. Never prints a token.
set -euo pipefail

pr="${1:?pull request number required}"
body_file="${2:?body markdown file required}"

if [[ ! -f "$body_file" ]]; then
  echo "error: file not found: $body_file" >&2
  exit 1
fi

for tool in gh jq; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "error: $tool is required" >&2
    exit 1
  fi
done

repo="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
endpoint="repos/${repo}/pulls/${pr}"
errors="$(mktemp)"
trap 'rm -f "$errors"' EXIT

patch() {
  jq -Rs '{body: .}' "$body_file" | "$@" gh api -X PATCH "$endpoint" --input - >/dev/null
}

auth="environment token"
if [[ -z "${GH_TOKEN:-}" ]]; then
  auth="stored login"
fi

if patch env 2>"$errors"; then
  :
elif [[ -n "${GH_TOKEN:-}" ]] && grep -qi 'bad credentials' "$errors"; then
  echo "warn: token environment variable rejected, retrying with stored login" >&2
  auth="stored login"
  patch env -u GH_TOKEN
else
  cat "$errors" >&2
  exit 1
fi

echo "patched: pull request #${pr} in ${repo} (authentication: ${auth})"
