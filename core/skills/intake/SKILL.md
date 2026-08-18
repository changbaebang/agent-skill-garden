---
name: intake
description: >-
  Turns a rough request, issue, meeting note, design, or pasted context into a
  reviewable work definition with goal, scope, acceptance criteria, unknowns,
  risks, and next steps. Use for intake, scope this work, define requirements,
  make acceptance criteria, 작업 정리, 범위 만들자, 요구사항 정리, or 상세하게
  정리. Draft and analyze first; do not write to trackers or external systems
  unless the user explicitly requests that write.
---

# Intake

Turn ambiguous input into a decision-ready draft before implementation or
external mutation.

## Gather evidence

1. Identify the requested outcome and who benefits from it.
2. Separate stated facts from assumptions and inferred constraints.
3. Inspect linked local context read-only when available.
4. Record missing information only when it changes scope, safety, or acceptance.

## Define the work

Produce:

- one-sentence goal;
- in-scope and out-of-scope boundaries;
- functional and non-functional acceptance criteria;
- dependencies, unknowns, and risks;
- verification approach;
- smallest safe next step.

Do not invent dates, estimates, owners, or external-system state. Label
assumptions explicitly.

## Preserve the write boundary

A request to organize, draft, or review work does not authorize creating or
updating an issue, document, message, branch, or pull request. Present the draft
first. Apply writes only when the user asks for the named action.

Use [references/output-template.md](references/output-template.md) for the
default result.
