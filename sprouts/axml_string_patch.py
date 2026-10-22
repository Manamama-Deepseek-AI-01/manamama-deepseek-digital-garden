#!/usr/bin/env python3
"""axml_string_patch.py — replace one string inside a binary AndroidManifest.xml.

An APK's manifest is compiled AXML: a string pool (UTF-8 or UTF-16, addressed by an
offsets table) followed by element chunks that reference strings by *index*. Changing
one string's text therefore means rebuilding the pool and shifting everything after it
— not overwriting bytes, which leaves the old tail behind and silently changes meaning.

This script does that one job, and refuses to guess:

  * exactly one string must match OLD, or it exits non-zero,
  * the output is re-parsed and checked before it is reported as done,
  * styles are rejected rather than half-supported.

Usage:
    ./axml_string_patch.py --list AndroidManifest.xml
    ./axml_string_patch.py --self-test AndroidManifest.xml
    ./axml_string_patch.py AndroidManifest.xml OLD NEW out.xml

`--self-test` rewrites the same strings into both pool encodings and re-reads them,
so the claim "UTF-8 and UTF-16 are both handled" is demonstrated rather than assumed.
(In practice, every manifest this garden has met is UTF-16.)

Typical use (see ../knowledge-graph/pairip_one_attribute.md):

    ./axml_string_patch.py AndroidManifest.xml \\
        com.pairip.application.Application \\
        android.app.Application \\
        AndroidManifest.patched.xml

No third-party dependencies. Python 3.8+.
"""
from __future__ import annotations

import argparse
import struct
import sys

RES_STRING_POOL_TYPE = 0x0001
RES_XML_TYPE = 0x0003
UTF8_FLAG = 0x0100


def _u8(buf: bytes, p: int) -> int:
    return buf[p]


def _u16(buf: bytes, p: int) -> int:
    return struct.unpack_from("<H", buf, p)[0]


def read_pool(buf: bytes, off: int) -> tuple[list[str], int, bool]:
    """Return (strings, offset just past the pool chunk, is_utf8)."""
    typ, _hsz, size = struct.unpack_from("<HHI", buf, off)
    if typ != RES_STRING_POOL_TYPE:
        raise SystemExit("no string pool at offset %d" % off)
    count, style_count, flags, strings_start, _styles_start = struct.unpack_from(
        "<IIIII", buf, off + 8
    )
    if style_count:
        raise SystemExit("styled string pools are not supported")
    utf8 = bool(flags & UTF8_FLAG)
    offsets = struct.unpack_from("<%dI" % count, buf, off + 28)
    strings: list[str] = []
    for rel in offsets:
        p = off + strings_start + rel
        if utf8:
            n = _u8(buf, p)
            p += 1
            if n & 0x80:
                n = ((n & 0x7F) << 8) | _u8(buf, p)
                p += 1
            blen = _u8(buf, p)
            p += 1
            if blen & 0x80:
                blen = ((blen & 0x7F) << 8) | _u8(buf, p)
                p += 1
            strings.append(buf[p : p + blen].decode("utf-8", "replace"))
        else:
            n = _u16(buf, p)
            p += 2
            if n & 0x8000:
                n = ((n & 0x7FFF) << 16) | _u16(buf, p)
                p += 2
            strings.append(buf[p : p + 2 * n].decode("utf-16-le", "replace"))
    return strings, off + size, utf8


def _utf8_len(n: int) -> bytes:
    return bytes([0x80 | (n >> 8), n & 0xFF]) if n > 0x7F else bytes([n])


def build_pool(strings: list[str], utf8: bool) -> bytes:
    data = bytearray()
    offsets: list[int] = []
    for s in strings:
        offsets.append(len(data))
        if utf8:
            raw = s.encode("utf-8")
            data += _utf8_len(len(s.encode("utf-16-le")) // 2) + _utf8_len(len(raw)) + raw + b"\x00"
        else:
            raw = s.encode("utf-16-le")
            n = len(raw) // 2
            if n > 0x7FFF:
                data += struct.pack("<HH", 0x8000 | (n >> 16), n & 0xFFFF)
            else:
                data += struct.pack("<H", n)
            data += raw + b"\x00\x00"
    while len(data) % 4:  # keep the following chunk 4-byte aligned
        data += b"\x00"

    header_size = 28
    strings_start = header_size + 4 * len(strings)
    chunk = struct.pack("<HHI", RES_STRING_POOL_TYPE, header_size, strings_start + len(data))
    chunk += struct.pack("<IIIII", len(strings), 0, UTF8_FLAG if utf8 else 0, strings_start, 0)
    chunk += struct.pack("<%dI" % len(strings), *offsets)
    return chunk + bytes(data)


def patch(src: str, old: str, new: str, dst: str) -> None:
    buf = open(src, "rb").read()
    typ, _hsz, size = struct.unpack_from("<HHI", buf, 0)
    if typ != RES_XML_TYPE:
        raise SystemExit("%s is not a binary XML document" % src)

    strings, after_pool, utf8 = read_pool(buf, 8)
    hits = [i for i, s in enumerate(strings) if s == old]
    if len(hits) != 1:
        raise SystemExit(
            "expected exactly one %r, found %d (indices %s)" % (old, len(hits), hits or "none")
        )

    strings[hits[0]] = new
    old_pool = buf[8:after_pool]
    new_pool = build_pool(strings, utf8)
    out = bytearray(buf[:8] + new_pool + buf[after_pool:])
    struct.pack_into("<I", out, 4, len(out))  # root chunk size == file size
    open(dst, "wb").write(out)

    # Re-read what we just wrote: never report success on an unverified artifact.
    check, _end, _utf8 = read_pool(open(dst, "rb").read(), 8)
    if new not in check or old in check:
        raise SystemExit("verification failed: replacement not visible after rebuild")
    print(
        "string #%d: %r -> %r  (%s pool, %d -> %d bytes, file %d -> %d, delta %+d)"
        % (
            hits[0],
            old,
            new,
            "UTF-8" if utf8 else "UTF-16",
            len(old_pool),
            len(new_pool),
            len(buf),
            len(out),
            len(out) - len(buf),
        )
    )


def self_test(src: str) -> int:
    """Rewrite the pool in both encodings and prove both round-trip."""
    buf = open(src, "rb").read()
    strings, after_pool, _utf8 = read_pool(buf, 8)
    print("# %d strings from %s" % (len(strings), src))
    ok = True
    for enc in (False, True):
        name = "UTF-8 " if enc else "UTF-16"
        chunk = build_pool(strings, enc)
        out = bytearray(buf[:8] + chunk + buf[after_pool:])
        struct.pack_into("<I", out, 4, len(out))
        back, _end, flag = read_pool(bytes(out), 8)
        same = back == strings and flag == enc
        ok = ok and same
        print("%s pool %6d bytes, %d strings -> %s" % (name, len(chunk), len(back), "ok" if same else "MISMATCH"))
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src", help="binary AndroidManifest.xml to read")
    ap.add_argument("--list", action="store_true", help="print the pool and exit")
    ap.add_argument("--self-test", action="store_true", help="prove both pool encodings round-trip")
    ap.add_argument("old", nargs="?", help="exact string to replace")
    ap.add_argument("new", nargs="?", help="replacement string")
    ap.add_argument("dst", nargs="?", help="output file")
    args = ap.parse_args(argv)

    if args.list:
        buf = open(args.src, "rb").read()
        strings, _end, utf8 = read_pool(buf, 8)
        print("# %d strings, %s pool" % (len(strings), "UTF-8" if utf8 else "UTF-16"))
        for i, s in enumerate(strings):
            print("%4d  %s" % (i, s))
        return 0

    if args.self_test:
        return self_test(args.src)

    if not (args.old and args.new and args.dst):
        ap.error("OLD, NEW and DST are required unless --list is used")
    patch(args.src, args.old, args.new, args.dst)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
