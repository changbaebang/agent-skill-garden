# Compare a skill change using captured behavior

[한국어](skill-evaluation.ko.md)

Garden Eval answers a bounded question: **does this skill revision help on these
review tasks, and what gets worse?** It captures real runner output and compares
human judgments. It does not score employee productivity or automatically rewrite
skills. Python 3.9+ and a POSIX host are sufficient for the harness.

`validate_evals.py` checks routing-case definitions. It does not run an agent or
prove routing correctness. `skill_eval.py` adds execution and comparison; the
first suite targets `critical-review`, with six calibration and four holdout
cases authored from scratch. No private work records are included. These are
small authored fixtures, not a validated benchmark. Inputs provide source code
and external contracts; expected verdicts belong only in the human criteria.
Repository validation discovers all JSON definitions under `evals/suites/`,
including nested directories, and rejects malformed suites. At the top level of
`evals/`, only `routing.json` is allowed; a misplaced JSON file fails with migration
guidance. Put other definition formats in named directories such as
`evals/schemas/`, with their own validators. Keep captured runs and assessments in
ignored `work/`, rather than among public definitions.

## 1. Run one condition

Run from the repository root. Choose a trusted runner that reads one prompt from
stdin, prints only its final answer to stdout, and exits nonzero on failure.
The command after `--` is executed once per case and repetition, without a shell.
The executable is located on `PATH`. Subsequent standalone file arguments must
include a path separator, such as `./runner.py` or an absolute path, to be
resolved relative to your starting directory and hashed. Bare words such as
`exec` stay unchanged even if a file has the same name. The harness uses a fresh
temporary working directory per attempt.

For example, on a Codex CLI version supporting these options:

```bash
python3 scripts/skill_eval.py run \
  --suite evals/suites/critical-review.json \
  --skill none --label baseline \
  --model YOUR_MODEL --environment 'Codex VERSION; controlled profile SETTINGS' \
  --split calibration --repeat 2 --timeout 180 \
  --out work/eval/baseline.json \
  -- codex exec --ephemeral --skip-git-repo-check \
     --sandbox read-only --model YOUR_MODEL -
```

Use the same model, environment, runner and other settings to run the current
skill, changing only these arguments:

```text
--skill core/skills/critical-review --label current --out work/eval/current.json
```

For a proposed revision, copy the skill directory (including its references) into
`work/candidate`, make a narrow change, and use:

```text
--skill work/candidate --label candidate --out work/eval/candidate.json
```

The host's existing authentication and configuration still apply. The harness
does not select or configure a provider: `--model` and `--environment` record
your declarations, while the command must actually use those settings. Use a
controlled host profile without preinstalled skill guidance for a meaningful
no-skill baseline. A temporary working directory is **not a security sandbox**;
enforce read-only, network, connector and tool permissions in the runner itself.
Do not run untrusted adapters. Model calls can consume paid or subscription usage.

The example flags were checked against the local Codex CLI help; other versions
or hosts may need a wrapper. Do not enable bypass flags to make an experiment
pass. Host behavior and hidden system guidance remain experimental limitations.
No live model is invoked by repository validation or tests.

## What an attempt contains

The runner receives only the task, the source snapshots, and visible regular
UTF-8 text files from the chosen skill directory, regardless of extension.
Any path component beginning with `.` is excluded before traversal or reading:
for example `.env`, `.git/`, and `references/.private/` never enter the snapshot,
prompt or skill hash. This is a path boundary, not a general secret detector;
remove sensitive values from visible reference files yourself. YAML, JSON and
script sources are included in both the prompt and the hashed snapshot; scripts
are supplied as text and are not executed by the harness. For visible paths,
symbolic links, non-regular files, NUL bytes, invalid UTF-8, files over 1,000,000 bytes, and a
combined snapshot over 4,000,000 bytes are rejected before runner execution with
the affected path, rather than silently omitted. Sizes refer to raw file bytes.
The runner does not receive check criteria, case IDs, split labels, previous
answers, or human judgments. The skill is supplied
explicitly: this experiment does **not** measure automatic skill discovery.
External skill dependencies, tools and linked remote documents are not
automatically loaded. Keep the first experiment within the self-contained
`critical-review` skill.

The result file captures the suite and skill snapshots, their hashes, the harness
source hash, model and environment declarations, the runner command and hashes
of its executable and explicit file arguments under `runner_identity`, every
attempt's answer, status, elapsed time and the bounded tail of stderr. Truncation
is recorded so a clipped answer or log is not mistaken for complete evidence.
The executable and explicit file arguments are hashed once before and once after
the experiment. Before each attempt their device, inode, size, modification time,
change time and mode are checked for drift. This avoids rehashing large binaries
for every attempt while stopping ordinary mid-run changes. Hashing detects
accidental edits, not malicious tampering or undisclosed model changes.
Dependencies imported by an adapter are not hashed; pin them and include
their versions in the environment declaration. Keep credentials in the host's
credential store or environment, never in command arguments.

Timeouts kill the runner process group on POSIX. An error, empty answer, or answer
over 1 MB cannot be graded as a successful review. A timeout or nonzero exit keeps
its failure status even when its answer also exceeds the limit.
Runner output is drained through pipes, with no temporary stdout/stderr files.
Only the first 1,000,000 stdout bytes and last 8,192 stderr bytes are retained in
memory; excess output is discarded while the runner continues until completion
or its deadline. Input delivery and both output streams are serviced concurrently,
so a runner that delays reading stdin cannot block output capture or the timeout.
The same deadline covers output pipes inherited by child processes. A supervisor
stays alive in the attempt's process group and reports the actual runner's exit
status over a dedicated pipe. On success, error, timeout or interruption, the
harness kills that group before reaping the supervisor. Descendants that merely
close their standard streams therefore still receive cleanup. The recorded
`exit_code` belongs to the runner; it is `null` if its status was not observed
before termination, rather than the supervisor's kill status. A runner status
already observed is retained even if inherited output pipes later time out.
Unexpected supervisor exit or cleanup failure is an error. Processes that escape
the group with `setsid`/`setpgid` or change privileges remain outside this cleanup
boundary; use runner-level isolation when you need a security sandbox.

The suite, snapshots and hashes are checked before any runner is invoked. The
requested output and a companion `<output>.journal.jsonl` are reserved without
overwriting existing files. Give the experiment exclusive ownership of these
paths: concurrent renaming or replacement is unsupported. If journal setup
conflicts, no runner is invoked. The harness checks the empty output's inode
before removing its own reservation as a best-effort cleanup; that check and
unlink are not atomic and cannot protect against concurrent path replacement.
The append-only journal records the experiment
header, attempt starts and finishes, and completion or failure, flushing each
event to disk. Completed attempts, including errors and timeouts, therefore
survive a later harness failure. An interrupted attempt may have only its start
record. Assess and compare accept only completed run files; a failed run may
leave an empty final output alongside its journal. There is no automatic resume:
use a new output path and include the interrupted experiment in cost analysis.

Logs and answers may be sensitive; keep runs,
assessments and reports in the ignored `work/` directory and inspect them before
sharing. Do not upload private logs as public evaluation cases.

## 2. Assess the captured answers

```bash
python3 scripts/skill_eval.py assess work/eval/current.json \
  --out work/eval/current-assessment.json
```

Read each answer in the run file against its `criterion`. Set `reviewer`, change
each `verdict` to `pass` or `fail`, and add a concrete `note` citing the answer or
its omission. Leave disputed or unchecked judgments as `unjudged`. Optional
`review_minutes` is actual human review time; `null` means unmeasured, not zero.
The same process applies to baseline and candidate runs. Do not edit the run file
or the assessment's criteria. An assessment is bound to the exact run hash.

Suite, run and assessment formats have separate versions: currently 1, 2 and 1.
Earlier version-1 captures remain readable and assessable with a legacy-format
notice when their recorded fields validate. If the selected-suite fingerprint
is absent, it is derived from the embedded suite in memory. The original run
file, fields and hash are preserved. Two version-1 captures can still be compared
when their harness and other conditions match; mixing run versions or harness
revisions is rejected. Create fresh matched captures for a new experiment rather
than relabeling old evidence as a new format.

The rubric separately asks whether known defects were detected, resolved issues
were repeated, a pre-existing issue was misclassified, or a claim exceeded the
evidence. These are case-level judgments, **not precision/recall over all possible
production bugs**. Where possible, have a reviewer assess answers without seeing
which skill version produced them. A model may assist, but its self-rating alone
is not evidence that a revision is better.

## 3. Compare and decide

```bash
python3 scripts/skill_eval.py compare \
  work/eval/current.json work/eval/candidate.json \
  --before-assessment work/eval/current-assessment.json \
  --after-assessment work/eval/candidate-assessment.json \
  --out work/eval/comparison.md --fail-on-regression
```

Also compare the baseline against the current skill to check that added guidance
has value at all. Comparisons require matching harness, model, environment, runner
identity, run format, split, repetition count, timeout and synthetic/runner kind. Suite
compatibility covers the selected cases and their criteria. The full suite is
retained and hashed for audit, but adding untouched holdout cases does not
invalidate earlier calibration comparisons. Changing a selected input or rubric
requires fresh matched runs. Version-2 captures sort selected cases by case ID for
both execution and comparison, so reordering cases alone does not change the
selected fingerprint or invocation order. The full-suite snapshot preserves the
original order for audit.

The two run hashes must differ: comparing one capture against itself is rejected.
Independently capture the same skill again to inspect variation in execution and
human judgments. With matching skill contents, comparison automatically emits a
**SAME-SKILL VARIABILITY** report; directory-name changes do not make a new skill.
It reports verdict transitions without calling them skill improvements. For
example, repeat the current-skill command into `work/eval/current-repeat.json`,
assess that fresh capture, then compare it with `work/eval/current.json` using
their respective assessments. No extra comparison flag is needed.

Different judgments of the same captured answer remain reviewer disagreement;
reconcile those manually rather than passing that one run twice. Neither
comparison mode establishes causality by itself. Repeated runs and human review
remain necessary to judge whether a skill change exceeds ordinary variation.

Prompt JSON uses a canonical object-key order, so reordering input keys alone
does not change the bytes sent to the runner. Each attempt records the full
`prompt_sha256` and a separate `input_sha256` for the prompt without skill content.
Run validation recomputes both hashes, and comparison requires matching input
hashes for each case/trial. The skill contents determine which report mode applies.

Each check/trial is classified as:

| Before → after | Changed skill | Same skill, fresh capture |
| --- | --- | --- |
| fail → pass | improved | fail_to_pass |
| pass → fail | regressed | pass_to_fail |
| pass → pass | unchanged_pass | unchanged_pass |
| fail → fail | unchanged_fail; the known failure remains | unchanged_fail |
| unjudged or execution failure on either side | inconclusive | inconclusive |

Reports keep calibration and holdout counts separate and list every compared
check. They show successful/total attempts, total elapsed time including failures,
successful-attempt median, and measured human review minutes with coverage. Tokens
and money are unavailable in this protocol, not zero. No composite score is
calculated, and regressions remain visible even if another case improves.

Exit codes: `0` means the command completed (not that quality passed); `1` means
the comparison found a judged pass-to-fail transition with `--fail-on-regression`,
including in same-skill variability mode; `2` means
invalid input, incompatible runs, or an output conflict. An all-unjudged report
completes with code 0 and explicitly says inconclusive; it is not a merge gate.

## The improvement loop

1. Start with a demonstrated failure; make a public-safe reproduction with raw
   inputs and an independently checked criterion.
2. Run baseline/current conditions on calibration cases. Explain one failure;
   capture the same condition again when you need to inspect ordinary variation.
3. Make the smallest justified skill edit. Compare current/candidate under the
   same conditions, including repeated runs and human review effort.
4. Freeze that candidate, then run and assess both conditions with `--split
   holdout` into fresh files. The bundled holdout is public and cannot prevent
   training leakage; avoid tuning to it and add new untouched cases over time.
5. Inspect regressions and uncertainty, then keep, revise or discard the change.
   Adding more instructions is not automatically the right correction.

These tiny snapshots do not reproduce a full repository investigation. Results
apply to the specified cases and host setup, not organization-wide productivity.
Document exceptions and limitations alongside the PR. The tool never edits a
skill, approves a PR, publishes a review or merges changes.

## No-cost plumbing smoke test

This scripted runner returns a constant answer and intentionally proves nothing
about model quality. Always mark scripted/mock execution with `--synthetic`.

```bash
python3 scripts/skill_eval.py run \
  --suite evals/suites/critical-review.json --skill none --label smoke-baseline \
  --model scripted --environment smoke --repeat 1 --synthetic \
  --out work/eval/smoke-baseline.json \
  -- python3 -c 'import sys; sys.stdin.read(); print("Scripted answer, not model evidence.")'
python3 scripts/skill_eval.py run \
  --suite evals/suites/critical-review.json \
  --skill core/skills/critical-review --label smoke-current \
  --model scripted --environment smoke --repeat 1 --synthetic \
  --out work/eval/smoke-current.json \
  -- python3 -c 'import sys; sys.stdin.read(); print("Scripted answer, not model evidence.")'
python3 scripts/skill_eval.py assess work/eval/smoke-baseline.json \
  --out work/eval/smoke-baseline-assessment.json
python3 scripts/skill_eval.py assess work/eval/smoke-current.json \
  --out work/eval/smoke-current-assessment.json
python3 scripts/skill_eval.py compare \
  work/eval/smoke-baseline.json work/eval/smoke-current.json \
  --before-assessment work/eval/smoke-baseline-assessment.json \
  --after-assessment work/eval/smoke-current-assessment.json \
  --out work/eval/smoke-comparison.md
```

The report is marked **SYNTHETIC**, and all checks remain inconclusive until
assessed. The harness cannot independently determine whether an arbitrary adapter
uses a real model: truthful provenance is the operator's responsibility.
