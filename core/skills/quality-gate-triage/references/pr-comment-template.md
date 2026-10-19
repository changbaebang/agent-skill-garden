# Asking, commenting, reporting

## Ask before fixing

Put the question to the user as options, not as a paragraph that trails off
into doing the work. Fill every field from the log and the diff:

```markdown
Gate findings on this pull request

- Flagged: <rule> at <path:line> (<n> occurrences); <rule> at <path:line> ...
- Fix scope: <n> files, all inside the change | <n> files outside the change's subject
- Risk: no behaviour change | behaviour change in <area>; regression tests needed: yes | no
- If nothing is fixed: the merge is blocked | the merge is not blocked (gate step may fail: <file:line>)

Options:
1. fix now, limited to the flagged lines
2. leave it, and post the comment below
3. split into a follow-up and post the comment below
```

Option 1 authorizes edits to the flagged files and lines only. Options 2 and 3
authorize nothing until the user also approves the comment.

## Comment when not fixing here

Write in the repository's working language. Keep the title verbatim in spirit:
it must read as a decision.

```markdown
## Quality gate: not fixing in this pull request

The gate check is green, but the log did not produce a verdict | produced a
failing verdict. The step is allowed to fail (`<file>:<line>`), so the check
color is not a pass.

| Step | Result | Meaning |
| --- | --- | --- |
| scan / upload | succeeded | the report reached the server |
| gate verdict | <timed out | failed: n conditions> | <no verdict was produced | real failure> |

Log, run <id>, line <n>:

> <quoted log line>

<When repository-wide:>
Of the last <n> gate runs, <k> on <b> branches ended the same way, so this is
the pipeline, not this change. <m> commits ran twice, which may have added to
the queue; not confirmed.

<When a real failure:>
The flagged items are <in files this change did not touch | gate configuration>,
which is outside this pull request's subject (<subject>). <Tracked in <ticket>.>

Dashboard: <link> <(private network required)>
```

Delete the branch that does not apply. Do not leave both alternatives in the
posted text.

## Comment after fixing

```markdown
## Quality gate: fixed in <commit>

- <rule>: <what changed> at <path:line>
- Verification: <lanes run and result>
- Remaining: <items left and where they are tracked | none>
```

## Post with the body as a file

```bash
cat > comment.md <<'MD'
...the comment...
MD

jq -Rs '{body: .}' comment.md \
  | gh api "repos/$repo/issues/$pr/comments" --input - --jq .html_url
```

Passing the body as an inline flag breaks on newlines, backticks, and code
fences. Read the comment back at the printed URL before reporting the link.

## Report to the user

```markdown
## Gate verdict
- <passed | failed | no-verdict> — run <id>, log line <n>: "<text>"
- Step allowed to fail: yes (<file:line>) | no
- Merge blocked by this gate: yes | no

## Action
- fixed: <commit, what> | not fixed: <reason>
- comment: <url> | draft shown, awaiting approval

## Open
- <anything the user still has to decide>
```
