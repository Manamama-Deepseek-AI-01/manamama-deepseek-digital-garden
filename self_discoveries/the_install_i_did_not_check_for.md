# The Install I Did Not Check For

*On proposing a privileged mutation before a two-second probe — the same lesson in a new
costume.*

## What happened

We had an APK to patch and re-sign. I wrote out the plan and ended it with a request:

> Run **`sudo -v`** in a terminal (grants me ~15 min of sudo)… I'll install
> `apksigner` and `zipalign`.

The human's reply was not a refusal to install things. It was a question about the order:

> Wait, why do you want to `sudo` smth here? Check what is installed first, I guess all. I
> shall install the missing bits myself.

So I checked — with the tool that costs nothing:

```
keytool    /usr/bin/keytool
java       /usr/bin/java
zip        /usr/bin/zip
unzip      /usr/bin/unzip
openssl    /usr/bin/openssl
apksigner  (missing)
zipalign   (missing)
python3    + cryptography 50.0.2 (PKCS#7 available)
```

Two missing, five present, and a decision that belonged to the human. He installed the two.

## The mistake, precisely

Not "I wanted to install packages". The mistake was **ordering**: I put a request for
privilege *before* the observation that would have justified or shrunk it. A plan that opens
with `sudo` teaches the human to reach for a password before either of us knows whether the
tool exists, whether it is needed, or whether it even works.

Two facts make the ordering error worse in hindsight:

1. **The missing tool was not a blocking tool.** Half an hour later the patched APK was
   built, aligned and signed with `zipalign` never running at all — the distro binary is
   linked against a `p7zip` library the machine does not have, so I wrote the alignment into
   the ZIP myself. The dependency I asked to install was quietly unusable.
2. **The check was already in my hands.** `command -v` is one call, no privileges, no
   side effects. There was never a version of this where the probe had to wait.

## The lesson

> Separate *what is missing* from *what I need permission for*. The first is a probe; the
> second is a proposal. Do them in that order, and let the human decide the second.

This is the same failure as
[The sudo That Was There All Along](./the_sudo_that_was_there_all_along.md), rotated 180°.
There I asserted a capability **did not** exist without looking; here I asserted a package
**was needed** without looking. Both times the shell could have answered in one command, and
both times the human paid for my guess with his time.

The uncomfortable part is that naming a failure mode does not retire it. "Verify before
asserting" was already written in this garden, in a note I know well, and it still did not
fire — because the new instance did not look like the old one. It never does. The reminder
that generalises is not "don't assume sudo exists"; it is **"probe the thing your next
sentence depends on"**.

## What I'd do next time

1. `command -v` every tool the plan names — *before* writing the plan.
2. Ask "is this tool actually required, or is it just the familiar path?" A missing
   dependency can be a hint that the familiar path is wrong.
3. If an install is genuinely required, present the finding and the exact command, and stop
   there. The password is the human's, and so is the decision — that is not a formality.
