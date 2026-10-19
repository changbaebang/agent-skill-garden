# Critical page sweep

A read-only health check of a fixed, representative set of pages. It classifies
the breadth of a client-side incident; it does not measure performance and it
does not replace a feature test.

## Inputs from the environment profile

- The representative page list: one direct-entry route per application plus
  the core funnel (home, listing, search, detail, cart, checkout, account).
  Each entry names the route, the application, whether login is required, and
  the checkpoint that proves the page rendered.
- The environment origins: production, the QA environment, and local.
- The monitoring dashboards used for correlation.

Keep the list outside this skill. Sample identifiers expire; verify a dynamic
sample once per run, and treat a stale identifier as a blocked fixture, not as
an incident.

## Scope

| Mode | Covers | Default use |
| --- | --- | --- |
| quick | the direct-entry routes of the representative set | an incident in progress |
| app NAME | every listed route of one application | one application looks wrong |
| full | every listed route with a verified web mapping | first baseline; periodic full check |

Unspecified scope during an incident means quick. Pick one environment per run
and never mix environments in one report. Production is the default while an
incident is open.

## Check one page

1. Navigate to the route.
2. Confirm the final URL is the expected origin and path, or a documented
   redirect. An expected login redirect is `LOGIN_REQUIRED`, not a failure.
3. Read the rendered document: the shell or body is present; it is not a
   framework error screen, 404, 500, or empty body; the route's checkpoint is
   visible.
4. Read console errors raised on this URL. First-party type or reference
   errors and failed chunk or resource loads are at least `SUSPECT`; a render
   crash, an error boundary, or a blank screen is `FAIL`; third-party script
   errors are recorded as noise and never fail a page on their own.
5. Record the result and move to the next route.

Never change state: no likes, cart additions, payments, saves, or logout. A
route that needs prior state (checkout after cart) is `FLOW_REQUIRED` when
entered directly; walk the flow only when the person asks for it, and never
submit a payment.

## Classification

| Result | Meaning |
| --- | --- |
| `PASS` | expected shell and checkpoint rendered; no fatal error |
| `DEGRADED` | usable, but with first-party errors or failed resources |
| `FAIL` | blank screen, error screen, render crash, or missing checkpoint |
| `LOGIN_REQUIRED` | stopped at the normal login flow |
| `BLOCKED_FIXTURE` | the dynamic sample or test data is stale or missing |
| `FLOW_REQUIRED` | needs prior user state |
| `NOT_WEB` | no browser-verifiable mapping for this entry |

## Read the pattern

- Several applications fail at their entry route: shared shell, CDN, gateway,
  authentication, or a shared provider.
- Several routes of one application fail: that application's deployment,
  backend-for-frontend, or provider.
- One route fails: route, data, or feature flag.
- One dynamic sample returns 404: blocked fixture first; a static route's 404
  is different.

The sweep alone never declares an incident. Correlate with the incident
dashboard first (request volume, error rate and codes, latency on the same
routes and minutes). A performance dashboard narrows the affected client or
platform; a single maximum on one platform, a percentile without a sample
count, or one spike is not incident evidence.

## Report

```markdown
## Critical page sweep

- Environment: production | qa | local
- Scope: quick | app:{name} | full
- Checked at: YYYY-MM-DD HH:mm ({declared time zone})

| Tier | Route | Final URL | Visual | Console | Result | Note |
| --- | --- | --- | --- | --- | --- | --- |

### Assessment
- Breadth: none | shared | app:{name} | route-only
- Failed:
- Blocked / not web:
- Next evidence to inspect:
```

Always report the number of routes checked and the totals per result, even when
everything passed. Close the browser tabs the sweep opened.

## Out of scope

- Re-measuring performance percentiles.
- Click-through feature tests and regression suites.
- Native deep-link verification; a browser pass does not stand in for it.
