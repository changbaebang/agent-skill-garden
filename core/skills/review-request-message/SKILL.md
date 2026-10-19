---
name: review-request-message
description: >-
  Drafts the chat message asking for review of an open pull request: mentions
  that notify, plain-language summary (not the title), visible-change line,
  team fallback, stop if review is done. Use for draft a review request, ping
  reviewers for my PR, 리뷰 요청 문구, 리뷰 요청 메시지 써줘. Not for answering or writing
  reviews; drafts only.
---

# Review request message

A review request is read in ten seconds by someone who was not in the work.
Three failures recur: the message is the pull request title and the reader
cannot tell what it means; the mention is plain text and nobody is notified;
the request goes out after the review was already finished. This workflow
produces a send-ready draft, and stops there.

## Gate before drafting

Fetch the pull request as it is now: state, draft flag, review decision,
requested reviewers, assignees, submitted reviews, author, title, body, changed
files, link. No fetch, no draft.

Stop, and report only the reason, when any of these holds:

- it is a draft;
- it is not open (merged or closed);
- the review decision is approved;
- no review request is pending and every human reviewer's standing review is
  an approval;
- a request for this pull request was already posted recently, found by
  searching the channel for its link or in the local send ledger that
  `scripts/review_request_gate.py --ledger` keeps. Re-sending needs the user
  to say so.

Proceed when it is open, not a draft, and review is required, requested, or
changes were requested. `scripts/review_request_gate.py` applies these rules to
the fetched JSON and lists the mention candidates; the fetch command and the
script's output are in
[references/message-shapes.md](references/message-shapes.md).

## Mentions that notify

Candidates are the requested reviewers plus the assignees, minus the author,
minus automation accounts, deduplicated.

Resolve each candidate to the chat platform's own user identity, usually by
e-mail from the code host profile and then by display name through the chat
directory. A code host handle pasted into chat renders as text and notifies
nobody. Leave unresolved candidates out of the mention line and list them in
the debug block.

When no candidate resolves, or the pull request names no reviewer or assignee,
mention the team group instead. The group's identity and the review channel
come from the environment profile's chat integration; routing between several
groups by the area of the change is organization policy and belongs in a
private extension, not here. Never substitute a handle string for a group
mention.

## Plain language, not the title

Chat and the pull request body have different readers. The body carries the
technical detail. The chat message carries exactly three things:

1. what changed, in terms of a feature or a screen, in one sentence;
2. whether a user sees anything different once this is deployed. When nothing
   changes, say so explicitly: it is the reviewer's first question;
3. the link.

Do not paste the title, the body's summary bullets, component or property
names, or long package paths. Write from the title, body, and diff; state facts
only, and do not guess at impact. Templates, the rewrite table, and the output
format are in [references/message-shapes.md](references/message-shapes.md).

## Draft, then wait

The default result is a draft in the conversation, written in the channel's
working language, with a result block (action, applied filter, mentions,
fallback used) and a debug block (resolved and unresolved candidates).

Send only when the user says to post. Before sending, check that the mention
line contains platform identities only, confirm the channel from the profile,
send once, and record the pull request in the ledger. If a message already went
out with text mentions, reply in its thread with the corrected mentions; do not
post a second top-level message.

## Follow-up in the same thread

After the author handles feedback, the thread gets one short reply. Classify
each reviewer's feedback as answered, updated, mixed, or pending from the
commits, not from the author's replies; mention only reviewers whose feedback
is now handled; never write "fixed" for a reply alone. Confirm with the user
that the humans about to be mentioned are available before sending. Shapes are
in [references/follow-up-reply.md](references/follow-up-reply.md). Driving the
review to a settled outcome is `review-response-loop`'s job.

## Do not

- Draft without fetching the current pull request.
- Use code host handles as mentions, or a handle string as a team fallback.
- Send, resolve review threads, add reviewers on the code host, or edit the
  pull request body as part of this skill.
