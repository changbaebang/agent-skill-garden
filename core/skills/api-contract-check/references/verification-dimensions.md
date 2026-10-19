# Verification dimensions

Check only the dimensions the work item can be affected by. For each one you
check, record the source that establishes it and when you observed it. For
each one you skip, write one line saying why the work cannot be affected.

| Dimension | What must be established | Typical mismatch |
| --- | --- | --- |
| Endpoint and method | path, HTTP method, base path, versioning, and the environment where it is deployed | spec describes a path that is not deployed to the target environment |
| Request shape | field names, optionality, enum values, serialization format, validation rules, pagination or filtering parameters | client sends a field the backend ignores, or omits one the backend now requires |
| Response shape | success body, empty and null behaviour, list versus single item, error body, status codes, partial-failure semantics | generated types mark a field required that the backend omits on an empty result |
| Authentication and session | required credentials, cookies, headers, user or session preconditions, anonymous behaviour | endpoint works in a logged-in manual test and fails for the anonymous path the client also serves |
| Compatibility and rollout | backward compatibility window, feature flag, rollout order between backend and client, fallback when the new behaviour is off | client ships first and reads a field the backend does not send yet |
| Client and type compatibility | existing API client, generated types, adapters, cache keys, and every consumer of the same boundary | regenerating types changes a shared type that other screens rely on |
| Routing | proxy, gateway, rewrite rules, base path, environment variables that select the host | spec host and client host differ, which is fine only when the effective route resolves to the deployed backend |

## Trace the effective route

Do not compare the specification host with the client's configured host as
strings. Follow the request the client actually makes:

1. the client's base URL or environment variable;
2. any rewrite, proxy, or gateway rule in the client's runtime configuration;
3. the backend host that rule resolves to in the target environment;
4. whether that host serves the deployed version the specification describes.

Different hosts are correct when the route resolves to the right backend.
Identical hosts are wrong when the route points at an environment where the
change is not deployed.

## Source precedence when sources disagree

Deployed behaviour outranks the specification; the specification outranks the
design document; the design document outranks a chat decision. Precedence tells
you which source is likelier to be current. It does not let you pick one and
move on: a disagreement between authoritative sources is still `blocked` until
an owner confirms which one is the contract.

## What counts as evidence

- A request made against the target environment, with the observed response.
- The backend source or merged change at a named revision.
- The specification document at a named version or retrieval time.
- Generated client types at a named client revision.

What does not count: a screenshot without an environment, a verbal assurance,
an older environment standing in for the target one, or a failed lookup read
as "nothing there".
