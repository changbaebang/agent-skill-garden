# Standup draft output

The first block is what the person pastes. Everything after the rule is for
their review and stays in the conversation.

```markdown
## Standup draft — {YYYY-MM-DD (weekday)}

> Draft only. Nothing was posted. Review it, then paste it into the thread yourself.

Done
- {item} — {detail}
- …

Next
- {carried over from yesterday, marked as such}
- {tracker item in progress}
- {open pull request}
- {meeting or on-call duty}

Blockers
- {only what a source stated; omit the section when empty}

Open assignments (only when Next has no confirmed item)
- {key} {summary}
- … up to five, as tracker links

---

### Evidence (review only, do not post)
| Item | Sources |
| --- | --- |
| {item} | pr #101 merged · tracker ABC-12 → Done |

### Confidence
- Done: high / medium / low, naming the weak lines
- Next: …
- Blockers: …

### Carry-over check
- Yesterday's next not reflected in today's done: {items, or "none"}
- Sources not checked: {gaps, or "none"}
```

## Section rules

- Three to seven bullets per section; one line each. When more exist, keep the
  seven with the strongest evidence and note the overflow count under
  Evidence.
- Use the team's own labels and bullet glyph as observed in the previous
  thread. The English labels above are defaults, not requirements.
- Write tracker keys the way the thread writes them. Inside an internal
  channel, bare keys are normal; do not expand them into prose.
- Confidence per line: high when two or more source kinds agree, medium when a
  single pull-request or tracker record supports it, low when only a local
  session supports it. A section's confidence is its weakest line.

## Feedback after posting

When the user shares the version they actually posted, reply with:

1. What the draft had that they removed.
2. What they added that no source showed, with a note on which source could
   have caught it.
3. Tone or format differences worth keeping.
4. One proposed line for their local preference notes, applied only after they
   confirm. Nothing is stored in this skill.
