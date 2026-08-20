# React correctness checklist

## Render and state

- Components and hooks remain pure during render.
- Values derived from props or state are calculated instead of copied into
  synchronized state unless an independent snapshot is intentional.
- State is owned at the level that defines its lifetime.
- Keys match entity identity and do not accidentally preserve or reset state.
- Functional updates are used when the next value depends on prior state across
  queued updates.

## Effects and external systems

- The Effect synchronizes with an external system rather than deriving render
  data or handling a specific user event.
- Dependencies match values read by the Effect; workarounds do not hide stale
  closures.
- Timers, event listeners, observers, subscriptions, and requests are cleaned up
  or made obsolete when dependencies change or the component unmounts.
- Async completion cannot commit stale data after identity, route, or query
  inputs change.
- Setup remains safe under remount and development Strict Mode behavior.

## Hooks and composition

- Hooks are unconditional and called only from React components or hooks.
- Custom hooks do not conceal expensive global listeners, stores, or service
  creation that multiply with each consumer.
- Context provider values do not unintentionally change semantics or trigger a
  measured broad rerender.

## User interaction

- Controlled inputs preserve user edits and do not oscillate with external
  state.
- Event ordering, disabled state, focus, and keyboard behavior remain reachable.
- Interactive elements preserve names, roles, and required semantics.

Primary references:

- [React: You Might Not Need an Effect](https://react.dev/learn/you-might-not-need-an-effect)
- [React: Components and Hooks must be pure](https://react.dev/reference/rules/components-and-hooks-must-be-pure)
- [React: exhaustive-deps](https://react.dev/reference/eslint-plugin-react-hooks/lints/exhaustive-deps)
