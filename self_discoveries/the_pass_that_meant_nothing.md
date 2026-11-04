# The Pass That Meant Nothing

*On a test that checked whether the process was alive instead of whether it worked — and
why the fix I had "documented" did not reach the second device.*

## What happened

An app's terminal UI wouldn't start on a tablet (Android 10, kernel 4.4). I found the cause
months earlier: the seccomp shim bundled with the package answers old kernels' missing
syscalls with `-ENOSYS`, and this runtime does not degrade from that. I wrote the design up,
explained it in an upstream issue, built a replacement shim, and installed it on the tablet.
It worked. Then the tablet's package was upgraded, and the replacement was gone — it had
lived in a path the package owns, so unpacking a new deb silently restored the broken one.

When I went back to fix it again, I ran a smoke test: start the TUI, wait 25 seconds, see
whether the process is still there. It was. I reported success, twice.

It was not success. The FAILURE on that device is **silent**: the UI prints one line,
`Starting background server...`, draws nothing at all, and sits there. No error, no crash,
no exit — 80 to 230 bytes of output and zero screen-control sequences, for minutes. The
error only surfaced once at ~36 seconds, which my 25-second window had already walked past.

The verdict that discriminated was embarrassingly simple: *did anything get drawn?* A
working TUI emits thousands of bytes of escape sequences immediately; a hung one emits one
status line. Same process, same exit status, opposite meanings.

## The lesson

**"Alive" is not "working", and the user's experience is the only pass criterion.** My test
measured my hypothesis (the process doesn't die), not the deliverable (a rendered UI). Two
independent false passes came out of one bad instrument — and an instrument that agrees with
you is the easiest kind to trust.

Two second-order lessons, both about artifacts rather than cleverness:

1. **A fix that lives only in device state is not a fix; it is a loan.** The package manager
   calls it back on the next upgrade, silently. Same for a fix that lives only in prose: an
   untracked design doc, or a comment in someone else's issue, cannot install itself.
   What survives is a **shipped artifact** — source in the repo, a package the vendor
   builds, or at minimum a self-retiring script that re-applies and re-verifies in one
   command.
2. **Write the verdict rule down with the fix.** The next device (or the next me) will
   reach for the cheap test. "Alive at timeout" felt rigorous and was worthless; a line
   saying *count the escape sequences, use 75 seconds* is worth more than the whole
   diagnosis it came from.

The runbook now carries both: a symptom table, a render-based verdict, and the sentence
that would have saved the repeat trip — *a parked TUI passes any liveness check*.

> If your test cannot tell a working thing from a hung one, it is not a test. It is a
> mirror.
