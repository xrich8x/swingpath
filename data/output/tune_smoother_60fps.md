# `max_gap_s` at 60 fps — a measured negative. 0.4 stays.

The frame-rate work (fps_decision.md) found that processing a 60 fps clip at full
rate improves every measurement number, and that the entire false-fire cost sits
in the Kalman smoother: through the detector and its gates 60 fps is *better*
(15.4% vs 19.2% on yt_rally2), and the smoother takes it to 30.8% vs 23.1%.
`smooth_forecast`'s `max_gap_s = 0.4` had only ever been swept at 30 fps
(Session F step 4), so it was named as the one thing blocking full-rate processing.

Swept now, at 60 fps, on **both** native-60fps calibrated gold clips.

**Pre-registered gate**, written before running: accept a 60 fps setting only if it
matches or beats the shipped 30 fps baseline on **recall AND far_geo** — E6 bought
those and this may not spend them — and does not increase solid ghost fires. Ghost
total is minimised subject to that.

Baseline (yt_rally2, step 2, `max_gap_s` 0.4): recall 72.5%, far_geo 74.3%,
false-fire 23.1%, 6 fires (5 solid / 1 faded).

---

## yt_rally2 @ 60 fps — 258 ball / 26 no-ball frames

| `max_gap_s` | frames | false-fire | recall | far_geo | ghost |
|---|---|---|---|---|---|
| ≤0.10 | 2–6 | 15.4% | 68.2% | 62.6% | 4 (4s/0f) |
| 0.15 | 9 | 26.9% | 68.6% | 63.1% | 7 (4s/3f) |
| 0.20 | 12 | 30.8% | 70.5% | 65.9% | 8 (4s/4f) |
| 0.30 | 18 | 30.8% | 73.6% | 70.4% | 8 (4s/4f) |
| **0.40 shipped** | 24 | 30.8% | 75.2% | 72.6% | 8 (4s/4f) |
| 0.60 | 36 | 30.8% | **77.1%** | **75.4%** | 8 (4s/4f) |
| 0.80 | 48 | 38.5% | 78.7% | 77.7% | 10 (4s/6f) |
| 1.00–1.50 | 60–90 | 38.5% | 79.8% | 79.3% | 10 (4s/6f) |
| 2.00 | 120 | 84.6% | 79.8% | 79.3% | 22 (4s/18f) |

Ghost is FLAT at 8 from 0.20 through 0.60, then breaks. 0.60 looks like a clean
knee and is the only setting that passes the gate: recall 77.1% ✓, far_geo 75.4% ✓,
solid ghosts 4 ✓.

## am_hard_utr @ 60 fps — 175 ball / 53 no-ball frames

| `max_gap_s` | frames | false-fire | recall | far_geo | ghost |
|---|---|---|---|---|---|
| 0.00 | 2 | 9.4% | 43.4% | 48.9% | 5 (5s/0f) |
| 0.10 | 6 | 9.4% | 48.6% | 54.6% | 5 (5s/0f) |
| 0.20 | 12 | 11.3% | 50.3% | 55.3% | 6 (5s/1f) |
| 0.30 | 18 | 15.1% | 54.3% | 60.3% | 8 (5s/3f) |
| **0.40 shipped** | 24 | 17.0% | 54.9% | 61.0% | 9 (5s/4f) |
| 0.60 | 36 | **22.6%** | 55.4% | 61.7% | **12** (5s/7f) |
| 0.80 | 48 | 32.1% | 55.4% | 61.7% | 17 (5s/12f) |
| 1.00 | 60 | 32.1% | 55.4% | 61.7% | 17 (5s/12f) |

**There is no flat region here.** False-fire rises monotonically. Going 0.4 → 0.6
costs **+5.6 pts of false-fire and +3 ghost frames** to buy **+0.5 pts of recall**.

---

## Verdict: GATE FAILS on replication. `max_gap_s = 0.4` stays.

The 0.60 knee is a **yt_rally2 artefact**. Pooled over both clips, 0.4 → 0.6 buys
+1.9 / +0.5 pts of recall for +0 / +5.6 pts of false-fire and 0 / +3 ghost frames.

**WHY THEY DISAGREE, and this is the transferable part.** yt_rally2 is a 3.31 m
camera with dense detections (recall 75%); its gaps are short, so widening the
bridge past 0.4 s rarely finds a gap to fill — hence the flat region. am_hard_utr
is a **1.74 m** camera at 1080p with recall 54.9%; its detections are sparse, its
gaps are long, and every extra 0.1 s of bridge invents more ball. So the optimal
gap policy scales with DETECTION DENSITY, and the low-camera amateur clip — which
is the footage this project targets — is the one that punishes a wide bridge.
Tuning this on the easy clip would have shipped a setting that is actively worse
where it matters most.

### The useful consequence

The blocker named in fps_decision.md is **removed, not resolved in its favour**:
`max_gap_s = 0.4` is already the right value at 60 fps on both clips, so full-rate
processing needs **no re-tune and no rate-dependent gap policy**. That is a
simpler outcome than expected, and it means the remaining 60 fps false-fire cost
(yt_rally2 23.1% → 30.8%) is **not** something the gap policy can remove — the
same shape as Session F's finding that nothing downstream of the detector removes
a solid ghost, except here it is the faded half that will not move.

### Correction to fps_decision.md as first written

That file explained the ghost increase (6 → 8) as the Session F frame-step trap,
on the reasoning that a 0.4 s bridge holds twice the frames at 60 fps. **That
reasoning is wrong and is withdrawn.** The tool scores a FIXED set of human-labelled
source frames — 258 ball / 26 no-ball, scoreable at both steps on this clip — so
the fire count is directly comparable across rates. The 6 → 8 increase is real:
two more of 26 no-ball frames get a drawn ball. Solid fires did fall 5 → 4, so the
extra two are interpolated, but they are still ghosts.

Reproduce:

```
cd backend
.venv-train/Scripts/python.exe ../tools/tune_smoother.py --clip yt_rally2 --device cuda --frame-step 1 --max-gap-s 0.0 0.10 0.20 0.30 0.40 0.60 0.80 1.00 1.50 2.00
.venv-train/Scripts/python.exe ../tools/tune_smoother.py --clip am_hard_utr --device cuda --frame-step 1 --max-gap-s 0.0 0.10 0.20 0.30 0.40 0.60 0.80 1.00
```
