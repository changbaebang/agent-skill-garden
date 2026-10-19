# Gates and decision

## Hard gates

Any failure blocks approval. Each needs evidence in the description, the diff,
or a linked test, run, or document.

| Gate | Pass looks like | Common failure |
| --- | --- | --- |
| Requirement implemented | The described change is present in the diff and matches the linked ticket | Description promises behavior the diff does not contain |
| No obvious correctness bug in a changed critical flow | Changed branches of a critical path are coherent on a read-through | Inverted condition, unreachable fallback, swallowed error |
| Failure preparedness where needed | A flag, fallback, rollback, or equivalent is named for a risky change | A user-facing or data-touching change with no way back |
| Verification evidence present | Test code, a test run, a recorded manual check, or an explicit rationale for why none is needed | "Tested locally" with nothing attached |
| No debug leftovers | No temporary logging, commented-out code, hard-coded test values | A console statement or a stubbed response left in |
| No high-impact typo | Identifiers, imports, environment keys, API fields, and paths spelled as their definitions | A misspelled key that silently reads undefined |

## Soft gates

Failures become comments, not blocks.

- Title and description clarity, including enough context for a reviewer who
  did not see the ticket.
- Readability and alignment with the repository's conventions.
- Documentation updated where behavior or configuration changed.
- Impact analysis: scope, expected effect, risk points, mitigation.
- Tier rationale: present, specific to this change, consistent with the scale.

## Acknowledgement items

- A QA-passed claim carries a link to the run or record. Without it, record
  the claim as unverified.
- A tier should cite the repository's policy or rubric when one exists.

## Typo policy

| Impact | Decision |
| --- | --- |
| Changes build, runtime, or behavior: symbol, import, environment key, API field, path | request changes |
| Comment, document, pull-request text, non-critical copy | comment |

Always report the exact wrong token, the expected token, and the concrete
impact. A list of misspellings with no impact statement is noise.

## Branch classes

| Class | Default patterns | Strictness |
| --- | --- | --- |
| production-bound | default branch, `release/*`, `production/*`, `hotfix/*` | Hard-gate failure is a request for changes |
| integration | develop, staging, QA, feature integration branches | WIP and temporary mocks may be downgraded to a comment |

Read the repository's branching notes before trusting the defaults. A long-lived
integration branch that deploys to production belongs in the first class even
when its name says otherwise.

## Decision matrix

| Observed | Decision |
| --- | --- |
| Production-bound, any hard gate fails | request changes |
| Any branch, a clear severe and immediate risk | request changes |
| Only soft-gate issues | comment |
| Integration branch, WIP or mock issue with mitigation and low immediate risk | comment with downgrade record |
| All hard gates pass with reasonable confidence, no meaningful open concern | approve |

## Downgrade record

A WIP or mock issue on an integration branch is downgraded to a comment only
when the required actions name all three:

1. the follow-up ticket;
2. the owner;
3. the target branch or date by which it is resolved before production.

Missing any one of them, the issue stays at its original severity.

## Confidence language

- "pass" means evidence was seen.
- "fail" means evidence was sought and the gate is not met.
- "not verifiable from here" means the evidence cannot be reached in this
  session. It counts against the gate and is reported as a limitation, never
  as a pass.
