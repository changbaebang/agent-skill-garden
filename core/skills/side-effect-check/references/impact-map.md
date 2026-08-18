# Impact map

| Area | Evidence to seek |
| --- | --- |
| Runtime UI | route, component entry, visible state transition |
| Server/client boundary | serialization, hydration, request-scoped state |
| API contract | client, type, adapter, error and empty handling |
| Shared state and cache | readers, writers, keys, invalidation |
| Auth and storage | read/write sites, expiry, scope, session boundary |
| Feature flags | both states and rollout order |
| Package boundary | exports, dependency graph, consuming applications |
| Operations | logs, metrics, retry, rollback, alert behavior |
