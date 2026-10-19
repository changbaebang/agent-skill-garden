# Report shape

Write the report in the language the user used. Keep the section order; a
reader who only has thirty seconds needs the risks first and the interval
above them.

```text
Production change report
Interval:  YYYY-MM-DD HH:mm ~ YYYY-MM-DD HH:mm (zone)
Basis:     production branch merge | production deployment
Scope:     owner/repo (branch), owner/repo (branch)
Totals:    N repositories changed · N merges · N leaf requests expanded
```

Then, in order:

1. **Risks at a glance** — prioritized high and medium items, each with
   `risk · mitigation · watch` and links. At most five; group the rest.
2. **Notable changes** — 8 to 12 user-visible or operational outcomes in the
   headline shape:

   ```text
   What changed, as the user or operator experiences it (links)
   • core mechanism or cause
   • activation condition, limit, rollback, or observation point
   ```

3. **Per repository** — merge count, grouped details, and
   `internal maintenance: N` for every changed repository. Mark wrappers,
   `leaf mapping incomplete`, `reverted`, and `flag off` inline.
4. **No changes** — repositories in scope with zero eligible merges.
5. **Not verified** — missing diffs, unexpanded wrappers, unavailable checks or
   deployment records, and any boundary that was interpreted rather than given.

## Empty result

```text
Production change report
Interval:  ...
Basis:     ...
Scope:     ...
No changes reached the production branch in this interval.
```

Do not fill an empty report with open pull requests, planned work, or changes
from an adjacent period.

## Wording rules

- Headlines describe outcomes; the title of the pull request is evidence, not
  the headline.
- "Faster", "safer", "more stable" require a measurement and a source.
- A flag-off change is described as shipped code awaiting activation.
- A reverted change is described as reverted, with both links.
- Inferences are marked as such; unavailable evidence is listed, not glossed.
