# Roadmap

The canonical layer started with twenty workflows that carry the shared
operating model. Additional proven material is promoted in packs after it is
rewritten for public use and tested in both hosts. The second promotion pass
brought the garden to forty-eight skills plus one host hook.

## Review pack

Shipped: routed pull-request review, fix-verifying re-review, React correctness,
TypeScript runtime type safety, Next.js routing and rendering boundaries,
dependency/export/repository hygiene, pull-request metadata and checklist
review (`pull-request-checklist`), change-reach review (`review-scope-guard`),
quality-gate triage (`quality-gate-triage`), and both sides of the review
conversation (`review-request-message`, `review-request-intake`).

## Verification pack

Shipped: E2E scenario design, evidence-backed browser checks across local,
deployed, and production environments, affected-scope CI verification
(`affected-verification`), API-contract verification before client
implementation (`api-contract-check`), performance artifact reading
(`perf-artifact-analysis`), and in-app webview timing measurement
(`webview-performance-measurement`).

- browser smoke evidence attached to a pull request as a published comment
- multi-viewport capture as a standalone skill
- code preflight before opening a browser (device gating, redirects, required
  query parameters)

## Delivery pack

Shipped: tracker ticket lifecycle (`ticket-lifecycle`), parent-ticket write
guard (`parent-ticket-guard`), ticket-to-pull-request orchestration
(`ticket-to-pull-request`), shared test-branch reflection
(`test-branch-reflect`), deployment approval tickets and request checks
(`deployment-approval-ticket`, `deployment-request-check`), work-request
kickoff (`work-request-kickoff`), standup drafting (`standup-draft`),
production change reports (`production-change-report`), and personal package
releases (`package-release`).

- QA hand-off request quality gates (what a human tester can actually verify)
- tracker work audit against estimates

## Operations pack

Shipped: incident lifecycle with page sweep and risk forecast
(`incident-response`), bug triage that diagnoses without fixing
(`bug-triage`), and local development environment setup (`local-dev-environment`).

- customer-feedback investigation from chat reports to logs
- monitoring alert detection rules

## Repository lifecycle pack

Shipped: safe local and remote branch cleanup, shared-branch synchronization,
review-response/re-review handling through the routed review workflow, and a
destructive-push guard hook for Claude Code (`adapters/claude/hooks`).

## Knowledge-work pack

Shipped: blog profile initialization, technical draft creation, publication
checks, explicit publication boundaries, and learning/writing topic curation
(`topic-radar`).

## Maintenance pack

Shipped: workflow promotion (`workflow-maintenance`), local usage audit
(`skill-usage-audit`), private skill scaffolding (`private-skill-scaffold`),
and vendored skill lifecycle (`vendored-skill-lifecycle`).

A pack is not accepted because a private version exists. It must meet the
promotion contract and demonstrate useful triggering in Claude Code and Codex.
