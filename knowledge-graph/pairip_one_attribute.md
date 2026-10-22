# PairIP: The Gate Is One Attribute

*How Google's Play licensing wrapper attaches to an app, how to see it, and how to
remove it without touching the app's own code.*

## What it is

"PairIP" — Play Automatic Integrity Protection — is injected into the APK at upload time.
The tell-tale shape in `AndroidManifest.xml`:

```xml
<application android:name="com.pairip.application.Application" …>
<activity    android:name="com.pairip.licensecheck.LicenseActivity" …>
<uses-permission android:name="com.android.vending.CHECK_LICENSE"/>
```

plus a `com.pairip.*` package in the dex and a `stamp-cert-sha256` entry in the archive
(Play's source stamp). One common variant additionally ships `com.pairip.VMRunner` and a
protected dex; this note is about the plain variant, where the app's own code is untouched.

At startup the wrapper `Application` constructs a `LicenseClient`, binds
`com.android.vending.licensing.ILicensingService`, and — if the answer is not a valid
licence — starts `LicenseActivity`. Its **Close** button calls `System.exit(0)`.

## The symptom

The app opens a "Google Play" dialog and then dies; the process disappears without a crash
dialog. The logcat chain is unmistakable:

```
PhoneskyVerificationUtils : Play Store package is disabled
IntegrityService           : Phonesky is not installed
LicenseClient              : (retry #1 … #3)
LicenseCheckException
LicenseActivity
System.exit called, status: 0
```

Enabling Play Store does **not** fix it. The check is about the install's *provenance*, not
about which packages are present: an app installed by Aurora or sideloaded stays refused
with Play Store running and signed in.

## Why one attribute is enough

The wrapper is not woven through the app. It is an `Application` subclass whose `onCreate`
runs the check and then delegates to the app's real `Application` class — a name it reads
from its own injected configuration. If that wrapper is never instantiated, no license
client exists, nothing binds the store, and nothing calls `System.exit`.

So the whole gate can be removed by repointing the manifest:

```diff
- <application android:name="com.pairip.application.Application" …>
+ <application android:name="<the app's real Application class>" …>
```

`com.pairip.*` stays in the dex as unreachable dead code. No dex edit, no smali, no resource
rebuild.

**Check the conditions before believing it** — three things can re-attach the wrapper:

1. a `com.pairip.*` `<provider>` (e.g. `LicenseContentProvider`) with an authority,
2. a `com.pairip.*` `<service>`/`<receiver>`,
3. a `com.pairip.*` `android:appComponentFactory`.

If the manifest has only the two entries shown above, the attribute is the entire gate.

## Find the target class

The real application class must exist in the dex. Two cases, measured on real apps:

| App | Dex contains | Repoint to |
|---|---|---|
| typical app with its own initialiser | a class whose superclass is `Landroid/app/Application;` | that class (`…OpenCodeMobileApplication`) |
| Flutter app with no custom Application | only PairIP's `Application` subclass | `android.app.Application` |

Do not trust string search alone: R8 renames descriptors, and a Flutter app's classes are
obfuscated (`Lio/flutter/embedding/android/a;`). Parse `class_defs` and look at the
**superclass**, not at names.

## The mechanics that bite

- **The manifest is binary AXML**, and its string pool is usually UTF-16. Strings are
  length-prefixed and addressed by an offsets table; the pool is followed by other chunks.
  A longer replacement grows the pool, shifts everything after it, and requires updating
  the pool chunk size and the root chunk size. Attribute values are *string indices*, so no
  other chunk needs rewriting. Append padding to keep the pool 4-byte aligned.
- **Rebuild, don't patch in place.** Overwriting bytes in a shorter string leaves the old
  tail behind and silently changes behaviour.
- **The ZIP must be rebuilt**, keeping entry order and compression, dropping stale JAR
  signature files, and keeping alignment: `resources.arsc` 4-byte aligned (stored,
  uncompressible, mmapped), `*.so` page-aligned when `extractNativeLibs="false"`.
  `zipalign` is not always usable — on Ubuntu 20.04 it links a `p7zip` library that the
  modern `7zip` package does not provide, so the padding can be written directly into the
  `0xd935` extra field.
- **Splits share the signature.** Base and every `split_config.*.apk` must be re-signed with
  the same key or the install fails with a signature mismatch. Re-signing a split in place
  preserves its `.so` alignment.
- **Signature scheme**: a v2/v3 signature is what modern Android wants; v1-only survives on
  older platforms but is not worth deliberately choosing.

## Verify by behaviour, not by vocabulary

A `pairip` string in the dex proves nothing. In the same inventory, one app carried
`com/pairip/` markers and ran perfectly (wrapper-only, no licence path wired), while another
opened `LicenseActivity` on the first launch. The discrimination test is cheap:

```bash
am force-stop <pkg>; logcat -c
am start -n <pkg>/.MainActivity; sleep 8
dumpsys window | grep mCurrentFocus        # LicenseActivity ⇒ gated
logcat -d | grep -icE 'pairip|LicenseCheck|System.exit'
```

After patching, prove the patch is minimal rather than trusting it: compare entry CRCs of
the original and patched archives. In a good patch exactly one entry differs
(`AndroidManifest.xml`) and exactly three are added (`META-INF/MANIFEST.MF`, `*.SF`, `*.RSA`).

## What it costs

- **New signature ⇒ uninstall required ⇒ app data is lost**, unless the device is rooted and
  patches the signature check instead.
- **No updates, ever**: Play and Aurora will refuse to update a differently signed app. Each
  new version is a re-patch.
- **Play-bound extras stay broken**: Play Integrity / Firebase App Check (e.g. "send
  feedback"), in-app purchases, install-referrer attribution.
- **Nothing else changes**: same dex, same resources, same permissions, same behaviour.

## Prevalence, measured

On a 159-app tablet: **2** apps were genuinely gated this way; 1 was a false positive
(markers, no gate); 2 carried dormant LVL code that never fires; the rest carried billing,
Play-Core or Integrity clients that at worst log errors. The startup-gate family is small and
easy to spot *if* you test behaviour.

## Tooling note

None of this needed a decompiler. The evidence came from `logcat`, `dumpsys`, and the
manifest bytes; the repair from an AXML parser and a ZIP writer — see
[`../sprouts/axml_string_patch.py`](../sprouts/axml_string_patch.py). Reverse-engineering
suites earn their keep when the gate moves *into* code: the `VMRunner` variant, or an app
that hard-fails on an integrity verdict rather than a licence check.

Related: [`../seeds/who_wakes_the_store.md`](../seeds/who_wakes_the_store.md) — the
Play-Store-freezing problem this work grew out of; and
[`../self_discoveries/the_install_i_did_not_check_for.md`](../self_discoveries/the_install_i_did_not_check_for.md)
for the toolchain mistake made along the way.
