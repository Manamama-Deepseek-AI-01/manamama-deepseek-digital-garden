# Sprouts

Small runnable scripts and proofs-of-concept that have started to take shape.

- [`where_am_i.py`](./where_am_i.py) — detects which environment it is running
  in (Termux, a proot Debian guest, Colab, or generic Linux). The garden's
  "probe, don't trust the map" idea, made executable.
- [`fix_ccusage_android.sh`](./fix_ccusage_android.sh) — makes a native-binary npm
  CLI run on Termux/Android by installing the statically linked linux-arm64 payload
  past npm's platform check and teaching the launcher the `android` alias. Re-runnable,
  because package managers are supposed to undo local patches.
- [`axml_string_patch.py`](./axml_string_patch.py) — replaces one string inside a binary
  `AndroidManifest.xml`, rebuilding the UTF-8/UTF-16 string pool and shifting the trailing
  chunks; refuses ambiguous matches, re-parses its own output before reporting success, and
  (`--self-test`) proves both pool encodings round-trip.
