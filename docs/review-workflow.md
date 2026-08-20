# Routed frontend review workflow

The review pack separates three concerns that are often mixed into one large
prompt:

1. `pull-request-review` owns current-state checks, pass selection, prior-thread
   reconciliation, the final decision, and publication boundaries.
2. `critical-review` and `side-effect-check` provide cross-cutting release and
   blast-radius analysis.
3. React, TypeScript, Next.js, and hygiene skills provide focused domain passes.

This design keeps detailed rules available without loading every checklist for
every pull request.

Install the routed review pack together so the orchestrator can delegate every
selected pass:

```bash
./scripts/install.sh --target all --scope project --root path/to/project \
  --skill pull-request-review \
  --skill critical-review \
  --skill side-effect-check \
  --skill react-review \
  --skill typescript-review \
  --skill nextjs-review \
  --skill hygiene-review
```

Review the dry run, then repeat it with `--apply`.

## Selection flow

```text
current PR state and diff
  -> read repository and path instructions
  -> always run critical-review
  -> select specialized passes from changed behavior
  -> trace context and consumers
  -> combine evidence-backed findings
  -> reconcile previous threads on re-review
  -> decide without publishing by default
```

The orchestrator reports both selected and skipped passes. This makes missing
coverage visible and prevents a `.tsx` extension or framework name from
silently turning on every possible rule.

## Research basis

The public workflow was rewritten from repeated local review experience and
cross-checked against primary sources:

- [Google Engineering Practices](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
  emphasizes design, functionality, tests, context, complete assigned scope,
  and comments about code rather than people.
- [GitHub Copilot code review](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review)
  separates repository-wide and path-specific instructions and documents that
  re-review can repeat dismissed comments. The re-review contract therefore
  compares reviewed heads and forbids new findings on unchanged code.
- [PR-Agent's public reviewer prompt](https://github.com/The-PR-Agent/pr-agent/blob/main/pr_agent/settings/pr_reviewer_prompts.toml)
  focuses findings on introduced lines, concrete scenarios, actionable issues,
  and calibrated uncertainty.
- [CodeRabbit path instructions](https://docs.coderabbit.ai/configuration/path-instructions)
  demonstrate path-focused rules and exclusion of generated, lock, binary, and
  build output from ordinary semantic review.
- Official [React](https://react.dev/learn/you-might-not-need-an-effect),
  [TypeScript](https://www.typescriptlang.org/docs/handbook/2/narrowing.html),
  and [Next.js](https://nextjs.org/docs/app/guides/production-checklist)
  documentation grounds framework-specific checks.

The repository does not copy those prompts. It preserves the shared decisions:
scope from the current diff, investigate context before judging, require a
failure path, route specialized guidance by evidence, and verify fixes.

## Public and local boundaries

The canonical skills contain no company channels, ticket prefixes, branch
names, bot identities, private paths, or organization-specific approval policy.
A project may add those through repository instructions or path-specific local
profiles. External review publication remains a separate, explicitly authorized
action.
