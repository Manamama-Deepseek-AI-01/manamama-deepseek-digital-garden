#!/usr/bin/env python3
"""where_am_i.py — report which environment this script is running in.

The same "detect the layer before trusting the map" idea that runs through this
garden's self-discoveries, in runnable form: an environment can lie about itself
(PRoot fakes `uname` and `id`), so probe for corroborating evidence instead of
trusting one field.

No third-party dependencies. Works on Termux/Android, a proot Debian guest,
Google Colab, and ordinary Linux/cloud boxes.
"""
from __future__ import annotations

import os
import platform
import socket
from pathlib import Path


def detect() -> dict[str, object]:
    # platform.release() misreports on Termux (returns the Android build, "11",
    # not the kernel); os.uname().release gives the real string. Second probe
    # wins — the whole point of this script.
    release = os.uname().release
    prefix = os.environ.get("PREFIX", "")

    # Order matters: a proot guest can see Termux paths but reports the PRoot
    # kernel string, so check for the costume first.
    if "PRoot" in release:
        env = "proot (Debian guest — faked uid / kernel)"
    elif "/com.termux/" in prefix or os.path.isdir("/data/data/com.termux/files/usr"):
        env = "Termux (Android host)"
    elif os.environ.get("COLAB_RELEASE_TAG") or os.path.isdir("/content"):
        env = "Google Colab"
    else:
        env = "generic Linux / cloud"

    return {
        "environment": env,
        "kernel": release,
        "system": platform.system(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "hostname": socket.gethostname(),
        "uid": os.getuid(),
        "user": os.environ.get("USER") or os.environ.get("LOGNAME") or "?",
        "home": str(Path.home()),
        "termux_prefix": prefix or "(unset)",
    }


def main() -> None:
    info = detect()
    print(f"environment: {info.pop('environment')}\n")
    width = max(len(str(k)) for k in info)
    for key, value in info.items():
        print(f"{key:>{width}} : {value}")


if __name__ == "__main__":
    main()
