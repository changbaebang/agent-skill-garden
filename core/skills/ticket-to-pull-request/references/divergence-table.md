# Return-value divergence table

A caller search answers "who calls this". It cannot answer "what changed",
because delegating one function to another changes behaviour without touching a
single call site. Build this table before the consumer sweep whenever a
function, parser, formatter, or adapter was delegated to or replaced by another.

## Method

1. Read the old function's branches to the end, including the final fallback.
2. Read the new function the same way.
3. Enumerate the input classes each branch handles, then the inputs that reach
   neither branch set and fall to the default.
4. For each input class, write the old return and the new return.

| Input class | Returned before | Returned after |
| --- | --- | --- |
| ... | ... | ... |

Look hardest at inputs where only one side falls to a fallback or default. Those
are the regression candidates.

An empty table is a legitimate result: say "equivalent" and cite the branches
read. A non-empty table is both the list for the pull request body and the list
of cases to pin with tests.

"The same priority order was kept" is not evidence. Identical branch order
still diverges on inputs that match none of the branches.

## Worked example

An application-local error-message parser is delegated to a shared parser. All
thirty-odd call sites are checked and none passes a different argument. The
table still finds a row:

| Input class | Returned before | Returned after |
| --- | --- | --- |
| error with a response payload | payload message | payload message |
| error with a status but no payload | status-mapped message | status-mapped message |
| error with neither payload nor status | caller's fallback message | raw error message |

A request timeout belongs to the last class. Every caller that already supplied
a careful fallback now shows the transport library's raw text instead. Drawn
before the pull request, the row costs one test; found in review, it costs two
rounds.

## Consumer sweep beyond imports

Import graphs and the type checker see symbols, not strings. After the table,
sweep text references that compile without the symbol:

- test mocks that name a module path as a string;
- relative-path mocks and fixtures;
- story or example files;
- manifests, registries, and generated maps that list provider or hook names;
- deprecated-path notes and migration comments that point at the old location.

Report the sweep with the search terms used so a reviewer can rerun it.
