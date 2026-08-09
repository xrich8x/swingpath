# Session I — localised confuser weighting

**Measured against:** human gold clicks. Detector rows pool all 6 gold clips
(1201 ball / 204 no-ball); chain rows pool the 3 calibrated clips at their SHIPPED
frame step (532 scoreable ball / 74 no-ball). Reproduce the chain verdict with
`tools/gate_verdict.py` over the JSON here.

## The intervention

Eight attempts at the solid ghost ball had failed. Phase 0 traced them all to one
structural fact: hard negatives are whole-frame zero targets, so every mining
criterion is forced to ask *"does this frame contain a ball?"* on clips that are
88.5% ball-present. Best purity any criterion reached: 43.7%.

The localised alternative asks about the LOCATION instead. On a frame whose ball
position is already known, a detector argmax landing >20 px away is a confirmed
false fire at a known spot. `tools/mine_localised_negatives.py` found **3,336 of
26,293 labelled training frames (12.7%)** carrying one. The BCE target is already
zero there — the racquet head is simply one pixel among 147,400, weighted like
empty sky — so this is **re-weighting, not new labels**: an 8x per-pixel loss
weight in a 12 px disc at each mined location.

Two 15-epoch arms:

| arm | flag | file | trained |
|---|---|---|---|
| A control | `--hard-weight 1.0` (exactly the shipped recipe) | `ballnet_i_base.pt` | 1h13m |
| B treatment | `--hard-weight 8.0` | `ballnet_i_conf.pt` | 1h09m |

A baseline arm was trained rather than reusing `ballnet_v21.pt`, which carries no
recipe. Neither checkpoint is shippable: both are undertrained by design (v21 is 40
epochs and scores 9 solid ghosts; these score 14-15).

---

## 1. THE DETECTOR IMPROVES, and it is not a measurement fluke

`eval_detector_gold`, all six clips, detector alone:

| clip | false-fire A | false-fire B | d | recall A | recall B | d |
|---|---|---|---|---|---|---|
| am_hard_utr | 50.9% | 43.4% | **-7.5** | 65.1% | 66.3% | +1.2 |
| gold_shell | 50.9% | 43.6% | **-7.3** | 86.4% | 88.0% | +1.6 |
| gold_clay | 71.4% | 57.1% | **-14.3** | 78.1% | 78.5% | +0.4 |
| gold_am | 43.8% | 31.2% | **-12.6** | 78.5% | 75.7% | -2.8 |
| yt_rally2 | 61.5% | 38.5% | **-23.0** | 84.5% | 86.0% | +1.5 |
| yt_match40 | 62.5% | 45.8% | **-16.7** | 84.2% | 85.3% | +1.1 |
| **POOLED** | **53.9%** | **42.2%** | **-11.7** | **79.9%** | **80.4%** | **+0.5** |

far_px 80.9% -> 82.5%, far_geo 80.4% -> 82.1%.

**False fire down on 6 of 6 clips, by 7.3 to 23.0 points, at slightly HIGHER
recall.** Pooled that is 110 -> 86 false fires out of 204 no-ball frames — a 3.4
sigma shift, and a 6/6 sign test would come up p=0.016 by chance alone.

This is not the usual precision-for-recall trade. The operating point moved
outward on both axes.

### What that does and does not establish

It establishes that **these two models genuinely differ**, and in the direction the
intervention predicts. It does NOT establish that the intervention caused it, for a
reason that is not subtle: **there is one training run per arm, and the trainer had
no seed.** The six clips are six measurements of the same two models, so the sign
test speaks to evaluation noise only. The unit of randomisation for the *treatment*
question is the training run, and n=1.

The trainer's own val metric agrees (best hit@10 - false-fire: A 18.8%, B 25.8%),
which is consistent with either explanation — a real effect, or a luckier seed.

FIXED FORWARD: `--seed` (default 0) now seeds python/numpy/torch and the train
DataLoader's shuffle generator, so a future pair shares initialisation and data
order. Not bit-determinism — cuDNN still picks conv algorithms nondeterministically
— but it removes the dominant source of divergence in a short run.

---

## 2. IT DOES NOT REACH THE PRODUCT. Gate FAILS.

Full chain, `+ kalman smooth (FULL)` — the row the renderer actually draws:

| clip | camera | solid ghosts A | solid ghosts B | d | recall A | recall B |
|---|---|---|---|---|---|---|
| am_hard_utr | 1.74 m phone, 1080p | 6 | 5 | **-1** | 60.0% | 61.1% |
| yt_match40 | 11.33 m broadcast | 4 | 4 | **0** | 70.1% | 69.6% |
| yt_rally2 | 3.31 m | 4 | 6 | **+2** | 71.7% | 71.3% |
| **POOLED** | | **14** | **15** | **+1** | **69.2%** | **69.0%** |

- solid ghosts **+1** — **FAIL**
- recall -0.2 pts — pass
- far_geo (worst clip) +4.1 pts — pass

An 11.7-point detector precision gain arrives at the product as **nothing**. On
yt_rally2 the detector's false fire nearly halved (61.5% -> 38.5%) while the same
clip's tracker-gates-only row went the WRONG way (30.8% -> 38.5%).

**This is the third time a detector-level precision gain has failed to reach the
product** (Phase 0 gate B, the score_thresh sweep in Session F step 3, and now
this). The mechanism is consistent across all three: the chain's own gates were
already removing the false fires that a better detector removes — those are the
easy ones — and what survives to be drawn is a different, harder population. The
detector and the chain are close to decoupled on precision.

---

## 3. THE TEST SET CANNOT RESOLVE THE PRODUCT QUESTION

The deciding metric is a count of ~14 out of **74** no-ball gold frames. Sampling
alone moves that count by **+/-3.4 frames**.

| effect to detect | no-ball frames needed per arm | we have 74 |
|---|---|---|
| near-eliminate ghosts | 62 | detectable |
| **halve** the ghost rate | 212 | **2.9x short** |
| cut by 30% | 656 | **8.9x short** |

(Two-proportion, alpha .05, power .80; unpaired, so it overstates what a paired
McNemar comparison on identical frames needs. Read it as an order of magnitude.)

So "solid ghosts did not fall", now recorded nine times, licenses exactly this:
**no intervention has come close to eliminating the ghost ball.** It does not
establish that any of them did nothing. Note the contrast with the detector table
above, where 204 no-ball frames across six clips resolved an 11.7-point effect
comfortably — the constraint is not the method, it is that the *chain* metric is
restricted to the three calibrated clips.

---

## 4. THE GHOST FRAMES ARE ONLY PARTLY THE SAME FRAMES

`eval_model_filters` now records `fire_frames_solid`, so a stable hard core and a
shifting set can be told apart — a count of 9 that never moves reads identically
either way.

| clip | A control | B treatment | fire on BOTH |
|---|---|---|---|
| yt_rally2 | 18, 762, 1494, 2106 | 18, 24, 762, 1494, 2158, 2196 | **18, 762, 1494** (3/7) |
| yt_match40 | 3571, 4773, 5425, 9271 | 3983, 4121, 4773, 9271 | **4773, 9271** (2/6) |
| am_hard_utr | 9316, 12344, 13276, 24106, 24688, 27134 | 9316, 9782, 12344, 13276, 24106 | **9316, 12344, 13276, 24106** (4/7) |
| **POOLED** | 14 solid | 15 solid | **9 of 20 distinct frames (45%)** |

So it is BOTH: a core of **9 frames that two independently-initialised models both
ghost on**, plus 11 that move with the model.

### Bringing in the shipped detector — a universal core of FIVE

`ballnet_v21.pt` scored the same way (a fair question even though it cannot serve as
a training control: this asks which FRAMES defeat it, not how it was made).

| clip | v21 solid ghosts | of the A&B core, v21 also hits |
|---|---|---|
| yt_rally2 | 18, 762, 1494, 2130, 2158 | **3 of 3** |
| yt_match40 | 172, 4773, 8928 | 1 of 2 |
| am_hard_utr | 13276 | 1 of 4 |
| **pooled** | **9** | **5 of 9** |

Two things fall out.

**v21's pooled solid-ghost count is 9** — reproducing the standing figure exactly,
which is a clean independent check on the whole measurement chain.

**Five frames are ghosted by all three models**: yt_rally2 18, 762, 1494;
yt_match40 4773; am_hard_utr 13276. Those are the frames that beat a 40-epoch
detector and two 15-epoch ones with different initialisations.

CORRECTION to a stronger claim made mid-session: the immovable 9 is **not** one
listable set of nine frames that every model fires on. The *count* is strikingly
stable (v21 9, arms 14 and 15, and 9 shared between the arms), but the
*composition* is only about half shared. There is a universal core of 5, and the
rest is model-specific. That is why the count is a poor statistic — it stays near
constant by a coincidence of rates as much as by one immovable set.

Also visible: v21 has **1** solid ghost on am_hard_utr against the arms' 5 and 6.
The 15-epoch arms are much worse on the low-camera amateur clip specifically, which
is the footage this project targets — another reason not to read anything shippable
into them.

---

## 5. WHAT THE SURVIVORS ARE — and why nine sessions of filtering could not touch them

`inspect_false_locks --stage chain` on v21, all three calibrated clips: **19 false
locks on 74 no-ball frames**, 9 solid + 10 faded — reproducing the Session F figure.
Crops: `hardcore*.png`, `universal5_zoom.png`.

The five universal frames, seen at zoom:

| clip:frame | reviewer class | what is actually there |
|---|---|---|
| yt_rally2:18 | fence | a fold/dark patch on the green curtain |
| yt_rally2:762 | *never classified* | a fixture on the white wall above the curtain |
| yt_rally2:1494 | racquet | a light blob at the head of a mid-swing player |
| yt_match40:4773 | background | ball-coloured foliage in the hedge |
| am_hard_utr:13276 | racquet | a light object against the dark windscreen, beside a player |

**No single object type.** Three are static scenery, two are person-attached. That
alone kills "detect the racquet and negate it" for *this* population — it reaches 2
of 5.

### THE MECHANISM, and it is one number

**All 19 survivors have `run_len = 1`**, with roam 208-829 px. The tool's own legend:
*"A real ball scores high roam and short run; a fixture the reverse."*

So every confuser that survives to be drawn has **the kinematic signature of a real
ball.** That is not a weakness in `suppress_false_locks` — it is the definition it
was built on. The persistence test removes things that hold still; these do not hold
still. The chain cannot remove them without also removing the single-frame real-ball
sightings it exists to preserve, and those are exactly the far-court balls the
project is already short of.

This explains the whole history in one stroke:

- **Nine downstream attempts failed** because every one of them — persistence,
  min-segment, court envelope, live-ball, threshold, gap policy — tests for
  *non-ball-like behaviour*, and these are ball-like by construction.
- **Detector-side attempts also failed to reach the product** because this is the
  *tail* of the detector's error distribution: one-off fires on ball-sized,
  ball-coloured things. Cutting the bulk error rate (which localised weighting did,
  by 11.7 pts) barely touches a tail of one-offs.
- **The count is stable but the composition is not** because it is a *rate* of
  single-frame errors, not a fixed set of defeated frames.

### One thing NOT concluded here

Two of the five (yt_rally2:1494, am_hard_utr:13276) show a light, ball-sized object
beside a player mid-swing, and a human marked those frames "no ball". That could be
a racquet head — which is what the reviewer called both — or it could be a ball at
contact that the labeller judged not in play. **Not adjudicated, and deliberately
not edited**: never quietly change human ground truth to suit a model. It belongs in
the Lab as a re-label question, alongside the 8 known-bad `am_indoor_hard1` court
frames. If some of the five are mislabels, part of this "floor" is not a model
problem at all.

---

## Also fixed this session

- **`tools/gate_verdict.py`** — pools the calibrated clips by summing numerators and
  denominators (a mean of three percentages over clips of 26/24/53 frames is not a
  rate), applies the gate, prints the resolution alongside the verdict, and warns
  when the clips disagree in sign.
- **The resume list omitted `yt_match40`**, one of the three calibrated clips. A
  *pooled* gate would have been decided on two thirds of its evidence.
- **Checkpoints now carry their recipe** (`train_ballnet.recipe_stamp`): args, seed,
  git commit, dataset counts, and `confuser_samples` — because `--hard-weight 8`
  with zero mined confusers IS the shipped recipe arithmetically, and a filename
  cannot tell you which run you are holding. This is the gap that made
  `ballnet_v21.pt` unusable as a control.
