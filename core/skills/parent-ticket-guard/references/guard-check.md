# Running the guard check

`scripts/guard_check.py` turns the facts you already read from the tracker into
a single decision. It never calls the tracker itself; collect the records
first, read-only, then hand them over.

## Input

A JSON document, from a file path or standard input:

```json
{
  "current_user": "account-id-of-the-user",
  "working_issue": "CHILD-1",
  "target": "TOP-1",
  "override": false,
  "issues": {
    "CHILD-1": { "owner": "account-id-of-the-user", "parent": "MID-1" },
    "MID-1":   { "owner": "account-id-of-the-user", "parent": "TOP-1" },
    "TOP-1":   { "owner": "account-id-of-someone-else", "parent": null }
  }
}
```

- `current_user`: the identity the tracker reports for the signed-in user. Use
  the account identifier, not a display name.
- `working_issue`: the issue the user is actually working on.
- `target`: the issue the write would touch.
- `override`: `true` only when the user stated in this session that the owner
  agreed to the write on this target.
- `issues`: one record per issue you read. `owner` may be a string or a list
  of strings when the tracker has more than one responsible person. `parent`
  is the parent key or `null`.

## Invocation

```bash
python3 scripts/guard_check.py facts.json
cat facts.json | python3 scripts/guard_check.py -
python3 scripts/guard_check.py facts.json --json
```

## Output and exit status

| Decision | Meaning | Exit |
| --- | --- | --- |
| `OUTSIDE` | the target is the working issue itself or not one of its ancestors; this guard does not decide, other write rules do | 0 |
| `ALLOW` | the target is an ancestor the current user owns, or the user gave an explicit override | 0 |
| `BLOCK` | the target is an ancestor owned by someone else, has no visible owner, has no record, or the current user is unknown | 2 |

Exit status 1 means the input was malformed; fix the facts, do not treat it as
a decision. The text after the colon is the reason; repeat it to the user when
you stop.

The script fails closed on purpose. Missing identity or ownership is not
evidence that writing is safe.
