---
name: quality-gate-triage
description: >-
  Triages a pull request's static-analysis quality gate from the step log, not
  the check color: real failure, no verdict, or pass. Fixes in-scope findings
  only after approval and posts the rest as a pull request comment. Use for
  quality gate failed, static analysis flagged my PR, coverage gate dropped,
  퀄리티게이트 떨어졌는데, 정적분석 결과 봐줘. Not for editing the CI workflow itself.
---

# Quality gate triage

A gate step that the pipeline is allowed to fail shows a green check whether
the gate passed, failed, or never returned a verdict. "The gate passed",
said from the check color, is then a guess dressed as a fact. The step log is
the evidence; the color is not.

## Read the log before saying anything

1. Find the gate run for the pull request's head commit, not the latest run on
   the branch. Note whether that commit has more than one run.
2. Open the gate step's log and keep the exact lines that state a verdict, a
   timeout, or the conditions that failed. `scripts/gate_log_triage.py classify`
   makes this first pass and prints the lines it relied on; read those lines
   yourself before trusting the label.
3. Open the CI definition and check whether the gate step is allowed to fail
   (`continue-on-error`, `allow_failure`, a trailing `|| true`, or a check the
   base branch's protection does not require). Record the file and line. This
   decides whether a failure blocks the merge, and the user must hear it.

A successful upload or scan step is not a gate verdict. Keep the two apart in
every sentence you write.

## Three verdicts, three paths

| The log shows | Verdict | Next |
| --- | --- | --- |
| a failed status and the conditions that failed | real failure | classify fixability |
| a timeout, or the analysis never finished | no verdict | prove the pattern with numbers |
| a passed status | pass | report; no comment needed |

A timeout is not a code-quality violation: the report uploaded and the step
stopped waiting for the server. Never report it as "the gate is red".

## A missing verdict needs numbers, not a feeling

"It is not this pull request's fault" is a claim. Prove or refute it:

- Collect the last several gate runs across the repository, classify each log,
  and tally by branch with `scripts/gate_log_triage.py tally`.
- Timeouts on other branches as well: infrastructure. Go to communicate.
- Timeouts on this branch only: this change made the analysis heavier, for
  example a jump in the files under coverage. Treat it as a real failure.
- Two runs for one commit lengthen the server queue and may contribute. Write
  "may have contributed; not confirmed". Do not state a cause you did not test.

## Real failure: decide what is fixable before touching anything

Read the violated conditions from the log or the gate's dashboard. Take the
dashboard link from the log or from the environment profile; when it needs
network access a reader may not have, say so beside the link.

| Finding | Decision |
| --- | --- |
| smell, duplication, or complexity in a file this change touched | fixable |
| coverage on new code below the threshold | fixable by adding tests |
| pre-existing violation in a file this change did not touch | not here: scope drift |
| gate or pipeline configuration: timeouts, duplicate triggers, exclusions | not here: separate change |

## Fixable does not mean fix now

Ask before editing, with explicit options rather than prose. Present:

- what was flagged: rule, `path:line`, count;
- the fix scope: files to touch, and how far they sit from the pull request's
  subject;
- the risk: behaviour change, regression tests needed;
- what happens if nothing is fixed: whether the merge is blocked under the
  current gate configuration.

Options: fix now; leave it and comment; split into a follow-up. The merge-block
fact is mandatory. Leaving it out makes the user hurry for no reason.

## Fixing after approval

- Edit only the files and lines the gate named. No "while I am here".
- Verify as the repository's policy requires; use `affected-verification` when
  it is installed.
- Name the rule and the change in the commit message.
- After pushing, draft a comment that says what was fixed and why.

## Not fixing: say so on the pull request

Silence is the failure mode: the next reader sees a green check and concludes
the gate passed. Draft a comment from
[references/pr-comment-template.md](references/pr-comment-template.md), show
it, and post it when the user approves. It carries:

1. "not fixing here" in the title, so it reads as a decision, not neglect;
2. that the green check is not a pass, the quoted log line, and the file and
   line of the setting that lets the step fail;
3. a table separating scan success from gate verdict;
4. the branch tally when the pattern is repository-wide;
5. why not in this pull request, with a link to any existing improvement
   ticket in the tracker;
6. the dashboard link and its access note.

## Do not

- Write "the gate passed" with the check color as the only evidence.
- Write "gate failure" for a timeout.
- Assert a cause you did not confirm.
- Change code the gate flagged without the user's approval.
- Edit the pipeline definition as part of this triage.

## Report

- The verdict and the log line number that proves it.
- What was fixed, or why nothing was.
- The comment link, or the draft awaiting approval.
- Whether the merge is blocked under the current configuration.

Commands, the tally procedure, and the pattern override are in
[references/verdicts-and-evidence.md](references/verdicts-and-evidence.md).
