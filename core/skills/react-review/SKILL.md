---
name: react-review
description: >-
  Reviews React changes for concrete correctness and lifecycle defects in
  rendering, state, effects, hooks, subscriptions, async work, identity, and
  accessibility. Use for React review, component review, hooks review, useEffect,
  stale state, rerender, or JSX behavior. Ignore speculative memoization and
  style-only advice.
---

# React review

Review changed React behavior in the context of its callers and rendered user
flow. Read [references/checklist.md](references/checklist.md) and apply only the
sections triggered by the change.

Prioritize reachable failures:

- render-time side effects or mutation that violate component purity;
- redundant or conflicting state that can become stale;
- Effects used for derived values or interaction-specific work;
- stale closures, incorrect dependencies, missing cleanup, duplicate
  subscriptions, and async races;
- identity or key mistakes that preserve or reset state incorrectly;
- hook order violations and conditional hook calls;
- provider or context changes that alter behavior for existing consumers;
- accessibility defects that prevent an actual interaction.

Do not recommend `useMemo`, `useCallback`, or component splitting without an
observed or strongly evidenced cost. Do not flag an Effect merely because a
different implementation is possible. Trace what causes it to run and what
external system, event, or state transition it synchronizes.

For each candidate, prove the trigger, stale or duplicated behavior, affected
consumer, and minimal fix. Follow the caller's severity and output contract when
this is selected by `pull-request-review`.
