# Commands, troubleshooting, report

All scripts live in `scripts/` and read the exports from the profile step.

```bash
eval "$(python3 scripts/profile_env.py)"            # load machine facts
bash scripts/setup_local_cert.sh                     # once per machine or expiry
bash scripts/resolve_cert.sh                         # report which source wins
bash scripts/run_app.sh <app> <env> --dry-run        # show command, cert, URL
bash scripts/run_app.sh <app> <env> [--mock] [--http]
bash scripts/stop_dev_servers.sh [--port N]... [--dry-run]
```

`resolve_cert.sh --link` creates the legacy-directory symlinks and marks
tracked paths skip-worktree; `run_app.sh` does this only outside `--dry-run`.
To undo: `git update-index --no-skip-worktree <path>` then restore the file.

## Troubleshooting

| Symptom | Cause | Action |
| --- | --- | --- |
| Browser: authority invalid or unknown | Local authority not trusted | Ask, then run the authority install once and regenerate. |
| Server: certificate file not found | Started without the resolver | Start through `run_app.sh`. |
| Address already in use | Stale server | Show holder, then `stop_dev_servers.sh --port N`. |
| Hostname does not load | No loopback entry | Tell the user the hosts line; do not edit it unasked. |
| Tracked certificate shows a type change | Symlink over a tracked file | Mark skip-worktree via `--link`; never commit. |
| Background task exits non-zero after a stop | Deliberate kill | Report; do not restart. |
| Script missing for an environment | Environment not offered by the app | List dev scripts and ask. |

## Report template

```text
Start: app=<app> env=<env> url=<url> cert=<source> mock=<on|off> scheme=<https|http>
Stop:  ports=<list> holders=<pid command> result=<clear|still listening>
Skipped: <item> because <reason>
Next step for you: <hosts entry | trust step | missing profile value>
```
