---
name: side-effect-check
description: >-
  Traces consumers, runtime paths, and regression risks introduced by a code
  change before review or release. Use for shared modules, state, API contracts,
  routes, caches, authentication, storage, feature flags, SSR, 영향도, 부작용,
  side effects, or what else can this break. Read-only by default.
---

# Side-effect check

## Establish the change

Confirm the base, head, committed diff, and working-tree diff. Preserve the
working tree and distinguish changed behavior from pre-existing behavior.

## Trace consumers

For every changed exported symbol, contract, state key, route, or side effect:

- find direct imports and callers;
- follow re-exports, wrappers, adapters, providers, and hooks;
- inspect server and client entry points when relevant;
- inspect cache keys, invalidation, storage, session, flags, analytics, and navigation;
- identify other applications or packages that consume the same boundary;
- state the trigger and expected failure mode for every claimed risk.

Prefer structured language or dependency tooling. If using text search, include
aliases and re-export paths rather than relying on one symbol search.

## Verify and report

Run focused tests and runtime checks when feasible. Mark unavailable environments
as blocked. Report consumer, evidence, behavior change, risk, verification, and
residual risk. If no additional path is found, say so explicitly.

This skill does not commit, push, publish comments, deploy, or update trackers.
Use [references/impact-map.md](references/impact-map.md) for coverage.
