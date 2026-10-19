# Deployment risk signals

Judge risk from the changed behavior, its blast radius, and the controls that
are verifiably present. Size of the diff is not a severity. A bug fix is not
automatically low; the flow it touches and the mechanism it changes decide.

## High

A plausible failure corrupts payment or order state, breaks authentication or
accounts, exposes data, takes down a broad surface, changes data irreversibly,
or fails every client at once, and no verified flag, fallback, staged rollout,
or rollback stands in front of it.

Examples:

- payment, order state, price, coupon, settlement, or inventory mutation;
- cookie, token, session, single sign-on, identity, age verification, or
  permission checks;
- database or data migrations and destructive configuration changes;
- global routing, application shell, server-side rendering or hydration,
  content delivery, or a shared API client;
- dependency or security fixes that also alter runtime behavior.

## Medium

A meaningful behavior or contract change whose impact is bounded or
recoverable.

Examples:

- API method, endpoint, request or response schema, caching, or invalidation;
- feature-flag removal, default change, or broad activation;
- fallback order, third-party integration, analytics or event collection;
- global navigation, dialogs, global event wiring, embedded-browser bridge,
  deep links, or navigation;
- scheduling and administrative controls that can publish customer-facing
  content.

## Low

Localized and readily reversible, with no cross-domain behavior change
identified.

Examples:

- narrow spacing, copy, or theme corrections;
- tests, documentation, lint, quality-gate cleanup, dead-code removal;
- a refactor with convincing behavior-preservation evidence.

## Hold

Use `hold` when the diff or the wrapper's leaf mapping is unavailable, the
body contradicts the changed files, or the live flag or deployment state cannot
be verified. Say exactly which evidence is missing. `hold` is a statement about
evidence, not a softer `medium`.

## Mitigations count only when verified

- default-off or staged feature flag, with the default observed;
- server or client fallback and timeout behavior, seen in the diff;
- focused automated tests or deployed smoke evidence, linked;
- an explicit rollback or revert path;
- monitoring tied to the stated failure mode.

A generic green check or third-party warning noise is not a targeted
mitigation.

## Choose an observation point that can reveal the failure

- checkout or payment success and error rates;
- login and session-refresh failures;
- client error rate, error-tracker issue volume, or route rendering errors;
- API contract errors, fallback rate, and latency;
- conversion or event-volume discontinuity;
- publish failures or invalid configuration in administrative tools.

Do not derive a probability or an incident likelihood from these qualitative
levels.
