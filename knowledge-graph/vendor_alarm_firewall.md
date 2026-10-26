# The Alarm That Was Silently Dropped

*A vendor ROM that filters `AlarmManager` requests on a static allowlist — how the
freeze looks from outside, why every conventional power setting is a decoy, and how
to find the branch that decides.*

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
- **Vendor "App Optimization" / "Freeze" UI**: irrelevant. Nothing in the check reads an
  app's frozen or optimised state.
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

## The parallel firewall: wakelocks

The same shape exists one floor down, for wakelocks (`android.onyx.pm.Wakelock*Schema`,
fed by the same `PMConfig` lists):

```
E PowerManager: WakeLock tag:ScreenOnWakeLock from [pkg] is forbidden
```

An app's own "keep screen on" is therefore also refused — which matters, because the
alarm policy is screen-state dependent (see above). Fixing alarms does not fix wakelocks,
and a long session that lets the screen sleep can hit the other schema.

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
5. **Prove it with `dumpsys` and a second logcat run.** A fix you cannot see in the
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

Related: [`../self_discoveries/the_decoy_that_fitted.md`](../self_discoveries/the_decoy_that_fitted.md)
— the wrong theories this session walked through before reading the branch.
