# Verdict template

Return exactly one verdict. Keep every claim traceable to a row in the
evidence table.

```markdown
## API contract check: <work item>

- Verdict: implementable | blocked | no-op
- Target environment: <where the client will run against this contract>
- Contract summary: <one or two sentences stating what the backend serves>

### Evidence
| Source | Version or observed at | Establishes |
| --- | --- | --- |
| deployed backend response | <environment, time> | <dimension> |
| specification | <version or retrieval time> | <dimension> |
| client types and API client | <client revision> | <dimension> |

### Compatibility
- Existing client and types: <compatible | needs regeneration | conflicts>
- Effective route: <client base URL -> proxy or gateway rule -> backend host>
- Rollout and flag: <order, flag name if any, fallback when off>

### Mismatches or unknowns
- <source A says X, source B says Y; owner who can resolve it>
- <dimension not reachable from here and why>

### Skipped dimensions
- <dimension>: <why the work item cannot be affected>

### Implementation boundary
- In scope: <client changes the confirmed contract requires>
- Out of scope: <changes that would be guesses until a mismatch is resolved>
- Next: work-start | owner confirmation | close as no-op
```

## Filling the verdict

- `implementable` requires every checked dimension to have a row in the
  evidence table and no entry under mismatches other than accepted unknowns
  that cannot change the implementation shape.
- `blocked` requires at least one mismatch or unknown that can change the
  verdict, plus the owner or action that unblocks it. Do not list the client
  change you would have made as if it were approved.
- `no-op` requires the evidence showing the request is already satisfied, or
  the confirmed contract that needs no client change, so the owner can close
  the item from the report alone.

When the gate does not apply, replace the whole template with one line:
`contract gate: not required` followed by the reason.
