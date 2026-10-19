# Migration map

The first release consolidates ideas proven in three generations of personal
configuration: a discontinued editor setup, a Claude Code setup, and a Codex
setup. Those sources remain private and are not mirrored into this repository.

| Public workflow | Reused idea |
| --- | --- |
| `intake` | draft scope before tracker writes |
| `work-triage` | independently mergeable and verifiable slices |
| `work-start` | base, worktree, scope, and authorization checks |
| `work-closeout` | evidence-based completion and explicit handoff |
| `critical-review` | high-confidence release-blocker filter |
| `side-effect-check` | caller-to-consumer runtime tracing |
| `pull-request-review` | diff-driven pass selection, thread reconciliation, and fix-verifying re-review |
| `review-response-loop` | author-side review cycle: judge, verify, reply with the commit, re-request, re-arm |
| `react-review` | concrete render, state, effect, hook, and lifecycle failure paths |
| `typescript-review` | runtime risk hidden by assertions, nullability, or suppressed type errors |
| `nextjs-review` | route-intent classification before rendering and navigation judgments |
| `hygiene-review` | dependency, export, generated-artifact, and repository drift checks |
| `collaboration-awareness` | file, module, dependency, and cross-work conflicts |
| `skill-usage-audit` | evidence-based trigger and coverage analysis |
| `workflow-maintenance` | deliberate promotion instead of sanitize-and-publish |
| `blog-writing-workflow` | local voice profile, draft review, explicit publishing, and live verification |
| `affected-verification` | Verify a change the way CI verifies it: resolve the real base, compute the affected scope from it instead of hand-picking packages, run the same lanes CI runs (type-check, test, dependency rules, lint, lockfile) with... |
| `api-contract-check` | Verify what the backend actually serves in the target environment before any client code is written, treat a disagreement between authoritative sources as a verdict (blocked) rather than a choice, verify only the... |
| `bug-triage` | Defect report to reproduction, root cause, fix-ownership (can this team fix it alone) verdict, history, test cases, and an approval request; fixed order reproduce-before-cause-before-verdict; "not reproduced on one... |
| `deployment-approval-ticket` | Create a deployment approval ticket by re-reading the live approval guide on every run instead of cloning an earlier ticket (guide rules change silently and can reverse, and an automated gate enforces the current... |
| `deployment-request-check` | Verify a deployment request from the recorded state of every linked pull request (approval, merge, mergeability, latest checks) and report approvable or hold with observable reasons; read-only by default, with the... |
| `incident-response` | Incident lifecycle run as drafts: recognize → declare (30-second check, 100-point declaration rubric, title shape) → respond in a named role (commander / communications lead / operations lead with ten-minute cards,... |
| `local-dev-environment` | One workflow for local HTTPS certificate setup, starting a single app with a chosen environment, and stopping dev servers to free ports. Hostname, ports, certificate directory and variable names come from an... |
| `package-release` | Release a personal package: argue the version from the changelog contract, promote Unreleased to a dated version header, find every version literal by scanning, prove the tarball and CLI with an &&-only gate, open... |
| `parent-ticket-guard` | Before any tracker write, resolve the working issue's ancestor chain and block every write (field edit, status change, comment, link, revert, delete) to a parent or epic the current user does not own, failing closed... |
| `perf-artifact-analysis` | Read performance artifacts that already exist (HAR, browser traces, profiler exports, console timing output, aggregated reports, recordings) by splitting each into deterministic fields that prove something and noisy... |
| `prd-review` | Score a requirements document on five fixed, higher-is-better axes with every deduction tied to a document citation or the literal "not in document"; classify it complete / draft / not-a-requirements-document via an... |
| `private-skill-scaffold` | Scaffold a private skill in an opaque random 32-hex directory under a private root and expose only an alias symlink in the host skills root, refusing to overwrite real paths and checking the sync boundary afterwards |
| `production-change-report` | Summarize changes that reached the production branch in a natural-language period (exact half-open interval, complete merge enumeration, wrapper/revert/flag handling) and flag lightweight deployment risks from PR... |
| `pull-request-checklist` | Judge a pull request's metadata and template rather than its code: hard gates decide approval, soft gates shape the comment, the risk tier must use the repository's own labels with a rationale and never be inverted... |
| `quality-gate-triage` | Triage a pull request's static-analysis quality gate from the step log rather than the check color. Classify the result as real failure, no verdict (timeout) or pass. Fix only in-scope findings after explicit... |
| `review-request-intake` | Reviewer-side intake: resolve a permalink or bounded cursor sweep, qualify by PR state, docs-only change and author, track a stable key per head, re-review on head change or author reply, then publish review, thread... |
| `review-request-message` | Draft a review request chat message: gate on current pull request state (stop if draft, closed, or already approved), notifying mentions resolved to chat identities, team fallback, plain-language summary with an... |
| `review-scope-guard` | Review the reach of a change (shared base styles, defaults, globals, overrides) rather than the changed lines: count consumers with a blast-radius script, then ask five scope questions only when the change is... |
| `standup-draft` | Draft a daily standup (done, next, blockers) from the previous standup thread, authored pull requests, assigned tracker items, and local agent sessions. Every line cites evidence, and the draft cross-checks... |
| `test-branch-reflect` | Reflect a work branch onto a shared test branch (QA/staging) so the test environment can deploy it: fetch and refuse on a dirty tree, fast-forward the integration base (stop if the local base diverged), rebuild the... |
| `ticket-lifecycle` | Tracker ticket lifecycle under one field contract: create a leaf with parent, start/due dates, points on the team scale, and estimated effort; split into a container plus leaves when points exceed the cap (totals... |
| `ticket-to-pull-request` | Orchestrate one tracker work item end to end as fixed stations (understand, branch, contract gate, align, implement, verify, smoke, commit, pull request, side effects, review, close) with re-entry at any station from... |
| `topic-radar` | Curate writing and learning topic candidates from sources into a prioritized backlog kept separate from drafts, gated by depth rather than interest, and promote learned items to draft input only on the user's statement |
| `vendored-skill-lifecycle` | Install an external skill plugin per ticket into a vendor area (clone read in place) with a thin managed wrapper and a lock file, and tear down the wrapper and lock entry when the ticket closes while keeping the... |
| `webview-performance-measurement` | Measure page-load timing in an Android webview over CDP directly (adb forward, origin-less websocket, Target.getTargets, poll sessionStorage instead of console) and report nearest-rank p50/p75/p90 with provenance and... |
| `work-request-kickoff` | Parse a chat work request, sweep related threads/tracker/docs, identify the owner by ranked evidence, draft a polite kickoff reply (held until authorized), then prepare implementation after the reply |
| `destructive-push-guard` (hook) | A PreToolUse Bash hook that denies force, delete, mirror and forced or deleting refspec git push variants while plain push stays allowed |
| `destructive-push-guard` (hook) | A PreToolUse Bash hook that denies force, delete, mirror and forced or deleting refspec git push variants while plain push stays allowed |

## Kept private or already covered

Private workflows that were examined and deliberately not promoted in this
pass. The reason is recorded so the question is not reopened every time.

| Private workflow | Outcome | Reason |
| --- | --- | --- |
| automated smoke spec discovered from code | promote-later | The portable core is a three-phase split that no garden skill has: (0) discover from code which routes open without authentication (middleware matcher, presence of an index page, auth-wrapping of server props, then a live 200 check) and... |
| browser smoke evidence published to a pull request | promote-later | browser-e2e-check deliberately stops before publishing ('draft the evidence first and publish only after separate authorization') and no garden skill owns the publishing step. |
| multi-viewport sticky-element capture script | promote-later | The script is already generic: it takes --url, --widths, --scroll, --target, --nav, --out and emits per-width clipped screenshots plus a measurements.json with sticky gap, nav height and target top. |
| local single-page click run | already-covered by `browser-e2e-check` | browser-e2e-check's local mode already enforces the same shape: one environment, prove the server and route are reachable, separate authentication from the scenario, user completes login, opening a page is not PASS, capture failure... |
| deployed scenario check | already-covered by `browser-e2e-check` | browser-e2e-check's deployed mode already requires confirming the deployed revision before testing, one scenario at a time, user-performed login with verification, evidence capture over repeated retries, no destructive actions without... |
| consolidated browser verification entry point | already-covered by `browser-e2e-check, e2e-test-design` | This is the consolidated successor of the five Cursor skills: modes A (local click run) and B (deployed scenario) map directly onto browser-e2e-check's local and deployed modes with the same invariants (user does the login, never mix... |
| review-bot approval loop | already-covered by `core/skills/review-response-loop` | The loop skeleton is the same: establish state, four closing steps (reply, resolve, re-request, re-arm), round-trip vs convergence reading, awaited-reviewer narrowing, round counting with self-audit and revert-to-previous-behaviour,... |
| author-side review response | already-covered by `core/skills/review-response-loop (Judge each finding) + core/skills/pull-request-review/references/re-review.md` | Judging a finding from the current file, refusing with evidence, treating deferral as non-resolution, scoping out-of-range requests, and the closure states (fixed / gone / accepted reason / unresolved) are all present in the garden. |
| bot-style reviewer prompt | already-covered by `core/skills/pull-request-review` | This is the reviewer-side counterpart: reclassify unresolved threads from the current file, then review only the new delta with an evidence gate, severity levels, a human-judgement level that blocks approval until a human acknowledges,... |
| reviewer prompt with fix verification | already-covered by `core/skills/pull-request-review/references/re-review.md` | A twin of the reviewer prompt that adds a verify-the-fix principle (read the current file, reproduce at runtime when static types cannot prove the fix, never treat green CI as proof) and a warm persona voice. |
| reviewer prompt sync environment file | stays-private | The directory holds no SKILL.md and no scripts, only an environment file with internal monitoring endpoints, a datasource id and a bot account email, plus two empty subdirectories. |
| usage-statistics commit generator | stays-private | The whole procedure is creating bulk empty co-authored commits on one internal repository to feed an internal usage metric, with a fixed PR title and an instruction not to say what it is for. |
| personal slash-command index | stays-private | It is only an index of one person's Cursor slash commands, their recommended order, and cloud-agent trigger mapping. |
| personal configuration backup (host A) | already-covered by `workflow-maintenance, environment-profile` | The portable part is 'back up personal agent assets to a git repo, with a whitelist .gitignore, a secret scan before every commit, and the rule that tracked logic may go in but values the hooks read (keys, machine ids) stay out'. |
| organization marketplace promotion | already-covered by `workflow-maintenance` | The skill promotes personal skills into an organization plugin marketplace via fork and PR. |
| QA hand-off page registration | promote-later | The target is one QA team's wiki release page and its HTML round-trip rules, which are not portable. |
| tracker work audit against estimates | promote-later | The dashboards, project keys, custom fields (Estimate MD, Actual MD) and issue-type names are organization-specific. |
| customer-feedback-to-logs investigation | promote-later | Channel names, product analytics project, and log index are internal, but the investigation discipline is generic: primary source for the customer journey, log search only as a cross-check, classify the finding, and never post the reply... |
| monitoring alert detection rules | promote-later | The channels and the particular monitors are internal, but the detection-rules reference is a self-contained, tool-agnostic scoring model for deciding whether a burst of alerts is a probable incident. |
| personal configuration backup (host B) | already-covered by `workflow-maintenance, environment-profile` | Same backup-and-install loop as the other two sync skills, adding ownership and sync-direction detection so a stale local copy does not overwrite the repository. |
| personal configuration backup (host C) | already-covered by `workflow-maintenance, environment-profile` | It rsyncs one editor's personal assets into a backup repo, runs the same secret scan, and guides commit and push. |
