# Who Wakes the Store?

*An open question, with enough measurements attached to be worth finishing.*

## The observed behaviour

On an ONYX NoteAir (Android 10, unrooted), Google Play Store refuses to stay disabled. Two
independent mechanisms were tried, one cold boot each:

| Attempt | State before reboot | State after reboot |
|---|---|---|
| `pm disable-user --user 0 com.android.vending` (+ `…partnersetup`) | both `enabled=3` (disabled-user) | vending `enabled=1` (**enabled**), partnersetup back to default |
| `pm uninstall --user 0` on both (`installed=false`, gone from `pm list packages`) | uninstalled for user 0 | both `installed=true`, vending `enabled=1` |

The second one is the interesting one: it does not merely flip a flag back, it
**re-materialises a package that was uninstalled for the user**. That is not something an
ordinary `pm` user can do, and it is not something a boot receiver does by accident.

## What it is *not*

A blanket firmware reset of disabled packages. Same two reboots, same `pm list packages -d`:

```
org.chromium.chrome                    enabled=3   (survived; it is /system/app/NeoBrowser)
com.onyx.android.production.test        enabled=3   (survived)
```

So exactly the two packages that came back are **"updated system apps"** — a system APK plus
a newer `/data/app` copy. The boot scan says so out loud, right before they reappear:

```
W PackageManager: Failed to scan /system/priv-app/Phonesky: … ignored:
                  updated version 85354820 better than this 82413110
W PackageManager: Failed to scan /system/priv-app/GooglePartnerSetup: … updated version 17309 …
W PackageManager: Relax SCAN_REQUIRE_KNOWN requirement for package com.android.vending
```

## The candidates

1. **`system_server` itself** — `PackageManagerService` handling of updated system apps on
   this vendor build may reset per-user install/enable state during the boot scan.
2. **A vendor process running as the system uid** — `com.onyx` (kcb-release, the reader
   framework) reports `userId=1000`. A uid-1000 process needs no permission at all to call
   the package manager; `CHANGE_COMPONENT_ENABLED_STATE` is irrelevant to it.
3. **Partner Setup** — it does hold `CHANGE_COMPONENT_ENABLED_STATE`, but it was *disabled*
   before the reboot and was itself restored, so it would have had to be re-enabled first.

(2) is the prime suspect and completely unproven.

## How to settle it (needs root)

- **Watch the file, not the log.** `inotifywait` on
  `/data/system/users/0/package-restrictions.xml` (root) turns "after boot" into "at
  21:34:0X", then correlate that instant with `dumpsys activity processes` and with the
  start times of uid-1000 processes in `logcat -b events`.
- **Bisect the actor.** Freeze `com.onyx`'s boot receivers/services (root), cold boot, see
  whether the store stays disabled. If it does: name the component, not the app.
- **Read the ROM.** Compare this build's `PackageManagerService` boot path against AOSP 29
  for the updated-system-app case; a vendor diff would explain the restore without any
  villain.

## Until then

Two workarounds, in order of robustness, both requiring root:

1. A Magisk `service.sh` that re-asserts `pm disable-user` a few seconds after boot **and**
   again a minute later — cheap, reversible, loses any race it does not cover.
2. A systemless module that bind-mounts an empty file over
   `/system/priv-app/Phonesky/Phonesky.apk`: the package cannot parse, so there is nothing
   left for anyone to re-enable.

Prefer (2) if the actor turns out to be a boot-time process; prefer (1) if it turns out to be
a one-shot scan, where a late re-assert is enough.

The generalisable rule the measurements already support: **on a vendor ROM, treat every
user-level debloat as advisory until it has survived one cold boot** — and check whether a
vendor app runs as uid 1000 before trusting the permission table to list the actors.
