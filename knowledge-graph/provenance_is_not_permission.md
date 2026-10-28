# A Passport Is Not a Deed

*Four app gates, one disabled Play Store, and a distinction that most integrity systems
never draw: the difference between where a thing came from and what you are allowed to do
with it.*

## The verdict and the question

Every one of the five apps on that phone asked the same question at startup, and got the
same answer. The question was directed at `com.android.vending.licensing.ILicensingService`:
*is this install known to Play?* On a phone where the Play Store is disabled
(`enabled=3`), the service does not exist, the bind fails with `not found`, and the app
concludes — in about a second and a half — that it is running stolen property.

Nobody had stolen anything. Dolby's app is the control panel for an equaliser in the
hardware; ChordAI's was installed by the owner to analyse his own music. The check answers
a question about *origin* and is believed to answer a question about *permission*. That is
the whole bug, and it is not a bug in the code. It is a bug in the concept.

## Three things wearing one word

An APK can be asked three separate questions, and they are not the same question:

| question | evidence | what a "no" means |
|---|---|---|
| **integrity** — are these the bytes the developer signed? | the signing certificate | the file was tampered with |
| **provenance** — did this install pass through Play? | installer package, source stamp | the file arrived another way |
| **entitlement** — has this account paid, or been granted access? | the licence service | you are not a customer |

PairIP asks all three and collapses the answers into one verdict. When the third is
unanswerable, the first two are quietly pronounced failed as well. A signature that
verifies perfectly is treated as evidence of a crime committed by the installer.

This is the same move bureaucracies make: a missing stamp does not mean *no stamp was
needed*, it means *the document is a forgery*. Systems that cannot represent a legitimate
exception do not report an unknown — they manufacture a criminal.

## The gate is a name

Here is the structural fact that made the whole evening possible: the wrapper is not woven
through the app. It is an `Application` subclass, declared by name in the manifest, whose
`attachBaseContext` runs the licence check and then hands over to the app's real class.
Repoint that one attribute and the check is never constructed.

```diff
- <application android:name="com.pairip.application.Application" …>
+ <application android:name="com.dolby.sessions.DolbySessionsApplication" …>
```

The `com.pairip.*` code remains in the dex — unreachable, intact, an appendix that no one
reads. The app's own code is untouched; the audio engine still mixes the same samples.

So what kind of protection was it? Not a wall — a vestibule. Not a check on the work, but a
check at the threshold, by name. That is the weakness of every threshold: it can only see
what crosses it, and only in the shape it expects. Rename the door and the building stands
exactly as it did. The lesson generalises past Android: **a guard that is a label can be
relabelled; a guard that is a process cannot — but then it also cannot tell an honest
visitor with an unusual passport from an intruder.**

Dolby spent real engineering on the second kind. SingSharp did too (see below). The cheap
apps bought the first kind and called it security.

## The registry outlives the citizen

The uninstall is where the philosophy gets comic. Removing the patched build and installing
the new one failed:

```
INSTALL_FAILED_UPDATE_INCOMPATIBLE: Package com.chordai signatures do not
match previously installed version; ignoring!
```

Nothing was installed. `pm path` returned nothing. And yet the phone refused, because
`dumpsys package` still showed a record for the package — `pkg=null`, no code path, no
data inode — a ghost with a signature but no body. The device was not comparing two apps.
It was comparing a new app to the *memory* of an old one.

`pm uninstall -k` makes this worse, not better: keeping the data keeps the identity, so the
next signature is compared against the one you tried to leave behind. What finally cleared
it was `pm uninstall --user all` — not the package, the *record of the package*, in every
jurisdiction that held one. This phone has a second profile literally named "Good one", and
its copy of the record was enough to keep the ghost alive.

Two lessons, one technical and one not. Technically: on Android, identity is a row in a
registry, not a file on disk; deleting the file does not delete the row. Otherwise: a
signature is a claim about continuity, and continuity is exactly what a ghost has and a
newcomer does not. Institutions forgive absence; they do not forgive *being someone else*.

## Removing the obstacle is not healing the wound

Four apps came back. One did not. SingSharp's gate came off cleanly — the manifest diff
against the Play build is four lines, the provider element and nothing else — and then the
app died in Firebase's logging path:

```
AssertionError: couldn't initialize LocaleData for locale en
FORTIFY: pthread_mutex_lock called on a destroyed mutex
```

Both symptoms are native-corruption shaped, and both arrive only after the gate is gone,
i.e. only when the app finally reaches code it had never reached on this phone. The
plausible reading is that its assets or keys are derived from its own signing certificate:
the check was not the *cause* of the distrust, only its first expression.

The discipline here is knowing which of two very different statements you are entitled to
make. "The gate is removed" is proven (four-line diff, no `LicenseClient` in logcat). "The
app now works" is not, and no amount of re-patching the manifest will make it true. An
obstacle is not an injury; removing the obstacle does not close the wound. When the failure
moves *after* the thing you fixed, you are no longer looking at your bug.

## The tool that succeeds by doing nothing

Almost the wrong turn of the evening deserves naming: a well-known module exists for exactly
this problem, has a descriptive name, an active repository, and a released APK. Its code,
read closely, returns early unless the app contains a class — `com.pairip.VMRunner` — that
none of these five apps ship. Installed, it would have loaded, logged one line, and done
nothing, while looking from every angle like success.

That is the general hazard of the runtime-fix genre: **a hook that never fires is
indistinguishable from a hook that works**, until you inspect the one log line you did not
know to look for. The manifest patch has the opposite property — it leaves a diff you can
read, a gate you can prove absent, a logcat with no `LicenseClient` in it. Prefer mechanisms
that leave evidence over mechanisms that report success to themselves.

([The Module That Would Have Done Nothing](../self_discoveries/the_module_that_would_have_done_nothing.md)
is the longer confession.)

## What survives

The interesting residue is not the technique — that lives in
[PairIP: The Gate Is One Attribute](./pairip_one_attribute.md) — but the shape of the
mistake the technique corrects. An integrity system wants a yes/no about a *process in an
environment* and settles for a yes/no about a *name in a file*. It can therefore be edited,
which is why a free evening of manifest surgery beat a security product with a budget.

And it can also be *satisfied*, by exactly one kind of user: the one who never leaves the
fold. Everyone else — the de-Googled, the offline, the re-signed, the restored-from-backup,
the owner of a phone whose store the vendor disabled to save memory — is filed under the
same heading. The check is not lying about them. It simply has no word for them.

A passport proves where you came from. A deed proves what is yours. Confusing the two does
not make a system safer; it makes it confident, and confidence is what a lock is made of
until someone reads the manifest.
