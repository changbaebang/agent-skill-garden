# TypeScript safety checklist

## Boundaries

- Parse or narrow user input, network data, storage, environment variables, and
  untyped library results before trusted use.
- Confirm that generated or shared types match the effective runtime contract.
- Keep public types minimal and stable; avoid exposing implementation details
  that consumers may start depending on.

## Escape hatches

- `any` does not propagate unchecked values into property access, calls, or
  assignments.
- Assertions are backed by an invariant visible in code or verified contract.
- Double assertions do not bridge incompatible shapes.
- Non-null assertions are unreachable for nullish runtime values.
- `@ts-expect-error` is narrow, intentional, and fails when the expected error
  disappears; `@ts-ignore` does not silently hide unrelated failures.

## Control flow and data modeling

- Discriminated unions handle new and unknown variants conservatively.
- Optional and nullable fields are not collapsed into a valid state by default.
- Narrowing remains valid after mutation, callbacks, and asynchronous work.
- Exhaustive branches do not rely on unsafe fallthrough.

## Async and utility types

- Promises are awaited, returned, deliberately detached with error handling, or
  otherwise observed.
- Callback and generic constraints preserve the values that consumers need.
- Duplicated types are derived from a stable source when independent copies
  would drift.

Primary references:

- [TypeScript: The Basics](https://www.typescriptlang.org/docs/handbook/2/basic-types.html)
- [TypeScript: Narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html)
- [TypeScript declaration Do's and Don'ts](https://www.typescriptlang.org/docs/handbook/declaration-files/do-s-and-don-ts.html)
