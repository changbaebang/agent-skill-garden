#!/usr/bin/env bash
# Stop listeners on dev ports. Usage: stop_dev_servers.sh [--port N]... [--dry-run]
# Without --port, uses LOCAL_DEV_PORTS from scripts/profile_env.py.
set -euo pipefail

ports=() dry=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) [[ $# -ge 2 && "$2" =~ ^[0-9]+$ ]] || { echo "--port needs a number" >&2; exit 2; }; ports+=("$2"); shift 2 ;;
    --dry-run) dry=1; shift ;;
    *) echo "usage: stop_dev_servers.sh [--port N]... [--dry-run]" >&2; exit 2 ;;
  esac
done
if [[ ${#ports[@]} -eq 0 ]]; then
  # shellcheck disable=SC2206
  ports=(${LOCAL_DEV_PORTS:-})
fi
[[ ${#ports[@]} -gt 0 ]] || { echo "no ports: pass --port or set ports in the profile" >&2; exit 2; }

listeners() { lsof -tiTCP:"$1" -sTCP:LISTEN 2>/dev/null || true; }

for p in "${ports[@]}"; do
  pids="$(listeners "$p")"
  if [[ -z "$pids" ]]; then echo ":$p idle"; continue; fi
  for pid in $pids; do
    echo ":$p pid $pid $(ps -p "$pid" -o command= 2>/dev/null | cut -c1-80)"
  done
  # shellcheck disable=SC2086
  [[ "$dry" == 1 ]] || kill $pids 2>/dev/null || true
done
[[ "$dry" == 1 ]] && exit 0

sleep 1
bad=0
for p in "${ports[@]}"; do
  pids="$(listeners "$p")"
  # shellcheck disable=SC2086
  [[ -z "$pids" ]] || { echo ":$p force kill $pids"; kill -9 $pids 2>/dev/null || true; }
done
sleep 0.5
for p in "${ports[@]}"; do
  if [[ -n "$(listeners "$p")" ]]; then echo ":$p still listening" >&2; bad=1; fi
done
[[ "$bad" == 0 ]] && echo "requested ports clear"
exit "$bad"
