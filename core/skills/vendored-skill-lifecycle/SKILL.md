---
name: vendored-skill-lifecycle
description: >-
  Installs an external skill plugin for one ticket into a vendor area with a thin wrapper and a lock file, then tears it down when the ticket closes. Use for vendor a plugin for this ticket, install external skills temporarily, vendor lock, 외부 플러그인 티켓 단위 설치, 벤더 스킬 설치, 티켓 끝나서 제거. Not for permanent plugin installs or publishing your own skills.
---

# Vendored skill lifecycle

An external plugin is borrowed for the length of one ticket. The whole design
exists so that borrowing leaves no residue: nothing copied into a project,
nothing auto-loaded, one file that says what is currently installed.

## Layout

Everything lives under the host's personal skills root (take it from the
environment profile; never from a project directory):

- `vendor/<repository>/<plugin-path>/`: the clone. Read in place, never loaded
  automatically.
- `vendor-lock.json`: the only record of active installs.
- `skills/<plugin>-vendor/SKILL.md`: a thin wrapper that exists only while the
  ticket is open. It lists the plugin's documents and points at them.

`scripts/vendor_lock.py` writes the lock and wrapper and removes them. It
performs no network access and never deletes a clone.

## Decide before installing

1. **Is a native install possible?** If the host can install the plugin
   permanently through its own plugin mechanism and the team wants it, use that.
   Vendoring is for temporary, ticket-scoped use of something you do not intend
   to keep.
2. **Which source outranks which?** Settle it now and say it aloud: the
   specification the ticket links to outranks the plugin. The plugin is a
   procedure, not an authority.
3. **Does the root sit inside a project repository?** If an enclosing work tree
   would track the vendor area or the lock, stop and pick another root. The
   script warns; do not wave the warning through.
4. **Is this plugin already installed for another ticket?** The script refuses
   duplicates. Finish or tear down the earlier ticket first.

## Install

1. Clone the source into `vendor/<repository>` yourself (shallow is fine). This
   is the only network step and it is yours to approve.
2. Dry-run the install, read the output, then run it for real. Inputs: plugin
   name, source, ticket identifier, and the plugin path inside the clone.
3. Open the generated wrapper. Confirm the document table lists the procedures
   you expect and the recorded revision is a real commit.
4. When the plugin names a command, open the matching document and follow it.
   Do not infer behavior from the command name; hosts that lack the plugin's
   command syntax still have the document.

## During the ticket

- Run the status command before relying on a plugin. It reports a missing clone,
  a missing or hand-edited wrapper, and a clone that moved off the recorded
  revision. A moved revision means the procedure you are reading may no longer
  be the one you installed.
- Never copy vendor files into a project repository, and never commit the lock.
- If the plugin disagrees with the ticket's specification, follow the
  specification and note the disagreement in the ticket.

## Tear down

Teardown happens when the ticket closes, not when you stop thinking about it.
Make it a closing step of the ticket, not a memory.

1. Dry-run teardown by ticket identifier and read what it would remove.
2. Run it. It removes the wrapper and the lock entry only. It refuses to delete
   a wrapper it did not write (the marker is missing), which protects a skill
   someone made by hand under the same name.
3. The clone stays. The output says whether another install still uses the same
   repository. Remove the clone only after the user confirms, and only when no
   other install uses it.
4. Run status once more and confirm the lock no longer lists the ticket.

## Traps

- Treating "the ticket is almost done" as done. A stale wrapper keeps offering a
  borrowed procedure in every later session.
- Editing the wrapper by hand. The next teardown will refuse it; regenerate by
  tearing down and installing again.
- Deleting the clone from the same step as teardown. Another ticket may be
  reading it.
- Reading the lock as proof the clone is healthy. Only status checks the disk.
- Putting the root, repository, or ticket tracker address in this skill. Those
  are environment values; read them from the environment profile.

Use [references/lock-and-wrapper.md](references/lock-and-wrapper.md) for the
commands, the lock format, and exit codes.
