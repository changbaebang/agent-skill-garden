---
name: api-contract-check
description: >-
  Verifies the real backend contract before client code exists and classifies
  it as implementable, blocked, or no-op. Use for check the backend contract,
  is the API ready, backend-dependent ticket, spec vs generated types, API 계약
  확인, 백엔드 준비됐나. Read-only; not for writing the client, side-effect
  tracing, or UI-only work.
---

# API contract check

A read-only readiness gate between a work item and client code. It confirms
what the backend actually serves in the target environment. It does not write
code, update the tracker, create branches, or post comments. Inside
`ticket-to-pull-request` it is the contract-gate station; it also runs alone
whenever someone asks whether the backend is ready for a change.

## Decide whether the gate applies

Run it when any of these holds:

- the work item is labelled or described as depending on a backend change,
  following a backend release, or blocked on one;
- the change touches an API client, generated types, a gateway or proxy route,
  a response adapter, or environment routing;
- the sources already disagree, or the client would otherwise have to guess a
  field, an enum value, an optionality rule, an endpoint, or a rollout state.

Do not run it because every page eventually calls an API. For pure UI, copy,
or local-state work, record `contract gate: not required` with one reason and
move on. The gate earns its cost only where a guess would become a defect.

## Collect evidence before forming an opinion

Read the work item and everything it links first. Then read the sources that
can prove the contract, in rough order of authority:

1. the backend implementation or its merged change, and what is deployed to
   the target environment;
2. the API specification for that environment;
3. the API design document and the work item's acceptance criteria;
4. the client's existing API client, generated types, and adapters;
5. recorded decisions in chat threads or handoff notes;
6. runtime routing: proxy, gateway, base path, and environment configuration.

Record each source with its version or the time you observed it. A contract
read last week is a claim about last week.

Take environment facts, such as the target hosts, where that environment's
specification lives, and the gateway or proxy configuration, from the
project's own configuration or the environment profile, or ask for them. A
missing value is a gap to report, not a value to infer.

Ask the user for missing material only when its absence can change the verdict
or the implementation shape. When new material arrives later, reopen the
verdict and update the evidence table instead of defending the earlier one.

A failed lookup is absence of evidence, not evidence of absence. Not finding a
dependency does not prove that none exists; say what you could not reach.

## A mismatch is a verdict, not a choice

When authoritative sources disagree, with the specification saying one thing,
the deployed backend another, and the generated types a third, do not pick one
silently. Record the mismatch with every source involved, classify the work as
`blocked`, and name who can resolve it. Choosing quietly moves the defect from
the gate into production, where it is far more expensive to find.

## Verify only the dimensions the work touches

Check endpoint and method, request shape, response and error shape,
authentication and session requirements, compatibility and rollout order,
client and type compatibility, and routing. Skip a dimension only when the
work item cannot be affected by it, and say so.

Do not demand that the specification host equal the client's configured host.
A proxy or gateway can make different hosts correct. Trace the effective
request route from the client to the backend instead of comparing strings.

Use [references/verification-dimensions.md](references/verification-dimensions.md)
for what each dimension must establish.

## Guardrails

- Do not invent fields, paths, response shapes, or rollout states.
- Do not bypass uncertainty with unchecked casts, broad type assertions,
  stub adapters, or speculative fallbacks.
- Do not add defensive code because it looks harmless. State the invariant,
  verify the real trigger, and add a defence only when it reduces a
  demonstrated risk without changing valid behaviour.
- Do not let "the backend team said it is fine" replace reading the contract.
  A verbal assurance is a lead to verify, not evidence.

## Return exactly one verdict

- `implementable`: the required contract is confirmed and compatible with the
  client in the target environment.
- `blocked`: a material contract detail is absent, conflicting, unreachable,
  or not deployed where the client needs it.
- `no-op`: the request is already satisfied, or the confirmed contract requires
  no client change.

Write the result with [references/verdict-template.md](references/verdict-template.md).

For `implementable`, hand the confirmed contract and source links to
`work-start`. For `blocked`, stop implementation and continue read-only
investigation only where it can shorten the block. For `no-op`, report what
already satisfies the request so the item can be closed by its owner.
