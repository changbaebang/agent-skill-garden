#!/usr/bin/env bash
# Pick the local certificate by precedence and print where it came from.
# Needs LOCAL_DEV_* from scripts/profile_env.py. Usage: resolve_cert.sh [--link]
set -euo pipefail

: "${LOCAL_DEV_CERT_DIR:?run scripts/profile_env.py first}"
name="${LOCAL_DEV_CERT_NAME:-local-dev}"
cert="" key="" source=""

if [[ -n "${LOCAL_DEV_CERT_VAR:-}" && -n "${LOCAL_DEV_KEY_VAR:-}" ]]; then
  c="${!LOCAL_DEV_CERT_VAR:-}"; k="${!LOCAL_DEV_KEY_VAR:-}"
  if [[ -n "$c" && -n "$k" && -f "$c" && -f "$k" ]]; then
    cert="$c"; key="$k"; source="server variables"
  fi
fi
if [[ -z "$cert" && -f "$LOCAL_DEV_CERT_DIR/$name.pem" && -f "$LOCAL_DEV_CERT_DIR/$name-key.pem" ]]; then
  cert="$LOCAL_DEV_CERT_DIR/$name.pem"; key="$LOCAL_DEV_CERT_DIR/$name-key.pem"; source="profile directory"
fi
if [[ -z "$cert" && -n "${LOCAL_DEV_LEGACY_CERT_DIR:-}" && -n "${LOCAL_DEV_REPO:-}" ]]; then
  d="$LOCAL_DEV_REPO/$LOCAL_DEV_LEGACY_CERT_DIR"
  if [[ -f "$d/$name.pem" && -f "$d/$name-key.pem" ]]; then
    cert="$d/$name.pem"; key="$d/$name-key.pem"; source="legacy repository directory"
  fi
fi
if [[ -z "$cert" ]]; then
  echo "no certificate found; run scripts/setup_local_cert.sh" >&2
  exit 1
fi

if [[ "${1:-}" == "--link" && -n "${LOCAL_DEV_LEGACY_CERT_DIR:-}" ]]; then
  d="$LOCAL_DEV_REPO/$LOCAL_DEV_LEGACY_CERT_DIR"
  mkdir -p "$d"
  [[ "$cert" == "$d/$name.pem" ]] || ln -sf "$cert" "$d/$name.pem"
  [[ "$key" == "$d/$name-key.pem" ]] || ln -sf "$key" "$d/$name-key.pem"
  for f in "$name.pem" "$name-key.pem"; do
    if git -C "$LOCAL_DEV_REPO" ls-files --error-unmatch "$LOCAL_DEV_LEGACY_CERT_DIR/$f" >/dev/null 2>&1; then
      git -C "$LOCAL_DEV_REPO" update-index --skip-worktree "$LOCAL_DEV_LEGACY_CERT_DIR/$f"
    fi
  done
fi

echo "source=$source"
echo "cert=$cert"
echo "key=$key"
