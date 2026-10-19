#!/usr/bin/env python3
"""Print the integration.local-dev section of the environment profile as shell exports."""
import argparse
import configparser
import os
import shlex
import sys

SECTION = "integration.local-dev"
SIMPLE = {
    "repo": "LOCAL_DEV_REPO",
    "apps_dir": "LOCAL_DEV_APPS_DIR",
    "hostname": "LOCAL_DEV_HOSTNAME",
    "cert_dir": "LOCAL_DEV_CERT_DIR",
    "cert_name": "LOCAL_DEV_CERT_NAME",
    "legacy_cert_dir": "LOCAL_DEV_LEGACY_CERT_DIR",
    "cert_var": "LOCAL_DEV_CERT_VAR",
    "key_var": "LOCAL_DEV_KEY_VAR",
    "https_var": "LOCAL_DEV_HTTPS_VAR",
    "mock_var": "LOCAL_DEV_MOCK_VAR",
    "default_env": "LOCAL_DEV_DEFAULT_ENV",
}
PATH_KEYS = ("repo", "cert_dir")
REQUIRED = ("repo", "hostname", "cert_dir")


def find_profile(explicit, cwd):
    candidates = [
        explicit,
        os.environ.get("AGENT_GARDEN_PROFILE"),
        os.path.join(cwd, ".agent-garden", "profile.ini"),
        os.path.join(os.path.expanduser("~"), ".agent-garden", "profile.ini"),
    ]
    for cand in candidates:
        if cand and os.path.isfile(os.path.expanduser(cand)):
            return os.path.abspath(os.path.expanduser(cand))
        if cand and cand is explicit:
            raise SystemExit("profile not found: %s" % cand)
    raise SystemExit("no environment profile found; ask the user to create one")


def expand(value, base):
    value = os.path.expandvars(os.path.expanduser(value.strip()))
    return value if os.path.isabs(value) else os.path.normpath(os.path.join(base, value))


def load(path):
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(path)
    if not parser.has_section(SECTION):
        raise SystemExit("profile has no [%s] section" % SECTION)
    sec = parser[SECTION]
    if sec.get("enabled", "true").strip().lower() not in ("true", "1", "yes"):
        raise SystemExit("[%s] is disabled in the profile" % SECTION)
    base = os.path.dirname(path)
    out = {}
    for key, name in SIMPLE.items():
        raw = sec.get(key, "").strip()
        if raw:
            out[name] = expand(raw, base) if key in PATH_KEYS else raw
    missing = [k for k in REQUIRED if SIMPLE[k] not in out]
    if missing:
        raise SystemExit("profile is missing: %s" % ", ".join(missing))
    out.setdefault("LOCAL_DEV_APPS_DIR", "apps")
    out.setdefault("LOCAL_DEV_CERT_NAME", "local-dev")
    out.setdefault("LOCAL_DEV_HTTPS_VAR", "HTTPS")
    ports = []
    for key, value in sec.items():
        if key.startswith("port.") and value.strip():
            app = key[5:].upper().replace("-", "_")
            out["LOCAL_DEV_PORT_" + app] = value.strip()
            ports.append(value.strip())
    for extra in sec.get("extra_ports", "").replace(",", " ").split():
        ports.append(extra)
    out["LOCAL_DEV_PORTS"] = " ".join(dict.fromkeys(ports))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile")
    args = ap.parse_args(argv)
    path = find_profile(args.profile, os.getcwd())
    values = load(path)
    print("export LOCAL_DEV_PROFILE=%s" % shlex.quote(path))
    for name in sorted(values):
        print("export %s=%s" % (name, shlex.quote(values[name])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
