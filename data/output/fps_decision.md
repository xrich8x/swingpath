# Frame rate: is `frame_step="auto"` throwing away accuracy?

`frame_step="auto"` targets ~30 fps to match TrackNet's rate, so on a 60 fps phone
clip the pipeline **processes every other frame and discards the rest**. This asks
what that costs.

Two independent measurements: a synthetic isolation (exact truth, large n, one
variable at a time) and an end-to-end A/B on a real 60 fps clip.

---

## 1. Synthetic isolation — frame rate separated from detector dropout

The first control run (height_curve.md §C) varied frame rate **and** dropout
together and the whole gap was attributed to frame rate. That was wrong: they are
different things to a user. Frame rate is a free recording and processing choice;
dropout is a detector property you cannot switch off.

Truth is computed once on a 240 Hz grid and every rate is an exact **decimation**
of it (`synth_truth.simulate(truth_fps=...)`), so the runs are strictly nested —
the 30 fps track is literally a subset of the 60 fps one, over identical flights
and an identical near-line population. Without this the truth bounce itself would
be least accurate at low fps and the comparison would flatter high rates for free.

Cells are `close-call accuracy / median bounce error`.

**Detector dropout held at the shipped 30%:**

| fps | 1.5 m | 3.0 m | 12.0 m |
|---|---|---|---|
| 15 | 57.7% / 5.50 m | 67.1% / 1.94 m | 81.4% / 0.52 m |
| **30 (shipped)** | **60.5% / 2.15 m** | **72.6% / 0.88 m** | **82.8% / 0.38 m** |
| **60** | **66.3% / 1.39 m** | **75.8% / 0.66 m** | **84.6% / 0.29 m** |
| 120 | 70.3% / 1.17 m | 76.9% / 0.57 m | 87.5% / 0.24 m |
| 240 | 72.9% / 1.10 m | 79.9% / 0.55 m | 86.4% / 0.21 m |

**Detector dropout held at 0%:**

| fps | 1.5 m | 3.0 m | 12.0 m |
|---|---|---|---|
| 15 | 62.0% / 2.87 m | 73.4% / 1.08 m | 83.7% / 0.43 m |
| 30 | 65.2% / 1.44 m | 75.1% / 0.65 m | 85.0% / 0.31 m |
| 60 | 68.5% / 1.17 m | 77.7% / 0.57 m | 86.8% / 0.25 m |
| 120 | 71.4% / 1.10 m | 76.9% / 0.55 m | 87.2% / 0.21 m |
| 240 | 72.5% / 1.05 m | 80.2% / 0.53 m | 86.4% / 0.20 m |

**30 → 60 fps is worth +5.8 pts of close-call accuracy at 1.5 m, +3.2 at 3.0 m,
+1.8 at 12.0 m, and cuts bounce error by 24–35%** — and it holds at both dropout
levels, so it is not a dropout effect in disguise.

For scale, at 30 fps *eliminating detector dropout entirely* buys +4.7 / +2.5 /
+2.2 pts at the same heights. **Doubling the frame rate we already have is worth
about as much as a perfect detector**, and unlike a perfect detector it is free.

Returns flatten above 60–120 fps. 15 fps is close to the majority-class floor and
should be treated as unusable.

---

## 2. End-to-end A/B on a real 60 fps clip

`data/yt_rally2.mp4` — 60 fps, 720p, calibrated at 1.4 px / 3.31 m, human ball
labels, and the 17 SwingVision HUD speed readings. Fresh perception both arms
(no cached runs), `ballnet_v21`, CUDA.

| | shipped (step 2, 30 fps eff) | full 60 fps (step 1) |
|---|---|---|
| gold per-frame recall | 72.5% | **75.2%** |
| far_geo recall | **74.3%** | 72.6% |
| false-fire on no-ball frames | **23.1%** | 30.8% |
| — before the Kalman smoother | 19.2% | **15.4%** |
| physics-arc reproj, median | 148.2 px | **91.2 px** |
| physics-arc reproj, best | 103.1 px | **24.5 px** |
| HUD speed MAE, confident shots | 38.9% (n=6) | **33.1% (n=7)** |
| HUD strokes we produced nothing for | 8 | **6** |
| shots with trusted speed | 7 of 12 | **8** of 16 |

**Every measurement-quality number improves.** The physics arc fit — the shipped
preferred speed path — nearly halves its reprojection error, and against the one
external reference this project has, speed error drops 5.8 points while covering
one more stroke.

**The cost is concentrated in one place, and it is the smoother.** Through the
detector and its gates, 60 fps is *better* on false-fire (15.4% vs 19.2%). The
Kalman stage then takes it to 30.8% vs 23.1% — it roughly doubles false-fire at
60 fps versus a third at 30. `max_gap_s = 0.4 s` bridges twice as many frames at
60 fps, and it has only ever been swept at 30 (Session F step 4).

### Two things that look like regressions and are not

- **`fixture` rejections 83 → 0.** The static-lock gate is already fps-scaled
  (`static_step_px = STATIC_STEP_PX_PER_S / fps`, `static_min_run =
  STATIC_MIN_RUN_S * fps`, Session E3c). At 60 fps it correctly declines to
  classify a slow-looking far ball as a fixture — the exact failure that scaling
  was introduced to fix. Working as designed.
- ~~**Ghost `fires` 6 → 8** — a 0.4 s bridge contains twice as many frames at
  60 fps, so the count is not comparable across rates.~~ **WITHDRAWN.** The scorer
  uses a FIXED set of human-labelled source frames (258 ball / 26 no-ball, all
  scoreable at both steps on this clip), so fire counts ARE directly comparable.
  The 6 → 8 increase is real: two more of 26 no-ball frames get a drawn ball.
  Solid fires did fall 5 → 4, so the extra two are interpolated — but they are
  still drawn where a human said there was no ball. See tune_smoother_60fps.md.

### One number still unexplained

`no-detection` misses went 10.1% → 20.0% of processed frames while the overall
lock rate *rose* (83.8% → 87.2%). Gold recall says per-frame detection did not get
worse, so this is most likely counter bookkeeping shifting between categories as
the fixture gate stops firing. **Not verified — do not cite it as a finding.**

---

## Verdict

The measurement case for processing 60 fps clips at full rate is strong and
consistent across two independent methods.

**The `max_gap_s` sweep is now done** (tune_smoother_60fps.md) and it came back a
measured negative: 0.4 is already the right value at 60 fps on both native-60fps
gold clips, so full-rate processing needs no re-tune and no rate-dependent gap
policy. The remaining 60 fps false-fire cost is therefore not something the gap
policy can remove.

What is left is a product call, not more measurement: 60 fps wins the MEASUREMENT
decisively and is a wash-to-negative on DETECTION, at 2x perception cost.

Reproduce:

```
cd backend
.venv-train/Scripts/python.exe ../tools/height_curve.py --n 6000 --fps-sweep --skip-real
.venv-train/Scripts/python.exe run.py analyze ../data/yt_rally2.mp4 --keypoints ../data/yt_rally2_pts.json --out ../data/output/fps_b_full60.json --frame-step 1 --device cuda
.venv-train/Scripts/python.exe ../tools/eval_model_filters.py --weights weights/ballnet_v21.pt --clip yt_rally2 --device cuda --frame-step 1
```
