# Pull request body

## Shape

```markdown
## Summary
One paragraph: what changes for the user or the system, and why now.

## Work item
Full tracker key, untruncated, with its link.

## Changes
- path: what changed and why

## Verification
- static checks: command and result
- tests: new cases, regression cases
- runtime smoke: environment, route, result, or the recorded skip reason

## Side effects
Divergence table or "equivalent" with the evidence; consumer sweep result.

## What remains
- follow-up items split out of scope, with their keys once created
- values or decisions awaiting confirmation and who confirms them

## Risk
Behaviour that could regress, how it would be noticed, how to roll back.
```

"What remains" is mandatory even when empty: write "nothing" so a reviewer can
tell an omission from a clean finish.

## Keep the tracker key whole

Some trackers put digits in the project prefix. A pattern such as
`[A-Z]+-[0-9]+` searched without an anchor starts matching after the digit and
returns a shorter key that links to the wrong item or to nothing. Match the
whole token:

```text
\b([A-Z][A-Z0-9]*-[0-9]+)\b
```

`scripts/work_item_key.py` applies this and prefers the longest match when
several keys appear. Pass `--prefer PREFIX` when the repository favours one
project; do not hardcode a prefix in the skill.

## Temporary mocks and work-in-progress code

A temporary mock, stub, or disabled path may be noted as a comment instead of
blocking the pull request only when both hold:

- the base is a non-production integration branch, and
- a fallback or mitigation keeps the immediate failure risk low.

When downgrading, record all three together: the follow-up item, its owner, and
the target branch or date by which it is removed before production. A risk that
is severe and immediate is not downgraded regardless of the base.

## Updating an open pull request body

Editing the body is a write; do it only when the user asks. When
`pull-request-checklist` is installed, use its section-level update: it
replaces content under the headings the template defines and leaves reviewer
checklists and automation-owned blocks byte-stable. Without it, read the
current body first, build the complete new text from it rather than patching
one section blind, write it to a file, and send it as JSON so multi-line text
and code fences arrive intact:

```bash
gh pr view "$number" --json title,body,baseRefName,headRefName
jq -Rs '{body: .}' new-body.md \
  | gh api -X PATCH "repos/$owner/$repo/pulls/$number" --input -
```

Read the body back after the write; an intended value is not an applied one.

The same JSON route applies to review replies; form-encoded fields break on
backticks and newlines:

```bash
jq -n --arg b "$reply" '{body: $b}' \
  | gh api "repos/$owner/$repo/pulls/$number/comments/$comment_id/replies" --input -
```

Reviewers may be reading the diff pinned to an older commit. A reply that
claims a fix names the commit and points at the current head.

## Optional: reflecting onto a shared test branch

When the change must reach a shared test branch before merge, cherry-pick the
commits onto a fresh local copy of that branch and push with an ordinary
fast-forward push. Never force-push a shared branch. Before the cherry-pick,
confirm the shared branch already carries the files, flag keys, and modules the
commit depends on; a missing module breaks the shared build for everyone.
