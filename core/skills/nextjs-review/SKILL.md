---
name: nextjs-review
description: >-
  Reviews Next.js changes after classifying route intent, covering Server and
  Client boundaries, routing, redirects, hydration, caching, dynamic APIs, and
  route handlers. Use for Next.js review, App Router, Pages Router, use client,
  middleware, proxy, route handler, redirect, searchParams, or hydration review.
---

# Next.js review

Classify each affected entry before applying framework rules:

- content page: stable user-visible or search-visible content;
- gateway or bridge: validation and immediate navigation or redirect;
- client interaction UI: browser events, state, or browser APIs;
- infrastructure or glue: routing, security normalization, or shared framework
  integration.

Read [references/checklist.md](references/checklist.md) and apply only checks
relevant to the classification and installed Next.js version.

Do not treat server-side `searchParams` validation followed by `redirect()` as a
defect on a gateway page. Security validation can legitimately take precedence
over static-rendering preference. Conversely, do not apply gateway exceptions to
content pages that unexpectedly become dynamic or client-heavy.

Trace route entry, layout/provider composition, Server/Client serialization,
cache behavior, cookie and header access, navigation target, and error/loading
boundaries as needed. Report an issue only with a concrete build, request,
hydration, navigation, security, or user-visible failure.

Follow the caller's severity and output contract when selected by
`pull-request-review`.
