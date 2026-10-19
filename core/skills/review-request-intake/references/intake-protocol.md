# Intake protocol

## Stable key and states

Key: `{channel}:{parent_message}:{repository}:{pr_number}:{head_revision}`.

| State | Meaning | Next |
| --- | --- | --- |
| discovered | candidate found, not claimed | qualify |
| reviewing | claimed by a sweep, a mention handler, or another reviewer | do not claim again |
| awaiting follow-up | review posted, actionable thread unresolved | re-review on head change or author reply |
| post-approval evidence | new human review or thread after approval, same head | audit read-only; post only if release-relevant |
| completed | review and chat actions verified, nothing actionable | skip unless head changes |
| blocked | external condition unmet | keep reason and head; reopen when either changes |

A promise of a follow-up ticket on the same head is not a changed condition.

## Cursor rules

- Store the cursor and reply markers outside the skill (the inputs listed in SKILL.md section 0).
- Read messages after the cursor plus the most recent ~20 roots as overlap.
- Advance only after the whole scan succeeded.
- Exactly one sweep owns channel-wide discovery. A separate mention handler
  may resolve a supplied permalink or bounded recent mentions, but it must
  share the same keys and must not run as a second always-on scan.

## Pre-publish checks

- Pull request still open; head unchanged since you read it.
- Your latest review is not already on this head with the same conclusion.
- Author identity taken from the pull request.
- Payload built as structured data and sent from a file, so backticks,
  newlines, and quotes survive. Reject payloads that contain a literal
  backslash-n pair or an empty body.
- Read the posted review back; do not auto-retry on mismatch, report it.

## Chat reply shape

- One line: author, topic, verdict.
- Zero to two sentences of what the whole team needs to know.
- Concerns only, marked by severity. No praise lists.
- Do not repeat the pull request link when the thread already has it.
- Several pull requests in one thread: one block each, with its own author.

## Reaction convention

Started: an "eyes" emoji reaction. Finished: a "check mark" emoji reaction on
the original message. A check mark means "this round posted", never "no further
re-review". Missing reaction permission: say so, do not claim completion.

## Withdrawals

Merged, closed, documentation-only: tell the user in the conversation, nothing
else. No reaction, no reply, no review.

## Scripts

`scripts/intake_state.py permalink <url> [regex]` prints channel and message
id as JSON, with the thread parent when the link points at a reply. The default
parser reads Slack-style links (`archives/<channel>/p<digits>`, optional
`thread_ts` query). For another chat tool pass a regex with named groups
`channel` and `message`, or read the ids by hand.
`scripts/intake_state.py decide < facts.json` prints one action among
`withdraw`, `skip-docs`, `review`, `re-review`, `audit`, `skip`. Facts keys:
`state`, `docs_only`, `head`, `last_reviewed_head`, `my_last_review`
(`none`, `approved`, `commented`, `changes_requested`), `unresolved_thread`,
`author_replied_after_review` (any author reply or prose explanation after
your review, on your thread or not), `new_human_evidence_same_head`,
`completed_head` (head already verified complete; skips unless it moves).
`unresolved_thread` is informational for the user-facing summary.
