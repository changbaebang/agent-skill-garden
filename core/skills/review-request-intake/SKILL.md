---
name: review-request-intake
description: >-
  Reviewer-side intake of pull request review requests from a chat message link or a channel sweep: find missed requests, decide review or re-review, report back in the original thread. Use for review request intake, 리뷰 요청 확인, 놓친 리뷰, 리뷰 누락, 재리뷰, review sweep. Not for requesting a review, answering reviews on your own PR, or judging code.
---

# Review request intake

Reviewer side only. This skill decides which requests deserve a review, when a
finished review must be reopened, and how to close the loop in the requester's
thread. It does not define how to judge code (see step 4).

## 0. Inputs and capabilities

Ask the user for any input that is missing; never guess it. Offer to keep the
answers in a local note the user owns.

- Request channel, and the message link if one was given.
- The user's own chat identifier and code-host login (exact strings).
- Sweep cursor: the last scanned message timestamp, kept by the user or in a
  local note. No cursor means ask, then run Recovery once.
- Chat tool able to read channels and threads, post replies, and add reactions.
  The bundled link parser reads Slack-style links; for other chat tools pass a
  pattern as described in the protocol reference, or read ids by hand.
- Code host with GitHub-style pull request semantics: merged or closed state,
  head revision, changed files, review states (approved, commented, changes
  requested), one review carrying a summary plus inline comments, and
  resolvable threads. For a different host, map each term to its closest
  equivalent and say so.
- Code review: use any pull request review skill the user has. Without one,
  review the diff yourself, checking correctness, risk, and tests.

## 1. Pick the entry mode

- **Permalink**: the user gave one message link. Resolve that one thread now,
  ignoring any sweep cursor. Parse it with `scripts/intake_state.py permalink`.
- **Sweep**: scheduled or manual scan of the request channel. Read only
  messages new since the cursor plus a small overlap window of recent roots.
  Never reread the whole history on a routine run.
- **Recovery**: allowed once, bounded, only when the cursor is missing, a prior
  read failed, or a concrete miss was confirmed. It is not a routine path.

Match requests by the user's exact chat identifier in the raw message text,
never by display name or phrases like "please review".

## 2. Qualify each candidate before any work

A candidate needs a pull request link and review intent. Ignore FYI mentions,
link shares, thanks, and chatter. Then read the pull request, not the chat:

1. State. Merged or closed: withdraw silently. Tell only the user, in the
   conversation. Late requests are common; a post-merge comment is noise.
2. Files. If every changed file is documentation, do not auto-review. Tell the
   user and stop. Judge documents only on explicit request.
3. Author. Take the author from the pull request, never from chat mentions.
   The requester, the person mentioned, and the author are often three people.
4. Prior art. Read other reviewers' reviews and open threads. If someone
   already raised the topic, do not restate it.

## 3. Decide new review versus re-review

Use `scripts/intake_state.py decide` for the mechanical part. The judgment:

- Track a request by a stable key: channel, parent message, repository, pull
  request number, head revision. One key is claimed once.
- A prior comment-only or changes-requested review on an open pull request is
  not finished. It stays "awaiting follow-up" until closed out.
- Re-review when the head moved past the last reviewed revision, or the author
  replied after your review (on your thread or in prose, explaining a fix).
- Do not re-review when nothing changed. Another reviewer's check mark, a
  "reviewing" note, or your own earlier emoji never blocks a re-review and
  never substitutes for one.
- Same head with only an author reply: reclassify the existing threads. Do not
  invent findings in unchanged code.
- A new human review or thread after your approval on the same head is evidence
  to audit, not a reason to post again.

## 4. Review, then publish in order

Do the code judgment as set out in section 0. For unattended sweeps, use the
softest posting action that still carries the finding: report problems as
comments, approve only when clean. Blocking verdicts are a manual,
user-requested act.

Immediately before every write, refetch state, head, your latest review, and
unresolved threads. If the same head is already completed, stop.

Publish in this order and stop at the first failure:

1. One review on the pull request: summary body plus inline findings together.
   Never post inline comments one by one. Read it back and verify head, state,
   and body.
2. A short reply in the original chat thread. Results only, addressed to the
   author. No corrections, apologies, or process talk; fix names before posting.
3. The completion reaction on the original message, only after the first two
   succeeded. Reaction text inside a reply is not a reaction.

Every write beyond reading needs current-session user approval, or an explicit
standing automation policy. Showing the user the draft first is the default.

## 5. Record state and fail loudly

States: discovered, reviewing, awaiting follow-up, post-approval evidence,
completed, blocked. Advance the cursor only after the scan and every needed
thread read succeeded. A failed read or failed authentication is not an empty
result: report it, post nothing, keep the cursor. If there is nothing to do,
end quietly with no external message.

Details, templates, and the state table: [references/intake-protocol.md](references/intake-protocol.md).
