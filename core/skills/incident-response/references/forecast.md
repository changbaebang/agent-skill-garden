# Weekly risk forecast

A personal, read-only forecast of which customer-visible areas are most likely
to fail in the coming week, and a grade of the previous forecast once the week
has ended. Every connected system is read-only in this mode.

## Modes

- `forecast`: the coming Monday through Sunday.
- `grade`: the most recent ungraded forecast whose window has closed.
- `refresh`: revise an active forecast only when a material schedule or change
  has appeared, and keep the original for grading.

Infer the mode from the request. For recurring runs, persist forecast
identifiers, evidence links, observation timestamps, and grades in the run's
memory file. Never store customer identifiers or copied message bodies.

## Collect evidence

Use the team's declared time zone for every boundary and verify every date and
weekday programmatically.

1. Scheduled exposure: releases, migrations, operational changes, campaigns,
   traffic events, and payment changes recorded in the tracker, the wiki, or
   confirmed in team channels. Prefer direct links over search summaries.
2. Change exposure: changes merged to the default branch in the preceding
   fourteen days and changes scheduled inside the window. Prioritize checkout,
   payment, pricing, promotion, discovery, authentication, routing,
   server-side rendering, ranking, API contracts, and infrastructure
   boundaries. Separate merged code from open or planned work.
3. Historical incidents: incident channels and postmortems, then bug-report and
   customer-feedback channels, over the preceding ninety days by default. Group
   repeated reports into one incident by symptom, domain, and time window.
4. Personal context: include the person's own work only when it changes
   exposure inside the window. Authorship alone raises nothing.

A source that is unavailable is named as missing. Missing evidence never
becomes a positive claim.

## Build the forecast

Cluster by customer-visible domain (campaign page, pricing and coupons, order
and payment, navigation and rendering, ranking and data freshness), not by team
ownership. For each candidate:

1. Write one falsifiable outcome and a concrete observation window.
2. Deduplicate historical incidents; count incidents and distinct active weeks.
3. Score with `scripts/risk_score.py score` using the components below.
4. Keep the top five candidates with a score of 25 or more. Never raise a score
   to fill the list.
5. State the main current exposure and two or three precedents with links.
6. Add one to three prechecks that could falsify or mitigate the prediction.

Render the score as `risk n/100`. Add a percentage only after at least eight
graded, decidable predictions exist for that domain.

## Score components

`risk = recurrence + exposure + change + blast_radius + observability - uncertainty`, clamped to 0-100.

| Component | Range | Anchors |
| --- | --- | --- |
| recurrence | 0-25 | 0 none in 90 days; 8 one incident; 14 two across two weeks; 20 three or four across two weeks; 25 five or more across three weeks |
| exposure | 0-25 | 0 nothing confirmed; 8 routine deployment or low-reach campaign; 15 major campaign, migration, or payment change; 20 two high-exposure events within four hours; 25 three or more overlapping, or one exceptional event plus a critical-path change |
| change | 0-20 | 0 none; 6 isolated and guarded; 12 customer-path behavior or contract; 16 cross-service, routing, rendering, pricing, order, or payment boundary; 20 critical path with incomplete validation or rollback uncertainty |
| blast_radius | 0-15 | 3 narrow cohort; 7 one major journey or platform; 11 broad discovery, promotion, or ordering; 15 payment, login, ordering, or all-user availability |
| observability | 0-10 | 0 clear prechecks, dashboards, alerts, rollback evidence; 4 partial monitoring; 7 known blind spot or delayed customer signal; 10 no reliable detection |
| uncertainty | 0-15 | 0 dates and change state confirmed by primary sources; 5 one claim rests on chat only; 10 schedule or deployment state ambiguous; 15 key source unavailable or mostly inference |

Open pull requests are not merged changes. QA-only, policy-only, and
customer-specific reports do not count toward recurrence.

Bands: 70-100 very high, 50-69 high, 25-49 watch, below 25 omitted.

## Grade

After the window closes:

1. Re-read incident, bug, feedback, deployment, and rollback evidence for the
   exact window.
2. Grade each prediction: `hit` (outcome and severity occurred), `partial`
   (domain and symptom matched, severity or window did not), `miss` (reliable
   observation exists and the outcome did not occur), `undecidable` (sources
   unavailable or ambiguous).
3. Link the evidence; deduplicated reports count once.
4. Report precision with `scripts/risk_score.py grade`: strict is hits over
   decidable, broad is hits plus partials over decidable, undecidable is shown
   separately and stays out of the denominator.
5. Record one adjustment for the next run. Never rewrite the original forecast
   or its score.

Give each forecast a stable identifier such as `F-YYYY-Www-NN` and store the
issue time, window, outcome statement, component scores, evidence links, grade,
and grading time.

## Output

```text
Risk forecast — YYYY-MM-DD to YYYY-MM-DD · personal
Observed: YYYY-MM-DD HH:mm ({declared time zone})

{band} {domain} · risk nn/100 · {observation window}
{one falsifiable outcome}
└ This week's exposure: {schedule or merged change}
└ Evidence: {n deduplicated incidents / n active weeks, representative links}
└ Precheck: {item}

Change map: {scheduled events and merged changes}
Sources not checked: {unavailable or ambiguous}
Scorecard: {issued, graded, cumulative strict and broad precision}

Personal reference only; nothing was posted to any channel.
```

## Safety boundary

- Never send or draft messages, replies, reactions, or mentions.
- Never create, update, transition, or comment on tracker records.
- Never review, comment on, merge, or modify repository content.
- Never declare an incident, create a channel, or change monitoring.
- Never expose personal data, order numbers, user identifiers, or private
  message bodies. Links and short paraphrases only.
