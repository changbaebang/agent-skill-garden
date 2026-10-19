# Recognize and declare

## Recognize: is this an incident?

Reports arrive through monitoring, customer feedback, bug-report channels, and
colleagues. Correlate what arrived in the last thirty minutes by journey,
symptom, and affected target before deciding. Repeated reports from one
reporter count once; repeated reports from different people do not get
excluded.

| Signal | Weight |
| --- | ---: |
| An employee states a current outage, broad failure, or many affected customers | +4 |
| The same symptom from three or more distinct reporters | +4 |
| The same symptom from two distinct reporters | +2 |
| A core journey is blocked (checkout, order creation, login, product detail or listing) | +3 |
| Unavailable, 4xx/5xx, blank page, infinite loading, or a dead control | +2 |
| Wording says all, repeated, simultaneous, many customers, or reproduced | +2 |
| A production URL, screenshot, or recording exists | +1 |
| An owner reproduces it or confirms a monitoring or server anomaly | +3 |
| Limited to one user, one product, or one device | -2 |
| Confirmed policy or operations configuration, not a defect | -3 |
| Already marked normalized, completed, or resolved | close the candidate |

Read 0-3 as observe, 4-6 as suspected (tell the person), 7 or more as
"consider declaring". Escalate at once regardless of score for duplicate
payment, incorrect monetary calculation, lost orders, personal-data exposure,
or broad login failure. When an incident channel already exists for the
symptom, link the report to it instead of recommending another.

Classify where the customer sees the failure: web page, in-app web view,
native app, admin or partner surface, backend only, or unknown. For unknown,
ask only for the failing URL or screen, the platform, web view or native, and
the failure type.

## Thirty-second check

- [ ] Is it an incident, not a one-off spike, a single user, or already recovered?
- [ ] Impact in one line: which journey, which customers, what symptom.
- [ ] Is the owning service known? If not, declare through the generic path and
      let the responders assign it.

## Declaration quality rubric (100 points)

| Item | Points | Standard |
| --- | ---: | --- |
| Impact clarity | 30 | Customer or business impact is visible in one or two sentences |
| Title accuracy | 20 | Service, symptom, and scope appear in the title |
| Path choice | 20 | Service-specific path when the service is known, generic path when not |
| Announcement readiness | 15 | A one-to-three-sentence announcement can be posted immediately |
| Handover readiness | 15 | Roles and a first status update are possible on entering the channel |

- 85 or more: declare now.
- 70 to 84: add one line of impact or sharpen the title, then declare.
- Below 70: re-examine whether this is an incident, or get a second opinion.

## Title shape

```text
{service or feature}: {symptom} ({scope or severity hint})
```

Avoid titles that carry no impact or scope: "it is broken", "urgent, please
check", or a bare error code.

## Declaration paths

The environment profile names which paths exist. Typical options, in order of
preference:

1. The incident bot command, which creates the tracker record and the channel
   together. Choose the service when known, otherwise the generic service.
2. A record created directly in the tracker's incident project. The creator is
   the reporter and the default communications lead until roles are agreed.
3. An emergency mention in the announcement channel, used when the first two
   are unavailable. Move all recovery conversation into the incident channel as
   soon as it exists.

Emergency mention body:

```text
[one-line summary]
Impact: (for example, checkout page does not load; product detail returns 5xx)
Detected by: (alert, customer report, monitoring)
```

## Immediately after declaring

1. Enter the incident channel; read the pinned messages and the topic.
2. Acknowledge, within a minute when on call.
3. Agree roles: commander, communications lead, operations lead. One person may
   hold two; say so in the channel.
4. Post the first status update within fifteen minutes using the template in
   [response.md](response.md).
5. Begin the gather step and move to the respond stage.

Recovery conversation stays in the incident channel. The announcement channel
carries summaries. Personal data and customer identifiers stay out of both.

## Output block

```markdown
## Declaration checklist — {title}

### Quality score
- Score: {n}/100
- Improve: {up to three points}

### Recommended path
- [ ] {path} — service: {service | generic}

### After declaring
- [ ] Incident channel entered and roles agreed
- [ ] Tracker record reporter confirmed
- [ ] First status update within 15 minutes

### Announcement draft
{one to three sentences, confirmed facts only}
```
