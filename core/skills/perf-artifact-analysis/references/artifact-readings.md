# Reading each artifact

Deterministic fields prove things. Noisy fields describe one run. The tables
below say which is which, and the examples are synthetic: they keep the
decision, not the original numbers.

## Request logs (HAR)

| Field | Nature | Use |
| --- | --- | --- |
| `_initiator.type` and `_initiator.stack.callFrames` | deterministic | Which code issued the request and at which lifecycle point |
| Request count per endpoint | deterministic | Cache parity, duplicate requests |
| `response.content.size` (raw body) | deterministic | Parse-and-execute cost of scripts |
| `response._transferSize` or `bodySize` (bytes on the wire) | deterministic | Download cost, compression ratio |
| `time`, `timings.wait` | noisy | Describes this run's server and network; never an effect |

Example, a prefetch toggle for the request that feeds the next route:

- Off: the request is issued from a hook inside the next route's chunk, so the
  initiator is a render frame and it cannot start before that chunk has loaded
  and mounted.
- On: the request is issued from the click handler in the current route's
  chunk, so the initiator is an event frame and it starts before the next
  chunk loads.
- Both sides show exactly one request to that endpoint: the cache was hit,
  nothing was duplicated, parity holds.
- The same two files report durations of 791 ms and 715 ms. That difference is
  server variance on a shared environment, not the effect of the toggle.

Size: read raw and transferred together. A main bundle of 930 KB on the wire
and 3.2 MB raw downloaded in under 200 ms; the cost was parsing 3.2 MB on the
main thread, not the download. A compression ratio near 3 to 4 for minified
script is normal; an outlier ratio points at a serving problem, not a code one.

`scripts/har_summary.py path.har --first-party example.com --match /api/items`
prints the party split, sizes, ratios, and the top initiator frames of the
matched requests.

## Browser traces (Chromium trace event JSON)

Preprocessing that must happen before any total is quoted:

1. Separate three populations by the script URL in the call frames: the
   application, browser extensions (`chrome-extension://`, `moz-extension://`
   and similar schemes, which include developer-tools extensions), and third
   parties (tag managers, analytics). A trace that charges 1.1 s of CPU to the
   application may hold 0.5 s of extension and third-party time.
2. Fix time zero to a user-timing mark that exists in both runs, such as the
   framework's route-change or before-render mark, and compare relative times.
   Absolute trace timestamps do not line up across runs.
3. Match network events by request identifier (send-request to finish), not by
   URL alone; the same URL can be fetched more than once.

Self-time attribution from sampled profile chunks:

1. Each chunk carries the node tree, the sample node identifiers, and the time
   deltas. Timeline position of sample `k` is `startTime + sum(timeDeltas[0..k])`.
2. Attribute each sample to its leaf node and sum per function; the leaf name is
   what identifies native cost such as a synchronous cookie read, a storage
   read, or style recalculation forced from script.
3. Compare per-function self-time against the length of the long task it sits
   in. A single 1.4 s block whose leaf is a native cookie read for roughly 64
   percent of its samples is a cookie-access problem, not a rendering one.

Layout: a large layout total is not automatically a lever. A forced synchronous
reflow shows a script call frame that triggered style and layout mid-task and
disappears when the trigger is removed. The one layout the content needs stays
after the fix and is not a lever. In one synthetic case two forced reflows of
450 ms together vanished after a fix, while 360 ms of remaining layout was the
page's own.

## Console timing output from an instrumentation harness

The marks are absolute times from navigation start and form a waterfall:

```text
navigation start → first byte → document parsed → script booted → component mounted
→ data requested → data received → state updated → render dispatched
→ section committed → above-the-fold painted
```

- Each segment can have its own sample count; the harness prints it per
  segment. Do not quote a p90 from a segment with five samples.
- Nearest-rank percentile: sort ascending, take `sorted[ceil(n * p) - 1]`.
  Linear interpolation (the default in most numeric libraries): index
  `(n - 1) * p`, interpolate between neighbours. On `1..10`, p90 is 9 under
  nearest-rank and 9.1 under linear interpolation. Numbers from the two formulas
  are not comparable.
- A section mark should be recorded when the section commits to the DOM, not
  in a deferred effect that runs after paint; moving it later contaminates the
  delta.
- Instrumentation often lives on a measurement branch only. Empty output on
  another revision is a branch mismatch, not a bug. Check which query switches
  the harness actually parses; a switch that is only tested for presence
  ignores whatever value is written after it.

`scripts/segment_delta.py --input runs.json --total end_to_end --noise backend`
computes per-segment percentiles with either formula, flags thin segments, and
subtracts the segments marked as noise.

## Aggregated reports and dashboards

- Find out which metric every column really is. A report may carry a single
  derived metric under several labels; if a column has no metric name, assume
  the report's one derived metric rather than a raw one.
- Anchor-based metrics subtract an anchor time that often spans another
  screen or the native shell. Half of the raw value can belong to someone
  else's phase. Do not read the raw value as the application's own time.
- Aggregators usually use linear interpolation and exclude outliers before
  computing percentiles. Do not compare their p50 with a harness p50.
- When the anchor definition or an exclusion rule changes, the series splits.
  Cycles on either side are different metrics; no trend line crosses the
  change.
- A bimodal raw distribution means the anchor was missed on part of the runs
  and the derived value collapsed to the full time. Exclude those cycles and
  state why.
- The same dataset can appear twice: an ad-hoc export and the later official
  cycle computed from the same recordings. Count it once.
- If re-analysis of the same recordings reproduces the value for only a
  fraction of them, single-run differences carry no meaning.

## Recordings

A blank screen and a spinner are different symptoms: a blank screen means the
shell has not painted (script boot or a blocking main-thread task); a spinner
means the shell painted and data or rendering is late. Pair the recording with a
trace from the same device before attributing either.

## Delta attribution worked example

End-to-end metric moved from 617 ms to 577 ms, a delta of -40 ms. The backend
segment moved -20 ms on its own, and the backend did not change, so that is
noise. Attributed contribution is about -20 ms, which the waterfall explains as
commit-to-paint -12 ms and commit -8 ms. All expected marks are present in both
runs, so the segments are intact and the improvement is not a truncation.
