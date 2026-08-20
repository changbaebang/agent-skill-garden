# Review routing

Choose passes from evidence in the changed paths, diff, manifests, and repository
instructions. Do not run every pass by habit.

| Pass | Select when the change includes |
| --- | --- |
| `critical-review` | Every pull-request review |
| `side-effect-check` | Shared modules, public contracts, state, cache, auth, storage, flags, routes, SSR, or cross-package consumers |
| `react-review` | React components, hooks, context, state, effects, subscriptions, or JSX behavior |
| `typescript-review` | TypeScript runtime boundaries, public types, narrowing, assertions, nullability, generics, or suppressed diagnostics |
| `nextjs-review` | App or Pages Router entries, layouts, middleware/proxy, route handlers, Server/Client boundaries, caching, redirects, or hydration |
| `hygiene-review` | Dependencies, manifests, lockfiles, exports, workspace boundaries, generated files, duplicate additions, or debug residue |

Inspect the repository before inferring the stack. A `.tsx` extension can justify
TypeScript inspection but does not by itself prove that framework-specific rules
apply. A Next.js route often needs React and TypeScript passes as well.

Examples:

- A shared provider change: critical, React, TypeScript, side-effect.
- A route-handler redirect change: critical, Next.js, TypeScript; add
  side-effect when auth, cookies, or cross-route behavior changes.
- A package update with no runtime code: critical and hygiene.
- A local presentational component change: critical and React; add TypeScript
  only when types or runtime boundaries changed materially.

If the change touches an unfamiliar domain such as cryptography, privacy,
concurrency, native integration, or accessibility, state that specialist review
is needed instead of pretending the selected passes are complete.
