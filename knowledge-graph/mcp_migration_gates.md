# The Four Gates of an MCP Server

*Why connecting a tool server fails in four different ways that all look the same, and the
order that untangles them.*

## The shape

An MCP client does not "install a server". It reads a config entry and then either spawns a
child process over stdio or opens an HTTP session to someone else's endpoint. Between the
config file and a working tool call there are four independent gates, and every one of them
can fail while the others are perfectly healthy.

| Gate | Question | Failure looks like |
|---|---|---|
| **G1** | Does the binary run at all? | `ModuleNotFoundError`, `command not found`, instant exit |
| **G2** | Is it registered in the client's config? | tool absent from the catalog; status `pending` |
| **G3** | Did the client spawn it with the right environment, path and working directory? | `pending` forever, silent exit, or a *confident and wrong* error from inside the server |
| **G4** | Has the provider authorised us for the real API? | `403`, `invalid_grant`, an endless consent loop, empty results |

The reason MCP troubleshooting feels like witchcraft is that G3 and G4 emit messages about
each other. A server that cannot see its credentials says *"no credentials configured"* —
which is a statement about its environment, not about your provider setup. Debug the gates
bottom-up, in isolation, and never touch G4 while G1 is unproven.

## G1 — the binary

The only honest test is running the thing:

```sh
<abs-path>/server --help
```

Two traps live here.

**A half-installed package impersonates a version incompatibility.** A missing-module error
on a package that *is* present at the expected version is not a dependency conflict; it is an
unfinished install. The cheap tell is a reinstall and `pip check` (or the npm equivalent).
Downgrading to a version that "should" work is how a healthy tree gets wrecked — I once
declared a working version permanently broken from a single snapshot of a half-replaced
package directory.

**A built server is not an installed server.** Some servers arrive as a directory with
dependencies already vendored beside them. They need no installer at all — only a path.

## G2 — the registration

`add` writes configuration. It does not install, and there is usually no `remove`: you delete
the entry. A status of `pending` immediately after adding is normal — the client has not
finished its first connection attempt. Re-read the status before concluding anything.

Mixed config generations coexist. A client that accepts both its old flat layout and a new
nested one will happily run entries written in either; migrating a working entry buys nothing
and risks everything.

## G3 — the spawn environment

This is the gate that lies.

**There are two whitelists, and neither is your shell.** An MCP client spawns children with
an environment it constructs, not necessarily the one your terminal has. Separately, the
reference client library for stdio routinely passes only a minimal default set — `PATH`,
`HOME`, and friends — unless the caller explicitly hands over the whole environment.

The consequence is subtle and expensive: **an error produced by your own test harness is not
evidence about the server.** If a throwaway script reports "credentials not found", the
honest reading is "this script stripped the environment", not "the configuration is broken".
Pass the environment explicitly, or dump it from inside the child:

```python
params = StdioServerParameters(command=ABS, args=[], env=dict(os.environ))
```

The same gate covers paths. A spawn from a service environment does not inherit an
interactive shell's `PATH`, so `command` should be absolute. And a client that offers no
templating has no equivalent for another client's `${extensionPath}` — that becomes an
explicit environment variable plus an `environment` block, or the server dies at startup with
a message about a missing variable.

## G4 — the provider

Registration is not capability. A handshake proves G2 and G3 and nothing else; a tool call
that touches the provider's real API is the only proof of G4.

Three shapes appeared in one day:

| Shape | What the server wanted |
|---|---|
| OAuth with a **pre-registered** client | client id + secret supplied by environment, local callback on a fixed port |
| OAuth with **dynamic registration** | nothing but a URL; the client registers itself |
| **Bearer token only** | a pre-issued token in a header; dynamic registration is refused outright |

The third shape is not a bug. Some authorization servers publish neither dynamic client
registration nor client-id metadata documents, and no amount of retrying will change that.
Recognise it early and fall back to a header.

**Interactive flows are races; tokens are not.** An authorisation flow is a browser
navigation plus a short-lived local listener. If the human is not at the keyboard in that
window, it ends in `Authorization expired` even though everything worked. Before opening a
flow, look for a credential that is *already present* in the environment — twice in one day
an existing token turned a two-minute race into a one-line header.

**Whoever owns the listener owns the flow.** The callback belongs to the process that started
it. Trigger an authorisation from an ephemeral test process and the browser will land on a
dead port: the grant is recorded, the code is spent, and the retry looks like a brand-new
failure. Confirm the port is actually bound *before* asking anyone to click:

```sh
ss -ltnp | grep ':PORT\b'
```

## Secrets: substitution, not duplication

Modern clients substitute inside config strings — an environment reference, and often a file
reference:

```jsonc
{
  "headers": { "Authorization": "Bearer {env:TOKEN}" },
  // or
  "headers": { "Authorization": "Bearer {file:~/.config/<client>/secrets/token}" }
}
```

That means the token never has to enter the configuration file. Two details matter: strip the
trailing newline when writing a file for a header, and check the store afterwards — a token
file at `0600` inside a `0700` directory is the whole point. Also check *whose* credential it
is: an environment token may belong to a different account than the one you intended to act
as, and "don't switch accounts" is not satisfied by borrowing another identity's secret.

## The recipe

```
0. Classify: remote HTTP, or local stdio?
1. Remote  → add by URL; then auth only if the status says it is needed
2. Local   → is a working binary already present (vendored or installed)?
             yes → use it.  no → install isolated, and mind shared-site collisions
3. `<abs-path> --help` runs clean                                    → G1
4. add <name> -- <abs-path> [args] [--env K=V ...]                   → G2
5. list → connected?                                                 → G3
6. bare handshake with the environment passed explicitly → tool names
7. auth, from the persistent client only; confirm the listener first
8. one live call against the real API                                → G4
9. record: tool count, credential path, scopes, disk delta
```

## What to record when you finish

A migration is not done when the status turns green. Write down:

- the **exact command** that produced a working registration;
- the **tool count**, so a later regression is visible at a glance;
- where the **credential** lives and what role it carries;
- the **scopes** granted, because "all tools" usually means "all scopes too";
- the **disk delta**, which for remote servers is zero and should stay zero;
- the **one call** that proved the provider side, so the proof can be repeated.

## The generalisable part

> A tool server is a chain of four independent trusts: the code runs, the client knows about
> it, the process can see what it needs, and the provider accepts who is calling. Diagnose
> the cheapest gate first, believe instrumentation only about itself, and never ask a human
> to click something whose landing site you have not confirmed is alive.
