# What the far-court pilot's 36 clicks actually landed on

Session I's pilot was read as "the burned-in scoreboard poisons the labels" and
Session J was scoped around fixing that. Re-adjudicating every click against the
pixels says that is **true but small**, and that it is not the main thing wrong.

Evidence: `data/output/farcourt_pilot_click_classes.json` (the per-frame
verdicts), `data/labels/farcourt_pilot.{manifest,labels}.json`,
`data/hud_masks.json`.

    py tools/farcourt_labels_to_dataset.py --clip farcourt_pilot \
        --contact-sheet data/output/farcourt_pilot_clicks.jpg   # all 36 at 5x
    py tools/farcourt_labels_to_dataset.py --clip farcourt_pilot --force --dry-run

The sheet is regenerable and not committed, same rule as
`data/output/session_i_ab/*.png`: the classification is the evidence.

---

## 1. The frames are the frames. RULED OUT FIRST.

Before blaming the labeller, the obvious rival explanation is that the queue
showed them a frame from the wrong moment, so the ball genuinely was not there.
All 36 queue JPEGs were re-decoded from `data/train_clips/` at the
`video_frame` each claims: **0 of 36 mismatch** (dHash 0-2 bits of 64, mean abs
0.70-1.47 grey levels, i.e. JPEG re-encode only). The window arithmetic in
`select_farcourt_labels.source_frame` is correct. MEASURED.

## 2. The HUD explains 5 of 36 clicks, not 24

| | |
|---|---|
| labels | 29 ball / 4 no-ball / 3 unsure |
| ball clicks inside a burned-in graphic | **5** (frames 0, 1, 2 on `yt_6jp23ghDY9Q`; 7, 8 on `yt_RZ_wyJ9rI3Q`) |
| ball clicks within 10 px of the tracker | 11 |

**RETRACTED** from `farcourt_label_yield.md` §2b: "on the four clips with a
burned-in scoreboard graphic, every click landed on the little tennis-ball icon
inside the scoreboard". Two of the four clips it names — `yt_8-BkpjFFIhQ` and
`yt_WjHZrIYteDA` — **carry no burned-in graphic at all** (visible in the median
plates, `data/output/hud_masks.jpg`), and their clicks were 503-569 px and
112-406 px out anyway. And on the two clips that do, the clicks landed on the
score digits and the panel body, not on a ball icon. The clip-level split in
that table was CORRELATIONAL: it happened to separate the clips where the
tracker was tracking a ball from the clips where it was not.

## 3. What the other clicks landed on — the finding

Classified by eye at 5x from the contact sheet
(`farcourt_pilot_click_classes.json`; one observer, one pass, n=36 — the split
it carries is "on a ball or on background", which was unambiguous at this zoom):

| what the human clicked | frames | n |
|---|---|---|
| a real ball | 18, 21, 22, 23, 27, 28, 29, 30, 31, 32, 33, 34, 35 | 13 |
| a burned-in scoreboard | 0, 1, 2, 7, 8 | 5 |
| empty sky / a cloud | 3, 4, 5 | 3 |
| foliage in a hedge | 24, 25, 26 | 3 |
| flat court surface or a windscreen | 15, 16, 20 | 3 |
| a floodlight at night | 14 | 1 |
| the net cord (ambiguous) | 19 | 1 |

So **11 of 29 ball clicks are on empty background**. That is not a noisy label,
it is a Gaussian on grass, and masking the HUD does not touch a single one of
them.

## 4. Why: the ANCHORS were false locks

A queued gap is the midpoint between two tracker detections, and the queue
already labels both anchors so a human verdict can be compared with the tracker.
Nothing had ever read that comparison. Zooming the 24 anchor priors
(`prior_x/prior_y`, which the UI never shows, so they cannot bias a click):
roughly half sit on a wall speaker, a parked car, a treetop, a spectator, a
building window or a graffiti fence — **not on a ball**.

The human's own clicks say the same thing without any eyeballing. Counting a
gap as *confirmed* when the human's click on either anchor is within 10 px of
what the tracker claimed there:

| | gaps | midpoint clicks that are on a real ball |
|---|---|---|
| at least one anchor confirmed | 5 | **5 of 5** |
| neither anchor confirmed | 7 | **0 of 7** |

The four clips `farcourt_label_yield.md` called "clean" (`yt_am_dbl_classb`,
`yt_col_hard_zheng`, `yt_nQan0M5JDM8`, `yt_tC0z7FYvMks`) are exactly four of the
five confirmed-anchor clips. The fifth, `yt_rz4T0-VALNw`, is the informative
one: the human clicked a **real ball 39-47 px from the tracker's prior** — the
tracker was wrong and the human was right, which a clip-level "agrees with the
tracker" reading would have scored as a failure.

**So the queue's selection criterion — "the tracker is confident on both sides"
— is satisfied about half the time by two false positives**, and the labeller is
then asked to find a ball on the segment between a hedge and a wall. n = 12
gaps: a clean split on a small sample.

### The consequence, now enforced

`farcourt_labels_to_dataset.py` accepts a midpoint only if the human confirmed
an anchor beside it. On the pilot that keeps 5 of 5 usable midpoints and drops
7 of 7 unusable ones. It costs two clicks per gap, which the queue was already
spending.

It is a LABEL-TIME filter, not a selection-time one, so it does not stop the
queue serving bad gaps — it stops them reaching training data. Making selection
itself better would need a way to tell a real anchor from a false one before a
human looks, and the next section is why that is not available.

## 5. TWO MEASURED NEGATIVES: no kinematic test substitutes for the human

Both were tried before writing the anchor control, because a selection-time fix
would be worth much more than a label-time one.

**Local roam does not separate them.** `inspect_false_locks.describe`'s roam
(max pairwise distance among locks within +/-8 frames) over each pilot gap:

| | roam (px) |
|---|---|
| gaps with a confirmed anchor (n=5) | 14.0, 33.6, 89.4, 93.6, 220.2 |
| gaps with neither confirmed (n=7) | 13.2, 32.5, 43.7, 104.4, 106.7, 116.9, 238.8 |

Fully overlapping, at both ends. The reason is the standing far-court problem:
a genuine far ball's per-frame excursion is small, so "barely moved" cannot be
read as "not a ball" — the same tension already recorded for
`static_radius_px` in Session E6.

**`ball.suppress_false_locks` is far too aggressive here.** Run over each clip's
pseudo-label track and requiring both anchors to survive: it keeps 1 of the 5
confirmed gaps and drops 4. It is not miscalibrated — the min-segment test needs
a run of consecutive locks, and the frame immediately after a gap starts a new
short segment by construction, so anchor `b` is dropped on 8 of 12 gaps as an
artefact of *being* an anchor. It is the wrong instrument for this question, not
a badly tuned one.

## 6. What this changes about Session J's plan

- Blocker 1 (mask the HUD) is real and is done, but it is worth **5 of 36
  labels**, not most of them. See `farcourt_hud_mask.md`.
- The dominant failure is anchor quality, and the fix is the control the queue
  was already built to provide.
- The step-4 re-run is therefore a test of **two** changes, not one, and its
  go/no-go should be read on the confirmed-anchor gaps: if the human still
  cannot find the ball where the tracker demonstrably was tracking one, the
  problem is the footage and no amount of labelling fixes it.
