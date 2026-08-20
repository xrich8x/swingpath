# What is actually going wrong — measured at the known-true court

Follow-up to [court_breadth_54.md](court_breadth_54.md). Two questions from the user:
*take only the top-down angle for the professional clips*, and *why do the framings
that show more of the court do worse?*

## 1. Top-down-only selection: done, and it does not help

`eval/pick_view.py` proposes N numbered candidate frames per recording and a human
keeps the ones that are the elevated top-down TV camera; the choice is written to
`eval/clip_classes.json`. Applied to six broadcast recordings, excluding serve cams,
half-court cameras, close-ups and score cards.

```
clip            frames locked votes    result
45VdNMtbulA          8      0     0   refused
9gUvgm23qMU          8      0     0   refused
DY6WVsuHqFs          8      1     1   refused
eala_segment         8      0     0   refused
J8__TwOgTY0          8      2     1   refused
U5Af1jGgYqA          8      1     1   refused
```

**0 of 6.** The instruction was right — the frames genuinely were mixed, and
`45VdNMtbulA`'s automatic selection had included a low tight camera showing only the
near half. Fixing that changed nothing, so camera-angle selection is not the cause.
`eala_segment` is the cleanest evidence: **23 of its 24 candidates were already the
same top-down camera**, and it locks zero frames.

## 2. Three hypotheses tested and killed

| hypothesis | test | result |
|---|---|---|
| the broadcast pose is not seeded | added 27 synthetic 6–18 m / long-lens poses, mirroring `_lowcam_seeds` | **no change** on any clip |
| the court is too small in the frame | cropped toward the court and upscaled, x1.18 → x2.50, nothing else changed | **no change**; `BwLUgip8OSI` got *worse* (2/4 → 0/4) as its corners cropped out |
| the wrong camera angle was selected | human top-down-only selection, above | **no change**, 0/6 |

A fourth reading was **retracted mid-run**: a wide parameter sweep found courts scoring
g = 0.41–0.52 on broadcast frames, above the 0.33 gate, which read as "the answer exists
but the search misses it". Drawn on the frames, **all four are junk** — three imply a
0.6–0.9 m camera at Wimbledon with 21–37 px `cam_fit` residuals. The agreement score's
global maximum sits on a wrong court, so that number meant the opposite of what it looked
like. Second time this session a figure pointed one way and the picture corrected it.

## 3. The real diagnosis: score the gates AT the true court

Ten clips carry a human-placed calibration (`"_exact": true`). Running the detector's own
accept criteria on the human's court removes all guesswork — no search, no ranking, just
"can these criteria recognise the correct answer when handed it".

```
clip                   verdict   g@truth  gate | struct match acr len  suff | what fails
A7vXlWIlyrI             vote<6     0.303  FAIL |   0.88     7   3   4   yes | g<0.33
am_hard_utr           ACCEPTED     0.314  FAIL |   1.00     8   4   4   yes | g<0.33
CYqapSq5llo             vote<6     0.490    OK |   0.88     7   3   4   yes | nothing
e8T34KoJzOw_s2          vote<6     0.486    OK |   0.88     7   4   4   yes | nothing
HoHxFSX_gLk_s1         refused     0.203  FAIL |   0.50     4   2   3   yes | g<0.33, struct<0.55
HoHxFSX_gLk_s2          vote<6     0.608    OK |   0.88     7   3   4   yes | nothing
sAjkpeRq4P4             vote<6     0.181  FAIL |   0.43     3   3   1    NO | g, sufficiency, struct
tc8CGFxyRE8             vote<6     0.440    OK |   0.88     7   3   4   yes | nothing
UHf0LeMU2pg             vote<6     0.220  FAIL |   0.50     4   2   2   yes | g<0.33, struct<0.55
uR5q2cSM6AY             vote<6     0.648    OK |   0.88     7   3   4   yes | nothing
```

**There are two different failures, five clips each.**

**A. The accept gate rejects the correct court (5 of 10).** g at the human's own court is
**0.18–0.31 against a 0.33 bar**. No amount of better searching fixes this — the criteria
refuse the right answer. `am_hard_utr` is the sharpest case: the true court scores 0.314
and *fails*, yet the clip is ACCEPTED, so what shipped is a court scoring higher than the
truth. That is the accept rule preferring a near-miss to the correct answer, and it is why
its measured error is 14.3 px rather than ~0.

**B. The correct court passes every gate and still is not found (5 of 10).** g = 0.44–0.65,
structure 0.88, sufficiency satisfied — and the clip reaches only 2–4 of 8 votes. Here the
scoring is fine and the search or its ranking is the problem.

So "what is going wrong" has no single answer: **half the failures are scoring, half are
search.** Any fix aimed at only one of them addresses at most half the gap, which is worth
knowing before Stage 2 is scoped.

## 4. On "more of the court shown does worse"

The court gold set **cannot test this** — all 20 clips show 94–100% of the court, so there
is no variation on that axis. What does vary is how much of the *frame* the court fills,
and on the gold set that is predictive: accepted clips occupy **0.21–0.40** of frame area,
and **every clip below 0.21 is refused (4 of 4)**, as is the one at 0.57.

Among the ten reference clips the split leans the same way — the five scoring-failures sit
at a median near-baseline width of 0.54 of frame width against 0.61 for the five
search-failures, i.e. the further-back framings are the ones whose true court fails the
agreement gate. **With five clips per group that is a lean, not a result**, and the zoom
experiment above shows apparent size is not itself causal. Treat the observation as
directionally supported and not yet explained.

## 5. A separate defect found on the way

`autodetect`'s coarse grid searches far-half-width over **0.20–0.42 of frame width**.
Measured from human corners across 30 courts (20 gold clips + 10 reference calibrations),
real courts sit at **0.09–0.22** — **30 of 30 fall outside the grid's range**. The grid is
largely searching poses that do not occur; the learned prior is doing the seeding work,
which is consistent with it failing wherever the prior has no coverage. Not fixed here —
recorded as the concrete thing to change first if search is the half being attacked.
