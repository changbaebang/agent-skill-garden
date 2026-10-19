# Lanes, commands, and the report

The commands below are shapes. The authoritative versions live in the CI
workflow definition committed to the repository, in whatever directory the
CI host reads. Copy from there; do not reconstruct a lane from memory.

## Resolve the base

```bash
# 1. the open pull request's base, when the hosting CLI exposes it
BASE=$(<hosting-cli> pr view --json baseRefName --jq .baseRefName 2>/dev/null)
# 2. otherwise the base the user named; otherwise ask. Never default silently.

git fetch origin "$BASE"
git merge-base "origin/$BASE" HEAD      # the comparison point affected mode uses
```

Some task runners read the base from environment variables rather than a
flag. The CI definition shows which; export the same variables locally.

## Prepare the environment

```bash
export PATH="$PWD/node_modules/.bin:$PATH"   # JavaScript workspaces: root binaries
```

Right after a branch switch, when an untouched file reports a missing module:

```bash
<package-manager> install --prefer-offline
```

Clear any environment variable that makes the install skip development
dependencies before running it; a production-mode install produces a tree
that fails tests for reasons unrelated to the change.

## Lane table

| Lane | Shape | Pass criterion |
| --- | --- | --- |
| type-check | `<runner> type-check <affected-flag>` | every affected task successful; record the task count |
| test | `<runner> test <affected-flag> --concurrency=<N from CI>` | zero failed tests and zero failed suites; classify first |
| dependency rules | `<runner> dependency-check` | violation count did not increase against the base |
| lint | `<linter> check <changed files>` | no new violations in changed files |
| lockfile | `<package-manager> install --frozen-lockfile` | exits zero; run only when a manifest changed |

Affected-flag shapes differ by runner: `--affected`,
`--filter='...[origin/<base>]'`, `affected --base=origin/<base>`, or a pair
of environment variables naming base and head. Use the one CI uses.

## Changed files for the lint lane

```bash
git diff --name-only "origin/$BASE"...HEAD | grep -E '\.(ts|tsx|js|jsx)$' > "$SCRATCH/changed.txt"
xargs <linter> check < "$SCRATCH/changed.txt"
```

Include uncommitted edits with `git diff --name-only "origin/$BASE"` (no
`...HEAD`) when verifying before a commit.

## Baseline without stash

```bash
git show "origin/$BASE:path/to/file" > "$SCRATCH/file.base"
<linter> check "$SCRATCH/file.base"      # compare counts, then delete the scratch copy
```

For dependency rules, run the check once on a clean checkout of the base in a
separate worktree when the baseline count is unknown:

```bash
git worktree add "$SCRATCH/base-tree" "origin/$BASE"
```

Remove the worktree afterwards. Never switch the user's working branch.

## Classify the test lane

```bash
<runner> test <affected-flag> 2>&1 | tee "$SCRATCH/test.log"
python3 scripts/classify_test_summary.py "$SCRATCH/test.log"
```

Exit codes: `0` pass, `1` assertion-failure, `2` suite-crash, `3` unknown.
On `2`, rerun with roughly half the concurrency and classify again.

## Lockfile when a dependency was removed

```bash
git diff --stat "origin/$BASE"...HEAD -- '**/package.json' '<lockfile>'
<package-manager> install --frozen-lockfile --lockfile-only   # when supported
```

A manifest diff with no lockfile diff is the failure signature. Check the
lockfile's declaration count for the package, not whether a linked directory
exists on disk.

## String sweep after moving a module

```bash
grep -rn --exclude-dir=node_modules --exclude-dir=.git -F '<old-specifier-or-path>' .
```

Inspect every hit by kind:

- import statements: the type checker already covered these;
- test mock calls that take a module string: the checker does not see them,
  and a stale one runs the real implementation;
- relative mock paths to a moved file: fail at runtime with "cannot find
  module";
- story files, manifests, and configuration JSON that name modules;
- deprecation comments pointing at the old path: no tool checks them.

## Report template

```
type-check        22 tasks passed
test              18 tasks passed (0 failed tests, 0 failed suites)
dependency rules  12 -> 9 violations (no increase)
lint              14 changed files clean
lockfile          frozen install passed
```

For a failure, add one line: lane, what failed, and `change` or
`environment`. For a lane that could not run, write `blocked: <reason>`.
