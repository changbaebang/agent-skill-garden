# Embedded client contract check

Use this when the defect reproduces only inside an embedded client (a native
app's webview on one or both platforms) and not in a mobile browser. Web code
is shared across platforms, so a platform-only reproduction points at what that
client sends to the web: a parameter, a user-agent token, a bridge call, or a
frame manipulation. The native code is read for comparison only. The output is
a verdict and an inquiry note, never a patch.

## Fill the reproduction matrix first

"Only visible on one platform" is not "caused by that platform". Run the
profile matrix before opening any client repository. A platform that looks
clean may be masked by a web-side polyfill writing the same value, in which
case the cause is shared and the inquiry would go to the wrong team.

| Reproduction | Where to look |
| --- | --- |
| One client only | That client's repository |
| Both clients, mobile browser clean | The shared webview contract: compare both repositories with the same keywords |
| Mobile browser too | Not this document; return to cause analysis in the web code |

## Read without cloning

Client repositories are large and owned by another team. Use the code host's
search and file APIs:

1. Search the repository for the contract keyword and list the matching paths.
2. Fetch each file at the default branch and read the relevant region.
3. Pin every link you will quote to a commit revision, not to a branch name.
   Branch links drift as lines move and the inquiry becomes unverifiable.

Do not clone, modify, or open pull requests against a client repository.

## What to look for

The signals the web code reads are the contract. Find where the client creates
or duplicates each one.

| Contract signal | What to search for in the client |
| --- | --- |
| Display-mode parameter (full screen, hide header, inset handling) | Where the parameter is appended and the allow-list that decides when |
| Frame or inset manipulation | Code that resizes or offsets the webview frame around system bars |
| User-agent token | Where the user agent string is assembled |
| Deep-link scheme | Routing that decides between a new webview and navigating the current one |
| New-window policy | Window or intent creation for links |

The shape that produces most platform-only defects is signal and action
duplication: the client sends a signal that means "web, you handle this" and
then also handles it itself. The web obeys the contract, and the effect is
applied twice. A client that sends the signal on one platform and hard-codes
the behavior on the other produces a defect that reproduces on one platform
only.

## Verdict

1. State the signal the web reads and its agreed meaning, with the web file and
   line as evidence.
2. State when the client sends it and what else the client does at the same
   time, with the pinned client link as evidence.
3. Choose the branch:
   - client violates the contract (duplication or a missing signal): write the
     inquiry below; do not paper over it with a web-side workaround, because
     the workaround breaks every surface that honors the contract;
   - web violates the contract (does not read, or misreads, the signal): a web
     defect; continue to the fix-ownership gate as a web change;
   - contract undefined (no agreed meaning recorded anywhere): include a
     proposed definition in the inquiry.
4. Write only what you read. "The client probably does X" is a hypothesis; a
   quoted line is evidence.

## Inquiry note

The web team does not fix this, so the quality of the hand-off is the output.

1. The symptom in one line and the report link.
2. Two pinned client links: where the signal is attached, where the duplicate
   action happens.
3. One paragraph on how the web reads that signal.
4. The web-side status: whether a related web fix already shipped and whether
   the reproduction conditions remain.

Phrase it as "this is where we looked" rather than a ruling; ownership is the
client team's call. Resolve the destination channel from the environment
profile; a missing profile entry is a configuration gap, not permission to
guess a channel. Send only when the user authorizes it, then wait. If nothing
web-side remains while waiting, say so and move on.
