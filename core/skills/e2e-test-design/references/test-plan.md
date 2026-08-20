# E2E test plan

## Target

- Change or risk:
- Repository and revision:
- Environment:
- Entry route:
- Required account or role:
- Device or viewport:
- Feature flags and query parameters:
- Test data:
- Required browser capabilities:

## Scenario matrix

| Priority | Entry state | User action | Expected result | Evidence |
| --- | --- | --- | --- | --- |
| P0 |  |  |  |  |

## Preflight

- Confirm the route exists and note redirects or rewrites.
- Confirm the selected browser tool can collect the evidence required by the
  scenario.
- Confirm the tested revision is present in the target environment.
- Confirm required data is available without changing production state.
- Separate authenticated and unauthenticated paths.
- Identify actions that purchase, delete, submit, send, or otherwise mutate
  durable state.

## Boundaries

- Keep one scenario focused on one user-visible outcome.
- A route-load-only scenario is valid when initial rendering, hydration,
  redirect behavior, or fatal page failure is the behavior under test.
- Prefer the shortest path that crosses the changed boundary.
- Record important adjacent cases as P1 instead of expanding P0 indefinitely.
- Mark a scenario `BLOCKED` when a prerequisite cannot be established.
- Do not publish results or screenshots without separate authorization.
