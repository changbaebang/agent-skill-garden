# Slack host connector integration

Driver: `slack-host-connector`

## Profile fields

| Field | Requirement |
| --- | --- |
| `workspace` | Human-readable workspace alias used to disambiguate environments |
| `channel_*` | Optional logical channel aliases such as `channel_reviews` |

## Contract

- Authentication and connector availability are managed by the active host,
  never by the profile.
- A static doctor can validate aliases but cannot prove connector login or
  permissions. Verify those in the active agent session.
- Reading, drafting, and posting are separate actions. A configured workspace
  never authorizes sending a message.
- Keep channel IDs and organization-only routing in a local profile or private
  extension when they should not be published.
