# Integration recipes

Integration recipes describe reusable behavior for an external service or
publication engine. They define configuration fields and verification limits,
but contain no personal values, credentials, host-specific invocation syntax,
or mutation authority.

- [`jekyll-git.md`](jekyll-git.md): local drafts to Git-backed Jekyll publishing
- [`slack-host-connector.md`](slack-host-connector.md): Slack through a host-managed connector

An environment profile selects a recipe and supplies local values. A core skill
uses that mapping only when its workflow needs the integration.
