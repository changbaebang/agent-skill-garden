# Measurement result

Report the provenance first; a number without it cannot be compared with
anything.

```markdown
Target     : <device model or emulator> · <browser or embedded webview, version>
Build      : production | development   (development numbers are not representative)
Page       : <route> · harness switch <on>
Capture    : storage polling over the protocol · n=<count> per run · nearest-rank percentiles
Raw samples: <path to samples_*.json for each run>

| segment | n | p50 | p75 | p90 |
| --- | --- | --- | --- | --- |
| <field> | <n> | <ms> | <ms> | <ms> |

Verdict    : <one sentence based on p50 of the headline segment>
Scope      : emulator → "no regression" at most | physical low-end device → gain or loss
```

Rules:

- Compare runs by p50. Single runs and spikes are not evidence.
- A/B runs share the same build, same session, same capture method, same `n`.
  If the build differs, rebuild and collect both sides again.
- Quote `n` with each percentile; a thin segment has no credible p90.
- State the percentile formula. These are nearest-rank; aggregators that
  interpolate are not comparable.
- An emulator renders with the host GPU. If a paint-side change shows no
  difference there, write "no regression on emulator" and stop; do not claim a
  gain or its absence for real devices.
- Attribution of a before/after delta (which segment moved, what was noise) is
  a separate reading step; hand the two raw sample files to it rather than
  concluding here.
- The measurement itself does not authorize a report, document, tracker
  comment, or message. Produce those only when asked.
