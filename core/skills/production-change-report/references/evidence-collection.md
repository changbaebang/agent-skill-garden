# Collecting the evidence

Everything here is read-only. The examples use the GitHub command-line client
because it exports pull-request metadata as JSON; any code host with a
pull-request API and a connected read-only tool serves the same purpose. Use
the tool the host already connected before falling back to a local client,
and never comment, review, label, merge, or edit anything while reporting.

## Verify the production branch

```bash
gh api "repos/$owner/$repo" --jq .default_branch
gh api "repos/$owner/$repo/branches/$branch" --jq .name
```

The default branch is usually the production branch but not always; some
repositories deploy from a release branch while the default branch is an
integration branch. Confirm with the repository's own documentation or the
environment profile's report scope before collecting.

## Export merged pull requests

Search slightly wider than the interval and let the script apply the exact
half-open boundary; the host's search granularity is a day, the report's is a
minute.

```bash
gh pr list --repo "$owner/$repo" --state merged --base "$branch" --limit 500 \
  --search "merged:$search_from..$search_to" \
  --json number,title,url,author,baseRefName,headRefName,mergedAt,mergeCommit,labels,isDraft,state \
  > merged.json

python3 scripts/change_window.py select --prs merged.json --base "$branch" \
  --start "$start" --end "$end" > selected.json
```

`select` drops requests merged into another base or outside the interval,
explains each exclusion, and marks likely wrappers (release, deployment, or
test-branch heads merging into production) and reverts. Add
`--wrapper-title REGEX` or `--wrapper-head REGEX` when the repository uses its
own naming. Confirm every wrapper mark by reading the request; the mark is a
prompt to look, not a verdict.

A list that stops exactly at the limit is probably truncated. Raise the limit
or split the interval until the count stops at a number below it.

## Collect per request

```bash
gh pr view "$number" --repo "$owner/$repo" \
  --json number,title,body,url,author,labels,mergedAt,mergeCommit,baseRefName,headRefName,additions,deletions,changedFiles,files,statusCheckRollup,closingIssuesReferences
gh pr diff "$number" --repo "$owner/$repo"
```

Read the diff for every request whose body is unclear, whose files touch a
high-risk area, or whose title claims a behavior change the file list does not
show. Note the observed default of any feature flag the diff introduces or
removes.

## Expand wrappers

For a wrapper merged at revision `$merge` with first parent `$merge^1`:

```bash
git log --merges --first-parent --format='%H %s' "$merge^1..$merge^2"
gh api "repos/$owner/$repo/commits/$sha/pulls" --jq '.[].number'
```

The first command lists the merges the wrapper carried; the second maps a
commit to the pull requests that introduced it. Leaves already merged into
production inside the interval are counted once, under their own request.
When the mapping cannot be completed, write `leaf mapping incomplete` rather
than guessing the leaf set.

## Deployment basis

Prefer this basis only when the records are reliable: a deployment system or
workflow that records a success time and the deployed revision.

```bash
gh run list --repo "$owner/$repo" --workflow "$deploy_workflow" --status success --limit 100 \
  --json databaseId,headSha,createdAt,updatedAt,conclusion
gh api "repos/$owner/$repo/deployments?environment=production&per_page=100" \
  --jq '.[] | [.sha, .created_at, .id] | @tsv'
```

The newly deployed range is `previous_success_sha..this_success_sha`; the
requests inside it are the deployed changes, whatever their merge time. Label
the report `production deployment` and still list requests merged in the
interval but not yet deployed, under "merged, not deployed".

Without such records the basis is `production branch merge`; say so, and never
describe a merge as a confirmed deployment.
