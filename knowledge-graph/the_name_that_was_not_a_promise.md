# The Name That Was Not a Promise

*A frozen binary asks the system for its libraries by number, and that number is a
promise of ABI stability. When ffmpeg was upgraded under a `whisper-cli` that nobody
rebuilt, the promise broke in three separate ways — and only one of them was actually
the number's fault. The owner was one download away from a hundred-MB recompile that a
twenty-byte patch made unnecessary.*

## The symptom

`whisper-cli` stopped starting, with one line:

```
CANNOT LINK EXECUTABLE "whisper-cli": library "libavformat.so.62" not found: needed by main executable
```

The binary was built on 2026-07-23 against one snapshot of ffmpeg. The device's ffmpeg
had since been upgraded to **9.1**, whose library generation is `.63` / `.61` /
swresample `.7`. The build had been made against the older generation — `.62` / `.60` /
swresample `.6` — and the linker could no longer find it by the name the binary asked
for.

The owner had already started hand-fixing, and the report carried the cheapest finding
in the whole story:

```
libavformt.so.62  ->  ...
```

A one-letter typo, `format` → `formt`. The link was created, it resolved to a real
file, and the linker never once looked at that name. Two further attempts symlinked
`.62` to the *current* `.63` library — which would have been ABI-unsafe even had the
spelling been right.

## What "a newer library doesn't matter" actually means

It means something narrow and easy to over-generalise. Binaries do not record versions;
they record **sonames** — the name under which a library promises its ABI. The rule that
makes upgrades safe is not "newer is fine" but:

> A shared library may change its ABI only if it **keeps the old soname available** for
> the binaries that were built against it.

So `libavformat.so.62` and `libavformat.so.63` are *meant* to coexist. Upgrading ffmpeg
should leave the old generation in place for old consumers. Here, three different things
went wrong with that safety net, and they failed at three different depths.

## Layer 1 — the number changed, and the old copy was dropped

The `.62` *real files* survived on disk (Apr 2025,`libavformat.so.62.0.100`, etc.), but
the `libavformat.so.62` **symlinks** had been removed by the upgrade. The `.62` files
were also now unowned by any dpkg package — orphans nobody was tracking.

This is the friendly failure, because the payload is still present and only the pointer
is missing. Four symlinks restored it:

```
ln -s libavformat.so.62.0.100   libavformat.so.62
ln -s libavcodec.so.62.0.101    libavcodec.so.62
ln -s libavutil.so.60.1.100     libavutil.so.60
ln -s libswresample.so.6.0.100  libswresample.so.6
```

(Two of the owner's hand-links also pointed at the wrong files — `libavutil.so.60` aimed
at `libavcodec.so.60`, and `libavcodec.so.62` at the `.63` build.)

## Layer 2 — the number changed, and no old copy exists

With the ffmpeg libraries resolving, the next refusal came from *inside* the chain:

```
cannot find "libtheoraenc.so.1" ... for "libavcodec.so.62.0.101"
```

`libtheora` had been rebuilt since the ffmpeg snapshot and now declares
`SONAME=libtheoraenc.so` — **unversioned**. Old ffmpeg asks for `libtheoraenc.so.1`;
only the current `libtheora` is installed, and its soname is different. There is no old
copy to point at, because this is a leaf library the package ships in one version only.

This is a *genuine* ABI generation gap, and it is where `ln -s` stops working. The fix
is to give the existing file the soname the consumer expects:

```
patchelf --set-soname libtheoraenc.so.1 libtheoraenc.so.1
patchelf --set-soname libtheoradec.so.1 libtheoradec.so.1
```

Both `.so.1` names were hand-made orphans, not package-owned, so replacing them touched
nothing dpkg tracks.

The diagnostic that mattered here was knowing which mismatches are **fatal**. bionic
hard-fails a name only when the requiring library carries a `DT_VERNEED` version
dependency on it. A scan for that turned a list of a dozen "soname differs" warnings into
a list of exactly two that could actually stop the load.

## Layer 3 — the number stayed the same, and the promise broke anyway

Then the honest wall:

```
cannot locate symbol "x265_api_get_215"
    referenced by "libavcodec.so.62.0.101"
```

`libx265` is at **4.3** and exports `x265_api_get_217`. The frozen ffmpeg wants
`x265_api_get_215`. This is the subtle one: **`libx265` never changed its soname.** It is
still `libx265.so`. On the soname's own terms it is "compatible" — and it is not, because
the API version is carried in the *symbol name*, which the soname says nothing about.

A soname promises that the *shape* of the interface is stable. It says nothing about the
symbols inside keeping their names. A library can keep its promise about the shape and
break the promise the consumer actually depended on. No symlink and no soname rewrite can
rename a symbol.

## The dead end that had to be abandoned

The first idea was to stop the linker binding that symbol eagerly at all. `libavcodec`
and `whisper-cli` were both linked `BIND_NOW` (full RELRO), so the reference was resolved
at load. The relocation is a `JUMP_SLOT` — lazy by nature. Clearing `DT_FLAGS.BIND_NOW`
and `DT_FLAGS_1.NOW` (a same-size, in-place, two-entry edit) *should* have deferred the
symbol to first call — and, since `whisper-cli` only ever decodes **audio**, the x265
HEVC *encoder* path is never reached.

It still failed. Android's bionic resolves the whole dependency tree eagerly and has no
lazy binding to defer to. Both files were restored from their backups (checksums checked)
and the approach abandoned rather than left half-applied.

## The fix that worked

A link-time reference is fatal only if it is `GLOBAL`. The same closure was already
carrying several unresolved references that loaded fine — `ZSTD_trace_*`, `__lsan_*` —
because they are `WEAK`. So the undefined `x265_api_get_215` was flipped from `GLOBAL` to
`WEAK` in `.dynsym`: one nibble (`st_info`), in place, reversible.

A weak undefined symbol resolves to **0** instead of failing the load. Because the x265
encoder path is never entered by an audio-only run, the null is never dereferenced.

`whisper-cli` then started, reported version 1.9.1, and decoded audio through the ffmpeg
path again.

## The fixes, in one table

| # | What broke | Depth | Fix | Reversible |
|---|---|---|---|---|
| 1 | Old ffmpeg sonames unlinked | name dropped, file present | `ln -s` to the surviving `.62`/`.60` orphans | yes |
| 2 | `libtheora` changed its soname | leaf ABI gap, no old copy | `patchelf --set-soname` | yes |
| 3 | `libx265` kept its soname, renamed a symbol | symbol-level ABI break | `GLOBAL` → `WEAK` in `.dynsym` | yes |
| — | eager binding | — | clearing `BIND_NOW`: dead end, reverted | n/a |

## The recipe

For "program X cannot link, the library is there but newer":

1. `readelf -d X` — read the `NEEDED` sonames the binary is frozen to. The number is the
   promise.
2. Resolve the whole closure, not just the first missing name. The first error is a
   courtesy; there are usually more behind it.
3. Check which "mismatched soname" warnings are **fatal**: only a consumer with a
   `DT_VERNEED` entry for that exact name will refuse to load.
4. Prefer `ln -s` when the old `.so` still exists — it is the least invasive and the most
   reversible.
5. Reach for `patchelf --set-soname` only when the old generation is genuinely gone.
6. When a symbol name itself changed, no name trick helps. A weak-versus-global flip is a
   legitimate stopgap *only* when you can prove the code path is never entered — here,
   an encoder symbol in an audio-only program.
7. Back up every binary before the first byte changes, and check the checksum on restore.
8. Remember that on Android, bionic binds eagerly: "make it lazy" is not available.

## The general lesson

The owner's instinct was honest and reasonable — *the libraries are newer, that shouldn't
matter* — and the reason it mattered is that "newer" was doing the thinking for three
different questions at once. A version bump can drop a **name** (layer 1), change a
**soname** (layer 2), or change a **symbol** while keeping the soname (layer 3). The first
is a missing pointer, the second is a real gap, and the third is a promise that was kept
in form and broken in fact.

The clean fix remains what the owner almost did: rebuild against the current generation,
so the whole set is one consistent snapshot again. The patches are a bridge, not a home —
and the bridge was worth building only because it was fully reversible and honestly
measured, including the road that dead-ended. The number on a library is not a promise.
It is only the shape of one.
