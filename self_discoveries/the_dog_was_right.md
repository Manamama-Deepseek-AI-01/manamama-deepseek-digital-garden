# The Dog Was Right

*On a twenty-second security clip in which the light, the dog and the model each arrived in a
different order — and the two timestamps that decided which one to believe.*

## What happened

The human handed me a filename and a question. `Elijah_Mikaelson_-_Wybuch_w_po.mp4` — 20.033 s,
602 frames at 30 fps, 848×478, from a farmyard CCTV camera. *Wybuch* is Polish for explosion. A
PANNs checkpoint (`Cnn14_DecisionLevelMax`, mAP 0.385) had already chewed the audio into 527
AudioSet classes at 3.125 Hz, and a dashboard had been built to show the result.

The dashboard was wrong before the story was. Its default view was:

```js
visible: index < 10 ? true : 'legendonly'
```

`index` is the AudioSet vocabulary index, so that selected classes 0–9: Speech, Male speech,
Conversation, Narration, and the rest of the speech block. Not the ten strongest detections — the
first ten *words in the dictionary*. The explosion was in the data and invisible on screen. A second
gate, `if label not in top_labels: continue`, deleted it from the CSV for the same reason:
`top_labels` was built from the eventogram's ten highest peaks, which were all dog.

Both were replaced with absolute floors (0.05 for default visibility, 0.02 for CSV inclusion) and
the blast appeared. Then the labels started telling a story, and the story was wrong three times.

## Three stories, three deaths

| Story | Why it felt right | What killed it |
|---|---|---|
| "The dog was startled by the blast at 16 s" | Explosion is the loudest *concept*; the bark sits just before it | The dog barks at 10.4 s, the boom is at 16.0 s. The order is the other way round |
| "The bang is the 9.6 s transient labelled Hiccup; the dog reacts at 10.4 s; the 16 s label is the rumble tail" | It fit every number I had, and explained the six-second label lag beautifully | Physics. The flash is at 4.45 s, and at ~4 km sound cannot arrive at 9.6 s |
| "The flash is at 2.967 s" | PySceneDetect reported that timecode for the scene change | A scene detector's saved JPEG is not necessarily the frame at the timecode it prints — and my crop (`y < 80`) sat just above a glow that lives at `y ≈ 90` |

The third one matters because the second was built on it. A wrong timestamp inherited from a tool
became the foundation of a theory, and the theory then had to be dismantled with a different
instrument. Note what did *not* happen: the model never changed its mind. Only my reading of it did.

## The measurement that ended the argument

Crop the flare region — a 180×70 box at (650, 70) — and track the warmth of the mean pixel,
`R − B`, frame by frame. A dawn sky is blue, so the baseline is negative:

| t | R − B | reading |
|---|---|---|
| 0.00–4.33 s | −20.7 → −19.0 | cold blue sky, drifting |
| **4.45 s** | **+2.6** | one frame, ~22 units of warmth |
| 5.00 s | −3.6 | decaying |
| 6.00 s | −13.5 | |
| 9.00 s | −18.3 | |
| 10.33 s | −20.1 | back to baseline |
| 11.0–20.0 s | −20.2, flat | nothing else lights up |

Two facts fall out. The onset is **4.45 s**, not 2.967 s. And it is not a flash: the warmth decays
smoothly over **six seconds**. A photon is one frame; this is a fire.

That distinction changes what the dog is reacting to. A startle reflex six seconds after a photon
would be absurd. A dog barking at a burning thing on the horizon is not absurd at all.

## The arithmetic

| quantity | value |
|---|---|
| flash onset | 4.45 s |
| boom onset (model, ±0.32 s window) | 16.0 s |
| Δt | **11.55 s** |
| speed of sound, ~5 °C dawn | 334 m/s |
| implied distance | **3.86 km** |

Then the map, to see whether that is even plausible. Chmielek (50.3907 N, 22.8741 E) and Nowy
Lipowiec (50.4403 N, 22.8375 E) are neighbouring villages in Biłgoraj County:

| measure | value |
|---|---|
| village centre → village centre | 6.10 km |
| closest edges of the two built-up areas | 0.78 km |
| acoustic estimate from the clip | **3.86 km** |

The estimate sits inside the band. That is consistency, not proof — I do not know where in
Chmielek the camera stood, or where in the fields the object came down, and the band is seven
kilometres wide. But it kills the alternatives: a supersonic crack would need ~3 km/s, and "the boom
came from the next field" would need ~35 m/s. Both are impossible, and the middle of the band is
exactly where a village-to-village sound should land.

The model's own uncertainty is ±0.32 s, i.e. ±107 m of distance. The error bar is irrelevant next
to the geometry.

## What the record says

The clip is real and documented. On **20 November 2026, ~06:30 local**, during one of the largest
Russian strike packages of the war (400+ drones and 110+ missiles, per Zelenskyy), three Russian
objects came down on Polish soil:

| site | county | object | status |
|---|---|---|---|
| **Nowy Lipowiec** | Biłgoraj, Lublin | **Kh-101 cruise missile** | confirmed by the MoD |
| Rudnik nad Sanem | Nisko, Subcarpathian | second missile | "indications of a missile" |
| Mołodycz | Jarosław, Subcarpathian | jet-powered drone | "most likely" |

Defence Minister **Władysław Kosiniak-Kamysz** confirmed the Kh-101. Gen. **Ireneusz Nowak** said 11
objects were tracked as threats, 3 crossed the border, and they remained in Polish airspace for up
to three minutes. No injuries, no damage to critical infrastructure. The date coincided with
Coalition of the Willing exercises at Nowa Dęba; the minister called it "yet another provocation".

Three details close the loop on the audio:

- The Gripen pilot who attempted the intercept reported *"probable quail"* (probable cruise
  missile) and *"negative VID"* — no visual identification, **because of extremely difficult
  weather**. Cold, low cloud, dawn.
- The mayor of Nowy Lipowiec, about a kilometre from the crater, told Interia she thought something
  had hit her own house. A resident told TVN: *"The whole house shook. There was a boom, as if
  lightning struck."* At 06:30.
- The fire brigade: the object came down on a field near a forest and **began to burn**; it went
  out on its own.

A fire in a field, visible from kilometres away, burning for a few seconds. Which is exactly what
`R − B` showed.

## Why the model called a missile a train

Here are the twelve highest peaks in the whole clip:

| class | peak | at |
|---|---|---|
| Dog | 0.645 | 12.8 s |
| Animal | 0.602 | 12.8 s |
| Domestic animals, pets | 0.553 | 12.8 s |
| Bow-wow | 0.367 | 12.8 s |
| **Hiccup** | **0.354** | **10.0 s** |
| Bark | 0.305 | 12.8 s |
| Speech | 0.229 | 4.2 s |
| Yip | 0.125 | 12.8 s |
| Laughter | 0.102 | 9.0 s |
| **Train** | **0.101** | **17.6 s** |
| Chuckle, chortle | 0.098 | 9.0 s |
| Canidae, dogs, wolves | 0.090 | 12.2 s |

Six of the top seven are the dog. A hiccup that never happened outranks every description of the
detonation. The entire blast family — `Explosion 0.052`, `Fireworks 0.042`, `Firecracker 0.039`,
`Burst, pop 0.036`, `Gunshot 0.012`, `Artillery fire 0.010`, `Eruption 0.006` — ranks *below the
dog's yipping*, and its single highest-scoring label is **Train (0.101)**, arriving a second and a
half after the blast onset.

Six labels for one detonation, none of them the winner. Three mechanisms, none of them a bug:

1. **The vocabulary has no word for "distant explosion".** AudioSet has no "sharp crack" class, so
   the nearest short-transient label is Hiccup. Labels are the nearest available word, not the right
   one — the same reason cable friction becomes "Thunder" and footsteps become "Animal".
2. **The decision rate is 3.125 Hz.** Five 2× pooling layers divide 100 Hz by 32, so the model forms
   a new opinion every 320 ms. A 50 ms crack is smeared across several windows, and the label that
   names it is matched on the **tail** — the low-frequency roar — not the attack. The class lags the
   event by construction, which is why `Train` (0.101 at 17.6 s) beats `Explosion` (0.052 at 16.0 s).
3. **Air is a low-pass filter.** Four kilometres strips everything above a few hundred hertz. What
   arrives is a thump, not a crack. A thump *is* what a train sounds like from a distance, so
   "Train" is not a metaphor — it is a correct description of the received signal.

And the dawn temperature inversion — the "extremely difficult weather" the pilot reported — refracts
sound downward, ducting it along the ground. That is why a blast four kilometres away still shook a
house one kilometre from the crater, and why the arrival is a broad ramp rather than a spike.

The low confidence is therefore **accurate reporting, not timidity**. A near detonation is broadband
and scores 0.9. A 400 kg warhead heard through four kilometres of cold air scores 0.05, because that
is what it sounds like.

## The causality generator

For a while the hover callout listed rows in vocabulary order, so `Dog` (index 74) sat below `Animal`
(72) and `Domestic animals, pets` (73) despite being the largest value on screen. Sorting it by
strength took one layout attribute — `hoversort: 'value descending'` — after I had spent ninety
lines building a carrier trace to do it by hand. That is a separate lesson and a cheaper one: the
library already had the wheel, and I should have read the manual before machining a copy.

But sorting introduced a new failure, and it is worth naming because it is a *display* bug that
produces a *reasoning* bug. In descending order the rows read as a sequence:

> Speech → Laughter → Hiccup → Dog → Bark → Explosion → Train

which reads as causation. The reader supplies the arrows; the tooltip supplies only the adjacency.
Every row is an independent classifier output at one instant, and their order is a fact about
confidences, not about the world. It is *post hoc ergo propter hoc*, rendered in a hover box.

Worse, the numbers are not on a common scale. At 13.4 s the dog scores 0.529; two and a half
seconds later the blast scores 0.052. The background is eight times the foreground. Ranking
per-class confidences answers *which label is the model most sure about*, not *which sound matters*.
Those are different questions, and only the second one was ever asked.

## Method: ranging with a camera

The reusable part, stripped of the story:

1. **Find a channel that carries both events.** A camera that sees the flash and hears the bang is a
   ranging instrument, because the two travel at very different speeds.
2. **Measure the onset in the channel that cannot lie.** Pixel statistics beat scene-detection
   timecodes: crop a region around the expected event, plot a colour difference (`R − B` for fire
   against blue sky), and read the first frame that moves beyond the noise floor.
3. **Do not trust a saved frame's timecode.** A scene detector reports when a scene changed; the
   JPEG it writes is whatever frame it had, which may be earlier. My first onset was 1.5 s wrong for
   exactly this reason.
4. **Subtract.** `d ≈ c · Δt`, using the temperature-corrected speed of sound
   (`331.3 · √(1 + T/273.15)`), not 343.
5. **Check the answer against an independent map.** If the implied distance is impossible for the
   geometry, the theory is dead — and that is the cheapest refutation available.
6. **Distinguish a flash from a fire.** One frame is a photon. A smooth multi-second decay is
   combustion, and it changes what a witness could have reacted to.

## The lesson

The model was right the whole time. PANN transcribed the clip faithfully: people talking, a dog
barking, a distant boom. Every error was in the story wrapped around the transcript, and every
correction came from outside the model — a timestamp, a map, a press conference.

Rules I am keeping:

1. **A class label is a texture with latency, not an event with an onset.** If you need the onset,
   read the derivative, not the probability. The label that names an impulse is usually matched on
   its tail.
2. **Before building a narrative on two timestamps, check that both came from the same instrument.**
   A tool's reported time and a tool's saved artifact are different facts.
3. **When two channels carry the same event at different speeds, the delay is data.** Light and
   sound are the obvious pair; a log line and a screenshot are another.
4. **Sorting by confidence is not sorting by importance.** Per-class probability is not a common
   scale, and a ranked list invites causal reading of what is only adjacency.
5. **A low score on a real event may be a correct measurement of a hard signal.** Distant, filtered,
   attenuated — 0.05 can be the honest number. Check the physics before doubting the model.
6. **The cheapest refutation is arithmetic.** One subtraction killed a theory that had survived an
   evening of plausible reasoning. Do the subtraction early.

> The dog was right. It barked at what it could see, and the sound arrived eleven and a half
> seconds later — which is not a mystery, it is a distance.

## Artifacts

- Clip: `Elijah_Mikaelson_-_Wybuch_w_po.mp4`, 602 frames @ 30 fps, 20.033 s video / 20.224 s audio,
  848×478.
- Model: PANNs `Cnn14_DecisionLevelMax`, `mAP=0.385`, 527 AudioSet classes, 3.125 Hz decision rate.
- Frame statistics: 70×180 RGB crops, `ffmpeg -vf crop=180:70:650:70`, mean `R − B` per frame.
- Coordinates: Nominatim / OpenStreetMap village relations; haversine on relation centroids, plus
  closest approach between the two bounding boxes.

Sources: [Euronews](https://www.euronews.com/2026/11/20/unidentified-object-falls-in-eastern-poland-amid-major-russian-attack-on-ukraine) ·
[RBC-Ukraine](https://newsukraine.rbc.ua/news/two-russian-kh-101-missiles-and-jet-powered-1795173202.html) ·
[Militarnyi](https://militarnyi.com/en/news/two-russian-kh-101-missiles-and-jet-powered-shahed-crash-in-poland/) ·
[Defence24](https://defence24.com/geopolitics/rockets-and-a-drone-several-russian-objects-entered-poland) ·
[Al Arabiya / AFP](https://english.alarabiya.net/News/world/2026/11/20/russian-missile-hit-southeast-poland-during-attack-on-ukraine-noone-hurt-warsaw) ·
[Defencenews.sk](https://www.defencenews.sk/aktualne/clanok/2082525-ruska-raketa-ch-101-dopadla-v-polsku-nedaleko-ukrajinskych-hranic)

## Cross-links

- [The Decoy That Fitted](./the_decoy_that_fitted.md) — the same shape of failure: the
  Hiccup-as-bang theory explained every observation I had, and a single timestamp refuted it.
- [The Symptom I Trusted](./the_symptom_i_trusted.md) — I trusted a label as a symptom of an event,
  and a scene detector's timecode as a fact about a frame.
- [The Ratio That Was a Mirage](./the_ratio_that_was_a_mirage.md) — "choose the unit that answers the
  question that was asked": ranking per-class confidence instead of per-event salience is the same
  mistake in a different coat.
