# Release pull request body

Title and single commit message: `chore: release X.Y.Z`.

```markdown
## What changes

<!-- Mirror the changelog section for this version. Keep its grouping. -->
### Added
-
### Changed
-
### Removed
-
### Fixed
-

## Why X.Y.Z

<!-- One of:
     "Breaking: <the change>; on 0.x that is a minor." /
     "Breaking: <the change>, so this is a major." /
     "Additions without a breaking change: minor." /
     "Fixes only: patch." -->

## Gate

| Check | Result |
| --- | --- |
| install, build, typecheck, test, lint | all passed in one `&&` chain |
| pack dry run | N files, `dist/` present, reported version X.Y.Z |
| tests | N passed |
| `cli --version` | X.Y.Z |
| generated files embed the version | yes / not applicable |

## Version literals

<!-- Paste the scan summary: how many lines carried the old version and that
     each was updated or deliberately left (and why). -->

## After merge

Tag and push the tag; the release workflow publishes from it.

    git pull && git tag vX.Y.Z && git push origin vX.Y.Z
```

Fill every table cell from the gate's actual output. A cell that says "ok"
without a number is not evidence.
