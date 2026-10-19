---
name: deployment-request-check
description: >-
  Verifies a deployment request from each linked pull request's approval,
  merge, mergeability, and check state, and reports approvable or hold with
  reasons. Use for deploy approval, can this ship, ready to deploy, 배포 승인
  가능, 배포 요청 검증, 승인해도 될까. Not a code review or ticket drafting;
  read-only unless a write is named.
---

# Deployment request check

A deployment request arrives as a chat thread or a tracker item with one or
more pull requests behind it. The question is narrow: has the team already
reviewed and accepted these changes, and is nothing failing right now? Two
mistakes answer it wrongly. Approving from the thread alone trusts a summary
that may be a day stale. Re-reviewing the diff repeats work the reviewers did
and delays a release for nothing. Check the recorded state of each change,
nothing more and nothing less.

Assume the requester usually asks when the work is ready. Hold only on a
clear, observable miss, and name it.

## Read-write boundary

The default is verify-only: read the thread, the tracker, and the code host,
then report in chat. "Check this request" authorizes no write. Transitioning
the tracker item, recording the result on it, and replying in the thread are
three separate actions, each performed only when the user names it. Never
merge, never deploy.

## 1. Resolve the request

Accept a thread link, a tracker key or URL, or pull request links directly.
From a thread, read the whole thread, not only the root message, and extract:

- tracker keys, in the thread and in linked items;
- pull request links or bare numbers;
- the **requester**: the author of the root message;
- the **worker**: the person mentioned as owner, or the item's assignee.

Requester and worker are often different people. An approval goes back to the
requester; a hold goes to the worker who must act. When the thread names one
key and the linked item points at a different change, the thread key is the
request; report the mismatch instead of silently following the item.

`scripts/change_refs.py` extracts keys, change links, and thread coordinates
from pasted text or a permalink.

## 2. Collect every change

Search in this order and stop only after all three: the thread, the tracker
item's linked changes, then the item's description and comments as raw text.
Rich-text link cards hide the URL from a rendered view, so scan the raw body.
A thread with no pull request link is normal, not a finding. Report "no change
linked" only after every source is empty.

Check every change found. One failing change holds the whole request.

## 3. Gate each change

Fetch the current state from the code host. Never judge from memory or from
the thread's description of the state.

| State | Passes when |
| --- | --- |
| Merged | Always on the review axis. A failing latest check is still a hold. |
| Open | Not a draft, review decision approved, mergeable, no failing or pending latest check. |

Checks mislead in two ways. The same check name appears twice after a re-run
and the older failure survives in the rollup; judge only the latest run per
name. A check the team has declared non-blocking may fail routinely; treat it
as exempt only when the environment profile lists that check name, and write
every applied exemption into the record. Never exempt on the spot.

Reviewer headcount is not a criterion: the host's review decision already
encodes the repository's required approvals, so one approval is an approval. An
authentication or not-found error from the code host means the change could
not be verified, which is a different finding from "no change linked".

Do not review the diff. The question is whether already-reviewed work may
ship, not whether the code is good.

`scripts/pr_gate.py` applies these rules to the code host's JSON for one or
more changes and prints the verdict, reasons, notes, and exemptions.

## 4. Add tracker context when reachable

When the tracker is reachable, read the item's status, assignee, blocking
links, and whether any work record exists: a description of the scope, a
linked change, or a progress comment. An item already in its ready or done
state needs no transition; say so. A cancelled item is a hold. An open
blocking item in the same release scope is a hold with its key named. In
verify-only these are context; when a write is requested they are gates.

## 5. Decide and report

The verdict is **approvable** when every change passes and no tracker gate
fails, otherwise **hold**. Report in chat:

```text
Verdict: approvable | hold
- Item: KEY (status)
- Change: repository#N - state, review decision, checks, mergeable
- Reasons: CODE - observable fact (hold only)
- Writes: none performed
```

Reason codes, the code host fields, and edge cases are in
[references/gates-and-reasons.md](references/gates-and-reasons.md).

## 6. Writes, only when named

- **Approve**: find the transition to the team's ready-for-deployment state by
  name among the item's available transitions. When several match, show them
  and ask; never use a done or closed transition as approval. Skip the
  transition when the item is already there. Record the verdict on the item in
  full: per-change table, checks, exemptions, the thread link, the time. Reply
  in the thread in one or two sentences mentioning the requester.
- **Hold**: change no status. Record the full reasons and the required actions
  on the item. Reply in the thread in two to four sentences mentioning the
  worker and pointing at the record.

The tracker record is the detailed one; the thread reply is brief. Never paste
the per-change table or a bullet list into chat, and keep agent or skill
meta-commentary out of both. After a transition, read the item back and
confirm the status and dates survived. Templates are in
[references/records-and-replies.md](references/records-and-replies.md).

## Do not

- merge, deploy, or review the diff;
- relax a failing check without a profile-listed, recorded exemption;
- hardcode a repository, channel, or status name; they come from the request
  or the environment profile;
- paste credentials, test accounts, or tokens into any record or reply.
