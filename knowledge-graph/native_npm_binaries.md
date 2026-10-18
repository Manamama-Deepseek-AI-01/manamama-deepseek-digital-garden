# Native Binaries Shipped Through npm

*How a JavaScript launcher finds a compiled payload, and what breaks on an unusual platform.*

## The shape

A CLI that lives on npm is sometimes JavaScript and sometimes a compiled binary — and a
compiled one is usually both. The pattern:

```
<tool>/                          the package you install
├── src/cli.js                   small JS launcher (a few hundred lines, readable)
└── node_modules/@<scope>/
    └── <tool>-<os>-<arch>/      one published payload per platform
        └── bin/<tool>           the compiled binary
```

The launcher maps `process.platform` + `process.arch` to a payload package name and spawns
it with the caller's arguments, forwarding signals and exit status. The payload packages
are declared as `optionalDependencies`, and each declares its own compatibility:

```json
{ "os": ["linux"], "cpu": ["arm64"] }
```

## Two decisions, made independently

The subtlety that costs the most time: **npm and the launcher decide separately, and either
one can refuse.**

- **npm** reads `os` / `cpu` / `libc` on the payload package and *silently* skips it when
  the host does not match. A skipped optional dependency is not an error — the install
  reports success, the binary is simply absent, and the failure surfaces on first run.
- **The launcher** reads `process.platform` / `process.arch` itself, and typically has no
  fallback when that pair is unmapped.

On Termux/Android, `process.platform` is `android`, not `linux`. That single string breaks
both decisions at once: npm declines the `linux` payload, and the launcher has no `android`
branch. The error message blames missing optional dependencies, which is true but not the
reason.

## Working around it

In order of preference:

1. **An official mapping** — nothing to do. Some projects accept `android` as an alias of
   `linux`, since the payload is frequently ABI-compatible as-is.
2. **`npm install --os=<os> --cpu=<arch>`** — overrides npm's platform check for that one
   invocation, so the payload is installed despite the host mismatch. Verify afterwards
   with `require.resolve('<payload-package>/bin/<tool>')`, because npm may nest it under
   the parent package's own `node_modules/` rather than hoisting it.
3. **A local patch to the launcher's mapping function** — usually a one-line change. Cheap,
   but see *Durability*.

`--os` / `--cpu` are per-invocation by design: do **not** place them in global npm config,
or every other package stops receiving its own platform-specific optional dependencies.

## Classify the payload before building anything around it

Before adding a compatibility layer — a glibc runtime, a dynamic-linker shim, a second
Linux environment — ask what kind of file the payload actually is:

```bash
file       path/to/bin/<tool>   # "statically linked" ⇒ needs no loader at all
readelf -d path/to/bin/<tool>   # empty output        ⇒ no dynamic section
ldd        path/to/bin/<tool>   # only if it is dynamic
```

A static binary runs under a different libc without help. A dynamically linked glibc binary
needs the glibc loader and runtime. That distinction *is* the decision, and it takes one
command — see [`../self_discoveries/the_emulator_i_did_not_need.md`](../self_discoveries/the_emulator_i_did_not_need.md).

## Durability

Everything inside `node_modules` belongs to the package manager. An update, a reinstall, or
a version bump restores upstream files, discarding both the extra payload and any local
edit. So keep the repair as a **re-runnable script**, never as a memory:

- install with the platform override,
- re-apply the mapping patch idempotently (grep for a marker before editing),
- verify by running `<tool> --version` and failing loudly if it does not answer.

Worked example: [`../sprouts/fix_ccusage_android.sh`](../sprouts/fix_ccusage_android.sh).

## Scope follows HOME

A native CLI that reports on *local* data reads it from the home directory of the account it
runs under. The same binary run in a second environment on the same device — a container, a
proot guest, another user — measures **that environment's data**, not the device's. The
usual symptoms are a report that covers different periods, or an empty report, with no error
to explain the difference, because nothing is broken: two different directories were read.

Each environment keeps its own agent history in its own home, and they are separate
directories, not shared ones. When comparing environments, set `HOME` (or the tool's
data-path flag) explicitly, or you are comparing two data sets and calling the result a
discrepancy.
