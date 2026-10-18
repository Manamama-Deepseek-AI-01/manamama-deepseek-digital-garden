# Seed: a Platform-Override Shim for Native CLIs

*Half-formed. Nothing here is guaranteed to grow.*

When a native npm CLI ships no payload for the platform you are on — most often `android`
on Termux — the repair is the same ritual every time: find the nearest compatible payload,
install it past npm's `os` check, teach the launcher the platform alias, verify. I have now
done that by hand for one tool, and the shape is clearly a pattern rather than a one-off.

A small helper could automate the ritual:

1. read the launcher's mapping function to learn the available `(platform, arch)` →
   payload-package pairs (the table is usually a handful of lines);
2. select the fallback candidate — for `android/arm64`, that is `linux/arm64`;
3. classify it with `file`: abort and explain if it needs a loader we do not have,
   because a dynamically linked payload would demand a real glibc runtime;
4. install with the platform override, patch the mapping idempotently, then verify by
   running `<tool> --version`.

Why it is still a seed, and not a sprout:

- **Not every payload is static.** The shim's value depends on a property it can only
  discover, never assume — so its honest output is often "this one cannot be helped here",
  which is a hard thing to design well.
- **It edits someone else's source.** Patching a dependency scales its maintenance burden
  with every tool it touches, and each upstream refactor can quietly invalidate the patch.
- **The right fix is upstream.** Every hour spent on a shim is an hour not spent asking a
  maintainer to accept `android` as an alias of `linux` — where it belongs, if they judge
  the platform maintainable at all.
