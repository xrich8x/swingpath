# Point-boundary label protocol

> Written so the founder can run the ~3-6 h labelling session queued at
> `docs/DECISIONS_PENDING.md` item 4 without me in the room. That queue is explicitly
> **blocked** on this document landing — the cost of a vague protocol is founder hours
> spent twice, not a re-run of a script. Everything below is designed against that cost.
>
> **What this document is not:** it does not design the scoring state machine or the
> rally segmenter (`segment_rallies` already exists and is a different piece of work —
> see `docs/evidence/the-score-and-rally-count-stop-pretending.md`). It produces the
> **evaluation labels** those consumers will eventually be checked against. Point
> boundaries are LOGIC under this project's own architecture rule (a deterministic rule
> over ball-in-play state and bounces, not a learned perception task) — so nothing here
> is a training set. It is evaluation-only, forever, per `[[point-boundary-ground-truth]]`.
>
> **Rule 11 compliance, stated once, applies to every section below:** every field
> defined here is filled by a human watching the actual match unfold on video — never by
> reading a scoreboard, HUD, or any burned-in graphic. `docs/evidence/using-a-burned-in-
> scoreboard-as-ground.md` is the record of that being tried and reverted; nothing here
> revisits it. A labeller may use ordinary tennis literacy (recognising a winner, a fault,
> a let) from watching the rally — that is observation of the game, not data entry about
> it, and is the same category of compliant source as a ball click.

---

## 1. What marks a point's start and end

Split deliberately into two questions with different achievable precision, per
`[[point-boundary-ground-truth]]`: **how many points, and roughly where** (humans agree on
this almost perfectly — it is a discrete countable event) versus **the exact boundary
frame** (genuinely fuzzy at the edges, and no amount of instruction-tightening removes
that fuzziness — see §4 and the "what this cannot fix" section at the end). The
definitions below are built to make the countable half unambiguous and to bound, not
eliminate, the fuzzy half.

### START

**The point starts at the video frame nearest the serving player's racket making contact
with the ball on the FIRST serve attempt of that point** — whether or not that first
serve is good. A fault does not start a new point; it is a continuation of the same point
(this matches actual tennis rules: the server gets two chances before the point is lost).

- If the first serve is a fault, the **second serve's contact frame** is recorded as a
  separate `serve_fault_count`/second-serve marker (useful for `derive_serve_order` in
  `schema.py`, see §2) but does **not** start a new point — the point's `start_frame`
  stays the first serve's contact frame.
- A **let** (serve clips the net, lands in the correct box) is **not** a point start or
  end at all. It is a replay: label it as its own zero-duration event (`is_let: true` on
  the record, see §2) and the point's real `start_frame` is whichever serve contact
  eventually puts the ball in play. If the labeller cannot tell whether a let occurred
  (can't see the net contact, can't hear it) — **REFUSE** that determination rather than
  guessing which serve attempt "really" started the point (see the refusal list below).

### END

**The point ends at the video frame of the event that decides its outcome** — one of:

| End reason (record verbatim) | Frame to mark |
|---|---|
| `unreturned_bounce` | the ball's second bounce, when no opponent contact intervened |
| `net_or_frame` | a shot strikes the net without crossing, or hits any part of the frame/post that ends the rally |
| `out` | the ball lands clearly out and no return is attempted |
| `double_fault` | the second serve's own fault (net/out), which ends the point immediately |
| `stoppage_no_replay` | a player stops play by rule (calls a ball out and it's accepted, catches a ball, injury) and no let/replay follows |

### Dead time — defined operationally, not labelled separately

**Dead time is not its own field.** It is derived, always, as the interval between one
point's `end_frame` and the next point's `start_frame`. Labelling it separately would be
gold-plating (per the brief's own warning) — every extra clicked field costs founder
minutes multiplied by every point, and this one is arithmetic on fields already
collected. This interval covers ball retrieval, walking back, toweling, second-serve
prep, and changeovers uniformly; nothing about it needs a distinct annotation.

### Ambiguous cases — REFUSAL is a valid label, a forced guess is pollution

Every case below gets a specific instruction, not "use your judgement" (that pattern is
the measured negative in `docs/evidence/telling-labellers-the-rule-instead-of-enforcing.md`
— a stated rule with no mechanical enforcement produced WORSE labels than the round
before it, because a written instruction is not a control). Since there is no second
labeller and no converter to mechanically enforce this on (see §4), the enforcement here
is that **every refusal has its own boolean field** (§2) so a downstream consumer can
mechanically filter refused points out, rather than trusting a labeller's judgement call
silently baked into a guessed timestamp.

- **Let (serve)** — not a start or end; see above. If undeterminable, `refused: true`,
  `refusal_reason: "let_unclear"`.
- **Second serve / fault** — continuation, not a new point; see above. Not refusable in
  itself (a fault serve is always visually clear — ball landed out or into the net); if
  genuinely unclear which serve attempt is which, refuse the whole point rather than the
  fault marker alone.
- **A rally that dies with no clear winner** (e.g. simultaneous double-hit dispute, a
  ball that clips the net cord and the camera angle can't show which side it landed on,
  a spectator/dog/second ball intrudes) — `refused: true`, `refusal_reason:
  "no_decision"`. Still record the `start_frame` (the point's existence is not in doubt,
  only its resolution), but `end_frame: null`.
- **Player retrieving a ball mid-point** (a stray ball rolls onto court, forcing a
  stoppage) — this is a rule-legal let-equivalent. Mark `refused: true`,
  `refusal_reason: "stoppage_ball_intrusion"` if play resumes as a genuine replay of the
  SAME point; do not invent an end_frame for the interrupted attempt.
- **Untelevised / off-screen gap** (camera pans away, cuts, or the frame is empty for a
  stretch) — `refused: true`, `refusal_reason: "off_screen_gap"`, with a note giving the
  visible bracket (frame the gap starts being invisible, frame it resolves). **This is a
  hard limit on what labelling can recover** — see the closing section.
- **Between-points warm-up rally** (players hitting practice balls before the receiver
  signals ready) — this is not a point. Do not label it at all; the null hypothesis is
  "no point here," and only a recognised START event (serve contact) creates a labelled
  point. The same rule applies to the **pre-match knock-up**: do not attempt to label
  anything before the first real point of the match. If the raw clip's start is
  ambiguous (a knock-up that blurs into match play with no clear first-point marker),
  set the session-level field `warmup_excluded_before_frame` to the first frame the
  labeller is confident is real play, and do not label anything earlier.
- **A dispute or coaching violation that a labeller cannot resolve without a
  scoreboard** — refuse rather than infer the outcome from anything except the video
  itself. (This is the direct, load-bearing consequence of rule 11: if the honest answer
  requires reading a score overlay, the honest label is REFUSED, not a value read off
  the barred source.)

---

## 2. What gets recorded per point — minimum field set

One record per point (plus session-level fields once per clip). Every field below is
tagged with which of the three downstream uses it serves — **scoring** (sets/games),
**clip segmentation**, **dead-time trimming** — so nothing is collected without a named
consumer.

| Field | Type | Serves | Why it's here, not gold-plating |
|---|---|---|---|
| `point_id` | int, sequential per clip | provenance | needed to reference a point at all |
| `start_frame` | int | clip seg, dead-time | the primary boundary |
| `start_type` | `"first_serve"` (always, per §1) | scoring (serve stats) | distinguishes fault-continuation from a true new point at review time |
| `end_frame` | int or `null` | clip seg, dead-time | the primary boundary; `null` iff refused |
| `end_reason` | enum from §1's table, or `null` | scoring, dead-time | scoring needs to know fault vs winner vs error to validate `derive_serve_order`; dead-time needs to know the point actually closed |
| `point_winner_side` | `"near"` \| `"far"` \| `null` | scoring only | the ONE field that exists purely to let a future scoring evaluator check itself — cut this first if the session runs long, since scoring is the least time-pressured of the three consumers (STATE.md already reports the layer as unvalidated with no user-facing claim riding on it yet) |
| `serve_fault_count` | 0 or 1 | scoring only | feeds `derive_serve_order`'s first/second-serve split validation |
| `refused` | bool | all three | the mechanical filter described in §1 |
| `refusal_reason` | enum from §1, or `null` | all three | lets a downstream consumer distinguish WHY a point is untrustworthy, not just that it is |
| `is_let` | bool | scoring | a let is a replay event, not a point; recorded so it isn't silently absorbed into `serve_fault_count` |
| `notes` | free text, optional | none (human aid only) | cheap escape valve for anything the enum set didn't anticipate; not scored, just read by whoever debugs a weird disagreement |

**Session-level fields, once per clip:** `clip` (raw basename, never renamed — trap T17),
`fps` (from the source video, needed to convert frame↔seconds for a tolerance-based
metric), `labeller`, `created` (timestamp), `warmup_excluded_before_frame` (int or null,
per §1).

**Deliberately NOT a field:** a separate dead-time start/end (derived, see §1); a
per-shot breakdown within the point (that is the shot detector's job once it runs, not a
label a human needs to produce — the point boundary is the only new ground truth this
protocol creates); anything about ball trajectory, speed, or bounce location (those are
either already the ball-gold labelling protocol's job or the analyzer's own geometry —
out of scope here and would duplicate an existing, different gold set).

---

## 3. Which footage, how much, and what the resulting n can and cannot support

**Only 9 files in the repository qualify as continuous, full-length match video at all**
— everything else has already been cut to single points (`split_by_serve.py`'s output,
which bakes in its own boundary guess and so cannot supply an independent boundary label)
or is a court-calibration still-frame set. They live in
`data/incoming/Raw - Do Not Process/` and split **7 Hardcourt, 2 Clay, 0 Shell, 0 Grass**
(table below, reproduced from `docs/evidence/audio-impact-screen-blocked-by-tooling-plus-
gt-cost.md` — not re-derived here, since re-listing the directory would just reproduce
the same table at the cost of a tool call). **This matches the founder's own queue scope
(Hardcourt + Clay only) exactly — no footage is being left out of the plan by choice.**

| Raw file | Title (verbatim, truncated) | Surface |
|---|---|---|
| `L73ep7JHiJ4` | UTR 10 vs UTR 10 Singles Practice Match [1st Set] | Hardcourt |
| `tc8CGFxyRE8` | USTA 5.5 vs USTA 5.0 or UTR 12 vs UTR 10 | Hardcourt |
| `uR5q2cSM6AY` | INSANE Point Play! 12 UTR vs 13yo Junior | Hardcourt |
| `HoHxFSX_gLk` | I Challenged a 12 UTR to Slice Only | Hardcourt |
| `e8T34KoJzOw` | USTA 4.5 vs UTR 12.5! | Hardcourt |
| `A7vXlWIlyrI` | Almost 50, Out Of Shape & SUPER GOOD! (UTR 9 vs 9) | Hardcourt |
| `UHf0LeMU2pg` | 7 UTR vs 8 UTR | Hardcourt |
| `CYqapSq5llo` | My Opponent Hits & Acts CRAZY!! UTR 9 vs 10 | Clay |
| `sAjkpeRq4P4` | Amateur Tennis - Full Match - LK 13.4 vs LK 15.8 (NTRP 4.0) | Clay |

Durations are **unmeasured** (title-based guesses only, no `ffprobe` pass has been run) —
flagged, not disguised as a number. That is exactly what the §3 prerequisite scrub below
exists to fix before any labelling hour is spent.

### How much to label: a stopping rule, not a fixed list

Rather than pre-committing to specific unmeasured-duration titles, **scrub all 9 first
(§ "what the founder actually does"), then label in ascending duration order, with both
Clay clips guaranteed included (there are only two — excluding either would leave the
surface unrepresented for no reason), stopping at whichever comes first:**

- **~3 hours of source video labelled** (soft target — the low end of the priced range,
  and the point at which the count/tolerance claim below becomes supportable), or
- **4.5 labelling-hours elapsed** (hard stop — see the hours estimate at the end for why
  4.5, not 5 or 6).

This reuses the pricing already done in `docs/evidence/audio-impact-screen-blocked-by-
tooling-plus-gt-cost.md` (30-45 min human time per 30 min of video, ~60-80 points per 30
min) rather than re-deriving it: **3-6 h of source video labelled ≈ 300-600 points across
4-5 matches.**

### What that n supports, and what it does not

**Supports:**
- A **point-count agreement** check against any automated proposal (the near-perfect
  half of the problem, per `[[point-boundary-ground-truth]]`).
- A **tolerance-based** start/end alignment metric (± N seconds, N set by the
  self-agreement measurement in §4 — never a raw tIoU against one annotator's frame,
  which Sigurdsson et al. 2017 (ICCV, re-annotating Charades/MultiTHUMOS) show is
  mostly measuring annotator noise: median start error 0.9±0.8 s, end error 1.4±1.4 s,
  even among trained annotators on shorter actions than a tennis point).
- A first-order sanity check of `derive_serve_order`'s first/second-serve and fault
  logic (`schema.py`) against `start_type`/`serve_fault_count`.
- Enough points to notice if `segment_rallies`'s tennis-rule branch (currently firing
  **0 of 62** times on `yt_match40` — it is a stopwatch wearing a rule's clothes, per
  `docs/evidence/the-score-and-rally-count-stop-pretending.md`) ever starts firing at
  all, once/if the ball-in-play chain improves enough to feed it.

**Does not support:**
- Anything for **Shell or Grass** — zero eligible footage exists; see the closing
  section.
- A **tight rare-event rate** (lets, double faults, disputed no-decisions). If lets occur
  at a rough ~1-in-20-points rate, 300-600 points yields only ~15-30 examples — enough to
  sanity-check that the definition in §1 is usable, nowhere near enough to tune a
  detector's precision on lets specifically.
- A **frame-exact** boundary claim of any kind, by construction (see above).
- Any claim about **inter-annotator** agreement — there is one labeller (the founder);
  see §4 for exactly what that limits.

---

## 4. Verification with no second labeller

There is no second labeller, so **inter**-annotator agreement cannot be measured — only
**intra**-annotator (self-) agreement, which is a strictly weaker guarantee (it says "this
person is internally consistent," not "an independent observer would agree"). State that
limit plainly rather than letting a self-agreement number quietly stand in for the
stronger claim.

**The check:** after finishing the labelling pass, wait **at least a day** (so the
re-label isn't just short-term memory of the first pass), then re-label a **fixed
15-20 minute segment** of one already-labelled clip from scratch, blind to the first
pass's timestamps (reopen the raw video, not the saved `.points.json`). A fixed segment,
not a random 10% of the whole set, is the cheaper and equally informative choice here —
it bounds the added time to a known ~15-20 minutes rather than scaling with however much
got labelled, and a systematic definitional problem (the kind this check is meant to
catch) will show up in any 15-20 minute window, not just a large one.

**Pre-registered bar:**
- **Point count** in the re-labelled segment matches the first pass's count for that
  segment **exactly**, or the discrepancy is itself attributable to a REFUSED point in
  one pass and not the other (i.e. not a silent miss).
- **Median |frame disagreement|** on matched start/end pairs is **≤ 1.0 s** (30 frames at
  30 fps, 60 at 60 fps) — set at Sigurdsson's measured end-boundary noise floor for
  *trained* annotators on shorter actions, so this project's own bar is not tighter than
  the published literature's evidence that boundary noise of this size is normal, not a
  labelling failure.

**If it passes:** the labels are usable, and — critically — **any downstream tolerance
metric must be quoted at this measured band, never tighter.** Publishing a tighter
number than what self-agreement supports would be measuring annotator noise and calling
it model error, the exact trap `[[point-boundary-ground-truth]]` already named.

**If it fails** (point count differs by more than a refusal-attributable gap, or median
disagreement exceeds 1.0 s): the ambiguous-case wording in §1 needs to be tightened
before trusting the rest of the set — re-read §1's table against the specific frames that
disagreed and add a missing case, rather than either (a) re-doing the whole 3-6 h pass
blind, or (b) quietly widening the tolerance band to make the number pass, which rule 2
(a failed gate stays failed) forbids.

**A free, zero-extra-hours triangulation, run after labelling, not instead of the check
above:** feed each labelled clip's raw video through the existing pipeline's
`segment_rallies(..., with_reasons=True)` and compare its guessed boundaries against the
human labels, point by point. This is **not** ground truth (rule 11 does not bar our own
derived geometry/logic, only overlays) and is not a substitute for §4's self-agreement
check — it is a corroboration signal, and, honestly, a weak one today: STATE.md already
reports `segment_rallies` resolving almost entirely via its 2.0 s timeout fallback (62 of
62 on `yt_match40`) rather than the tennis-rule branch, so most of what this comparison
will show is "how far off a bare stopwatch is," not "how good the rule-based logic is."
Run it anyway — it costs nothing beyond code that already exists, and any point where the
stopwatch and the human label land far apart is a good, free candidate for the founder to
double-check by eye before trusting that specific record.

---

## 5. The leak guard

**Precedent, read directly from the repo, not assumed:** the ball gold-leak guard is
`train_ballnet.gold_source_videos`, keyed on video **basename** (never on folder location
or any other identifier — `data/incoming/README.md` states directly that a rename
silently defeats it, trap T17). Court gold has its own guard (`assert_no_court_gold_leak`,
named in CLAUDE.md rule 4) on the same basename discipline. **Rule 4 warns explicitly that
a discipline enforced on one model is not enforced on the project** — so this new gold
needs its own guard, not a reuse of either existing one, because a point-boundary
consumer is neither the ball trainer nor the court trainer.

**Proposed name and home:** `assert_no_point_boundary_gold_leak`, living in
`tools/_goldset.py` — the existing shared gold registry, already the single place
`GoldClip`/`CALIBRATED`/`HOLDOUT` are defined for ball and court. Extending it with a
`POINT_BOUNDARY_GOLD` registry (same `basename` keying) is more consistent with this
project's own stated reason for `_goldset.py` existing at all ("seven tools each
hardcoded their own table... they drifted") than inventing a fourth registry pattern
elsewhere.

**Keyed on:** the raw video's basename (`L73ep7JHiJ4`, `sAjkpeRq4P4`, etc. — the same
identifiers already in `_goldset.py`'s `_trimmed()` clips for **4 of these 9 raw files**:
`L73ep7JHiJ4`, `sAjkpeRq4P4`, `UHf0LeMU2pg`, `uR5q2cSM6AY` are already BALL gold under
those exact basenames, sourced from the same raw match). **This is a finding worth
flagging, not just a coincidence to note:** any future point-boundary heuristic that uses
ball-in-play/bounce state as a feature (the most likely design, since that is what
`segment_rallies`'s tennis-rule branch already wants) must not be TUNED against these 4
raw files' point-boundary labels while also being evaluated on their existing ball-gold
trims, or vice versa — the two gold sets share a match, even though they are different
tasks. Ball gold is already test-only/one-way, so no ball model was ever trained on these
trims; the guard's job is to stop a *point-boundary* model's thresholds being swept
against the trims of a raw file whose full match is also point-boundary gold.

**Where it must be called:** inside whatever tool eventually reports a point-boundary
agreement number (the not-yet-built point-boundary equivalent of `eval_gold.py`), at load
time, and inside any sweep tool for a parameter that feeds point-boundary logic (audio
`k_mad`/`min_contrast`/`min_sep_s` in `audio.py`, `segment_rallies`'s `gap_s`, or a future
learned rally-boundary classifier) — the same pattern `tune_suppress.py`/
`tune_smoother.py` already follow via `_goldset.py`'s `tunable_calibrated_map()`/
`HOLDOUT`.

**Given only 9 raw candidates exist and at most 4-5 get labelled, there is no slack for a
separate tune/test split within this gold set** — unlike the ball gold's `HOLDOUT`
mechanism (which exists because ball-model *parameters* get swept against gold clips),
point boundaries are logic, not a trained model, so by default **treat every labelled
point-boundary clip as TEST-only, one-way**, same discipline as ball/court gold, and only
carve out a small disjoint dev subset later if a specific threshold (e.g. `audio.py`'s
`k_mad=6.0`) genuinely needs sweeping against these labels — decided when that need is
concrete, not pre-emptively spent now.

---

## 6. File format

**`backend/swingvision/schema.py` checked directly** (the single source of truth for
`match.json`): it already has a `Rally` dataclass (`id, start_s, end_s, shot_ids, winner,
ball_track`) and a `Score`/`ScoreEvent` pair. **Do not reuse `Rally` for ground truth, and
keep the gold format separate — three reasons, not just precedent:**

1. `Rally.start_s`/`end_s` are **computed outputs** of an already-run shot/rally
   pipeline, referencing the analyzer's own `shot_ids`. A ground-truth file shaped
   exactly like a `Rally` risks being wired into the product's own load path by mistake
   — the reverse of "a model grading its own homework," but the same failure mode: gold
   masquerading as output. Keeping the shapes visibly different (no `schema_version`, no
   `players`/`court` keys `schema.validate()` expects) makes that mistake load-bearingly
   hard to make.
2. Ground truth needs fields the product schema should never carry — `refused`,
   `refusal_reason`, `off_screen`, `is_let` as a *labelling* artifact. Putting
   researcher-only fields on `schema.py`'s `Rally` would be forking the contract in the
   direction CLAUDE.md's "don't fork the format" rule warns against (two things half
   agreeing on one schema); keeping them apart means neither side has to know about the
   other's fields.
3. **Direct precedent already exists and is not being deviated from:** ball gold uses its
   own shape (`data/gold/<clip>.labels.json`, `{frame: {ball, x, y, t}}`) rather than
   `schema.py`'s `Shot`/`TrackPoint`, even though the concepts visibly overlap (a labelled
   ball position vs. a `Shot.hit_xy`). Point-boundary gold following the same pattern is
   consistency, not a new departure.

**Proposed shape**, mirroring the ball-gold convention where the concepts line up and
departing where they genuinely differ (a point is an interval spanning two frames, not a
single timestamp, so a flat list rather than the ball label's `{frame: {...}}` dict is
the natural fit):

```json
{
  "clip": "L73ep7JHiJ4",
  "created": "2026-09-05 14:20:00",
  "tool": "point_label v1",
  "labeller": "founder",
  "fps": 29.97,
  "warmup_excluded_before_frame": 1840,
  "points": [
    {
      "point_id": 1,
      "start_frame": 1840,
      "start_type": "first_serve",
      "end_frame": 2318,
      "end_reason": "unreturned_bounce",
      "point_winner_side": "near",
      "is_let": false,
      "serve_fault_count": 0,
      "refused": false,
      "refusal_reason": null,
      "notes": ""
    }
  ]
}
```

A companion `data/gold/point_boundary.manifest.json` lists which raw basenames carry
this gold (mirroring the pattern `data/incoming/README.md` already uses to flag ball/court
gold explicitly, since folder location alone stopped being a visual cue once footage was
filed by surface) — this is what `assert_no_point_boundary_gold_leak` reads, rather than
re-deriving the list from `_goldset.py` (which doesn't know about these 9 raw files under
their raw names at all — only their trimmed derivatives).

---

## What this protocol cannot fix

Stated plainly, per the brief's own instruction, rather than quietly promised away:

- **Shell and Grass have zero eligible continuous footage.** No labelling discipline
  creates ground truth from video that does not exist in the repo. This needs new
  recordings, not a better protocol — a resourcing decision, not a research one.
- **The exact end-of-point frame is irreducibly fuzzy**, per Sigurdsson et al.'s
  published annotator-noise numbers (0.9-1.4 s median error even among trained
  annotators). No amount of instruction-tightening in §1 removes this; the protocol's
  answer is to make the metric tolerance-based and to set that tolerance from the
  self-agreement measurement in §4, not to chase a frame-exact number that does not
  exist even in the published literature.
- **An untelevised/off-screen gap is an unrecoverable hole**, not a labelling failure.
  `refused: true, refusal_reason: "off_screen_gap"` flags it; nothing recovers the point
  count inside it. Any total-point-count claim for a clip with such a gap is a **floor**,
  not an exact count, and must say so.
- **Self-agreement is not inter-annotator agreement.** With one labeller, §4's check
  measures whether the founder is internally consistent, not whether an independent
  second observer would draw the same boundary. That is a genuinely weaker guarantee,
  and no protocol design fixes the absence of a second labeller — only hiring one does.
- **A "perfect" label set does not, by itself, validate or fix `segment_rallies`.** That
  logic currently resolves almost every rally via its 2.0 s timeout fallback (0 of 62 via
  the tennis rule on `yt_match40`), which depends on the ball-in-play/bounce chain being
  reliable at the far court — a separate, currently open perception problem
  (`[[player-detection-negatives]]`, `[[ball-negatives]]`). These labels can measure the
  gap; they cannot close it.

---

## What the founder actually does

1. **Scrub all 9 raw clips**, ~5 min each (45 min total): confirm each is a continuous,
   unedited take (no jump-cuts removing dead time — a channel that edits for viewer
   retention would silently destroy dead-time-trim ground truth even though it could
   still support a point count), and note the actual duration (replacing the unmeasured
   title-based guess in §3).
2. **Order the 9 by measured duration, ascending.** Guarantee both Clay clips
   (`CYqapSq5llo`, `sAjkpeRq4P4`) are included if they pass the scrub — there are only
   two, and dropping either removes the surface entirely for no reason.
3. **Label clips in that order**, applying §1's definitions and §2's fields, using
   REFUSAL wherever a case in §1's ambiguous list applies, until reaching **3 hours of
   source video labelled** (soft target) or **4.5 labelling-hours elapsed** (hard stop),
   whichever comes first. Save each as `data/gold/<clip>.points.json` per §6.
4. **Wait at least a day.** Re-label one fixed 15-20 minute segment of an
   already-labelled clip from scratch, blind to the first pass. Compute the §4
   self-agreement check against the pre-registered bar (exact point count modulo
   attributable refusals; median frame disagreement ≤ 1.0 s). If it fails, revise §1's
   wording against the specific disagreement and redo only what that revision affects —
   not the whole set.
5. **Hand the resulting `.points.json` files, the manifest, and the self-agreement
   number to whoever builds the point-boundary evaluator** (a `researcher`/`backend-dev`
   task, not this one). Do not attempt to design the scoring state machine or the rally
   segmenter — that is explicitly out of scope for this protocol.

### Hours estimate against the 3-6 h budget

| Step | Time |
|---|---|
| Scrub (9 clips × 5 min) | 45 min |
| Labelling (hard-capped) | ≤ 4.5 h |
| Self-agreement re-label (fixed segment) | ~20 min |
| **Total, worst case** | **≈ 5.6 h** |

**This lands inside the 3-6 h budget, with margin, but only because the labelling
hard-stop was deliberately set to 4.5 h rather than the priced range's own 5-5.6 h upper
end.** If the session is running long and something has to give, **cut the self-agreement
check's segment length first** (drop to a 10 minute segment, ~15 min instead of ~20) —
never the scrub prerequisite, since skipping that risks silently labelling an edited clip
and destroying dead-time truth without anyone noticing until much later. If it must be
cut further, reduce the labelling hard-stop to match the 3 h soft target exactly (i.e.
stop as soon as the low end is reached rather than pushing toward 4.5 h) and report the
resulting n against the same §3 claims — a smaller n inside 4-5 matches still supports the
point-count and tolerance-based claims, just with wider uncertainty on the rare-event
counts already flagged as unsupported in §3.

---

## For the lead: one item for `docs/DECISIONS_PENDING.md`

*(Not written there directly — `DECISIONS_PENDING.md` is outside this agent's write
allowlist. Exact text for the lead to append, per the founder's "append, don't ask"
instruction:)*

> **Shell and Grass have zero eligible continuous footage for point-boundary ground
> truth (§3 of `docs/evidence/point-boundary-label-protocol.md`).** The queued 3-6 h
> labelling session can only ever cover Hardcourt + Clay, matching the founder's own
> scope — so this is not currently blocking anything. It becomes a decision only if/when
> Shell or Grass point-boundary numbers are wanted: record a continuous, unedited match
> on either surface (a phone-on-a-fence recording, per the project's own target
> footage), or accept those surfaces stay unmeasured on this layer indefinitely. Cost to
> unblock: one sentence saying which, whenever it becomes relevant — nothing is waiting
> on it today.
