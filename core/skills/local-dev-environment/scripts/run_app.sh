#!/usr/bin/env bash
# Start one app. Usage: run_app.sh <app> [env] [--mock] [--http] [--dry-run]
# Needs LOCAL_DEV_* from scripts/profile_env.py.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
app="" env="" mock=0 http=0 dry=0
for a in "$@"; do
  case "$a" in
    --mock) mock=1 ;;
    --http) http=1 ;;
    --dry-run) dry=1 ;;
    -*) echo "unknown option: $a" >&2; exit 2 ;;
    *) if [[ -z "$app" ]]; then app="$a"; elif [[ -z "$env" ]]; then env="$a"; fi ;;
  esac
done
[[ -n "$app" ]] || { echo "usage: run_app.sh <app> [env] [--mock] [--http] [--dry-run]" >&2; exit 2; }
: "${LOCAL_DEV_REPO:?run scripts/profile_env.py first}"
: "${LOCAL_DEV_HOSTNAME:?run scripts/profile_env.py first}"
env="${env:-${LOCAL_DEV_DEFAULT_ENV:-}}"
[[ -n "$env" ]] || { echo "no environment given and the profile has no default_env" >&2; exit 2; }

pkg="$LOCAL_DEV_REPO/${LOCAL_DEV_APPS_DIR:-apps}/$app/package.json"
[[ -f "$pkg" ]] || { echo "no manifest at $pkg" >&2; exit 1; }
script="dev"; [[ "$env" == "dev" ]] || script="dev:$env"
if ! node -e "const p=require(process.argv[1]);process.exit(p.scripts&&p.scripts[process.argv[2]]?0:1)" "$pkg" "$script"; then
  echo "script '$script' not found; available dev scripts:" >&2
  node -e "const p=require(process.argv[1]);Object.keys(p.scripts||{}).filter(s=>s.startsWith('dev')).forEach(s=>console.log('  - '+s))" "$pkg" >&2
  exit 1
fi

portvar="LOCAL_DEV_PORT_$(echo "$app" | tr 'a-z-' 'A-Z_')"
port="${!portvar:-}"
if [[ -n "$port" ]] && lsof -tiTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "port $port is occupied; stop it with scripts/stop_dev_servers.sh --port $port" >&2
  exit 3
fi

scheme="https"; cert_info="skipped (HTTP)"; cert_raw=""
if [[ "$http" == 1 ]]; then
  scheme="http"
else
  link=""; [[ "$dry" == 1 ]] || link="--link"
  cert_raw="$("$here/resolve_cert.sh" $link)" || exit 1
  cert_info="$(printf '%s' "$cert_raw" | tr '\n' ' ')"
fi

echo "command: pnpm -F $app $script   (run from $LOCAL_DEV_REPO)"
echo "certificate: $cert_info"
echo "url: $scheme://$LOCAL_DEV_HOSTNAME${port:+:$port}/ (append the app base path)"
[[ "$dry" == 1 ]] && exit 0

if [[ "$http" == 1 ]]; then
  export "${LOCAL_DEV_HTTPS_VAR:-HTTPS}=false"
else
  cert="$(printf '%s\n' "$cert_raw" | sed -n 's/^cert=//p')"
  key="$(printf '%s\n' "$cert_raw" | sed -n 's/^key=//p')"
  [[ -n "${LOCAL_DEV_CERT_VAR:-}" ]] && export "$LOCAL_DEV_CERT_VAR=$cert"
  [[ -n "${LOCAL_DEV_KEY_VAR:-}" ]] && export "$LOCAL_DEV_KEY_VAR=$key"
fi
if [[ "$mock" == 1 ]]; then
  [[ -n "${LOCAL_DEV_MOCK_VAR:-}" ]] || { echo "profile names no mock_var" >&2; exit 2; }
  export "$LOCAL_DEV_MOCK_VAR=true"
fi
cd "$LOCAL_DEV_REPO"
exec pnpm -F "$app" "$script"
