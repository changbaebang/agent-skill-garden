# Conflict levels

| Level | Evidence | Default response |
| --- | --- | --- |
| File | both changes touch the same file or hunk | coordinate order or ownership before merge |
| Module | different files change one package or public boundary | compare contracts and tests |
| Dependency | one change modifies an API consumed by the other | coordinate sequencing and compatibility |
| Cross-work | overlap spans different initiatives or owners | identify an owner and shared decision point |

No detected conflict means “no conflict found in the inspected active set,” not
proof that no concurrent work exists.
