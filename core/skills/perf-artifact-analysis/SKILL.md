---
name: perf-artifact-analysis
description: >-
  Reads existing performance artifacts (HAR, browser traces, profiler exports,
  console timing, recordings), strips noise from before/after deltas, and
  attributes the bottleneck. Use for read this trace, check this HAR, 성능 산출물
  판독, before/after 비교, or 병목 찾기. Not for new measurements, bundle sizing,
  or report writing.
---

# Performance artifact analysis

The artifacts already exist. This workflow reads them and stops. Collecting a
new measurement is a separate step, and so is writing anything up.

## Gate: provenance before reading

A precise reading of a contaminated artifact is a confident wrong answer.
Before interpreting anything, confirm these facts for every artifact:

| Fact | Why it decides the reading |
| --- | --- |
| Build: production build or development server | Development servers inflate style injection and script-parse phases; levers that look large there often vanish in production. |
| Environment: isolated or shared | A shared test environment carries other people's concurrent changes and backend load; its deltas belong to nobody. |
| Device and viewport | A phone viewport and a desktop viewport are different measurements, not one measurement at two sizes. |
| Throttling: CPU multiplier and network profile | A before/after pair recorded under different throttling is void. |
| Sample count per run | One run is an anecdote. |

If any fact is unknown, ask before reading. If the device or the metric
definition changed between the before and after runs, say that the delta cannot
be attributed to code, and stop there.

## Read each artifact for what it can prove

Every artifact has deterministic fields and noisy fields. Build the conclusion
on the deterministic ones only. Field names, formulas, and synthetic examples
are in [references/artifact-readings.md](references/artifact-readings.md).

**Request logs (HAR).** The initiator call stack is deterministic: it proves
which code issued a request and at which lifecycle point (render, event
handler, preload). Per-request duration is server and network noise; never
judge an optimization by it. Count requests per endpoint to prove cache parity
and the absence of duplicates. Read compressed and raw sizes together: a short
download of a large raw script is a parse-and-execute cost, not a download cost.

**Browser traces.** Separate extension and third-party scripts from the
application before summing CPU time, or the application is overcharged. Anchor
time zero to a user-timing mark present in both runs and compare relative times.
Reconstruct function self-time from the sampled profile and attribute by leaf
function; native leaves (synchronous cookie or storage reads, forced style and
layout) are where a single long block usually hides. Distinguish a forced
synchronous reflow, which is a lever, from the one layout the page needs anyway,
which is not.

**Console timing output from an instrumentation harness.** The marks form a
waterfall of absolute times from navigation start. Segments may carry different
sample counts; distrust tail percentiles of thin segments. Before calling empty
output a bug, confirm the harness exists on the revision under test and that
the query switch you set is one the harness actually parses. Know which percentile
formula the harness uses and never compare its numbers with an aggregator that
uses the other one.

**Aggregated reports and dashboards.** Identify what each column truly measures,
including the anchor it subtracts; anchor-based metrics usually include time that
belongs to another screen or to the native shell. A metric-definition change
splits the series: do not draw a trend line across it. A bimodal raw
distribution signals anchor-detection failure, not two user populations; exclude
those runs. The same dataset exported twice is one data point. A single-run
difference is not an effect when re-analysis of the same recording does not
reproduce the value.

**Recordings.** Tell a blank screen from a spinner; they implicate different
phases. Pair a recording with a trace before attributing anything to it.

`scripts/har_summary.py` classifies requests by party, initiator, and
raw-versus-transfer size. `scripts/segment_delta.py` computes per-segment
percentiles under either formula, flags thin segments, and subtracts the
segments you mark as noise.

## A delta is not an effect

Subtract backend and network variance from the total before claiming a
contribution. Then verify that every mark expected in the waterfall is present
in both runs: a missing mark is a truncated segment, which reads as faster and
is not.

## The environment flips the bottleneck

A desktop with CPU throttling is a model of the target, not the target.
Synchronous native work that dominates a low-end device can be invisible on a
desktop, and layout that dominates the desktop can be marginal on the device.
Treat any desktop-throttled conclusion about a mobile bottleneck as a hypothesis
until one trace from the target device confirms it.

## Stop rules

This workflow invites over-analysis by construction. Depth of analysis is not
certainty of conclusion: when the root attribution is unconfirmed, every lever
built on it is a hypothesis.

- Before proposing a lever or filing it in the tracker, obtain one cheap
  confirmation on the target device. One remote trace separates CPU from network in minutes.
- Do not settle "how it behaves now" by reading code alone. Global style
  resets, base stylesheets, and upstream guards change the outcome without
  appearing in the file; one browser measurement settles it.
- Ship the clean 80 percent. Do not chase the remaining 20 with
  disproportionate risk.
- When one problem is spawning several documents, tracker items, or workflows,
  stop and ask whether the attribution is confirmed or still a hypothesis.

## Report

Conclusion first, then the one or two deterministic signals behind it, then what
was subtracted as noise and why, then `confirmed` or `hypothesis`. A hypothesis
ships with the single cheap measurement that would confirm it. Use
[references/output-template.md](references/output-template.md).

Reading artifacts does not authorize writing a report, document, or tracker
item. Produce those only when the user asks for them.
