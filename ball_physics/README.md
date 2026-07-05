# Tennis Ball Speed & Spin — a monocular tracking framework

A runnable research framework for estimating tennis-ball **speed** and **spin**
from a single consumer camera (a phone on a tripod), in the spirit of
SwingVision. It pairs a physically-correct flight model with learnable
components and is organised so you can swap in stronger public models without
touching the rest of the pipeline.

The core physics, synthetic-data generation, calibration, tracking, and the
physics-inversion estimator are implemented in NumPy/SciPy/OpenCV and are
**validated and runnable today**. The two learned components — the ball
detector and the learned spin/velocity estimator — are implemented in PyTorch
for you to train.

> Dropped into the SwingVision-clone repo under `ball_physics/`. It is a
> self-contained package; run scripts/tests from this directory.

## The key idea

A phone shoots at 30–60 fps. At those rates **you cannot read spin off the ball
optically** — the logo/seam blur is unreliable and the ball is a few pixels
wide. So spin is **inferred from the geometry of flight**: the Magnus force
bends the trajectory as a function of the spin vector, and the bounce changes
direction as a function of spin. Recover the 3D trajectory accurately and you
can solve for spin by inverting the physics.

A second reality shapes the design: **real spin labels barely exist**. The fix —
established by Kienzle et al. (CVPRW 2025) — is to train spin estimation
**entirely on synthetic, physically-simulated trajectories** and transfer to
real video. The simulator here is that data engine.

## Pipeline

```
 video ─▶ [2] detect ball ─▶ [3] track + smooth + ─▶ [4] calibrate court ─▶ [5] speed  ─▶ [6] spin ─▶ [7] eval
          (heatmap CNN)        bounce + segment        + lift 2D→3D            (fit |v0|)    (Magnus inv.)
   [1] ground truth & synthetic data underpins detector pre-training and ALL spin training
```

| # | Stage | Module | Status |
|---|-------|--------|--------|
| 1 | Synthetic data / ground truth | `data/synthesize.py`, `physics/` | runnable ✓ |
| 2 | Ball detection (heatmaps) | `detection/tracknet.py` + training | PyTorch, train it |
| 3 | Track / smooth / bounce / segment | `tracking/tracker.py` | runnable ✓ |
| 4 | Court homography + 2D→3D lift | `calibration/court.py`, `calibration/lift.py` | runnable ✓ |
| 5 | Speed (fit `|v0|`) | `estimation/trajectory_fit.py` | runnable ✓ |
| 6 | Spin (physics inversion + learned) | `estimation/trajectory_fit.py`, `estimation/spin_net.py` | fit ✓ / SpinNet: train it |
| 7 | Evaluation | `eval/metrics.py` | runnable ✓ |

## What's validated

- **Physics** — topspin dips/lands short; backspin floats long; sidespin curves
  several metres; quadratic drag bleeds ~40% of ball speed.
- **Speed from one arc** — launch speed to < 0.1 % from clean 3D, ~0.2–5 % from
  monocular 2D.
- **Spin** — magnitude to a few percent; the spin *axis* is ill-conditioned on a
  single short arc (≈ 0–30° with noise) — why bounce anchoring + SpinNet exist.
- **Calibration** — court-plane ⇄ image homography round-trips to ~0 m.

Reference: a recent single-camera speed+spin system reports ~4.8 % speed MAE,
~3.4 % spin RMSE — the ballpark once the detector and SpinNet are trained.

## Quickstart (no training, no GPU)

```bash
pip install -r requirements.txt
python scripts/demo_physics.py --out physics_demo.png   # how spin bends flight
python scripts/demo_fit.py                               # recover speed & spin
python tests/test_physics.py                             # validation suite
```

## The monocular catch

From one view, an airborne point's depth is not directly observable. Three
things resolve it, all built in: (1) **anchor at contact** — a bounce lies on a
known plane, so the homography gives exact 3D; (2) **ball-size depth cue**;
(3) a **learned prior (SpinNet)** trained on synthetic tracks, refined by the
physics fit.

## Train the components

```bash
# detector (TrackNet CSV datasets, e.g. yastrebksv/TrackNet)
python -m tennis_tracker.detection.train_tracknet --data /path/to/dataset --epochs 30 --out runs/tracknet
# learned spin/velocity (synthetic-to-real)
python scripts/make_synthetic_dataset.py --n 20000 --out data/synth_train.npz
python scripts/make_synthetic_dataset.py --n 2000  --out data/synth_val.npz --seed 99
python -m tennis_tracker.estimation.train_spin_net --train data/synth_train.npz --val data/synth_val.npz --epochs 50 --out runs/spinnet
```

## Conventions

- `x` along court length (near baseline `0`, far `23.77`, net `11.885`); `y`
  across width (centre `0`); `z` up.
- Topspin → ω about **+y** (Magnus down, dips/short); backspin → −y; sidespin →
  about ±z.

## Open-source building blocks (drop in behind the same interfaces)

- **Ball**: TrackNet (yastrebksv/TrackNet), WASB (nttcom/WASB-SBDT), BlurBall
  (cogsys-tuebingen/blurball).
- **Court**: yastrebksv/TennisCourtDetector (14-keypoint heatmap + homography).
- **Spin/3D**: Kienzle et al. arXiv:2504.19863; Uplifting Table Tennis
  arXiv:2511.20250; TT3D 2504.10035. Physics: Cross; Stepanek (1988).

## Integrating with the SwingVision-clone

This repo already has a TrackNet ball detector (`backend/swingvision/ball.py`)
and a court homography (the Court Setup tab / `calibration.py`). To feed those
into this framework: build a `data.camera.Camera` from the court homography
(decompose H with the camera intrinsics, or `cv2.solvePnP` on the 4 court
corners), then call `TennisTracker(camera, homography, ...).process_track(times,
uv_track)` with the ball pixel track. See `scripts/bridge_demo.py` if present.
