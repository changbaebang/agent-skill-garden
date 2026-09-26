#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATTERNS="$REPO_ROOT/config/forbidden-patterns.txt"
failed=0

# Use one Git-aware file set for both scanners. Ignored local runs stay private,
# while tracked files are scanned even if their path now matches .gitignore.
# Git also omits its metadata, including the .git file in a linked worktree.
file_list="$(mktemp)"
trap 'rm -f "$file_list"' EXIT
if ! git -C "$REPO_ROOT" ls-files -z --cached --others --exclude-standard > "$file_list"; then
  echo "Cannot enumerate repository files; cannot verify public safety." >&2
  exit 1
fi
cd "$REPO_ROOT"
files=()
while IFS= read -r -d '' path; do
  [[ "$path" == config/forbidden-patterns.txt ]] && continue
  if [[ -L "$path" ]]; then
    echo "Cannot safely scan symbolic link: $path" >&2
    exit 1
  fi
  # A tracked deletion has no working-tree contents to publish.
  [[ ! -e "$path" ]] && continue
  if [[ ! -f "$path" ]]; then
    echo "Cannot scan non-file repository entry: $path" >&2
    exit 1
  fi
  files+=("./$path")
done < "$file_list"

# A successful enumeration with no eligible contents is not a completed scan.
if [[ ${#files[@]} -eq 0 ]]; then
  echo "No eligible repository files; cannot verify public safety." >&2
  exit 1
fi

# Resolve the scanner up front; distinguish a clean result (1) from an error.
# Treat binary files as text in both implementations so their coverage agrees.
if command -v rg >/dev/null 2>&1; then
  scan() {
    rg -n --text --no-ignore -e "$1" -- "${files[@]}"
  }
elif command -v grep >/dev/null 2>&1; then
  echo "ripgrep not found; scanning with grep." >&2
  scan() {
    grep -nEa -e "$1" -- "${files[@]}"
  }
else
  echo "No usable scanner found; cannot verify public safety." >&2
  exit 1
fi

active_patterns=0
while IFS= read -r pattern || [[ -n "$pattern" ]]; do
  [[ -z "${pattern//[[:space:]]/}" ]] && continue
  [[ "$pattern" == \#* ]] && continue
  active_patterns=$((active_patterns + 1))
  if scan "$pattern"; then
    failed=1
  else
    status=$?
    if [[ "$status" -ne 1 ]]; then
      echo "Public-safety scanner failed (exit $status)." >&2
      exit 1
    fi
  fi
done < "$PATTERNS"

if [[ "$active_patterns" -eq 0 ]]; then
  echo "No active public-safety patterns; cannot verify public safety." >&2
  exit 1
fi

if [[ "$failed" -ne 0 ]]; then
  echo "Public-safety scan failed." >&2
  exit 1
fi

echo "Public-safety scan passed."
