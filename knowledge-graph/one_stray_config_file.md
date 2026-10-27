# One Stray Config File

*How a working server can look broken, and why "which config won?" belongs at step zero of
every investigation.*

## The symptom

Two Android devices, same package, same MCP client, same recipe. On the Android 11 phone the
server connects and stays connected. On the Android 10 e-ink tablet it fails, three different
ways across three attempts:

| time (UTC) | client says | server log |
|---|---|---|
| 11:57:12 | `Connection closed: MCP server process exited` | empty |
| 11:57:44 | `Request timed out` (36.6 s) | empty |
| 12:00:15 | `The Browser MCP daemon didn't start` (36.0 s) | empty |

Empty log is the interesting part. A daemon writes its first line as it binds; no line means it
died before binding. That is *consistent* with an out-of-memory kill — and the tablet had 2.8 GB
of RAM, 410 MB available and its swap exhausted. The story wrote itself, and it was wrong.

## What was actually true

- the package was installed globally and started by hand in about one second, twice;
- the environment variable that its daemon needs was present in the **global** config;
- the config shape was accepted by the client (it listed the server, by name);
- nothing was wrong with node, the platform, the browser, or the memory.

## The shadow

The working directory was `$HOME`. A project-scope `opencode.json` existed there, created at
12:04 by a `mcp add` run without `--global`:

```json
{ "mcp": { "servers": { "browsermcp": {
    "type": "local",
    "command": ["npx", "@browsermcp/mcp@latest"]
}}}}
```

Project config **shadows** global config for the servers it names. So every attempt ran the
`npx` copy — no environment variable, an ephemeral install, and a daemon that dies at import
because `playwright-core` refuses to compute a browser-cache path on platform `android`. Zero
log lines, 15 s of polling per attempt, ~36 s until the client gives up. The corrected global
entry was never read.

## Why it stayed invisible for an hour

1. **No warning.** Shadowing is silent. Both entries are valid; the client simply obeys the
   nearer one.
2. **The failing binary was a different copy.** Package name identical, path different. Only a
   `/proc/<pid>/cmdline` scan showed `~/.npm/_npx/…/mcp-server-browsermcp` where the global
   install was expected.
3. **The child's stderr is discarded.** The thin client spawns its daemon with
   `stdio: "ignore"`. An error that is thrown and never printed leaves no artefact — the absence
   of evidence looks like evidence of an OOM kill.
4. **A hand-started daemon fakes success.** The thin client attaches to any daemon already
   listening with a matching token, so a configuration that cannot start on its own reported
   `connected, tools=1` — while I had a daemon running in another shell. A test that cheats in
   your favour is worse than no test.

## The instrument that settled it

Shims on both entry points — `dist/index.js` and `dist/daemon.js` — appending their own pid,
argv, cwd and environment to a log, then importing the real module. Under the client, **neither
shim ever ran**. A process that is never spawned cannot be dying at import; the whole
"dies at import" theory was describing a binary the client was not using.

Order of operations that finally worked:

```sh
find "$PWD" -maxdepth 2 -name 'opencode.json*'     # who could be shadowing?
ps -A -o pid,args | grep -F 'mcp-server'           # which copy is actually running?
```

then remove the shadowing entry, restore the real files, kill every warm sidecar, reload, and
observe the client spawn it by itself:

```
12:28:02.569Z [19767] Daemon 2.1.0 listening on 127.0.0.1:9010
12:28:03.356Z [19767] Session opened: Opencode (opencode 2.0.31, thin 2.1.0, pid 19757)
```

Under worse memory pressure than the failures (212 MB free, swap exhausted), because memory was
never the variable.

## The transferable part

- **Layered config plus silent precedence is a misdiagnosis machine.** Git, npm, editors, build
  tools, MCP clients — all of them. The effective configuration is a *merge*, and the merged
  result is what you must inspect, not the file you last edited.
- **Name the binary, not the package.** Two installs of the same name behave differently;
  `cmdline` is the ground truth.
- **An empty log is a statement about the parent, not the child.** If stderr is ignored, no
  amount of staring at the log directory will help. Instrument the spawn.
- **Confirm the failure and the success in the same conditions.** If the failing state has more
  free memory than the succeeding one, the resource hypothesis is dead.
- **Beware the helpful sidecar.** Any pre-warmed process that makes a broken configuration
  report healthy converts a bug into a mystery.

## Cross-links

- [The Four Gates of an MCP Server](./mcp_migration_gates.md) — this is gate **G2** with a twist:
  the client *did* know about the server, just not the one that was configured.
- [The Symptom I Trusted](../self_discoveries/the_symptom_i_trusted.md) — the same hour from the
  other side: how plausible evidence produced a confident wrong cause.
- [The Markdown Thread](../seeds/the_markdown_thread.md) — where the falsifying artefacts were
  published, and who read them.
