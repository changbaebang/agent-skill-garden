# Jekyll Git integration

Driver: `jekyll-git`

## Profile fields

| Field | Requirement |
| --- | --- |
| `repository` | Existing Git repository containing the Jekyll site |
| `drafts` | Existing directory that preserves unpublished source drafts |
| `content_root` | Relative post destination, commonly `_posts` |
| `branch` | Publication branch |
| `base_url` | Public HTTP or HTTPS site URL |
| `verify` | Comma-separated subset of `page`, `sitemap`, and `home` |

## Contract

- Drafting and publication checking do not authorize a commit or push.
- Re-read the repository state before publication and stage only intended files.
- Keep the source draft until the public artifact is verified.
- A successful Git command is not publication proof. Apply the configured
  page, sitemap, and home checks when available.
- Writing voice, audience, metadata tendencies, and article structure belong in
  the blog writing profile, not this environment mapping.
