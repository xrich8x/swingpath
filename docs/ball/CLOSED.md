# Ball detection & tracking — CLOSED

**Things tried here that did NOT work, and the number that killed each one.**

Read this before proposing anything in this area. Hard rule 3: **do not re-propose these.** Nine
distinct ideas in this project have been re-proposed at least once, each costing a run to re-kill.

**The code is gone, not lost.** Where a row names a deleted file, recover it with:

```bash
git log --diff-filter=D --oneline -- <path>     # find the commit that removed it
git show <sha>^:<path>                          # print the file as it last existed
```

A row here is a verdict. The mechanism and the war story live in `docs/evidence/`.

| What was tried | What we did | The result that killed it | Deleted code | Evidence |
|---|---|---|---|---|
| **Expecting a detector gain of ANY kind to reach the product** | Four separate detector improvements | **Four for four.** Input resolution, `score_thresh`, localised weighting and +57% data each cut detector error substantially and delivered **nothing** to the rendered output. **This is hard rule 5** | - | [expecting-a-detector-gain-of-any-kind](../evidence/expecting-a-detector-gain-of-any-kind.md) |
| **Raising the detector's input resolution** | Larger input | **Gate B FAILS on both clips** | - | [raising-the-detector-s-input-resolution](../evidence/raising-the-detector-s-input-resolution.md) |
| **Raising the detector score threshold** | 0.6 and 0.7 | Both **fail the recall gate** | `tools/score_thresh_gates.py` | - |
| **Localised confuser weighting** | Weight the loss near known confusers | **PRODUCT GATE FAILS** - pooled solid ghosts **14 -> 15** while the detector improved on 6 of 6 clips | `tools/mine_localised_negatives.py` | [localised-confuser-weighting](../evidence/localised-confuser-weighting.md) |
| **Mining whole-frame hard negatives** | Whole-frame negatives into training | **Gate C fails**, and it names the root cause | `backend/mine_hard_negatives.py` | [mining-whole-frame-hard-negatives-at-all](../evidence/mining-whole-frame-hard-negatives-at-all.md) |
| **Mining `suppress_false_locks` rejections as hard negatives** | Feed the suppressor's rejects back | **GATE FAILS**, and it corrects an over-attribution | `tools/eval_suppress_mining.py` | [mining-suppress-false-locks-rejections-as-hard](../evidence/mining-suppress-false-locks-rejections-as-hard.md) |
| **Motion attention (TrackNetV4)** | Motion-weighted detection | **59.2%** of false locks travel **with a person**; only 38.0% are static scenery - motion attention addresses the wrong 38% | - | [motion-attention](../evidence/motion-attention.md) |
| **Racquet-box negation (COCO class 38)** | Suppress detections near a detected racquet | **Failed twice.** The second run found why - COCO finds the **near** player's racquet while the detector fires on the **far** player's | `tools/eval_racquet_negation.py` | [racquet-box-negation](../evidence/racquet-box-negation.md) |
| **Tightening it to the racket HEAD** | Narrow the negation region | **The head is not the discriminator** | `tools/eval_racquet_head.py` | [tightening-it-to-the-racket-head](../evidence/tightening-it-to-the-racket-head.md) |
| **Pose-proximity negative mining** | Mine negatives near skeletons | **11.4%** catch at the 5% collateral ceiling vs a 60% gate - a skeleton has no racquet (**2.12 body heights** away) | `tools/eval_pose_proximity.py` | - |
| **Detector fusion (TrackNet + WASB)** | Ensemble two detectors | Rescued **4 frames** and doubled the dominant cost | - | - |
| **Blur augmentation alone** | Augment with motion blur | Dead end on its own; only pays combined with occlusion work | - | - |
| **Court + vertical cone gate for false alarms** | Gate detections by court geometry | Real far balls and fixtures overlap in court coords (real span **-229..+1667 m**) | - | - |
| **Scaling the fixture radius 12 -> 18 px** | Widen the static-fixture guard | Halves false-fire (13.2 -> 5.7%) but costs **4.3 pts** far-court recall | - | - |
| **Depth-aware Kalman process noise** | Scale Q by depth | Median-referenced made false-fire **worse** (19 -> 27%) | - | - |
| **Depth-invariant static-player guard** | `body_relative` guard | **GATE FAILS on 1 of 3** calibrated clips | - | [depth-invariant-static-player-guard](../evidence/depth-invariant-static-player-guard.md) |
| **Offline live-ball trajectory filter** | Filter the track offline | Net-negative once suppression runs; recall 50.2 -> **40.5%**. Retired | - | - |
| **Shrinking the smoother's `max_gap_s`** | Sweep the gap | Every value fails; solid ghosts sit at **9 regardless** | `tools/tune_smoother.py` | [tightening-the-smoother-gap-to-cut-ghosting](../evidence/tightening-the-smoother-gap-to-cut-ghosting.md) |
| **Retuning `max_gap_s` for 60 fps** | Re-sweep at the higher rate | **GATE FAILS on replication** - clean on yt_rally2, collapses on am_hard_utr. Never tune a gap policy on one clip | - | [retuning-max-gap-s-for-60-fps](../evidence/retuning-max-gap-s-for-60-fps.md) |
| **Lowering the smoother's `reset_after`** | Reset the filter sooner | **GATE FAILS on replication** | - | [lowering-the-smoother-s-reset-after-to](../evidence/lowering-the-smoother-s-reset-after-to.md) |
| **Making the smoother respect suppression** | `blocked` mask into the smoother | **GATE FAILS on the recall guards** | - | [making-the-smoother-respect-suppression](../evidence/making-the-smoother-respect-suppression.md) |
| **A second bounce HYPOTHESIS in the smoother** | `bounce_hypothesis` | **GATE FAILS on P2 and P6** over 10 gold clips. Recall passes (+18 hits) and separation passes at **9.00:1** vs a >7 bar - it fails because ghosts rise on **5 of 10** clips | - | [bounce-hypothesis](../evidence/bounce-hypothesis.md) |
| **`bounce_hypothesis` v2 - the position fix** | `restitution_set` | **GATE FAILS on 4 of 7 bars.** The gate's named cause is disconfirmed | - | [bounce-hypothesis-v2-gate](../evidence/bounce-hypothesis-v2-gate.md) |
| **Bounce-aware smoother reset** | `bounce_reset` | **FAILS on all 3 clips**; best case **1.4 pts short** | - | [bounce-reset](../evidence/bounce-reset.md) |
| **Re-admitting gate rejections via the BACKWARD (RTS) pass** | Re-admit on the smoother pass | **FAILS, 0 of 3 clips.** Best real-to-ghost ratio **1.14:1** against a >=3:1 bar; pooled **0.93:1** | - | [smoother-gate-backward-readmit-separation](../evidence/smoother-gate-backward-readmit-separation.md) |
| **Raising `meas_var` - 'R was never calibrated'** | Widen the innovation gate | **DEAD, and the premise had the SIGN BACKWARDS.** The gate's own rejects are **21 real / 28 ghost = 0.75:1**; then measurement showed innovations are **~12x SMALLER** than the filter's `S` predicts | - | [innovation-gate-noise-calibration](../evidence/innovation-gate-noise-calibration.md) |
| **M1 - counting 1-2 frame interpolated bridges as 'seen'** | Re-bin coasted frames | **KILL by its own pre-registered falsifier.** TrackNet '1-2' coast-bin median **19.90 px** against a <=10.0 px bar | - | [innovation-gate-noise-calibration](../evidence/innovation-gate-noise-calibration.md) |
| **M2 - rejection-run COHERENCE as a separating signal** | Enrichment in runs >=2 vs runs of 1 | **KILL on both legs.** 1 of 3 clips against a 2-of-3 bar; seeded null reached p = 0.105 / 0.589 / 0.585 | - | [innovation-gate-noise-calibration](../evidence/innovation-gate-noise-calibration.md) |
| **Raising `acquire_bound_m` 4 -> 10 m** | Widen acquisition | +0.6 pt recall for +1 ghost | - | - |
| **Screening far-court gaps at SELECTION time** | Predict which gaps are findable | **GATE FAILS under cross-validation** - 569 passing feature pairs cross-validate to **0-3%**. The shuffled-label null returns **0**, so the signal is real and far too weak | `tools/eval_gap_findability.py` | [screening-far-court-gaps-at-selection-time](../evidence/screening-far-court-gaps-at-selection-time.md) |
| **Screening far-court gaps by lock kinematics** | Use lock motion to screen | **Two measured negatives** - and they are why the anchor control exists | - | [screening-far-court-gaps-by-lock-kinematics](../evidence/screening-far-court-gaps-by-lock-kinematics.md) |
