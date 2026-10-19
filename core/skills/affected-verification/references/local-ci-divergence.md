# When local and CI disagree

Each row is a symptom seen locally, the cause behind it, and what to do
before touching code. Rows marked `environment` are not findings about the
change; report them as such.

| Symptom | Cause | Action | Owner |
| --- | --- | --- | --- |
| Hand-picked package list passes; CI fails in another package | the list omitted a consumer; CI computed the affected set | rerun with the affected flag against the same base CI uses | change |
| `command not found` for a compiler or linter inside a package you did not touch; the whole affected run aborts | the package relies on a hoisted binary it never declared | put the repository-root binary directory on `PATH` and rerun | environment |
| "Cannot find module" in a file you never edited, right after switching branches | installed dependencies match the previous branch | reinstall with the offline cache; clear variables that skip development dependencies | environment |
| Test summary: suites failed but zero tests failed | a worker process crashed (memory, signal, retries exceeded) | rerun at lower concurrency; classify again | environment |
| Dependency-rule violations are nonzero | the repository already carried violations | compare with the base count; only an increase is a finding | change only if increased |
| Lint reports many violations in a file you touched | the file had them before | report the delta; fix only what the change introduced | change only for new ones |
| Local install passes; CI frozen-lockfile install fails after a dependency was removed | removal does not force a reinstall, so the lockfile kept the stale entry | run the frozen check whenever a manifest changed; verify the lockfile entry, not the linked directory | change |
| New files vanished or staged work reverted after comparing before and after | a stash covered more than the intended paths and the pop restored part of it | never stash for a baseline; extract the base file with `git show` into scratch | environment (self-inflicted) |
| Tests pass locally after moving a module; CI runs the real implementation or fails with "cannot find module" | mock paths are strings the type checker ignores | sweep the old path across all text files and update every hit kind | change |
| Everything passes locally; CI fails on a type or lint rule | different runtime version or a tool that changes behavior under `CI` | match the version pinned by the repository's version file; reproduce with `CI=1` | environment until matched |

## Reading the test summary

Monorepo affected runs print one summary block per package. Sum the counts
across blocks before judging. The rule is:

- any failed test: assertion failure, investigate the change;
- failed suites with zero failed tests, or a crash signal such as a
  segmentation fault, "worker process has quit unexpectedly", or "call
  retries were exceeded": worker crash, rerun with lower concurrency;
- no summary at all: the run did not reach the reporter; read the log head
  for the abort reason instead of guessing.

`scripts/classify_test_summary.py` applies this rule deterministically.

## Why delta, not zero

A repository with historical violations cannot be held to zero without
blocking every unrelated change. The question verification answers is
"did this change make it worse", which requires a measured baseline. When the
baseline is unknown, measure it on the base revision rather than estimating.
