# Scoring rubric

## Eight-section checklist

A requirements document is recognized as one only when every section below can
be located in the body. Mark each as present, absent, or explicitly deferred.

| Key | Section | Present when the document states |
| --- | --- | --- |
| `background` | Background and problem | why the work exists and what hurts today |
| `goals` | Goals and non-goals | what success means and what is deliberately excluded |
| `users` | Target users and channels | who is affected and on which surfaces |
| `scenarios` | Key scenarios | the primary flows from entry to outcome |
| `acceptance` | Acceptance criteria | observable conditions that can each be verified |
| `data` | Data, API, and policy | contracts, fields, and rules, or an explicit "undecided" |
| `exceptions` | Exceptions and failures | behavior on error, empty state, timeout, and conflict |
| `impact` | Impact and regression | affected areas, flags, rollback or containment |

An explicit "undecided" or "deferred" in `data` counts as present: the author
declared the gap, which is what the section is for. A heading with nothing
under it is absent.

## Document type

- **complete**: all eight sections present.
- **draft**: at least one present, at least one absent.
- **not a requirements document**: none present, or the page is a template
  with headings only, meeting or sync notes, a collection or index page, a
  deprecated or archived copy, or an otherwise empty stub. Pass the reason as
  `not_requirements_reason` so the classification is recorded, not inferred.

## Five axes, 1 to 5, higher is better

| Key | Axis | Score 5 | Score 1 |
| --- | --- | --- | --- |
| `clarity` | Implementation clarity | tasks follow from criteria and exceptions without asking | nothing can be sized |
| `scope` | Scope fixation | in, out, and "not this time" are explicit | boundaries undefined |
| `risk` | Side-effect and regression awareness | analysis matches the blast radius of the domain | wide-impact domain, no analysis |
| `dependencies` | Dependency declaration | backend, API, design, external party, release order named | dependencies unknown |
| `ambiguity` | Freedom from ambiguity | no open markers or contradictions | open markers throughout, sections contradict |

Score the fit, not the length. A low-risk copy change with no impact analysis
can still earn a 4 on `risk`; a payment or authentication change with no
analysis earns 1 or 2. An `ambiguity` deduction names the marker (TBD, WIP, a
question left in the text) or the two passages that conflict.

## Readiness score and band

`readiness = mean(axes) x 20`, an integer from 20 to 100.

| Band | Range | Meaning |
| --- | --- | --- |
| high | 80 to 100 | development can start |
| medium | 60 to 79 | start only with the questions answered |
| low | below 60 | document revision required |

"Implement now" is eligible only when the type is complete, the band is high,
and no axis is 2 or lower. One weak axis blocks it even when the mean is high,
because the mean hides the exact thing that will stall implementation.

## Recommendation guide

Exactly one of:

- **implement now**: eligible per the rule above, open questions are minor;
- **revise the document first**: draft type, or any axis at 2 or lower, or an
  acceptance criterion that cannot be tested as written;
- **cut scope and spike**: dependencies or data contracts are unresolved and
  unlikely to resolve soon, but a smaller verified slice is available;
- **reference only**: not a requirements document, or archived.

## Alignment score

`alignment = (met + 0.5 x partial) / (met + partial + missing) x 100`, rounded
half up to an integer.

- `undocumented` rows are excluded from the denominator and reported as the
  overbuild count. Extra work never raises coverage.
- No rows at all means the score is not computable. Report that instead of a
  number.

## Running the script

```bash
python3 scripts/score_requirements.py --input review.json
python3 scripts/score_requirements.py --input review.json --format text
cat review.json | python3 scripts/score_requirements.py
```

Input, one JSON object:

```json
{
  "sections_present": ["background", "goals", "users", "scenarios",
                       "acceptance", "data", "exceptions", "impact"],
  "not_requirements_reason": null,
  "axes": {"clarity": 4, "scope": 3, "risk": 4, "dependencies": 3, "ambiguity": 4},
  "alignment": {"met": 4, "partial": 1, "missing": 2, "undocumented": 1}
}
```

`alignment` is optional; omit it when Part B is skipped. Output fields:
`document_type`, `missing_sections`, `readiness_score`, `readiness_band`,
`weakest_axes`, `implement_now_eligible`, `alignment_score`,
`overbuild_count`. The script validates ranges and key names and exits with
status 2 on bad input, so a typo cannot become a score.
