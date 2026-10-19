# Lock file, wrapper, and commands

All commands take `--root`, the personal skills root. Run the script with
`python3 scripts/vendor_lock.py <command> --root <root> ...`.

## Commands

| Command | Required flags | Effect |
| --- | --- | --- |
| `install` | `--plugin`, `--source`, `--ticket` | Appends a lock entry and writes `skills/<plugin>-vendor/SKILL.md`. |
| `status` | none (`--json` optional) | Lists active installs with age and drift problems. |
| `teardown` | `--ticket` or `--plugin` | Removes the wrapper and lock entry. Keeps the clone. |

Optional install flags: `--plugin-path` (path of the plugin inside the clone),
`--vendor-dir` (explicit plugin directory), `--wrapper` (wrapper name, default
`<plugin>-vendor`), `--installed-at`, `--dry-run`. `install` and `teardown`
both accept `--dry-run`, which prints the plan and writes nothing.

Without `--vendor-dir`, the plugin directory is
`<root>/vendor/<repository>/<plugin-path>`, where the repository name is the
last segment of the source with any `.git` suffix removed.

## Lock format

```json
{
  "installs": [
    {
      "plugin": "example-plugin",
      "source": "<clone source>",
      "plugin_path": "plugins/example-plugin",
      "vendor_dir": "~/<relative path to the plugin directory>",
      "revision": "<commit hash or null>",
      "ticket": "<ticket identifier>",
      "wrapper_skill": "example-plugin-vendor",
      "installed_at": "<ISO 8601 timestamp>"
    }
  ]
}
```

Paths under the home directory are stored with a leading `~/` so the lock
survives a machine move. `revision` is null when the directory is not a Git
checkout or Git is unavailable; that is "unknown", not a failure.

## Wrapper

The generated wrapper carries a managed marker line. Teardown and the
overwrite check rely on it: a directory without the marker is never deleted or
replaced. The wrapper holds a field table (source, plugin path, revision,
install time, read-in-place path), three rules for following the plugin, and a
table of Markdown documents found up to three levels deep (hidden, build, and
dependency directories skipped).

## Status problems

| Problem | Meaning | Action |
| --- | --- | --- |
| clone missing | The recorded directory is gone. | Re-clone, or tear down. |
| wrapper missing | Lock entry without a wrapper. | Tear down, then reinstall if still needed. |
| wrapper not managed by this script | Marker absent. | Do not tear down blindly; inspect the directory. |
| clone moved off the recorded revision | Someone pulled or checked out. | Decide whether the new revision is wanted; reinstall to re-record. |

## Exit codes

0 done. 1 refused (message on stderr). 2 usage error.

## Tracking warning

The install prints a warning when the vendor area, the lock, or the wrapper sits
inside a Git work tree and is not ignored. Treat it as a stop sign when that
work tree is a project repository. It is informational when the root lives in a
dedicated personal configuration repository.
