# Evidence contract

## Status definitions

- `PASS`: every planned action completed and every expected observable result
  was confirmed under valid preconditions.
- `FAIL`: the scenario reached the tested behavior and an expected result did
  not occur, or a relevant browser error or request failure was observed.
- `BLOCKED`: deployment, route, authentication, data, browser access, or another
  prerequisite prevented a valid test.

Opening a page, seeing a successful HTTP response, or capturing a screenshot is
not enough for `PASS` unless that is the complete planned assertion.

## Result template

- Environment and URL:
- Tested revision:
- Scenario:
- Preconditions:
- Actions performed:
- Expected result:
- Observed result:
- Browser errors or failed requests:
- Evidence:
- Status: `PASS`, `FAIL`, or `BLOCKED`
- Remaining risk:

For failures, capture the first observed state before retrying. Distinguish a
product failure from a test-environment failure. Treat console errors and failed
requests as failures only when they are relevant to the scenario; record
unrelated background noise as remaining risk. Keep screenshots and traces out
of the repository unless the repository explicitly owns those artifacts.
