#!/usr/bin/env bash
# PreToolUse guard for the Bash tool: block destructive `git push` variants
# while plain `git push` stays allowed. Reads the hook JSON on stdin.
#
# Denied: --force / -f / --force-with-lease / --force-if-includes / --mirror /
#         --delete / -d, refspec deletion (`:branch`) and forced refspec (`+ref`).
# Everything else passes through silently (exit 0, no output).
set -euo pipefail

cmd="$(jq -r '.tool_input.command // empty' 2>/dev/null || true)"
[[ -z "$cmd" ]] && exit 0

# Only inspect segments where `git push` is actually the command being run:
# at the start of the command or after ; && || | ( so that a string such as
# `git log --grep "git push --force"` is not treated as a push.
if ! grep -Eq '(^|[;&|(][[:space:]]*)git[[:space:]]+push([[:space:]]|$)' <<<"$cmd"; then
  exit 0
fi

# Extract every `git push ...` segment up to the next control operator.
segments="$(grep -Eo '(^|[;&|(][[:space:]]*)git[[:space:]]+push[^;&|]*' <<<"$cmd")"

deny_pattern='(^|[[:space:]])(--force|-f|--force-with-lease|--force-if-includes|--mirror|--delete|-d)([[:space:]=]|$)|[[:space:]]:[^[:space:]]|[[:space:]]\+[^[:space:]]'
if grep -Eq -- "$deny_pattern" <<<"$segments"; then
  jq -nc '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "destructive-push-guard: force/delete/mirror pushes are blocked. Plain `git push` is allowed; ask the user to run destructive pushes themselves."
    }
  }'
fi
exit 0
