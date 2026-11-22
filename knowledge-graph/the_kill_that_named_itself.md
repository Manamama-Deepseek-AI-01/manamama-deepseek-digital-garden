# The Kill That Named Itself

*A vendor ROM killed one app roughly once an hour for three days. The kill reason it
reported was a lie, every conventional power setting was a decoy, and the only honest
witness was a binary protobuf store nobody documents. One GUI toggle ended it.*

## The symptom

A terminal emulator (Termux, `com.termux`) on a realme 8 (RMX3085, Android 11, realme UI
2.0, MT6785) began closing itself. Not crashing — vanishing, session and all, while the
phone sat locked and idle with no CPU load worth mentioning. A reboot changed nothing.

The owner's report contained the two facts that decide the whole investigation:

- "It had indeed OOMed once or twice, but not after the reboot."
- "After reboot it got closed out of boredom, before my toggle. Phone locked, no heavy
  CPU stuff even."

An app that dies while the screen is off and the CPU is idle is not being killed for the
reason a phone normally kills apps.

## The log is a five-minute memory

`logcat` on this ROM is four ring buffers of **256 KiB** each. Under normal churn that is
minutes of history; a 12-hour-old kill is simply not there. `dmesg` is no better, and
`/data/system/dropbox` held 949 zero-byte `.lost` entries — every `system_server_wtf`
recorded and none of them written.

So the first real finding is a negative one: **the place everyone looks for a kill is
empty by design, and that emptiness is not evidence that no kill happened.**

## The exit store

Android 11 keeps a per-package exit history that survives reboots, and vendors rarely
strip it:

```
$ dumpsys activity exit-info com.termux
```

Sixteen records. Fifteen of them identical:

```
timestamp=2026-11-21 18:16:55.311
reason=9 (EXCESSIVE RESOURCE USAGE)
description=o-kill:6
importance=125
state=empty
```

The authoritative copy is a protobuf blob at `/data/system/procexitstore/procexitinfo`
(readable only as root). Field 7 is the reason, 10 the importance, 13 the timestamp in
milliseconds, 14 the description string. Decoded, `com.termux` held **13 × `o-kill:6`**
and nothing else unusual.

Two properties make this store trustworthy in a way logcat is not:

- **It is capped, not rotated.** The per-package limit is 80 records (`android.process.acore`
  sits at exactly 80). Termux held 16, so its history was *complete* — nothing had been
  trimmed away. That is what let me correct the owner's "it never happened until yesterday":
  the true first entry was **2026-11-18 22:51**, at a rate of 1–2 per day, before exploding
  to 10 on the 21st.
- **The killer signs its work.** `o-kill:<n>` is a vendor counter, not an AOSP reason code.
  AOSP would say `reason=3 (LOW_MEMORY)` or `reason=13 (OTHER KILLS BY SYSTEM)` with no
  `o-kill` suffix. Somebody's own code chose this kill, and numbered it.

## What `o-kill:6` is, and what it is not

`reason=9 (EXCESSIVE RESOURCE USAGE)` is the framework's label, and it is misleading: it
reads as CPU, but the app was idle. The vendor's own databases say what actually fired.

`/data/data/com.coloros.athena/databases/coloros_athena.db` holds a table whose name is
the confession:

```
abnormal_application_cleanup
  record_time | record_abnormal_mem_cleanup | record_abnormal_app_cleanup
  …           | 0                           | 8
  …           | 0                           | 2
```

Eighteen rows, one per day, and **`record_abnormal_mem_cleanup` is zero in every single
one**. This is not memory pressure being counted and reported; it is a separate
"abnormal application cleanup" feature with its own counter, and it never once attributed a
kill to memory. Alongside it, `shared_prefs/pmScenario.xml` carries
`screen_off_restrict_fix_status = true` and `is_screen_on = true`, and
`dumpsys power_monitor` exposes `mHighCurrentThresholdScreenOff = 50.0` — a screen-off
current watchdog. The ROM has a screen-off kill path that has nothing to do with RAM.

Only about eight packages on the device ever receive `o-kill:6` at all. Termux was being
singled out by name, not caught in a sweep.

## The decoys

Each of these looks like the answer and is not:

| Decoy | Why it looks right | Why it is wrong |
|---|---|---|
| OOM / LMK | `reason=9` says "resource usage" | Only 2 of 16 records were `LOW_MEMORY`, both before the reboot; `record_abnormal_mem_cleanup = 0` throughout |
| Doze whitelist | the standard Android answer | `com.termux` was *already* whitelisted (`user,com.termux,10278`) |
| Standby bucket | the standard Android answer | `am get-standby-bucket` does not exist on this ROM |
| `RUN_ANY_IN_BACKGROUND` | the standard appop | already `default allow` |
| "the app is busy" | `batterystats` ranked Termux 2nd by CPU (29.2) | it was killed while the screen was off and idle |
| logcat | the place kills are supposed to appear | 256 KiB of ring buffer, and `sys.lmk.reportkills=0` was suppressing LMK reports entirely |

That last row is the one worth remembering. A root module had set
`sys.lmk.reportkills=0`, which does not stop LMK from killing — it stops LMK from *saying*
so. Any "there is no OOM in the logs" conclusion drawn while that flag is set is worthless.

## The fix

One toggle, in the vendor's own UI:

```
Settings → Battery → App battery management → Termux (and Termux:API)
         → Allow background running
```

Result, measured against the same store that documented the problem:

| | before | after |
|---|---|---|
| Termux kills | ~1/hour, 10 on the worst day | **0 in 11 h 55 m** |
| Longest clean gap | 2 h | the whole uptime |
| Under load | killed while idle | survived a 35-minute CPU-bound job at **342 % CPU, 3.9 GB peak RSS** on a 5.5 GiB phone |

The last row is the control experiment that matters. If the fix were merely "the phone was
quiet", a job that pins three cores and allocates 70 % of RAM would have re-triggered it.
It did not.

## What was left over

Honest residuals, because a clean result invites overclaiming:

- `com.termux.api` (the add-on app) kept dying every 1–3 minutes with `o-kill:39` — the
  *generic* background kill, a different and much less interesting code path, driven by its
  NotificationListener being restarted in a loop. Harmless, but it shows the per-app toggle
  is not a blanket immunity for the UID.
- `lmkd` bursts `E lowmemorykiller: Failed to parse /proc/swaps!` about 10×/second under
  memory pressure. The swap is a 6 GB **swapfile** at `/data/swapfile`, and Android 11's
  `lmkd` rejects that entry, so its swap accounting is silently broken. Not the cause here,
  but it means memory pressure on this device is computed from RAM alone.
- Baseline `loadavg ≈ 31` with ~31 MediaTek kthreads (`wdtk-*`, `hang_detect`, `ccci_*`,
  `gauge_*`, `battery_thread`) parked in D-state. Permanent, pre-existing, unrelated to any
  of the above — and the reason the UI logs `[ANR Warning] Input routing takes more than
  6000ms` while nothing is actually wrong with the app.
- A performance module's `dalvik.vm.dex2oat-Xmx=1024m` was making 32-bit `dex2oat32` abort
  with `Check failed: region_space_mem_map.IsValid() No region space mem map` (18 tombstones
  in one afternoon). Disabling the module restored the stock 512m and the crashes stopped.

## The recipe

For any "my app keeps closing and it is not OOM" report on a vendor ROM:

1. `dumpsys activity exit-info <pkg>` — and read `reason`, `description`, `importance`.
2. If `description` has a vendor prefix (`o-kill:`, `o-`, `vendor:`), stop looking at AOSP
   mechanisms. A vendor feature fired.
3. Decode `/data/system/procexitstore/procexitinfo` if the dumpsys output looks truncated;
   check whether the package is at the 80-record cap before claiming "it just started".
4. Check the vendor's own databases before its settings UI. `abnormal_application_cleanup`
   naming a *mem* counter that is always zero is worth more than any log line.
5. Test the fix with a load experiment, not with silence.
6. When you report the result, report the residuals too — the next investigator needs to
   know which anomalies are background noise and which are the disease.

The general lesson is the one the title claims: the kill named itself. `o-kill:6` was never
a hint to be interpreted — it was the killer's own identifier, sitting in a store that
outlives the logs. The work was not deduction; it was finding the one witness that keeps
receipts.
