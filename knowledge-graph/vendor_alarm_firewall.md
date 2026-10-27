# The Alarm That Was Silently Dropped

*A vendor ROM that filters `AlarmManager` requests behind a two-door gate — how the
freeze looks from outside, why every conventional power setting is a decoy, how to
find the branch that decides, and (added 2026-10-27) the one per-app GUI toggle that
really does fix it.*

## The symptom

A phase-based meditation timer (Zazen Meditation Timer on an ONYX NoteAir, Android 10)
with a 2-second *preparation* followed by a 15-minute sit freezes at the first phase
boundary: the display stays on "Preparation", the remaining time runs **negative**, both
control buttons grey out. The same APK behaves on other Android devices.

Two observations pin the failure down before any code is read:

- A single-phase session counts down correctly and freezes **when the phase ends**.
- Bells played from the settings screen ring; bells at a transition never do.

So the audio path is fine and the timer arithmetic is fine. What never happens is the
*transition callback*.

## What the log actually says

```
D ZMT_MeditationService: startMeditation
D ZMT_Meditation: Started Alarm for next section: sectionStartTime=… alertTime=…+2000
V AlarmManager: ***** Do not allow [pkg] set action=[ZAZENTIMER_SECTION_ENDED]
```

Read the order of those two lines: the app logs success **after** the framework refused.

`AlarmManager.set()` does not throw when a vendor policy drops the request. There is no
exception, no callback, no error the app can see — only that verbose line, which the app
has no way to read. From the user's seat it is a freeze with no cause.

## The gate is three lines of vendor Java

The message string lives in `services.jar`, but the *decision* lives in `framework.jar`,
in `android.onyx.pm.OnyxAlarmHelper`:

```java
boolean isAllowToSetAlarm(int uid, String pkg, String action) {
    AlarmBaseSchema s = getCurrentAlarmSchema();
    if (s.isAllow(pkg, action)) return true;
    if (OnyxAppOpsHelper.getInstance().isFullPMAccessPkg(uid, pkg)) return true;
    return false;
}
```

Two schemas implement `isAllow`:

| Schema | Matches | Allowlist source |
|---|---|---|
| `AlarmRunSchema` | **prefix** of the *package name* | three `PMConfig` lists, plus any action starting with `onyx_` |
| `AlarmMemSchema` | **suffix** of the *action* | a small built-in set: keyguard delayed, `*walarm*:*`, condition providers, the vendor's own receiver |

Which one applies is chosen by `isInteractive` — **the policy changes when the screen
goes off**. That detail matters later.

## Why the obvious repairs cannot work

- **Doze / power whitelist** (`cmd deviceidle whitelist +pkg`): irrelevant. The drop
  happens inside `setImpl`, before the alarm is ever stored.
- **"Battery optimisation → unrestricted"**: the same thing under a friendlier name.
- **Vendor "App Optimization" / "Freeze" UI as a freezing mechanism**: a red herring for
  this failure — nothing in the check reads an app's frozen or optimised state. Careful
  though: the *same dialog* holds the switch that does fix it, through a totally different
  field. This bullet was flat wrong until 2026-10-27; see *The switch that actually
  persists* below.
- **AppOps**: `cmd appops get <pkg>` shows nothing denied. The vendor's log prose
  ("user blocked background alarms") describes a *category*, not the trigger.

Each of these is a plausible mechanism; none of them is this mechanism. The only decisive
move is reading the branch.

## The switch the vendor already ships

Immediately next to the helper is a runtime receiver, registered with no permission:

```
action: com.onyx.action.disable_restriction
extra:  package = <pkg>

  → OnyxAlarmHelper.disableRestriction(pkg)
       ├ EACConfig.addToHiddenApiThirdPartyAppWhiteList(pkg)
       └ AlarmRunSchema.addToAllowList(pkg)
```

```sh
am broadcast -a com.onyx.action.disable_restriction --es package <pkg>
```

This is a supported path — the ROM ships it for its own UI — and it needs neither root nor
a patched APK. It is also **in-memory only**: the allowlist is a static list inside
`system_server`, so it is lost on reboot and must be re-sent. (On this device it is now
part of the post-boot Shizuku bootstrap script, which is the one thing that has to run
after every reboot anyway.)

Proof comes from `dumpsys`, not from a screenshot:

```
ELAPSED_WAKEUP #0: Alarm{… <pkg>}
  tag=*walarm*:ZAZENTIMER_SECTION_ENDED   … +12m22s
```

and from logcat showing the next transition (`onReceive … SECTION_ENDED` → bells playing →
next alarm scheduled).

## The switch that actually persists

Door #2 in the gate above is not a fallback. It is the *designed* path, and it is a
per-app toggle in the vendor's own EAC ("Optimize") dialog — not in Settings, and not
reachable by any `settings put`:

> long-press the app's icon → **Optimize** → tab **Others** →
> **"Stay active in the background"** → on

That writes one boolean, `extraConfig.fullPMAccess`, into the app's entry in the device's
EAC config store — `/onyxconfig/eac_config` here, a dedicated **rw ext4 partition**
(`/dev/block/mmcblk0p47`) whose SELinux label keeps `shell` out, so the file itself is
neither readable nor writable from Termux. Being on disk, the setting **survives
reboots**: no broadcast, no doze whitelist, no AppOps, no bootstrap script.

Reading the result without root still works, through the vendor's binder service:

```sh
service call oec_service 24             # getFullPMAccessPkg — every package with the flag on
service call oec_service 43 s16 <pkg>   # getAppConfigBundle — that app's effective JSON
```

`getFullPMAccessPkg()` is not a list anyone maintains; it is a filter over the app-config
map (`appConfigMap[pkg].extraConfig.fullPMAccess`). Entries are created lazily by
`EACDeviceConfig.ensureAppConfig(pkg)`, and for a **non-system** app that factory is
`EACAppConfig.createOnyxAppConfig()` — which hardcodes the flag to `true`. So an app can
end up permanently exempt with nobody ever touching the switch: any implicit EAC write
(a display or refresh mode applied to whatever is the current top component) materialises
the entry, and it inherits `true`. An explicit save from the dialog instead carries the
switch state, i.e. `false` unless the human turns it on.

That asymmetry explains the confusing field report that started this whole thread: of two
meditation timers on the same device, one chimed and one hung — for weeks — and **both**
had EAC entries; only one had the flag. The "working" app had never been deliberately
whitelisted by anyone.

Shell-only approximations, both weaker than the toggle:

- `service call oec_service 53 i32 <mode>` writes the config of the app that is
  **currently on top**, so it can *create* an entry (which defaults the flag to `true`) —
  but it cannot flip the flag on an entry that already exists. `service call oec_service
  22` lists the packages that have entries at all, which is how you tell "no entry" from
  "entry with the flag off".
- `cmd appops set <pkg> 70 allow` — op 70 is stock `RUN_ANY_IN_BACKGROUND`; the vendor's
  `OnyxAppOpsHelper` watches it and adds the package to the same in-memory set at runtime.
  Immediate, but that set is rebuilt from the config store at boot, so it must be re-issued
  every boot (force a transition — `70 deny` then `70 allow` — or the watcher may see no
  change to react to).

Flipping an existing entry properly is `applyAppConfigToService(List, Bundle)`
(transaction 14): a **List + Bundle**, which `service call` cannot marshal. There is no
one-liner for it — which turned out not to matter, because the GUI already is one.

## The parallel firewall: wakelocks

The same two-door shape exists one floor down, for wakelocks
(`android.onyx.pm.Wakelock*Schema`, same `PMConfig` lists, plus the same
`isFullPMAccessPkg` bypass):

```
E PowerManager: WakeLock tag:ScreenOnWakeLock from [pkg] is forbidden
```

An app's own "keep screen on" is therefore also refused — which matters, because the
alarm policy is screen-state dependent (see above). The two repairs also differ in
coverage: the `disable_restriction` broadcast only extends the *alarm* schema and leaves
wake locks vetoed, while the per-app "Stay active in the background" switch opens both,
because `WakelockHelper.isFullPMAccessPkg(int, String)` resolves through the same
`OnyxAppOpsHelper.fullAccessPkgSet` that door #2 consults.

## Recipe, portable to other vendor ROMs

1. **Establish what is missing, not what is wrong.** Here: a callback, proven by an absent
   `onReceive` and a negative countdown. "It freezes" is a symptom, "the transition alarm
   was never scheduled" is a finding.
2. **Grep the framework for the sentence you saw.** `grep -a 'Do not allow'
   /system/framework/*.jar` named `services.jar`; the class it pointed at lived in
   `framework.jar`. Vendor code is rarely where its log tag suggests.
3. **Read the decision, not the prose.** Method names, config names and log strings
   describe categories; only the branch gives the condition.
4. **Look next door for a receiver or service.** Code that blocks usually ships an escape
   hatch for its own UI: scan the same class's inner classes for `BroadcastReceiver`,
   `disable`, `unrestrict`, `whitelist`.
5. **Ask what the failing condition reads, and who writes it.** An in-memory allowlist is
   a per-boot patch; a per-app config entry is the real setting. Find the store and its
   writer, and prefer the writer — here the writer was a switch in the vendor's own
   dialog, i.e. a fix that survives reboots and needs no shell at all.
6. **Prove it with `dumpsys` and a second logcat run.** A fix you cannot see in the
   system's own state dump is a hypothesis.

## Tooling note

No JDK on the tablet, so jadx, apktool and `rea`'s Android tools (which require a JADX
MCP jar plus a JDK) were all out. What worked: `framework.jar` and `services.jar` store
their dex **uncompressed**, so `grep -a` finds strings and the class data can be parsed
directly. The reader used here is
[`../sprouts/dex_method_disasm.py`](../sprouts/dex_method_disasm.py) — header, id tables,
`class_data`, `code_item`, then disassemble one method. An operand-order mistake in the
`35c` invoke format cost about an hour; the script's docstring carries the coordinates so
it costs nobody else that hour.

## Aside: the label I never resolved

While hunting the writer of that flag I quoted the human a Russian UI string —
*«Разрешить работу приложения в фоновом режиме»* ("allow the app to run in the
background") — as if it were the label on the switch. It was not. I had keyword-searched
the APK's resource table (`resources.arsc`) for Russian words about power and background,
then presented the nearest hit with a straight face. I never resolved the actual resource
name (`eac_item_full_pm_access_label`) by ID. A resource table ships *every* locale, so a
search written in Russian returns Russian: that is a property of my query, not of the
device, and quoting it back at the human read as an inexplicable insistence on another
language. The label actually on his screen is English — **"Stay active in the background"**,
inside a tab called **Others**, in a dialog called **Optimize**.

Two lessons, both cheap: resolve resources by id/name, never by grepping for a phrase you
hope is there; and when a human describes what is on his screen, that outranks any string
dump, however confidently formatted.

Related: [`../self_discoveries/the_decoy_that_fitted.md`](../self_discoveries/the_decoy_that_fitted.md)
— the wrong theories this session walked through before reading the branch.
