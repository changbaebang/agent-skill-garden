# Review request message shapes

## Fetch the pull request

With the GitHub CLI, for example:

```bash
gh pr view "$pr" --json number,url,title,body,state,isDraft,reviewDecision,author,assignees,reviewRequests,reviews,files,baseRefName \
  | python3 scripts/review_request_gate.py
```

The script reads that JSON on standard input and prints:

```text
action: proceed | stop
applied_filter: none | draft | not_open | review_already_complete | duplicate_request
review_decision: REVIEW_REQUIRED | CHANGES_REQUESTED | APPROVED | (empty)
mention_candidates: login, login
team_requests: group-slug
excluded: author:login, bot:login
reason: one sentence
```

Exit status is 0 for `proceed`, 3 for `stop`, 2 for unreadable input. Pass
`--json` for machine-readable output, `--bot LOGIN` for automation accounts the
default markers do not catch, and `--ledger PATH --window-hours N` to detect a
request already sent for the same pull request. After a confirmed send, run the
same command with `--record` to append the entry.

## Two readers, two tones

| | Chat message | Pull request body |
| --- | --- | --- |
| Reader | a reviewer deciding whether to open it now | the reviewer reading the diff |
| Goal | understood in ten seconds | implementation and verification detail |
| Register | everyday language | technical terms are fine |
| Must contain | what changed, visible change or not, link | summary, test plan, references |

The three required lines of the chat message:

1. What changed, described by feature or screen.
2. Whether the screen changes once deployed. Write "no visible change" when
   that is the case; do not leave the reviewer to infer it.
3. The pull request link, as given by the code host.

## Rewrite table

Replace what the diff says with what a person outside the work would say.

| Written in the diff or body | Written in chat |
| --- | --- |
| `trailingSlot` prop on `TopBarShell` | a spot in the mobile top bar where screens can add a button |
| `hideCompactFooter` | hide the footer on phones only; desktop keeps it |
| legacy parity | matches what the old screen used to do |
| packages only, app layout not switched | nothing uses it yet, so the screen stays the same |
| migration epic, phase 3 | one step of the header and footer consolidation |

Never in chat: the title verbatim, the body's summary bullets verbatim, lists
of component or property names, long package paths.

## Templates

Mention tokens below stand for the chat platform's own user or group
identities, resolved as the skill describes. Draft in the channel's working
language.

### A. Individual reviewers

```text
{mention} {mention}

Could you take a look? 🙏

**{short title or tracker key and a few plain words}**
{one sentence: what changed}

{one sentence: visible change, or "no visible change for users"}

{pull request link}
```

### B. Team fallback

Used only when no individual identity resolved or the pull request names no
reviewer or assignee.

```text
{group mention}

Could someone take a look? 🙏

**{short title}**
{one sentence: what changed}

{one sentence: visible change or not}

{pull request link}
```

### C. Preparation work with no visible change

The visible-change line is the one reviewers look for first. Make it the
longest line in the message when the answer is "nothing changes".

```text
{mentions}

Could you take a look? 🙏

**Shared top bar: optional slot for an extra button**
Adds a place in the shared top bar where a screen can put one more button,
matching what the old screen already allowed.

Nothing uses the slot yet, so merging this changes nothing on any screen.

{pull request link}
```

A bad version of the same message, which must not be sent:

```text
Added a trailingSlot to TopBarShell for legacy parity with the previous
navigation module's children rendering.
```

## Stop outputs

Report the reason in one or two sentences and nothing else:

- review already complete: "Every requested review on this pull request is
  already an approval, so no request was drafted."
- draft: "The pull request is still a draft; the request is held until it is
  marked ready."
- not open: "The pull request is merged or closed; nothing to request."
- duplicate: "A request for this pull request was posted {when}; say so
  explicitly if it should go out again."

## Result block

```markdown
## Result
- action: proceed | stop
- applied_filter: none | draft | not_open | review_already_complete | duplicate_request
- pull request: {number} {link}
- review_decision: {value}
- mentions: {resolved identities}
- mention_fallback: individual | team

## Draft
(the full message, ready to paste)

## Send guidance
- Not sent. Say "post it" to send to {channel alias from the profile}.

## Debug
- reviewers on the code host: [...]
- resolved: login → identity (via e-mail | via display name)
- unresolved: [...]
- assignees on the code host: [...]
```

## Repairing a message that went out with text mentions

A message whose mention line was pasted as code host handles notified nobody.
Reply inside its thread with the corrected mention line and one line saying
the earlier mention did not render, keeping the original body. Do not post a
new top-level message; the thread keeps the request in one place.
