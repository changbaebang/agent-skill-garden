# Round-trips and convergence

Two situations look identical in a frequency count of `path:line` and call for
the same response, but they mean different things and are worth telling apart.

## Round-trip

The same place is raised again in a **later** round, a point closed by agreement
is reopened, or the same topic arrives pushing the opposite way.

A round-trip means the point-by-point answers are not landing. Continuing to
answer that one thread adds rounds without moving the outcome.

## Convergence

Several reviewers land on one place within the **same** round.

That is not a disagreement cycle. It is a signal that the place is genuinely
weak, and usually the strongest signal available in the whole review.

## Telling them apart

Frequency and timestamps alone cannot separate them because elapsed time does
not define where a round starts. Keep the initial request and every re-request
timestamp as explicit round marks, then compare:

- The same place in more than one marked round is a round-trip, regardless of
  which reviewer raised it.
- Distinct reviewers at the same place inside one marked round are convergence.
- One reviewer writing twice at one place inside a single marked round is also
  only `repeated`: it is one person elaborating, not a cycle and not agreement
  between reviewers.
- Without round evidence, report only `repeated` and inspect the exchange rather
  than guessing.

Round marks come from the loop itself. Each time step 3 re-requests review, keep
that timestamp; with the initial request they are the whole set.

## The response is the same

Stop answering thread by thread. Publish one comment that covers the topic:

- Each affected path, before and after.
- The options considered and what each costs.
- Which one was chosen and why.
- What evidence would overturn the choice.

Then point the individual threads at that comment and re-request review, saying
explicitly that the comment is the thing to read.

## Ending a reopened debate

When every remaining question needs information the code cannot supply, more
argument will not settle it. Return the behaviour to exactly what it was before
the change. The policy under debate is then no longer part of the change, and
the question cannot recur.

Widening it may still be the right call. It is a separate change, made when
evidence exists.
