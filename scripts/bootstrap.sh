#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="codex"
HOME_ROOT="$HOME"
APPLY=0
SKIP_VALIDATION=0

usage() {
  cat <<'EOF'
Usage: scripts/bootstrap.sh [options]

Options:
  --target codex|claude|cursor|all  Host environment to prepare (default: codex)
  --home PATH                       Home directory to prepare (default: $HOME)
  --apply                           Apply the reviewed plan
  --skip-validation                 Skip repository validation (intended for tests)
  -h, --help                        Show this help

The command never overwrites an existing host guidance file or skill.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="${2:-}"; shift 2 ;;
    --home) HOME_ROOT="${2:-}"; shift 2 ;;
    --apply) APPLY=1; shift ;;
    --skip-validation) SKIP_VALIDATION=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "$TARGET" =~ ^(cursor|claude|codex|all)$ ]] || {
  echo "Invalid target: $TARGET" >&2
  exit 2
}

[[ -d "$HOME_ROOT" ]] || {
  echo "Home directory does not exist: $HOME_ROOT" >&2
  exit 2
}
HOME_ROOT="$(cd "$HOME_ROOT" && pwd)"
CREATE_PROFILE=1
if [[ -n "${AGENT_GARDEN_PROFILE:-}" ]]; then
  PROFILE="$(
    HOME="$HOME_ROOT" python3 -c \
      'import os, sys; print(os.path.abspath(os.path.expandvars(os.path.expanduser(sys.argv[1]))))' \
      "$AGENT_GARDEN_PROFILE"
  )"
  CREATE_PROFILE=0
  [[ -e "$PROFILE" || -L "$PROFILE" ]] || {
    echo "AGENT_GARDEN_PROFILE does not exist: $PROFILE" >&2
    exit 2
  }
else
  PROFILE="$HOME_ROOT/.agent-garden/profile.ini"
fi

if [[ "$SKIP_VALIDATION" -eq 0 ]]; then
  "$REPO_ROOT/scripts/validate.sh"
fi

run_installer() {
  local apply_mode="$1"
  if [[ "$apply_mode" -eq 1 ]]; then
    HOME="$HOME_ROOT" \
      AGENTS_HOME="$HOME_ROOT/.agents" \
      CLAUDE_HOME="$HOME_ROOT/.claude" \
      "$REPO_ROOT/scripts/install.sh" \
        --target "$TARGET" \
        --scope user \
        --apply
    return
  fi
  HOME="$HOME_ROOT" \
    AGENTS_HOME="$HOME_ROOT/.agents" \
    CLAUDE_HOME="$HOME_ROOT/.claude" \
    "$REPO_ROOT/scripts/install.sh" \
      --target "$TARGET" \
      --scope user
}

conflicts=0
guidance_plan() {
  local source="$1"
  local destination="$2"
  if [[ ! -e "$destination" && ! -L "$destination" ]]; then
    echo "PLAN $destination <- $source"
  elif cmp -s "$source" "$destination"; then
    echo "OK   $destination"
  else
    echo "CONFLICT $destination (merge manually; it will not be overwritten)" >&2
    conflicts=$((conflicts + 1))
  fi
}

if [[ "$TARGET" == "codex" || "$TARGET" == "all" ]]; then
  guidance_plan "$REPO_ROOT/adapters/codex/AGENTS.md" "$HOME_ROOT/.codex/AGENTS.md"
fi
if [[ "$TARGET" == "claude" || "$TARGET" == "all" ]]; then
  guidance_plan "$REPO_ROOT/adapters/claude/CLAUDE.md" "$HOME_ROOT/.claude/CLAUDE.md"
fi
if [[ "$TARGET" == "cursor" || "$TARGET" == "all" ]]; then
  guidance_plan \
    "$REPO_ROOT/adapters/cursor/rules/agent-skill-garden.mdc" \
    "$HOME_ROOT/.cursor/rules/agent-skill-garden.mdc"
fi

if [[ "$CREATE_PROFILE" -eq 0 || -e "$PROFILE" || -L "$PROFILE" ]]; then
  echo "KEEP $PROFILE"
else
  echo "PLAN $PROFILE <- public environment profile template"
fi

if ! run_installer 0; then
  echo "Bootstrap stopped because skill conflicts must be resolved first." >&2
  exit 3
fi

if [[ "$conflicts" -gt 0 ]]; then
  echo "Bootstrap stopped because host guidance conflicts must be merged first." >&2
  exit 3
fi

if [[ "$CREATE_PROFILE" -eq 0 || -e "$PROFILE" || -L "$PROFILE" ]]; then
  python3 \
    "$REPO_ROOT/core/skills/environment-profile/scripts/profile_doctor.py" \
    --profile "$PROFILE"
fi

if [[ "$APPLY" -eq 0 ]]; then
  echo "Dry run only. Re-run with --apply after reviewing the plan."
  exit 0
fi

run_installer 1

copy_guidance() {
  local source="$1"
  local destination="$2"
  if [[ ! -e "$destination" && ! -L "$destination" ]]; then
    mkdir -p "$(dirname "$destination")"
    cp "$source" "$destination"
    echo "COPY $destination <- $source"
  fi
}

if [[ "$TARGET" == "codex" || "$TARGET" == "all" ]]; then
  copy_guidance "$REPO_ROOT/adapters/codex/AGENTS.md" "$HOME_ROOT/.codex/AGENTS.md"
fi
if [[ "$TARGET" == "claude" || "$TARGET" == "all" ]]; then
  copy_guidance "$REPO_ROOT/adapters/claude/CLAUDE.md" "$HOME_ROOT/.claude/CLAUDE.md"
fi
if [[ "$TARGET" == "cursor" || "$TARGET" == "all" ]]; then
  copy_guidance \
    "$REPO_ROOT/adapters/cursor/rules/agent-skill-garden.mdc" \
    "$HOME_ROOT/.cursor/rules/agent-skill-garden.mdc"
fi

if [[ "$CREATE_PROFILE" -eq 1 && ! -e "$PROFILE" && ! -L "$PROFILE" ]]; then
  python3 \
    "$REPO_ROOT/core/skills/environment-profile/scripts/profile_init.py" \
    --scope user \
    --home "$HOME_ROOT"
fi

python3 \
  "$REPO_ROOT/core/skills/environment-profile/scripts/profile_doctor.py" \
  --profile "$PROFILE"

cat <<EOF

Bootstrap complete for: $TARGET
Home: $HOME_ROOT

Next steps:
1. Edit $PROFILE and enable only the integrations you use.
2. Keep credentials and organization-only rules outside the public profile.
3. Restart the host and test one read-only request before authorizing writes.
EOF
