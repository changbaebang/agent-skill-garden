# Review output

Produce the sections in this order. Keep every claim tied to a citation from
the document, a file path from the implementation, or the literal phrase
"not in document".

```markdown
## Metadata
- Document: title and source
- Implementation: pull request or revision range, or "none supplied"

## Part A: document quality
1. One-line summary: what changes, for whom, to what end
   (or "not assessable: document body missing")
2. Scores: clarity N · scope N · risk N · dependencies N · ambiguity N
   → readiness NN (band)
3. Document type: complete | draft | not a requirements document
4. Missing or ambiguous items
   - item — citation, or "not in document"
5. Pre-implementation questions (at most seven, each answerable yes or no)
6. Recommendation: implement now | revise the document first |
   cut scope and spike | reference only

## Part B: implementation alignment
(or "Part B skipped: no implementation input")

| Criterion or scenario | Evidence (file, component, behavior) | Status |
| --- | --- | --- |
| ... | ... | met / partial / missing / undocumented |

- Gaps: underbuild · overbuild · mismatch (confirm needed) · non-functional (withheld)
- Implementation risks: regression-prone areas, criteria too vague to test
- Alignment: NN (met M · partial P · missing X · overbuild U)

## Summary
Readiness NN, alignment NN — the single most important gap on each side.
```

## Collecting implementation evidence

Start from the summary level and open files only when a mapping row needs
proof:

```bash
git diff --stat <base>...<head>
git log --oneline <base>..<head>
```

The pull request description and its comments supply the document link and
the author's intent. Treat generated comments as lower-priority evidence than
the author's own words. Never paste a diff hunk that contains a token, key, or
personal record into the review.

## Input checklist for the requester

Hand this back when the review cannot start:

- document body, or at minimum its scope, acceptance criteria, and exception
  sections pasted inline;
- whether an implementation comparison is wanted;
- the pull request, branch, or revision range when it is;
- any decision already made outside the document that the reviewer should
  treat as settled.

## Comment-triggered request shape

A team may agree on a short keyword that, when posted as a pull request
comment, asks for this review. Such a comment should carry:

- the document link;
- optionally the key sections pasted inline, so the review survives a failed
  fetch;
- whether alignment against the diff is wanted.

The keyword requests analysis. Posting the result back to the pull request is
a separate action the user must ask for.
