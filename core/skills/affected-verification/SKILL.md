---
name: affected-verification
description: >-
  Runs the checks CI will run on the affected scope (type-check, tests,
  dependency rules, lint, lockfile) and separates real failures from
  environment traps. Use for verify my changes, run checks like CI, pre-PR
  check, 검증해줘, CI 처럼 돌려줘, 타입체크 돌려. Not for discussing past results
  or the commit, push, or PR that follows.
---

# Affected verification

A hand-picked package list passes the moment it omits one consumer. CI does
not pick by hand: it computes the affected set from the base revision and
runs every lane on it. Verify from that same set, with the same lanes, or a
local pass proves nothing about the pipeline.

## Decide whether to run at all

- Run only when there is a change to check: uncommitted edits or commits past
  the base. With neither, say "no change to verify" and stop.
- If this session already verified and no code changed since, report that
  instead of rerunning.
- If it is unclear whether the user wants a run or a conversation about one,
  ask. A full affected run costs minutes; a wrong guess wastes them.
- The skill ends at the report. A following commit, push, or pull request is
  the user's next request, not part of verification.

## Fix the base before anything else

Affected mode is a comparison, so it needs a base. Resolve it in this order:
the open pull request's base, then a base the user named, then ask. Do not
assume the default branch; stacked and release branches are common, and
comparing against the wrong one silently shrinks the affected set. Fetch the
base so the comparison uses the remote's current tip, not a stale local copy.

## Read the lanes from the CI definition, not from memory

Open the repository's CI workflow and copy the exact commands, the affected
flag or environment variables it passes, and the concurrency it uses. The
lanes are usually: type-check, test, dependency rules (import-boundary
checks, when the repository has them), lint, lockfile. Run them from the
repository root with the root binary directory on `PATH` (`node_modules/.bin`
in JavaScript workspaces); a workspace package that relies on a hoisted
compiler it never declared will otherwise abort the whole affected run with
`command not found` in a package you did not touch. That is an environment
fault, not a finding.

If a file you never edited reports a missing module right after a branch
switch, the installed dependencies no longer match the branch. Reinstall
(prefer the offline cache) before reading a single line of code.

## Run each lane and classify its result

**Type-check.** Pass means every affected task succeeded. Count the tasks.

**Test.** A red suite with zero failed tests is a worker crash, not a code
failure. Run the output through `scripts/classify_test_summary.py`; on
`suite-crash`, rerun at lower concurrency before blaming the change. Only
`assertion-failure` is yours to investigate.

**Dependency rules.** Repositories carry pre-existing violations, so zero is
not the target. Measure the delta against the base: unknown baseline means
measure the base first, then compare.

**Lint.** Check changed files only. On a file that already had violations,
report the delta and fix only what the change introduced.

**Lockfile.** Run only when a manifest changed, and run it every time one
did. A removed dependency is the trap: nothing forces a reinstall locally,
the lockfile keeps the stale entry, and only CI's frozen install fails. A
linked package directory existing is not evidence; the lockfile entry is.
A full install may be slow in large repositories, so ask before running one.

## Never manufacture a baseline with stash

Stashing to compare before and after reverts staged changes outside the paths
you meant, and a partial pop leaves new files gone. When a baseline file is
needed, extract it from the base revision into a scratch file and compare
against that.

## Moved files or symbols need a string sweep

The type checker follows import statements and nothing else. Grep the old
path or specifier across every text file and inspect each hit kind: test
mock paths, story files, manifests and configuration JSON that name modules,
and deprecation comments that point at the old location. A mock that still
names the old module silently runs the real implementation.

## Report with numbers

One line per lane with a count, never a bare "passed". For each failure name
the lane, what failed, and whether it belongs to the change or to the
environment. A blocked lane is reported as blocked, not skipped.

Commands, flag shapes, and the report template are in
[references/lanes-and-commands.md](references/lanes-and-commands.md). The
symptom-to-cause table for local and CI disagreeing is in
[references/local-ci-divergence.md](references/local-ci-divergence.md).
