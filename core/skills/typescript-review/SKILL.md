---
name: typescript-review
description: >-
  Reviews TypeScript changes for runtime-relevant type-safety failures involving
  any, assertions, nullability, narrowing, public contracts, suppression comments,
  and async values. Use for TypeScript review, type safety, 타입 리뷰, any,
  ts-ignore, double assertion, or strictness review. Do not flag type preference
  without a concrete failure path.
---

# TypeScript review

Treat types as claims about runtime values. Read
[references/checklist.md](references/checklist.md) and trace each candidate from
its source boundary to the consumer that trusts the type.

Investigate:

- `any`, double assertions, broad assertions, and non-null assertions that hide
  reachable runtime mismatch;
- suppression comments that conceal an error without a narrow reason;
- missing null, optional, unknown-enum, or error-state handling;
- incorrect narrowing or non-exhaustive discriminated unions;
- public types that misrepresent serialized or external data;
- unhandled promises and async return contracts;
- type duplication that can drift across a shared boundary.

The presence of `any`, `as`, `!`, or `@ts-expect-error` is a search signal, not a
finding. Report it only when the unchecked value reaches an operation that can
fail or corrupt behavior. Prefer `unknown` plus validation at untrusted
boundaries, but do not demand extra runtime parsing for values already guaranteed
by a verified internal contract.

Test-only shortcuts are normally non-blocking. Escalate them only when they hide
a production contract mismatch, make the test incapable of detecting the target
failure, or create flaky runtime behavior.

Follow the caller's severity and output contract when selected by
`pull-request-review`.
