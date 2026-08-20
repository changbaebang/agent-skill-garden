---
name: browser-e2e-check
description: >-
  Executes a defined browser end-to-end or smoke scenario in exactly one local,
  deployed, or production environment and returns evidence-backed PASS, FAIL,
  or BLOCKED. Use for run browser E2E, smoke test this page, verify after deploy,
  브라우저 E2E, 화면 검증, 운영 확인, or 배포 후 확인. Use e2e-test-design
  first when the route, user journey, or expected result is still unclear.
---

# Browser E2E check

Execute one defined scenario against one environment.

1. Select exactly one mode: local, deployed, or production.
2. Confirm that an available browser-control capability can inspect the page,
   interactions, console, and failed requests required by the scenario. If it
   cannot, report `BLOCKED` before claiming runtime evidence.
3. Record the target URL, expected revision, scenario, preconditions, and
   mutation boundary before opening the page.
4. Prove the target is ready:
   - local mode: the intended server and route are reachable;
   - deployed mode: deployment of the intended revision is confirmed;
   - production mode: observe only by default.
5. Establish authentication and test data. Ask the user to complete passwords,
   one-time codes, CAPTCHAs, or other secrets, then resume only after an explicit
   completion signal.
6. Perform the planned action and inspect the expected visible state. A valid
   route-load scenario may use navigation itself as the action when initial
   rendering, hydration, redirect behavior, or fatal page failure is the target.
7. Check relevant browser errors and failed requests when the environment makes
   them available.
8. Capture failure evidence before at most one controlled retry. Do not hide an
   initial failure with repeated reloads.
9. Report each scenario as `PASS`, `FAIL`, or `BLOCKED` using the evidence
   contract.

Do not mix local and deployed evidence in one result. Do not purchase, delete,
submit, send, or otherwise change durable state without explicit authorization
and suitable test data. Production checks remain observation-only unless the
user explicitly authorizes a safe mutation.

Browser execution does not authorize posting comments, uploading screenshots,
or updating external systems. Draft the evidence first and publish it only
after separate authorization.

Use [references/environment-modes.md](references/environment-modes.md) before
execution and [references/evidence-contract.md](references/evidence-contract.md)
for the final result.
