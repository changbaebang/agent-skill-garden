---
name: webview-performance-measurement
description: >-
  Measures page-load timing percentiles (p50/p75/p90) inside an Android webview or mobile browser by attaching over the DevTools protocol with adb, polling page storage, when the inspector cannot attach. Use for webview load time, 웹뷰 성능 측정, 안드로이드 로드 속도, inspector shows no device. Not for desktop-only profiling or reading existing traces.
---

# Webview performance measurement

Goal: a defensible load-timing number from a real Android webview, collected
without the desktop inspector. The page must already carry a timing harness
that appends samples to session storage; this skill attaches, collects, and
summarizes. It does not add instrumentation to the page.

## 1. Decide whether this measurement can answer the question

- Desktop CPU throttling does not throttle the GPU, so paint-bound changes
  (content visibility, paint skipping, layer changes) are invisible on desktop.
  A device or emulator is required for those.
- An emulator renders on the host GPU. Paint is already cheap there, so a
  paint-side gain is muted toward zero. Use it to rule out a regression; never
  to claim a gain. Gain or loss claims need a physical low-end device.
- Measure a production build. A development build is unminified and its numbers
  do not represent users. Use development only to check the harness works.
- Confirm the harness exists on the revision under test and learn its switch,
  storage key, and optional start/stop functions from the project or the
  environment profile. If there is no harness, stop and say so.

## 2. Attach directly, not through the inspector

When the inspector page does not list the device, or lists it but will not
open, skip it. Forward the device DevTools socket with adb and speak the
protocol yourself. Commands and the page-reachability options (emulator
loopback alias, proxy for physical devices) are in
[references/attach-and-poll.md](references/attach-and-poll.md).

Three facts decide whether the attach works:

- The websocket must be opened without an origin header; recent browsers
  reject DevTools sockets that carry one.
- The HTTP page list can be empty on recent browser versions. Enumerate pages
  through the protocol target list instead of concluding there are no pages.
- An embedded webview exposes a socket only if the host application enabled
  webview debugging, and its socket name differs from the standalone browser.

## 3. Poll storage, never the console

Do not enable the console or runtime event stream. It replays earlier console
history, so a stale "done" line looks like a fresh result, and the stream dies
when the page reloads. Session storage survives reloads, so reading it on an
interval is robust. Tolerate reads that fail mid-reload, and ignore a sample
list that is shorter than one already seen.

Run the bundled script with the match string, storage key, and sample count
supplied by the project or profile:
`python3 scripts/cdp_poll.py --match ... --storage-key ... --samples 100`.
It needs the `websocket-client` package at run time only.

## 4. Statistics and comparison discipline

- Use nearest-rank percentiles and say so; interpolating aggregators are not
  comparable with them.
- Compare by p50. A single run, a spike, or a thin segment is not evidence.
  Quote n beside every percentile.
- Before/after runs share the same build kind, session, capture method, and
  n. If the build differs, rebuild and collect both sides again.
- Keep the raw sample files for every run; they are the evidence, the table is
  a summary.

## 5. Report

Use [references/result-template.md](references/result-template.md). Lead with
provenance (device, browser or webview version, build kind, page, n), then the
table, then one sentence of verdict limited to what the device class supports.
Explaining which segment moved and why is a separate reading step; hand over
the raw files rather than concluding here.

## Traps

- Reading old results as new: caused by console capture; switch to storage.
- "Function is not defined": wrong revision or the harness switch is absent
  from the opened URL, not a script fault.
- Count stuck below target: the harness stopped early, the page navigated away,
  or storage was cleared. Raise the margin and reopen the page.
- Leaving the port forward in place; remove it when finished.

## Boundaries

This skill drives a local device and writes sample files in the working
directory. Opening the page on the device and writing a report are in scope.
Posting results to a tracker, document, or chat, installing packages system
wide, or changing device settings needs separate approval.
