# Next.js review checklist

## Server and Client boundaries

- `use client` appears only where interactivity, hooks, or browser APIs require
  it, and the boundary does not unintentionally pull large server-safe trees into
  the client bundle.
- Props crossing the Server/Client boundary are serializable and preserve the
  intended contract.
- Browser APIs and time-dependent values do not make server and initial client
  output diverge.
- Server-only secrets, headers, or services cannot enter client code.

## Routing and navigation

- Redirect and rewrite targets are validated against open-redirect and protocol
  injection risks.
- Gateway pages preserve query, fallback, and error behavior intentionally.
- Client navigation uses framework navigation when state preservation and
  prefetching matter; hard navigation is intentional when selected.
- Middleware or proxy matchers do not capture unrelated routes.

## Rendering, cache, and data

- Dynamic APIs such as cookies, headers, and search parameters make rendering
  dynamic only where intended.
- Cache keys, revalidation, tags, and invalidation match data ownership and
  mutation paths.
- Server Components fetch from the effective source instead of calling an
  internal route handler through an avoidable HTTP round trip.
- Loading, error, not-found, and redirect paths do not leave a blank or mixed
  state.

## Route handlers and mutations

- Authentication, authorization, input validation, and error status are handled
  at the server boundary.
- Request body and response serialization match callers.
- Mutations define cache refresh or revalidation behavior when users expect the
  result to become visible.

Primary references:

- [Next.js App Router](https://nextjs.org/docs/app)
- [Next.js production checklist](https://nextjs.org/docs/app/guides/production-checklist)
- [Next.js hydration error guide](https://nextjs.org/docs/messages/react-hydration-error)
- [Next.js backend-for-frontend guide](https://nextjs.org/docs/app/guides/backend-for-frontend)
