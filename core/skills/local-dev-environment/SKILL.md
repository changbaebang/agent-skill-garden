---
name: local-dev-environment
description: >-
  Trusts a local HTTPS certificate, starts one app with a chosen environment,
  and stops dev servers to free ports; machine values come from the environment
  profile. Use for start the dev server, local HTTPS cert, SSL error on localhost,
  port already in use, 로컬 서버 띄워줘, 서버 내려줘, 포트 비우기. Not for
  browser verification, test runs, or deployment.
---

# Local dev environment

Three jobs share one rule: the repository is never the place to keep a
certificate, a hostname, or a port. Those are facts about this machine and
they live in the environment profile. Starting a server must leave
`git status` exactly as it was.

## Resolve machine facts before running anything

Load the `integration.local-dev` section of the environment profile;
`scripts/profile_env.py` prints it as `LOCAL_DEV_*` exports. It names the
repository, the apps directory, the local hostname, the certificate directory,
each app's port, and the variable names the dev server reads. A missing value
is a question for the user, not something to infer from the code base.

When the hostname is not `localhost`, it has to resolve to the loopback
address on this machine. Check with a lookup; do not edit the hosts file
without asking.

## Certificates live outside the repository

Generate the certificate once with a local certificate authority tool
(`scripts/setup_local_cert.sh` wraps mkcert), trust that authority once, and
keep both files in the profile's certificate directory. The setup script
refuses a directory inside a Git work tree unless it is ignored.

`scripts/resolve_cert.sh` picks the certificate by precedence: variables the
server already reads that point at existing files; then the profile
directory; then a legacy in-repository directory, only when the profile names
one. Report which source won.

Some apps hard-code an in-repository certificate path. Satisfy them with a
symlink from that path to the resolved files, never with a copy. When the
repository tracks files at that path, the symlink shows up as a type change;
mark those paths skip-worktree so the override stays local. Do not commit a
certificate, a key, or an ignore rule that would hide them.

A browser warning about an invalid or unknown authority means the local
authority is not trusted yet: run the authority install step once and
regenerate. A missing-file error means the server was started without the
resolver; start it through `scripts/run_app.sh` instead.

## Start exactly one app

1. One server per app. Confirm which app and which environment the user
   means; default the environment from the profile, never from a guess.
2. Check the port first. An occupied port is stopped with the stop script,
   not avoided by choosing another number: the URL everyone expects would
   change and a stale server would keep answering.
3. Map the environment to a script name (`dev`, or `dev:<env>`) and prove it
   exists in the app's manifest. When it does not, list the available dev
   scripts and ask; do not invent an environment.
4. Serve HTTPS by default through the resolved certificate. Fall back to
   HTTP only when the certificate is the blocker and HTTPS itself is not what
   the user is verifying, and say so.
5. Enable the mock-service toggle only when the profile names it and the user
   asked for mocks.
6. When the server runs in the background, wait for the ready line or a
   health response before reporting, then give the full URL with its base
   path. A background task that exits non-zero right after a deliberate stop
   is the stop working, not a crash to restart.

`scripts/run_app.sh --dry-run` prints the resolved command, certificate
source, and URL without starting anything or touching the repository; show
that first when the user has not run this app before.

## Stop and free ports

Stop through `scripts/stop_dev_servers.sh`, which terminates the listeners on
the profile's ports (or the ports the user names), waits one second, force
kills what remains, and verifies with a port listing. Show which process holds
each port before killing when the list is not obviously dev servers. Stop
before switching branches and at the end of a local QA session; a server left
running serves the old branch and misleads the next check.

## Report

State the app, environment, URL, and certificate source for a start; the
ports and processes for a stop; and anything skipped with its reason. When a
hosts-file entry, a trust step, or a profile value is missing, name it as the
next step for the user rather than working around it.

## Do not

- edit, ignore, or commit repository files to make the server run;
- edit the hosts file or install a certificate authority without asking;
- kill a port that is neither in the profile nor in the request;
- store certificates, keys, or hostnames in the repository or in this skill;
- read a hostname, port, or path out of the code base when the profile lacks
  it; ask instead.

Field names and a synthetic profile are in
[references/profile-fields.md](references/profile-fields.md); commands, the
troubleshooting table, and the report template are in
[references/commands.md](references/commands.md).
