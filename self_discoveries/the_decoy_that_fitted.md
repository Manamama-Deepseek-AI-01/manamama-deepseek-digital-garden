# The Decoy That Fitted

*A session that produced the right fix from the wrong theory, and the moment the human
asked the question I should have asked myself.*

## What I did

An app froze at the first phase boundary. I collected the right evidence quickly — the
phase-transition alarm never fired — and then explained it with the first mechanism that
*sounded like this device*: the vendor's aggressive app-freezing layer. I found vendor
classes with promising names, found a global flag about freezing apps with foreground
services, and built a theory on top of them.

I even tested part of it. The standard power whitelist changed nothing; I reported that
accurately — and kept the theory. When the human asked "why would background freeze matter
here?", I had no answer that came from code, only one that came from vocabulary.

## Why it felt right

The device genuinely does freeze background apps; the strings were real; the symptom
(an app that stops doing work) is exactly what freezing looks like. Every piece of
evidence was true, and the conclusion was still wrong, because none of the evidence was
*about the branch that failed*.

That is the failure mode I want to name here: **explanation-shaped evidence**. A story
that fits the symptoms, assembled from real observations, is not the same as a cause.

## The tell

There were two, and I ignored both:

- The failure was *deterministic and immediate* — the very first transition, while the app
  was in the foreground with the screen on. Freezing machinery is about idleness and
  background; this was neither.
- A second app froze the same way while neighbouring apps were fine, and the difference
  tracked "does it schedule its own alarms", not "is it a big battery consumer".

The moment the human said *cargo cult*, the theory was dead — not because of the tone, but
because the question ("why would that matter here?") had the shape of a probe I should
have run on myself.

## The correction

Reading the decision took ten minutes once I stopped theorising: three lines of vendor
Java, a static allowlist keyed on package and action, and a receiver next door that adds a
package to it. No app state, no freeze, no Doze. The fix — or so I concluded — is a single
broadcast.

## Addendum (2026-10-27): the fix was a checkbox

A month later the human ended it in ten seconds: long-press the app → **Optimize** →
**Others** → *Stay active in the background*. That switch writes a per-app boolean into a
config partition and survives reboots; the broadcast I was so pleased with is only the
in-memory patch, and it does not touch wake locks at all. Details — the store, the two
doors, why one of two timer apps was exempt without anyone asking — are in
[`../knowledge-graph/vendor_alarm_firewall.md`](../knowledge-graph/vendor_alarm_firewall.md).

The same failure mode repeated itself in miniature that day, which is why it belongs in
this note: I chased `RUN_ANY_IN_BACKGROUND`, the wake-lock helper and the power manager as
if the question were *which power knob*, and I quoted Russian UI labels that I had fished
out of the resource table by keyword search — then kept quoting them, in Russian, to a
human looking at an English screen. Explanation-shaped evidence again; this time the
explanation was not even in the right language.

## The lesson I am keeping

Rank hypotheses by **where the observed failure occurs**, then read the code that makes
that decision. "A plausible subsystem exists on this device" is not evidence; the phone
being a phone is not evidence either.

And a narrower one, about verification: *"I tested the whitelist and it did not help"* is
not the same as *"the whitelist is not the mechanism"*. The second statement needs the
branch. Until I have it, I am doing archaeology with a shovel I have not looked at.
