#!/usr/bin/env bash
# Generate a locally trusted certificate into the profile's certificate directory.
# Needs LOCAL_DEV_* from scripts/profile_env.py. Does not install the authority.
set -euo pipefail

: "${LOCAL_DEV_CERT_DIR:?run scripts/profile_env.py first}"
: "${LOCAL_DEV_HOSTNAME:?run scripts/profile_env.py first}"
name="${LOCAL_DEV_CERT_NAME:-local-dev}"

if ! command -v mkcert >/dev/null 2>&1; then
  echo "mkcert not found; install it with the platform package manager" >&2
  exit 1
fi

mkdir -p "$LOCAL_DEV_CERT_DIR"
if git -C "$LOCAL_DEV_CERT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if ! git -C "$LOCAL_DEV_CERT_DIR" check-ignore -q "$LOCAL_DEV_CERT_DIR/$name.pem"; then
    echo "refusing: $LOCAL_DEV_CERT_DIR is inside a Git work tree and not ignored" >&2
    exit 2
  fi
fi

cd "$LOCAL_DEV_CERT_DIR"
mkcert -key-file "$name-key.pem" -cert-file "$name.pem" \
  "$LOCAL_DEV_HOSTNAME" localhost 127.0.0.1 ::1
chmod 600 "$name-key.pem"
openssl x509 -in "$name.pem" -noout -dates -subject
echo "If the browser reports an unknown authority, run: mkcert -install (once)"
