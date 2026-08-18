#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATTERNS="$REPO_ROOT/config/forbidden-patterns.txt"
failed=0

while IFS= read -r pattern || [[ -n "$pattern" ]]; do
  [[ -z "${pattern//[[:space:]]/}" ]] && continue
  [[ "$pattern" == \#* ]] && continue
  if rg -n --hidden --glob '!.git/**' --glob '!config/forbidden-patterns.txt' -e "$pattern" "$REPO_ROOT"; then
    failed=1
  fi
done < "$PATTERNS"

if [[ "$failed" -ne 0 ]]; then
  echo "Public-safety scan failed." >&2
  exit 1
fi

echo "Public-safety scan passed."
