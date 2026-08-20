---
name: e2e-test-design
description: >-
  Designs a page- or journey-based end-to-end test plan from code changes,
  routes, consumers, preconditions, and expected user-visible behavior. Use for
  design E2E scope, write an E2E plan, E2E test cases, E2E 범위, E2E 테스트 설계,
  or 배포 전 검증 시나리오. This skill plans verification only; it does not
  operate a browser, create test data, or publish evidence.
---

# E2E test design

Turn a change into a small set of executable user journeys.

1. Read the change, request, or incident evidence before proposing scenarios.
2. Trace changed code to actual consumers, routes, and visible user actions.
3. Record environment, revision, authentication, device, flags, query
   parameters, and test-data preconditions.
4. Check that each proposed entry route and transition exists in the current
   code or supplied runtime evidence.
5. Prioritize scenarios:
   - P0: the changed behavior or a release-blocking regression path;
   - P1: an important adjacent state or boundary;
   - out of scope: unrelated exploration or low-value duplication.
6. Write each scenario as entry state, user action, expected observable result,
   and required evidence.
7. Mark missing deployment, credentials, data, or environment facts as blockers
   instead of inventing them.

Do not count opening a page as an end-to-end scenario. At least one meaningful
interaction and assertion must connect the entry point to the changed behavior.

Use [references/test-plan.md](references/test-plan.md) for the output contract.
Hand the accepted plan to `browser-e2e-check` for execution.
