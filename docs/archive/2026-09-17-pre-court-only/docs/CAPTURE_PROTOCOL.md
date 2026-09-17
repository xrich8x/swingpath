# CAPTURE PROTOCOL — the court visit that builds v1's truth set

**Written by pm, 2026-09-15, before the visit. This is a field document: print it, carry it, fill
it in.** It is pre-registered under hard rule 2 — the visit's own success criterion (§7) is fixed
here, before any data exists, and does not move afterwards.

**Why it exists.** P3 (`evidence/capture-floor-census.md`) found the v1 validation corpus **does not
exist**: 7 of 213 clips clear 60 fps + 1080p, across 2 surfaces, Shell 0 and Grass 0, and **no clip
is simultaneously ≥60 fps, ≥1080p, fixed-mount AND at a height where 10 cm is physically
reachable.** P5's older argument was that the 10 cm gold set is not *labellable* from footage we
own; P3 makes it stricter — the footage does not meet the *capture* floor either. So the gap is not
a labelling gap and no labelling session can close it.

**Truth at 10 cm is therefore built AT CAPTURE, by construction**: balls land, they leave a print,
and the print's distance from the line is read off a steel rule and written on paper. The video is
never consulted to establish truth. That is what makes this an independent reference under rule 1.

---

## 0. THE ON-DEVICE CATCH — read this before anyone objects

**A tape measure, a steel rule, a chalk line, a ball machine, a tripod, and a second, third or
fourth camera used ONLY to build this truth set are LAB INSTRUMENTS. They are not product
dependencies, and using them is NOT a breach of "100% on-device, forever."**

The rule that does not move is that **the shipped app runs entirely in-process on one iPhone, with
no server and no network call.** Nothing in this protocol touches that. `tools/synth_truth.py` is
the same kind of object — a rig that produces truth the product never sees.

The test, stated so it can be applied to the next proposal too: **does the user need this thing to
get a call?** A tape measure at a lab visit: no. A second phone in the founder's bag: no. A cloud
endpoint that scores a hard bounce: **yes — and that is the scope violation.** This protocol
contains none of the second kind.

**One thing this does NOT license.** Nothing captured here may become a *runtime* input. The
fiducial marks in §3 exist to score the calibration; the product still ships a four-tap on a bare
court with no tape on it.

---

## 1. WHAT THE VISIT MUST PRODUCE — the pre-registered bar

> **≥30 landing points whose ground-truth position is known to ≤3 cm INDEPENDENT of any video,
> PER DIRECTION CLASS, across ≥2 surfaces.**

**"Per direction class" supersedes the earlier pooled reading of ≥30**, on pm's delta of 2026-09-15
(`DECISIONS_PENDING.md`, "P5-scope" §5.3). R1 measured the error to be one-dimensional — median
**5.4 cm** perpendicular to the camera ray, **1.28 m** along it, a factor of **23.5**
(`evidence/monocular-3d-routes.md`, "R1 — RUN AND SETTLED"). A pooled truth set cannot separate the
two axes, and a visit that comes back unable to separate them has not answered the question that put
it at the top of the queue.

The two classes:

| Class | Lines | The margin is measured in | R1's verdict on this axis |
|---|---|---|---|
| **ALONG** | both doubles sidelines, both singles sidelines, the centre service line | **x** (across the court) | the *well-measured* axis — but only near the centreline (§2) |
| **ACROSS** | both baselines, both service lines | **y** (down the court) | the **blind** axis: ≤10 cm rate **4.1%** in the 18-24 m band |

---

## 2. WHY THE MARK LAYOUT IS AN EVIDENCE QUESTION, NOT A CONVENIENCE

**R1b killed the simple version of this.** The "good" axis is good only near the centreline. In the
same range band, median lateral error runs **0.049 m on the centreline → 0.348 m at the doubles
sideline**, and the ≤10 cm rate **72.9% → 20.0%** — a **7x** degradation driven purely by how far
off the camera's axis the bounce sits (`evidence/monocular-3d-routes.md`, "R1b"). A quadrature model
`sqrt(tangential² + (sin θ · radial)²)` accounts for the whole gradient to 5-13% with nothing fitted.

**Consequence for the layout: the marks must span BOTH axes the geometry says matter —
RANGE (down-court distance) and LATERAL OFFSET from the centreline.** A layout that only clusters
marks near the lines confounds the two and cannot falsify the obliquity model. §3's table names, for
every station, which prediction it exists to test.

**A prediction this layout can refute, stated now:** for an **ACROSS**-court line the radial error
projects onto the perpendicular direction with `cos θ`, which is **0.99 at 7.3°**. So the ACROSS
class must show **essentially no obliquity gradient**, while the ALONG class shows a steep one. If
the ACROSS class also shows a gradient, the quadrature model is wrong and the diagnosis is
incomplete. The ACROSS stations therefore deliberately span 1.3 to 3.0 m of offset as a control.

---

## 3. THE TARGET SHEET — print this page

**Coordinate frame** (`backend/swingvision/court.py`, unchanged — nothing here invents a dimension):
`x` 0 → 10.97 m, left doubles sideline to right doubles sideline. `y` 0 → 23.77 m, near baseline to
far baseline. Net at `y` = 11.885. Singles sidelines at `x` = 1.37 / 9.60. Centre service line at
`x` = 5.485, spanning `y` 5.485 → 18.285. **Camera at (5.485, −6.00)** — on the centreline, 6.00 m
behind the near baseline.

**MEASUREMENT CONVENTION — get this wrong and the 3 cm budget is gone before you start.** ITF
measures a court **to the OUTSIDE of the lines**, except the centre service line, which is measured
to its **centre**. So `x = 0` is the *outer* edge of the left doubles sideline's paint, `y = 23.77`
is the *outer* edge of the far baseline's paint, and `x = 5.485` is the *middle* of the centre
service line. Paint is 5 cm wide (a baseline may be 10 cm) — **1.7x to 3.3x the whole error
budget**, so measuring to the wrong edge is not a rounding error, it is a failed visit.
*(Note for the lead: `court.py` does not state this convention anywhere. Worth a docstring line.)*

### 3.1 ALONG-class stations — margin measured in **x**

| ID | Line | x (m) | y (m) | Offset from centreline | Ground dist. to camera | Balls | Exists to test |
|---|---|---|---|---|---|---|---|
| **L1** | centre service | 5.485 | 6.50 | **0.000** | 12.50 | 6 | R1b bin 0-1 m, near band — the predicted **best** cell (72.9% @10 cm) |
| **L2** | right singles sideline | 9.600 | 6.50 | 4.115 | 13.16 | 5 | obliquity at matched near range |
| **L3** | right doubles sideline | 10.970 | 6.50 | 5.485 | 13.65 | 5 | max obliquity at matched near range |
| **L4** | centre service | 5.485 | 17.00 | **0.000** | 23.00 | 6 | zero obliquity at **far** range — separates range from obliquity |
| **L5** | right singles sideline | 9.600 | 17.00 | 4.115 | 23.37 | 5 | matched to L4 in range |
| **L6** | right doubles sideline | 10.970 | 17.00 | 5.485 | 23.64 | 5 | matched to L4; R1b bin 4-6 m |
| **L7** | right singles sideline | 9.600 | 22.30 | 4.115 | 28.60 | 6 | far band |
| **L8** | right doubles sideline | 10.970 | 22.30 | 5.485 | 28.83 | 6 | **the far doubles corner — the worst cell and the contested call** (20.0% @10 cm) |

**44 balls.** By obliquity: 0 m → 12 · 4.115 m → 16 · 5.485 m → 16. By range band:
near (L1-L3) 16 · far-service (L4-L6) 16 · far (L7-L8) 12.

**Note what the far band cannot offer, because it is itself a finding:** there is no centre service
line beyond `y` = 18.285, so at the far baseline **every** along-court line sits at 4.1 or 5.5 m of
offset. There is no low-obliquity sideline call to be had out there. That is a structural property
of a tennis court, not a gap in the layout.

### 3.2 ACROSS-class stations — margin measured in **y**

| ID | Line | x (m) | y (m) | Offset from centreline | Ground dist. to camera | Balls | Exists to test |
|---|---|---|---|---|---|---|---|
| **C0** | near baseline | 4.200 | 0.00 | 1.285 | 6.14 | 6 | **positive control** — shortest range; if this fails, something is broken beyond geometry |
| **C1** | near service line | 7.500 | 5.485 | 2.015 | 11.66 | 8 | blind axis at short range (P1: 36.4% @10 cm in the 0-6 m band) |
| **C2** | far service line | 7.500 | 18.285 | 2.015 | 24.37 | 10 | blind axis, long range |
| **C3** | far baseline | 3.000 | 23.77 | 2.485 | 29.87 | 10 | **the hardest across-court call there is** (4.1% @10 cm); also the only LEFT-side station, guarding against a lens-decentring / roll asymmetry |
| **C4** | far baseline | 8.500 | 23.77 | 3.015 | 29.92 | 8 | matched range to C3, higher obliquity — the **cos θ control** of §2 |

**42 balls.** By range band: near (C0, C1) 14 · far-service (C2) 10 · far-baseline (C3, C4) 18.

**Every station is placed ≥0.75 m clear of any line junction**, so a margin is never ambiguous
between two lines. That is why L1 sits at `y` = 6.50 rather than on the near T, and why C1/C2 sit
at `x` = 7.50 rather than on the T.

**Total: 86 fed balls.** The ≥30-clean-per-class bar therefore needs a **68-73% clean-print yield**,
which leaves real headroom for skidded and overlapping prints.

### 3.3 FIDUCIALS (F-marks) — 8 tape marks, and they are not decoration

Placed at court intersections the four-tap calibration **does not use**, so they remain independent
of it (the same one-way discipline as `assert_no_court_gold_leak`).

| ID | Landmark | x (m) | y (m) |
|---|---|---|---|
| F1 | `near_t` | 5.485 | 5.485 |
| F2 | `far_t` | 5.485 | 18.285 |
| F3 | `near_sl_left` | 1.370 | 5.485 |
| F4 | `near_sl_right` | 9.600 | 5.485 |
| F5 | `far_sl_left` | 1.370 | 18.285 |
| F6 | `far_sl_right` | 9.600 | 18.285 |
| F7 | `near_bl_singles` | 1.370 | 0.000 |
| F8 | `far_br_singles` | 9.600 | 23.770 |

**Form:** a 10 cm square of bright (orange/pink) gaffer tape with **one corner exactly on the
intersection**, laid in the quadrant *inside* the service box so no measurement line is covered. The
fiducial point is the tape corner — sharp, high-contrast, sub-pixel locatable. On clay, where tape
will not hold, use a chalk cross and accept ~1 cm placement.

**They do three jobs, and the third is the one nobody expects:**
1. Give the along-line ruler a local origin, so a print's position along the line is a short tape
   pull rather than a 20 m one.
2. Provide 8 known points the four-tap did not use — **the first-ever independent measurement of how
   accurate the manual four-corner calibration actually is.**
3. **Framing B (§4) cannot be calibrated by the shipped four-tap at all** — its near corners are out
   of frame. The far F-marks are the only thing that can calibrate it. Without them, half the visit
   is unusable.

**HARD INSTRUCTION for whoever labels this footage later:** the four-tap uses **only** the four
doubles corners. The F-marks are scoring-only, one way. An F-mark fed into the calibration stops
being evidence and becomes a model grading its own homework (rule 1).

### 3.4 Diagram

```
                      FAR BASELINE  y=23.77
    +-------------------------------------------------+
    |        C3(3.00)        |        C4(8.50)   F8   |   <- ACROSS: hardest cells
    |                    L7(9.60,22.30)  L8(10.97,22.30) |  <- ALONG: the far corner
    |                                                 |
    |  F5 - - - - - - - - F2 - - - - - - - - - F6     |  y=18.285  FAR SERVICE LINE
    |                    C2(7.50)                     |   <- ACROSS
    |             L4(5.485,17.0)  L5(9.60,17.0)  L6(10.97,17.0)
    |                          |                      |
    |                          | centre service line  |
    +==========================+======================+  NET   y=11.885
    |                          |                      |
    |             L1(5.485,6.5) L2(9.60,6.5) L3(10.97,6.5)
    |                    C1(7.50)                     |   <- ACROSS
    |  F3 - - - - - - - - F1 - - - - - - - - - F4     |  y=5.485  NEAR SERVICE LINE
    |                                                 |
    |  F7          C0(4.20)                           |   <- ACROSS positive control
    +-------------------------------------------------+
                      NEAR BASELINE  y=0
                            ^
                            | 6.00 m setback, on the centreline x=5.485
                        [ CAMERAS ]  at two heights on one mount
```

---

## 4. THE TWO FRAMINGS AND THE TWO MOUNT HEIGHTS

### 4.1 The governing principle: **the lever is CAMERAS, not BALLS**

Measuring a print is the bottleneck — roughly 30 s each, plus walking. **Every additional camera
pointed at the same bounce is free.** So the 2x2 matrix is captured **SIMULTANEOUSLY**, which does
two things: it collapses four ball sessions into one, and it makes every comparison a **paired**
test on identical bounces, which is far more sensitive at n≈40 than four unpaired sets would be.

- **4 recording devices: ideal.** One pass, all four cells, every comparison paired.
- **2 devices: the practical minimum.** One pass gives the **height pair at framing A** — the
  highest-value comparison. Framing B then needs a second pass (+~70 min) or a second visit.
- **1 device: do not attempt the matrix.** Record framing A at the higher height and accept that the
  visit answers the direction-split question only.

Only the primary arm needs to be the iPhone 17. The secondary arms can be **any** camera that shoots
1080p60 and holds still — a borrowed phone, an old phone, an action camera. See §0: they are lab
instruments.

### 4.2 The four cells

Setback **6.00 m** behind the near baseline for all cameras, on the centreline, measured with a
tape and written down. All cameras on **one mount** (a fence post is by far the most rigid option
available at a real court) so the setback is identical by construction.

| Cell | Height | Framing | Lens | What it exists to prove |
|---|---|---|---|---|
| **A-low** | **2.5 m** | full court | ultra-wide (0.5x) | the shipped capture spec, on real footage, for the first time |
| **A-high** | **3.5 m** | full court | ultra-wide (0.5x) | paired against A-low: does down-court error really scale as **1/h** on real footage? |
| **B-low** | **2.5 m** | far half | telephoto (2x+) | paired against A-low: does narrowing the field of view buy the blind axis? |
| **B-high** | **3.5 m** | far half | telephoto (2x+) | **the only cell in this protocol that meets the (b2) requirement** — see 4.4 |

**HEIGHTS: what matters is the RATIO, not the absolute numbers.** The project has never confirmed
that 2.5 m is reachable at a real court — that ask has been open for ten days. So the **first act of
the visit** is to find out what height this court actually allows, then set the pair. **Target ratio
≥1.4; floor ≥1.0 m of separation.** If the court tops out at 2.2 m, run 1.2 m and 2.2 m — a ratio of
1.83, which is *better* leverage than 2.5/3.5. Record both heights to ±2 cm.

### 4.3 Framing A — FULL COURT, and it forces the ultra-wide

All four doubles corners plus ~1 m of runoff beyond the far baseline must be in frame.

> **[PM-ARITHMETIC]** 10.97 m of near-baseline width at 6.00 m of setback needs
> `hfov ≥ 2·atan(5.485/6.00) = 84.9°`, plus margin → ~95-105°. **That is the 0.5x ultra-wide.** The
> main (1x, ~26 mm equiv, hfov ≈ 69°) would need **7.9 m** of setback, and a club court has 5.5-6.4 m
> behind the baseline. **The main lens cannot frame a full court at a real court.**

**Two consequences, neither of which is currently written down anywhere:**
1. **v1's shipped framing is an ULTRA-WIDE framing.** The detector, the four-tap and the k1 honesty
   gate all have to work through ultra-wide barrel distortion. This visit is the first evidence
   about that.
2. **Framing A can never reach bar A, at any height a person can mount.** At hfov 100° and 4K,
   `f = 1920/tan(50°) = 1611 px`, so `f·h = 5,639` at 3.5 m against the **8,862** needed for even
   1 px of down-court resolution at the far baseline. **Framing A is not a candidate — it is the
   real-footage counterpart of the measured FAILURE**, and that is exactly what it is for.

### 4.4 Framing B — FAR HALF, telephoto, and it is the only feasible escape

**Instruction at the court, no arithmetic required:** zoom to the **highest OPTICAL setting at which
both far-baseline doubles corners sit inside the frame with ≥5% margin on each side**. Write down
the zoom factor the screen shows.

**The on-the-day check that decides whether this cell is worth anything:** *does the far baseline
span at least HALF the screen width?* If not, framing B misses its own requirement and the cell is
decoration.

> **[PM-ARITHMETIC]** At 2x (≈41.1° hfov) and 4K, `f = 1920/tan(20.55°) = 5,122 px`. At h = 3.5 m,
> `f·h = 17,927` against the **17,724** that bar A's 2 px of detector noise requires. **It clears by
> 1.1%.** At 1080p the same cell gives `f·h = 8,963` — which clears the 1 px requirement and misses
> the 2 px one.

**So: 4K is NOT optional for framing B, and framing B is not optional if (b2) is to be decided.** It
is also the tightest margin in this document and it should be read as "marginal, not impossible",
which is a genuinely different status from framing A's "no solution at any setback".

**Three costs of framing B, all of which must be stated together:**
1. The near half of the court is out of frame. You call one end at a time.
2. Fewer observations of each arc, which may make P1's conditioning problem **worse** rather than
   better. This must be measured, not assumed.
3. **A device consequence three steps out: the iPhone SE 2nd and 3rd generation have no telephoto
   camera at all.** If framing B wins, the supported device list narrows **below** our stated A13
   floor. The founder should know that before, not after.

### 4.5 Camera settings — every take

- **4K at 60 fps** where the device offers it; otherwise **1080p60**. P3 found that **not one clip in
  213 is both 4K and 60 fps** — so if this device can do it, it is a combination this project has
  never had, and the downscaled-to-1080p copy of the same take is free. That pair is the data that
  would settle whether detector pixel noise grows with resolution (researcher's R7 caveat), which is
  otherwise undecidable under rule 6.
- **All stabilisation OFF** — Action Mode, "Enhanced Stabilisation", anything similar. Stabilisation
  is a per-frame warp: it manufactures exactly the background displacement that mount fixity is
  measured by, and it silently changes the effective intrinsics frame to frame.
- **HDR video OFF. Cinematic mode OFF.** Lock AE and AF (long-press the preview) before starting.
- Record which **lens** was used, per take. Ultra-wide and tele have different distortion.

---

## 5. THE RUN SHEET

### 5.1 Equipment

**Required**
- Camera(s): see §4.1. Charged, ≥64 GB free each (4K60 is ~400 MB/min).
- Mount: fence clamps (best) or a weighted tripod/light stand per camera. **Centre column DOWN, legs
  wide, weight on the hook.**
- 30 m tape measure; a rigid **steel rule** (300 mm minimum) — not a cloth tape, for the
  perpendicular reading.
- Bright gaffer tape (F-marks) or ground chalk.
- ~12 tennis balls; **coloured chalk / talc in 4 distinguishable colours** for hard court.
- Soft broom or damp cloth (to erase prints between batches).
- 4 marker cones.
- This document, printed; the tally sheet (§5.5), printed, ~6 copies; two pens.
- A thermometer or a weather app (for the speed of sound, §6).

**Strongly recommended — it is what makes this a one-person job**
- **A BALL MACHINE at the far baseline.** Repeatable placement, realistic speed and spin, and one
  person can run the whole session.

> **STATED UP FRONT, as asked: with a ball machine this is executable ALONE. WITHOUT a ball machine
> a HELPER IS REQUIRED** — one to feed from the opposite baseline, one to measure — or the solo
> session runs to roughly four hours of walking.

### 5.2 Setup order — the order matters

1. **Establish the mount.** Find the fence post nearest the centreline behind the near baseline.
   Tape-measure the setback to the near baseline and record it. Mark the spot.
2. **Find out what height this court allows.** Set the height pair per §4.2. Record both to ±2 cm,
   and record each camera's lateral offset from the centreline to ±2 cm.
3. **Mount the cameras. Do not aim them yet by hand after this point is fixed** — see step 7.
4. **Lay the 8 F-marks** (§3.3), tape-measured from the court's own lines. Double-check two of them.
5. **Place 4 cones**, each 1.0 m *outside* the line at the station currently in play, as an aiming
   reference for the feeder. A cone never goes in the print zone.
6. **Record the paint width** at one station per line type, on the tally sheet header.
7. **CALIBRATE LAST.** Aim and frame each camera, then **do not touch it again**. The four-tap
   calibration will be done later from **that take's own first frame** — never from a frame captured
   before the phone was finally placed. If you re-aim a camera for any reason, **that take is dead
   and restarts.**
8. **The 10-clap slate** (§6): stand 1.0 m in front of the lens and clap sharply **ten times**, ~1 s
   apart, in view of every camera, at the start of every take.
9. **GATE 0** (§7).

### 5.3 The ball session

Work one station at a time, in the order **L1 → L8, then C0 → C4** (near to far within each class,
so the broom work migrates away from you).

**Per batch of 4 balls:**
1. Dust 4 balls, one in each colour (hard court). On clay the natural ball mark is the reference and
   colours are a bonus, not a requirement.
2. Feed the 4 balls at the station's cone, one at a time, **noting the colour order on the tally
   sheet as you go**.
3. Walk out. Measure all 4 prints (§5.4). Photograph each.
4. Sweep the print area. Walk back.

**THE ATTRIBUTION RULE, and it is the one thing that can silently destroy the whole dataset:**

> **One row per BOUNCE, in time order. The tally sheet's row order IS the key that links a measured
> print to a bounce in the video.**
>
> - **Nothing else may bounce on the court during a take.** No warm-up, no stray balls, no ball
>   rolling back. If one does, write a VOID row for it anyway — do not skip it.
> - A ball that clips the net and bounces twice gets **two** rows.
> - A ball that misses everything and is re-fed still gets its own row.
>
> A skipped bounce shifts every subsequent row by one and turns clean measurements into confident
> wrong labels. That is worse than losing them.

**WHAT TO DO WHEN A BALL MISSES ITS MARK: nothing. It still counts.** This protocol does not ask the
ball to hit a target — it measures where the ball actually landed. Concretely:

- Print within **±0.60 m** perpendicular of the station's line → it is a **LINE** row and feeds that
  line's margin bar. The margin ladder (−60 cm … +60 cm) is produced by the ball's *natural
  scatter*; nobody has to control it.
- Print beyond ±0.60 m → mark it **SPAN**. It still feeds the range and obliquity analysis. Nothing
  is wasted.
- Print overlapping another print, or its rear edge not identifiable → **AMBIGUOUS**, discarded from
  the truth set, row still written.
- Ball hits the net, the fence, or lands off court → **VOID**, row still written, re-feed.

> **Why ±0.60 m and not ±0.20 m:** P1's p90 *lateral* error is **0.611 m**. The margin ladder has to
> span the estimator's own p90, or the truth set never exercises the decision boundary it exists to
> test.

### 5.4 How a print becomes truth — the ≤3 cm budget

1. Identify the print's **REAR edge** — the edge on the side the ball came **from**.
   > **THE TRUTH IS PINNED TO FIRST CONTACT, NOT THE PRINT'S CENTRE.** A skidding ball leaves a
   > 6-8 cm streak; its centre and its first-contact point differ by 3-4 cm, which is the entire
   > error budget on its own. SPEC §4's vertical-velocity sign reversal is an event at first contact,
   > so the rear edge is the quantity that matches the bar.
2. Lay the steel rule **perpendicular to the line**, through the rear edge. Read the distance from
   the rear edge to the **outer edge of the paint** (or to the **centre** of the paint for the centre
   service line — §3). Record in **mm**, signed: **positive = OUT** (away from the court centre for
   an ALONG line; away from the net for an ACROSS line).
3. Tape from the nearest F-mark **along the line** to where the rule crosses it. Record in mm, and
   record which F-mark.
4. Photograph from **directly above**, with the rule in shot. Record the photo number.
5. Sweep.

> **PRE-REGISTERED ERROR BUDGET.** rule reading ±2 mm · **rear-edge identification ±10 mm (the
> dominant term)** · along-line tape ±5 mm · F-mark placement ±10 mm · paint-edge identification
> ±3 mm. In quadrature: **±15 mm**, against the ≤30 mm bar. Two-sigma of margin, and it survives any
> single term doubling. **GATE 1.5 (§7) tests this on the day rather than trusting it.**

### 5.5 The tally sheet

**Header, once per take** — a missing entry here makes the take useless for geometry, because every
conclusion in P1/R1 is `D²/(f·h)` and `h` is the lever:

`TAKE ID · date · court name · SURFACE · device · lens · resolution · fps · stabilisation OFF? ·
MOUNT HEIGHT (±2 cm) · SETBACK (±5 cm) · lateral offset from centreline (±2 cm) · air temperature ·
wind · paint width by line type · slate: 10 claps at 1.0 m? · start time`

**One row per bounce:**

| # | Station | Colour | Perp. offset (mm, +OUT) | Along-line dist (mm) | From F-mark | Status | Photo # |
|---|---|---|---|---|---|---|---|
| 1 | L1 | red | | | F1 | LINE / SPAN / AMBIG / VOID | |
| 2 | | | | | | | |

### 5.6 Mount fixity — how it is secured, and how it is verified

P3 found this is the floor that actually binds: **a known static tripod reads 0.1-0.4 px of
background displacement; our best "compliant" clip reads 6.3 px**, and four of the fourteen
compliant clips are eliminated outright at 105-190 px.

**Securing it:**
- Fence clamp on a fence post, first choice. A weighted tripod on the ground, second. **Never** a
  bench, a bag, a wall ledge, or a stand you have not weighted.
- **Start recording with a timer, a voice command or a Bluetooth remote.** Pressing record with a
  finger is the single most common fixity failure and it happens at the start of every clip.
- **Short takes: 6-8 minutes each.** This is a scheduling decision and it is the real mitigation —
  one fixity failure then costs one take, not the visit.
- 20 s of **empty court before** and 20 s **after** each take, phone untouched.

**Verifying it on the day — and here is the honest limit.**
> **Fixity CANNOT be certified at the court. Only gross failure can be excluded there.** Flipping the
> before/after stills in Photos resolves maybe 2-3 px to a trained eye on a 1080p frame; the
> reference tripods sit at 0.1-0.4 px. So the eye check catches the **20 px class** (the drift
> clips), not the **6 px class**. The real number comes from the ORB/RANSAC background-displacement
> measurement after the visit.

The day's check is therefore **procedural plus gross**:
1. Flip the before-still and after-still of each take in Photos. A named fixed distant object (a
   fence post corner, a light pole) must show **no visible shift**. Visible shift → **the take is
   void, re-run it.**
2. **Declare the take void if**: anyone touched the camera, a ball struck the mount or the fence, or
   a gust moved the fence while recording. No judgement calls — void it and re-run. A 6-8 minute
   take is cheap; a wrong fixity assumption is not.

### 5.7 Surfaces

**§7 wants hard / clay / shell. P3 found Shell 0 and Grass 0 compliant.**

**The call: this visit must cover HARD COURT and CLAY, on two visits if necessary. Shell is a third
visit and it is not urgent.**

- **Hard court first if forced to choose** — it matches 39 of the corpus's clips and all 7 strictly
  compliant ones, and the dusted-ball print is controllable.
- **Clay is the cheaper truth source** — the ball mark is the reference standard used to adjudicate
  real clay line calls, it is free, permanent and unambiguous, and it roughly halves the per-point
  time. If both are available on the same day, do clay second and enjoy it.
- **Clay caution:** do not drag or sweep the whole court mid-session. The lines are pinned tapes and
  the calibration depends on them not moving. Brush the print area only.

**What is lost if only ONE surface is available, stated precisely, because the loss is smaller than
it looks:**
> **Geometry is surface-blind.** The obliquity gradient, the `1/h` scaling and the direction split
> are properties of the camera and the court dimensions, not the surface. A single-surface visit
> answers **all** of the geometric questions in §8.
>
> What a single surface leaves open is exactly two things: (i) **whether truth can be MADE at all**
> on the missing surface — on shell/sand infill a ball mark is poor, which is a real risk to a future
> shell visit; and (ii) **detector contrast** against a different background. Neither is a geometry
> question. So: **one surface is a valid and worthwhile visit. Two meets the bar. Do not delay the
> first visit to arrange the second.**

---

## 6. BOUNCE TIMING FROM AUDIO — **ACCEPTED**, with two mandatory corrections

SPEC §4 needs **±1 frame, 90% of the time**. The audio transient of the ball striking the court is
the **GAME, not an overlay** — it is the physical event itself, so rule 12 permits it, and it is
independent of the visual track, which is what makes it useful.

**But uncorrected it is disqualifying, and the reason is worse than "it is late".**

> **[PM-ARITHMETIC]** Sound covers 343 m/s at 20 °C. Slant distance camera→bounce at h = 3.0 m:
>
> | Station | slant dist | delay | **frames @60 fps** |
> |---|---|---|---|
> | C0 (near baseline) | 6.71 m | 19.6 ms | **+1.17** |
> | C1 (near service) | 11.87 m | 34.6 ms | **+2.08** |
> | L8 (far doubles corner) | 28.99 m | 84.5 ms | **+5.07** |
> | C4 (far baseline) | 30.20 m | 88.0 ms | **+5.28** |
>
> Uncorrected, the bias runs **+1.17 to +5.28 frames** — and it is **RANGE-DEPENDENT**, spread over
> 4.1 frames across the court. A constant bias is annoying; a range-dependent one is dangerous,
> because it is exactly the signature an estimator bias would have. **P1's bar B already found the
> fitted arc crossing the ground +3.66 frames late.** That number sits squarely inside this band. It
> was measured on synthetic flights, so audio cannot be its cause — but anyone who ever times truth
> by an uncorrected audio transient will manufacture that bias and then explain it as physics.

**The correction is exact, and this truth set is the one thing that makes it possible:** we know the
camera position and — by construction, to ≤3 cm — the bounce's true ground position. So
`t_contact = t_audio − d/c`, with `c = 331.3 + 0.606·T`.

**Residual budget:**

| Term | Contribution |
|---|---|
| ±3 cm in `d` | ±0.005 frames |
| ±2 °C in temperature (a thermometer or the weather app) | ±0.02 frames |
| Locating the transient onset (~±2 ms) | ±0.12 frames |
| **Audio/video sync inside the phone container** | **the real unknown — see below** |

**The A/V sync term is why the 10-clap slate is mandatory.** A single clap can only be located to
±0.5 frame visually, which would be a constant per-take bias at half the bar. But the clap's phase
relative to the frame clock is random, so **ten claps averaged give ±0.5/√12/√10 ≈ ±0.05 frames.**
Clap **1.0 m in front of the lens** so the clap's own propagation delay (2.9 ms = 0.18 frames) is
known exactly and subtracted.

**Total residual ≈ ±0.15 frames against a ±1 frame bar — a 6x margin. VERDICT: USE IT.**

**Three caveats, carried rather than buried:**
1. **The audio marks FIRST CONTACT. The vertical-velocity sign reversal happens mid-compression,
   about 3-5 ms later — roughly +0.2 to +0.3 frames.** That is a known, small, one-sided offset. It
   must be **declared** in the label, not absorbed into the estimator's error.
2. **Audibility at 30 m is not guaranteed.** Wind, traffic or an indoor echo can bury the far-baseline
   transient. **GATE 0 field-tests it in the first five minutes**, and if the far baseline is
   inaudible the audio arm is limited to the near half and that is recorded, not worked around.
3. A ball machine's firing thump is also a transient. It precedes its bounce by ~1 s so it is
   separable, but the label pass must know it is there.

---

## 7. THE VISIT'S OWN SUCCESS CRITERION — pre-registered, checkable before packing up

**This section matters more than anything else in the document.** A failed visit discovered a week
later costs another visit, and a court visit has days of lead time. **Every gate below is checkable
with a phone and this sheet of paper, and every way a gate can fail has a same-day remedy.**

### GATE 0 — the five-minute dry run. Before any real data. Four yes/no answers.
1. Dust and feed **4 coloured balls** at one station. Are the prints **readable** and **distinguishable
   by colour**? *(No → batch size drops to 2, or to 1 on clay. Session gets longer; data is unharmed.)*
2. Play back 10 s of the take on the phone. Is a **far-baseline bounce audible**? *(No → the audio
   timing arm is near-half only. Record it and continue.)*
3. On framing A, are **all four doubles corners plus ~1 m of runoff** in frame? *(No → increase
   setback, or the ultra-wide is not wide enough on this device. Fix it now.)*
4. On framing B, does the **far baseline span at least HALF the screen width**? *(No → framing B will
   not clear its own requirement. Either get more optical zoom or drop framing B and reallocate the
   camera to the height pair.)*

### GATE 1 — count, on paper, not on video
**≥30 rows marked CLEAN (LINE or SPAN) in the ALONG class, AND ≥30 in the ACROSS class.**
*Remedy if short: feed more at the thin stations while you are still standing on the court.*

### GATE 1.5 — the truth-quality check, run after the FIRST 10 prints, not at the end
Re-measure **5 prints a second time, blind to the first reading** (fold the sheet over). **If any
repeat differs from the first by more than 2 cm, the measuring procedure is not meeting its ±15 mm
budget and must be changed before continuing.**
*This is the only gate that tests the truth itself, and it is deliberately early: if it fires at the
end, the visit is already spent.*

### GATE 2 — spread, so the two axes can actually be separated
- **≥8 clean rows in each of the 6 primary cells**: {ALONG, ACROSS} x {near band, far-service band,
  far band}.
- **≥8 clean rows at each of the 3 ALONG obliquity levels**: 0 m, 4.115 m, 5.485 m.
*Remedy: feed more at that station. This is why the gate is counted on the day.*

### GATE 3 — fixity, per take
Every take: camera untouched between the start slate and the end slate; before/after empty stills
flipped in Photos show no visible shift. **A failing take is VOID and re-run.**

### GATE 4 — the take matrix
- **MANDATORY: the height pair exists at framing A, over the SAME bounces.** Without it, the visit
  has not answered its primary question.
- **DESIRABLE: the framing pair exists at the higher height.**
*If only two cameras are available and time is short, the height pair wins. Framing B is the first
thing cut.*

### GATE 5 — the metric record
Mount height per camera (±2 cm), setback (±5 cm), lateral offset from centreline (±2 cm),
temperature, surface, device/lens/resolution/fps per take, paint widths, 10-clap slate on every
take. **Any of these missing makes the take unusable for geometry.**

### The cut ladder, if time runs out — in this order, and no other
1. **Framing B** (both heights).
2. **The 4.115 m obliquity level** (L2, L5, L7 — 16 balls, ~20 min). The R1b contrast survives on
   0 m vs 5.485 m, which is the whole gradient.
3. **Nothing else.**
> **Never cut below 30 clean per class.** That is the pre-registered bar. A half-length visit does not
> produce a smaller result; it produces **no** result, and it will have to be repeated.

---

## 8. WHAT EACH ARTEFACT FEEDS

| Artefact | Feeds |
|---|---|
| ALONG truth set, by **obliquity level** | R1b's gradient on **real** footage: does 0.049 m → 0.348 m (72.9% → 20.0%) survive a real detector's correlated, heavy-tailed noise? |
| ALONG truth set, by **range band** | SPEC §3.1 — the per-line, **per-region** bar R1b showed is required |
| ACROSS truth set, by range band | SPEC §3.2 — whether any across-court accuracy bar can honestly be offered at all |
| **Both classes at matched ranges** | the direction split itself — separates direction from depth, which a pooled set cannot |
| ACROSS truth set, by obliquity | the **cos θ control** of §2: predicts NO gradient. A gradient here refutes the quadrature model |
| **Paired 2.5 / 3.5 m heights, same bounces** | the `1/h` radial scaling on real footage. **Pre-registered prediction, written before the data:** paired median `\|Δy\|` ratio (low/high) in **1.2-1.6**; paired median `\|Δx\|` ratio in **0.9-1.15**. Outside either range and the geometric diagnosis is incomplete. Also re-tests bar D's founding premise in a regime where not everything fails |
| **Framing A vs B, same bounces** | the (b2) telephoto decision → and its device consequence (SE has no tele) |
| **4K60 take + its 1080p downscale** | P3's "not one clip in 213 is both". Also the only clean read on researcher's R7: does detector pixel error grow with resolution? (The project has measured the opposite hazard — 720p-tuned thresholds silently deleting balls at 1080p.) |
| **Audio-derived bounce frames** | SPEC §4's ±1 frame timing bar, from a source independent of the visual track |
| **F-mark fiducials** | the first independent measurement of four-tap calibration accuracy; and the **only** way to calibrate framing B |
| Empty-court before/after stills | mount fixity, against the 0.1-0.4 px static-tripod reference |
| Per-print photos with the rule in shot | post-hoc audit of the ≤3 cm budget — the truth set must itself be checkable (rule 1) |

---

## 9. TIME, AND WHO IS NEEDED

| Step | Minutes |
|---|---|
| Setback, mount position, height measurement and recording | 30 |
| 8 F-marks, tape-measured | 25 |
| Cones, paint widths, camera settings | 10 |
| GATE 0 dry run | 10 |
| Ball machine setup and aim | 15 |
| **Ball session: 86 feeds, batched, incl. GATE 1.5 and re-aims** | **110** |
| End slates, before/after stills | 5 |
| Pack, final gate checklist | 15 |
| **TOTAL — 4 cameras, one pass** | **≈ 3 h 40 min** |
| 2 cameras, second pass for framing B | + ~70 min → ≈ 4 h 50 min |
| Minimum viable (height pair only, framing A) | ≈ 3 h 30 min |

**There is no 90-minute version.** The ball session dominates and it does not compress — 86 prints
have to be walked to and measured. Budget a **half day** and book the court for **four hours**.

**Alone with a ball machine: yes. Alone without one: no — bring a helper**, or accept roughly four
hours of walking for the same data.

---

## 10. WHAT THIS COSTS, AND WHAT DOES NOT GET BUILT

**Sessions:** ~1 to write this (spent). The visit is the founder's half day. **~2 sessions afterwards**
to ingest, calibrate, label and score — and that work cannot start until the footage exists.

**What the yes to this is a no to:** P2's occlusion census and P6/P7 slip by the same ~2 sessions.
That is the right trade: P2 can only *raise* the refusal floor and does not gate anything, whereas
every bar in SPEC §3 and §4 is currently scored on synthetic flights with i.i.d. Gaussian noise and a
uniform flight population. **This visit is the first real-footage falsifier the project has ever
had for the whole geometric diagnosis.**

**Definition of done for THIS DOCUMENT** (written before the visit, per rule 2): the founder can
execute it end to end without asking a question; every gate in §7 is answerable with a phone and a
sheet of paper; and no number in §3 was invented — all of them come from `backend/swingvision/court.py`.

**Definition of done for THE VISIT:** all gates in §7 pass before packing up.

---

## 11. OPEN QUESTIONS — for the founder, not blocking the visit

1. **Is a ball machine obtainable?** It is the difference between a one-person job and a two-person
   one, and between 110 minutes of ball session and ~200.
2. **How many cameras can you put on the fence?** Four turns one visit into four answers. This is the
   single highest-leverage logistics decision in the document.
3. **What height does your court actually allow?** The 2.5 m ask has been open ten days. The answer
   changes the height pair, and §4.2 already tells you what to do with any answer.
4. **Hard court or clay first?** Either is a valid visit (§5.7). Do not delay to arrange both.
