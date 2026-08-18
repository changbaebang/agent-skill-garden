#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="all"
SCOPE="project"
INSTALL_ROOT="$PWD"
APPLY=0
SELECTED_SKILLS=()
SELECTED_COUNT=0

usage() {
  echo "Usage: $0 [--target cursor|claude|codex|all] [--scope project|user] [--root PATH] [--skill NAME ...] [--apply]"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="${2:-}"; shift 2 ;;
    --scope) SCOPE="${2:-}"; shift 2 ;;
    --root) INSTALL_ROOT="${2:-}"; shift 2 ;;
    --skill)
      SELECTED_SKILLS+=("${2:-}")
      SELECTED_COUNT=$((SELECTED_COUNT + 1))
      shift 2
      ;;
    --apply) APPLY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "$TARGET" =~ ^(cursor|claude|codex|all)$ ]] || { echo "Invalid target: $TARGET" >&2; exit 2; }
[[ "$SCOPE" =~ ^(project|user)$ ]] || { echo "Invalid scope: $SCOPE" >&2; exit 2; }
if [[ "$SELECTED_COUNT" -gt 0 ]]; then
  for skill_name in "${SELECTED_SKILLS[@]}"; do
    [[ "$skill_name" =~ ^[a-z0-9][a-z0-9-]*$ ]] || {
      echo "Invalid skill name: $skill_name" >&2
      exit 2
    }
    [[ -d "$REPO_ROOT/core/skills/$skill_name" ]] || {
      echo "Unknown skill: $skill_name" >&2
      exit 2
    }
  done
fi

if [[ "$SCOPE" == "user" ]]; then
  CLAUDE_SKILLS_DIR="${CLAUDE_HOME:-$HOME/.claude}/skills"
  SHARED_SKILLS_DIR="${AGENTS_HOME:-$HOME/.agents}/skills"
else
  INSTALL_ROOT="$(cd "$INSTALL_ROOT" && pwd)"
  CLAUDE_SKILLS_DIR="$INSTALL_ROOT/.claude/skills"
  SHARED_SKILLS_DIR="$INSTALL_ROOT/.agents/skills"
fi

conflicts=0
install_one() {
  local source="$1"
  local destination_root="$2"
  local name destination resolved
  name="$(basename "$source")"
  destination="$destination_root/$name"

  if [[ -L "$destination" ]]; then
    resolved="$(readlink "$destination")"
    if [[ "$resolved" == "$source" ]]; then
      echo "OK   $destination"
      return
    fi
  fi

  if [[ -e "$destination" || -L "$destination" ]]; then
    echo "SKIP $destination (existing path; remove or migrate it explicitly)" >&2
    conflicts=$((conflicts + 1))
    return
  fi

  if [[ "$APPLY" -eq 1 ]]; then
    mkdir -p "$destination_root"
    ln -s "$source" "$destination"
    echo "LINK $destination -> $source"
  else
    echo "PLAN $destination -> $source"
  fi
}

install_target() {
  local destination_root="$1"
  local skill
  if [[ "$SELECTED_COUNT" -gt 0 ]]; then
    for skill in "${SELECTED_SKILLS[@]}"; do
      install_one "$REPO_ROOT/core/skills/$skill" "$destination_root"
    done
    return
  fi
  for skill in "$REPO_ROOT"/core/skills/*; do
    [[ -d "$skill" ]] || continue
    install_one "$skill" "$destination_root"
  done
}

if [[ "$TARGET" == "claude" || "$TARGET" == "all" ]]; then
  install_target "$CLAUDE_SKILLS_DIR"
fi
if [[ "$TARGET" == "cursor" || "$TARGET" == "codex" || "$TARGET" == "all" ]]; then
  install_target "$SHARED_SKILLS_DIR"
fi

if [[ "$conflicts" -gt 0 ]]; then
  echo "$conflicts conflict(s) detected; no existing skill was overwritten." >&2
  exit 3
fi

if [[ "$APPLY" -eq 0 ]]; then
  echo "Dry run only. Re-run with --apply after reviewing the plan."
fi
