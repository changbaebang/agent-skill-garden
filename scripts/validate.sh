#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$REPO_ROOT/scripts/validate_skills.py"
python3 "$REPO_ROOT/scripts/validate_evals.py"
python3 - "$REPO_ROOT" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "scripts"))
from skill_eval import main

# Routing has its own format and validator above. Every other JSON definition
# under evals is a behavioral suite, including suites added in subdirectories.
for suite in sorted((root / "evals").rglob("*.json")):
    if suite == root / "evals" / "routing.json":
        continue
    status = main(["validate", str(suite)])
    if status:
        raise SystemExit(status)
PY
python3 -m unittest discover -s "$REPO_ROOT/tests" -p 'test_*.py'
python3 "$REPO_ROOT/scripts/context_report.py" --check
"$REPO_ROOT/scripts/check-public-safety.sh"

if grep -rnE 'TODO|PLACEHOLDER' \
  "$REPO_ROOT/core" "$REPO_ROOT/docs" "$REPO_ROOT/adapters" \
  "$REPO_ROOT/examples" "$REPO_ROOT/evals" "$REPO_ROOT/integrations" \
  "$REPO_ROOT"/README*.md; then
  echo "Unresolved placeholder found." >&2
  exit 1
fi

echo "Repository validation passed."
