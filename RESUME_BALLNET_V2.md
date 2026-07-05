# RESUME — BallNet v2 pipeline (paused mid-run 2026-07-06)

Session paused on a usage limit. This is the exact runbook to finish. All
tooling is committed; the only thing not on disk-and-committed is the
regenerated ball dataset (gitignored, regenerable) and the v2 weights (not
trained yet). Follow the steps in order. Commands run from the repo root
`E:\Claude Outputs\Cowork Tasks\Swing Vision` unless noted.

Interpreters (see memory [[python-invoked-as-py]]):
- CPU / general: `backend\.venv\Scripts\python.exe`
- CUDA (training, GPU perception): `backend\.venv-train\Scripts\python.exe`
  (RTX 5060 Ti 16GB; torch cu128)

## State at pause

- Gold benchmarks DONE and committed:
  - `data/gold/yt_rally2.labels.json` — 300 labels (258 ball/26 no-ball/16 unsure).
  - `data/gold/yt_match40.labels.json` — 300 labels (184 ball/24 no-ball/92 unsure).
    yt_match40 is the COLD generalization clip — in NO training data (verified
    visually + by duration/fps vs all 10 train clips). NEVER train on either.
- BallNet v1 gold scores (the bar v2 must beat), hit@10px on yt_rally2:
  ballnet 65.9 / archive 65.5 / fusion 43.0 / tracknet 41.5; false-fire on
  true dead time: ballnet/archive 58.8%, gated fresh 5.9%. v2's job: keep
  v1's recall, kill the false-fire. Full tables: `data/gold/yt_rally2.benchmark.md`,
  HANDOFF.md §11.
- Pseudo-label REGEN (background job bgowrdsr2) was 7/10 clips done at pause,
  writing `data/ball_dataset/yt_<id>/{*.jpg,labels.json}` with the static gate
  ON and mined "negatives". Script: `backend/relabel_train_clips.py`.

## STEP 1 — confirm the regen finished (or rerun it)

Check every training clip has a fresh gated labels.json with a `negatives` key:

```
backend\.venv\Scripts\python.exe -c "import json,glob,os; \
[print(os.path.basename(os.path.dirname(p)), 'neg=' in open(p).read() or 'negatives' in json.load(open(p))) for p in glob.glob('data/ball_dataset/yt_*/labels.json')]"
```

Expect 10 `yt_*` dirs, each True. If fewer than 10 or any lacks `negatives`,
rerun the regen (GPU, ~50 min):

```
cd backend
.venv-train\Scripts\python.exe relabel_train_clips.py --device cuda
```

(indoor_elev = yt_rally2 is intentionally NOT regenerated — it's the gold clip.)

## STEP 2 — train BallNet v2 (GPU, ~25 min)

```
cd backend
.venv-train\Scripts\python.exe train_ballnet.py --epochs 40 --out weights/ballnet_v2.pt
```

- `--exclude` defaults to `indoor_elev` (yt_rally2) — leave it; v2 must not
  see the gold clip.
- Watch the log: it prints `within10px` AND `false-fire %` per epoch. The best
  checkpoint is chosen by `hit@10 minus false-fire`, so it can't win by firing
  everywhere. Accept only if best false-fire is well under v1's implied ~59%.
- v1 stays at `weights/ballnet.pt` (untouched); v2 is a separate file.

## STEP 3 — score v2 on yt_rally2 gold (v1's home clip, v2 has never seen it)

Generate v2's track on yt_rally2 (CPU is fine, 2215 frames ~25 min; or cuda):

```
backend\.venv\Scripts\python.exe backend\run.py analyze data\yt_rally2.mp4 \
  --keypoints data\yt_rally2_pts.json --ball-model ours --pose-quality fast \
  --frame-step 2 --out data\output\yt_rally2_v2.json
```

(`--ball-model ours` = BallNet. Ensure it loads `weights/ballnet_v2.pt` — if
OurBallDetector hardcodes `ballnet.pt`, either temporarily copy v2 over it OR
add a weights arg. SAFEST: `copy backend\weights\ballnet_v2.pt` to a temp,
point the detector at it; do NOT overwrite `ballnet.pt` without a backup.)

Then score all five:

```
backend\.venv\Scripts\python.exe tools\eval_gold.py \
  --labels data\gold\yt_rally2.labels.json \
  data\output\demo30.perception.json \
  data\output\demo30_staticgate_fusion.perception.json \
  data\output\demo30_staticgate_tracknet.perception.json \
  data\output\demo30b.perception.json \
  data\output\yt_rally2_v2.perception.json \
  --names archive968 fusion746 tracknet686 ballnet_v1 ballnet_v2 \
  --markdown data\gold\yt_rally2.benchmark.md
```

## STEP 4 — score on yt_match40 (the COLD clip) — the real generalization test

yt_match40 has NO court calibration (no keypoints). That's fine for a BALL
benchmark (we score pixels vs clicks); the court-plausibility gate is simply
off there. Run each track over the full clip (10,268 frames). Parallelize:
GPU on the big set, CPU on whatever's spare.

```
# for m in tracknet, fusion, ours(v1), ours(v2):
backend\.venv-train\Scripts\python.exe backend\run.py analyze data\yt_match40.mp4 \
  --ball-model <m> --pose-quality fast --frame-step 1 --device cuda \
  --out data\output\yt_match40_<m>.json
```

Note: manifest frame_step for yt_match40 is 1 (uniform selection), so run
perception at `--frame-step 1` or eval_gold will skip the odd gold frames.
Then:

```
backend\.venv\Scripts\python.exe tools\eval_gold.py \
  --labels data\gold\yt_match40.labels.json \
  data\output\yt_match40_tracknet.perception.json \
  data\output\yt_match40_fusion.perception.json \
  data\output\yt_match40_v1.perception.json \
  data\output\yt_match40_v2.perception.json \
  --names tracknet fusion ballnet_v1 ballnet_v2 \
  --markdown data\gold\yt_match40.benchmark.md
```

(No archive968 on yt_match40 — the archive was a one-off pre-git artifact for
yt_rally2 only.)

## STEP 5 — verdict, docs, commit, push

- Plain-English verdict: did v2 keep v1's recall (esp. far-court) while
  dropping false-fire? Did it generalize to the unseen clip, or overfit the
  10 training clips? Compare v2 vs v1 on BOTH clips.
- Update CLAUDE.md status + HANDOFF.md §11 (append a v2 sub-section with both
  tables). Note whether v2 replaces v1 as the shipped `ballnet.pt`.
- Commit after training (weights) and after scoring (tables+docs) separately.
- Push to GitHub backup: `git push origin master` (repo xrich8x/swingpath,
  memory [[swingpath-github-remote]]).

## Deferred to future runs (NOT started — user-approved order)

1. **Tracker pass** (memory [[ball-tracker-live-and-hit-trajectory]] /
   `ball-tracker-live-ball-and-hit-trajectory.md`): (a) live-ball gate — only
   START a track on a struck ball, not any moving ball-shape; (b) hit-anchored
   ballistic extrapolation — emit an assumed parabola (gravity + launch
   velocity + homography) through fully-missed frames instead of dropping out.
   Both are ball.py logic, scored before/after on both gold clips. This is a
   TRACKER upgrade, separate from v2 (a detector upgrade).
2. Optional: drag yt_match40 court corners (~5 min) to unlock speed/line-calls
   + the court gate on that clip.
3. Optional: a 3rd gold clip for an even broader generalization read.
```
```
