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
- [`dex_method_disasm.py`](./dex_method_disasm.py) — reads a DEX file with no JDK: lists
  classes, searches by name, and disassembles one method (strings, fields, calls, branches).
  Exists because framework jars ship uncompressed dex and the usual RE suites want a JVM;
  contains the `35c` operand-order trap that makes registers look impossible when wrong.
