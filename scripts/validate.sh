#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$REPO_ROOT/scripts/validate_skills.py"
python3 "$REPO_ROOT/scripts/validate_evals.py"
python3 -m unittest discover -s "$REPO_ROOT/tests" -p 'test_*.py'
python3 "$REPO_ROOT/scripts/context_report.py" --check
"$REPO_ROOT/scripts/check-public-safety.sh"

if grep -rnE 'TODO|PLACEHOLDER' \
  "$REPO_ROOT/core" "$REPO_ROOT/docs" "$REPO_ROOT/adapters" \
  "$REPO_ROOT/examples" "$REPO_ROOT/evals" "$REPO_ROOT"/README*.md; then
  echo "Unresolved placeholder found." >&2
  exit 1
fi

echo "Repository validation passed."
