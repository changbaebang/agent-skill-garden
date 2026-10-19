# Profile fields

The skill reads one section of the environment profile. Selection order and
safety rules are in the environment profile contract; this file lists only the
fields specific to local development. Every value below is synthetic.

```ini
[integration.local-dev]
enabled = true
repo = ~/work/example-monorepo
apps_dir = apps
hostname = dev.example.test
cert_dir = ~/.local-dev/certs
cert_name = local-dev
legacy_cert_dir = _certs
cert_var = SSL_CERT_PATH
key_var = SSL_KEY_PATH
https_var = HTTPS
mock_var = ENABLE_MOCKS
default_env = qa
port.web = 3002
port.checkout = 3003
extra_ports = 3010
```

| Field | Required | Meaning |
| --- | --- | --- |
| `repo` | yes | Absolute or `~` path of the repository root. |
| `hostname` | yes | Local hostname that resolves to loopback. |
| `cert_dir` | yes | Directory outside any work tree for the certificate pair. |
| `apps_dir` | no | Directory holding app packages. Default `apps`. |
| `cert_name` | no | File stem: `<stem>.pem` and `<stem>-key.pem`. Default `local-dev`. |
| `legacy_cert_dir` | no | Repository-relative directory some apps hard-code. Enables the symlink step. |
| `cert_var`, `key_var` | no | Variable names the dev server reads for the pair. |
| `https_var` | no | Variable that switches HTTPS. Default `HTTPS`. |
| `mock_var` | no | Variable that enables the mock service. Omit when unsupported. |
| `default_env` | no | Environment used when the user names none. |
| `port.<app>` | no | Default port per app; also the stop list. |
| `extra_ports` | no | More ports to free, comma or space separated. |

`scripts/profile_env.py` prints these as `LOCAL_DEV_*` exports, with
`LOCAL_DEV_PORT_<APP>` per app and `LOCAL_DEV_PORTS` as the combined list. Use
`eval "$(python3 scripts/profile_env.py)"` in the shell that runs the other
scripts. A profile never authorizes a kill, a trust-store change, or a
hosts-file edit; those still need the user's approval in the current session.
