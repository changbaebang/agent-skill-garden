#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATTERNS="$REPO_ROOT/config/forbidden-patterns.txt"
failed=0

# The scan must never pass by accident. `if <scanner> ...` treats a missing
# binary as "no match", so an absent ripgrep would report a clean repository
# without reading a single file. Resolve the scanner up front and fall back to
# grep, which is always present.
if command -v rg >/dev/null 2>&1; then
  scan() {
    rg -n --hidden \
      --glob '!.git/**' \
      --glob '!config/forbidden-patterns.txt' \
      -e "$1" "$REPO_ROOT"
  }
elif command -v grep >/dev/null 2>&1; then
  echo "ripgrep not found; scanning with grep." >&2
  scan() {
    grep -rnE --binary-files=without-match \
      --exclude-dir=.git \
      --exclude=forbidden-patterns.txt \
      -e "$1" "$REPO_ROOT"
  }
else
  echo "No usable scanner found; cannot verify public safety." >&2
  exit 1
fi

while IFS= read -r pattern || [[ -n "$pattern" ]]; do
  [[ -z "${pattern//[[:space:]]/}" ]] && continue
  [[ "$pattern" == \#* ]] && continue
  if scan "$pattern"; then
    failed=1
  fi
done < "$PATTERNS"

if [[ "$failed" -ne 0 ]]; then
  echo "Public-safety scan failed." >&2
  exit 1
fi

echo "Public-safety scan passed."
