# Environment modes

Choose one mode for the entire run.

| Mode | Required proof | Default mutation policy |
| --- | --- | --- |
| Local | intended server and route are reachable | non-destructive test data only |
| Deployed | intended revision is deployed to the named environment | non-destructive test data only |
| Production | production URL and observation scope are explicit | observation only |

## Readiness checklist

- Name the environment and target URL.
- Record the expected branch, commit, build, or release identifier when known.
- Confirm route behavior, including redirects and rewrites.
- Separate authentication setup from the tested scenario.
- Confirm the account, flags, query parameters, and data needed for the result.
- Identify any action that writes durable state before execution.

If deployment or revision identity cannot be proven, report `BLOCKED` rather
than testing a possibly stale build. If the browser requires a secret or human
verification step, pause for the user; never request that the secret be pasted
into the conversation.
