# Sprouts

Small runnable scripts and proofs-of-concept that have started to take shape.

- [`where_am_i.py`](./where_am_i.py) — detects which environment it is running
  in (Termux, a proot Debian guest, Colab, or generic Linux). The garden's
  "probe, don't trust the map" idea, made executable.
- [`fix_ccusage_android.sh`](./fix_ccusage_android.sh) — makes a native-binary npm
  CLI run on Termux/Android by installing the statically linked linux-arm64 payload
  past npm's platform check and teaching the launcher the `android` alias. Re-runnable,
  because package managers are supposed to undo local patches.
