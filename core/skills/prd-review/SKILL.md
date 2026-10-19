---
name: prd-review
description: >-
  Scores a requirements document on five axes and maps its acceptance criteria
  to implementation evidence when a diff exists. Use for PRD review, is this
  PRD ready, spec quality, implementation alignment, PRD 리뷰, PRD 품질, 기획서
  점검, or 구현 일치도. Not for writing requirements or hunting bugs. Read-only
  unless asked to comment.
---

# Requirements document review

The document is judged on what it states and the implementation on what the
code shows. A title, a link, a ticket summary, or a memory of a meeting is not
evidence for either part.

## Collect inputs first

1. **Document body.** Accept pasted text, a local file, or a page fetched
   through a connector the host exposes. If only a link is available and the
   body cannot be fetched, stop: report that neither part can be assessed and
   ask for the body, or at least the scope, acceptance-criteria, and exception
   sections. Never produce a score from a link.
2. **Implementation evidence (optional).** A changed-file list with a diff
   stat, the pull request description, commit messages, or an author-written
   summary. Open changed files only as far as a mapping row needs. If the diff
   carries a credential or personal data, say so without quoting it and ask for
   a masked resubmission.
3. **Comment-triggered runs.** When a team requests this review with an agreed
   keyword in a pull request comment, take the document link from that comment
   and prefer the author's comment over generated ones. The trigger authorizes
   reading, not posting.

## Part A: document quality

Walk the eight-section checklist in
[references/scoring-rubric.md](references/scoring-rubric.md). Mark each section
present, absent, or explicitly deferred; a section that states "undecided" for
data, API, or policy counts as present because the gap is declared.

Classify the document:

- **complete** when all eight sections are present;
- **draft** when some are present;
- **not a requirements document** when it is a template, a meeting sync, a
  collection or index page, a deprecated copy, or an empty stub.

Score the five axes (clarity, scope, risk, dependencies, ambiguity) from 1
to 5. Every axis is oriented so that higher is better, including risk (higher
means impact analysis is present in proportion to the domain's blast radius)
and ambiguity (higher means fewer open markers and contradictions). Each
deduction cites the document or says "not in document".

Do the arithmetic with `scripts/score_requirements.py` (input shape in the
rubric); it returns the readiness score, band, document type, and whether
"implement now" is still eligible. Then list missing or ambiguous items with
citations, at most seven pre-implementation questions that can be answered yes
or no, and exactly one recommendation: implement now, revise the document
first, cut scope and spike, or reference only.

## Part B: implementation alignment

Run this part only when implementation evidence was supplied. Otherwise write
"Part B skipped: no implementation input" and do not infer behavior from the
document.

Build the mapping table: each acceptance criterion or scenario, the evidence
that addresses it (file, component, or observed behavior), and a status of
met, partial, missing, or undocumented. Then name the gaps by type:

- **underbuild**: in the document, absent from the code;
- **overbuild**: in the code, absent from the document, so scope may have crept;
- **mismatch**: the document says one thing and the code does another; mark it
  "confirm needed" rather than deciding which side is right;
- **non-functional**: logging, flags, error handling, or accessibility the
  document never specified, so judgment is withheld rather than scored.

Record regression-prone areas and any acceptance criterion the document leaves
too vague to test. Feed the status counts to the script for the alignment
score; undocumented rows count as overbuild and never raise coverage.

## Output and boundaries

Follow the fixed order in
[references/output-template.md](references/output-template.md): metadata,
Part A, Part B, one summary line. Do not reproduce personal or payment data
found in either source.

The result goes to the chat by default. Post it as a pull request comment only
when the user asks for that action, post once, and read the comment back. Do
not edit the document, the code, or the tracker.

When the recommendation is to revise, hand the missing items to `intake`; when
scope must shrink, to `work-triage`; when Part B exposes a dangerous mismatch,
to `critical-review` for the diff itself.
