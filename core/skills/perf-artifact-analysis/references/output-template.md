# Analysis output

Lead with the conclusion. Do not walk through the artifacts one by one.

```markdown
Artifacts : <file names or pasted output>
Provenance: build <production|development> · environment <isolated|shared> ·
            <device, viewport> · throttling <CPU multiplier, network profile> · n=<per run>

Conclusion: <one sentence>
Evidence  : <one or two deterministic signals: initiator stack, mark integrity,
            self-time attribution, request count parity>
Noise     : <what was subtracted from the delta and why>
Confidence: confirmed | hypothesis
            <if hypothesis: the single cheap measurement that would confirm it>
```

Rules for the block:

- The provenance line is mandatory. If a field is unknown, write `unknown` and
  say the reading is conditional on it.
- Evidence names the deterministic field, not the noisy one. "Duration fell
  from 791 to 715 ms" is not evidence; "one request per side, issued from the
  click handler instead of the render" is.
- A delta reported without its subtracted noise is incomplete.
- `confirmed` requires either a target-device trace or mark integrity on both
  runs plus a subtracted noise term. Everything else is `hypothesis`.
- Do not append a report, ticket text, or document unless the user asked for
  one.
