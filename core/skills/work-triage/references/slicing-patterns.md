# Slicing patterns

| Change | Useful slice | Avoid |
| --- | --- | --- |
| API migration | compatibility layer, one consumer path, cleanup | switching every consumer without a fallback |
| Shared component | contract first, representative consumers, remaining consumers | file-by-file slices with no visible outcome |
| Defect | reproduction test, minimal fix, optional hardening | unrelated cleanup in the fix |
| Mechanical move | move plus references plus verification | leaving a temporarily broken import graph |
| Research | decision record with evidence | coding before the contract is known |
