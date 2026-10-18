#!/usr/bin/env bash
# fix_ccusage_android.sh — make the `ccusage` native CLI run on Termux / Android arm64.
#
# Background (see ../knowledge-graph/native_npm_binaries.md):
#   * ccusage >= 20 is a compiled native binary, published as one package per platform.
#     There is no android-arm64 payload.
#   * Termux's node reports process.platform === 'android', so npm silently skips the
#     `linux` payload (its package.json says os: ["linux"]) and the JS launcher
#     (src/cli.js) has no 'android' branch. Result on first run:
#         ccusage native binary is not available for android-arm64. ...
#   * The published linux-arm64 payload is STATICALLY LINKED, so it runs on Termux
#     unmodified — no glibc runtime, no dynamic-linker shim, no second environment.
#     Verify that claim yourself with:  file <payload>/bin/ccusage
#
# What this does:
#   1. installs the linux-arm64 payload despite the platform mismatch (--os / --cpu),
#   2. teaches the launcher to treat 'android' like 'linux' (idempotent one-line patch),
#   3. verifies by running `ccusage --version`.
#
# Re-run after every `npm update -g ccusage` (or any reinstall): npm restores the
# upstream launcher and drops the extra payload, which is exactly what the package
# manager is supposed to do.
#
# Usage:  fix_ccusage_android.sh [extra npm args...]     e.g.  fix_ccusage_android.sh ccusage@21

set -euo pipefail

prefix="${PREFIX:-/data/data/com.termux/files/usr}"
cli="$prefix/lib/node_modules/ccusage/src/cli.js"

echo "==> installing ccusage + the linux-arm64 payload (platform override)"
npm install --global ccusage --os=linux --cpu=arm64 "$@"

if [ ! -f "$cli" ]; then
	echo "ERROR: launcher not found at $cli" >&2
	echo "       (is ccusage installed globally? try: npm install -g ccusage)" >&2
	exit 1
fi

if grep -q "platform === 'android'" "$cli"; then
	echo "==> launcher already patched"
else
	echo "==> patching launcher platform map (android -> linux)"
	sed -i "s/if (platform === 'linux') {/if (platform === 'linux' || platform === 'android') {/" "$cli"
	if ! grep -q "platform === 'android'" "$cli"; then
		echo "ERROR: patch failed — upstream launcher layout changed." >&2
		echo "       Inspect $cli and adjust the sed pattern." >&2
		exit 1
	fi
fi

if version="$("$prefix/bin/ccusage" --version 2>&1)"; then
	echo "==> OK: $version"
else
	echo "ERROR: ccusage still not runnable:" >&2
	echo "       $version" >&2
	exit 1
fi
