# Speed coverage is CHAIN-shaped, and the two stages are named — the best-measured open target

> Evidence for the `speed-coverage-is-chain-shaped-and-the` row in [docs/STATE.md](../STATE.md) (Open).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**ATTRIBUTED 2026-08-15 on the population that matters.** `seen_frac` over the whole hit→landing span must be ≥50% for a trusted speed. Counting it at every chain stage: on **am_hard_utr** mean coverage goes **raw 75.5% → 72.1 (rectify) → 64.9 (suppress) → 64.9 (court gate, ZERO cost) → 52.9 (smoother)**, and shots clearing the gate go **106 of 120 → 69**. **yt_match40 is the same shape** (79.3% → 59.7%, 182 → 124). So **the detector already covers 88% of shots on the target clip and only 58% survive the chain — 37 shots lose their speed to the chain, not the detector.** Per-stage, identical order on both clips: **`smooth_forecast` largest (−12.0 / −9.7 pts), `suppress_false_locks` second (−7.2 / −8.1), court gate exactly zero** (reproducing Session G part 3); the two own ~85%. This **supersedes the post-bounce framing** — that window is the minor failure mode worth 3–4 pts, this is worth **20–23**. NO FIX PROPOSED: two smoother attempts have already failed because loosening the gate buys coverage and pays in ghosts, and this measurement does not change that trade, only its size. A third attempt needs a mechanism that **separates** real from false better, not one that admits more of both. Evidence: data/output/post_bounce_chain.md (part 3)

---

## Re-measured under TrackNet, 2026-09-02: the cost SURVIVES. It is the STAGE.

**Why this was re-run.** The numbers above were measured under **BallNet v21**. The v1
ball detector is a founder decision for **TrackNet**, and on 2026-09-02
[smooth-forecast-adds-ghosts.md](smooth-forecast-adds-ghosts.md) established that
`smooth_forecast`'s *per-frame* behaviour is a property of the **detector pairing**, not
of the stage (BallNet −1.0 pt recall / +12 ghosts; TrackNet **+3.9 pts / +3 ghosts**).
If the smoother's innovation gate rejects real detections, how many it rejects depends on
what the detector produced — so the −12.0 pt coverage cost was open to the same doubt.

**Measured against.** `seen_frac` is a **coverage** statistic computed on the tracker's
own post-chain output over hit→landing spans the tracker's own events defined. It is not
an accuracy number and nothing here claims a seen frame was on the ball; the recall and
ghost numbers quoted for these detectors come from `tools/eval_model_filters.py`, which
scores against human gold clicks.

### Pre-registered, before any run

`D_smooth` = mean `seen_frac` at `+gate_ball_to_court` minus mean at `+smooth_forecast`,
per clip. Both arms re-measured; the published table is the target for **probe
validation only**, never an arm.

- **V — probe validation.** Reproduce every published row within **±1.0 pt** and
  **±2 shots** from the same input, or nothing below is trusted.
- **A — PAIRING property (cost does not survive):** `|D_TrackNet| ≤ 0.5 × |D_BallNet|`
  on **both** clips, and the shot loss at the smoother likewise ≤ half on both.
- **B — STAGE property (cost survives):** `|D_TrackNet| ≥ 0.75 × |D_BallNet|` on **both**
  clips, **and** ≥ 5.0 pts absolute on both, **and** `smooth_forecast` still the largest
  single-stage cost in the TrackNet ladder.
- **C — INDETERMINATE:** anything else, including a split across the two clips.
- **Live-target floor (separate):** to stay a live target under v1's detector the
  smoother must cost ≥ 5.0 pts on at least one clip **and** push ≥ 10 shots under the
  50% bar on at least one clip.

### V — the probe reproduces the published table

New tool `tools/eval_speed_coverage_chain.py`, run on the same main perception caches:

| clip | published | probe |
|---|---|---|
| `am_hard_utr` | 75.5 / 72.1 / 64.9 / 64.9 / **52.9**, shots 106/101/90/90/**69** | 75.5 / 72.0 / 64.9 / 64.9 / **53.1**, shots 106/101/90/90/**71** |
| `yt_match40` | 79.3 / 77.5 / 69.4 / 69.4 / **59.7**, shots 182/174/150/150/124 | 79.3 / 77.5 / 69.3 / 69.3 / **59.6**, shots 182/174/150/150/124 |

Within ±0.2 pt on every mean. The one shot-count difference (+2) is **at** the tolerance,
not inside it, and is stated rather than rounded away. Independently corroborated: the
probe printed *"speed not trusted for 64/120 shots"* on the smoother row — the exact
figure part 2 of `post_bounce_chain.md` quotes from the shipped analyze run. **V passes.**

### The A/B — one variable, matched caches

Both arms come from `data/output/detector_ab/`, built the same day with the same
`score_thresh` (0.5), the same static gate and the same frame counts. Pose, camera motion
and the player court tracks are **detector-independent** and are shared from the clip's
standard cache, so the ball track is the only thing that changes.

| clip | arm | raw | +rectify | +suppress | +court gate | **+smooth** | **D_smooth** | shots ≥50% at smoother | n_shots |
|---|---|---|---|---|---|---|---|---|---|
| `am_hard_utr` | BallNet v21 | 77.7% | 74.0% | 66.3% | 66.3% | 56.2% | **−10.1** | 87 → 73 (−14) | 124 |
| `am_hard_utr` | **TrackNet** | 69.6% | 67.2% | 62.0% | 62.0% | 51.1% | **−11.0** | 65 → 50 (−15) | 90 |
| `yt_match40` | BallNet v21 | 81.9% | 80.3% | 73.3% | 73.3% | 63.1% | **−10.2** | 155 → 138 (−17) | 187 |
| `yt_match40` | **TrackNet** | 68.8% | 67.5% | 63.1% | 63.0% | 55.0% | **−8.1** | 131 → 103 (−28) | 186 |

**Cross-check on identical shots.** TrackNet finds fewer hits on `am_hard_utr` (91 vs
126), so its shot population is smaller. Re-scoring both arms over **one** span set
(BallNet's) removes that difference entirely:

| clip | BallNet `D_smooth` | TrackNet `D_smooth` (BallNet spans) |
|---|---|---|
| `am_hard_utr` | −10.1 | **−10.2** |
| `yt_match40` | −10.2 | **−8.1** |

Same answer. The result is not an artefact of the shot populations differing.

### Verdict

- **A fails.** `|D_TN|` is 11.0 and 8.1 against a half-of-BallNet bar of 5.1 on both clips.
- **B passes.** 11.0 ≥ 7.6 and 8.1 ≥ 7.7; both ≥ 5.0 pts absolute; and `smooth_forecast`
  is still the largest single-stage cost under TrackNet (−11.0 vs suppression's −5.2;
  −8.1 vs −4.4).
- **Live-target floor met** on both clips (≥5 pts, and 15 / 28 shots pushed under the bar).

**The −12.0 pt cost survives under v1's actual detector. Speed coverage remains the live
target it is recorded as, and the row above does not need rewriting** — only the note
that it now holds for TrackNet as well as BallNet.

### Mechanism, and why it does not contradict the ghost finding

Real detections deleted by the smoother's innovation gate (frames seen at the court gate
→ frames seen after the smoother):

| clip | BallNet | TrackNet |
|---|---|---|
| `am_hard_utr` | 9,757 → 8,278 (**−15.2%**) | 8,330 → 6,910 (**−17.0%**) |
| `yt_match40` | 6,918 → 5,927 (**−14.3%**) | 5,965 → 5,148 (**−13.7%**) |

**14–17% in every arm.** The rejection rate is detector-independent even though the ghost
behaviour is not.

Both findings are true because they count coasted frames differently. Per-frame recall
counts an **interpolated** position within 10 px of a human click as a hit; `seen_frac`
excludes coasted frames by construction, because a forecast is a physics guess and not a
measurement. The TrackNet ladder logs show the gain is made of exactly those frames — on
`am_hard_utr` recall rises 34.4 → 37.8 (+3.4 pts ≈ 3 hits) with **5** of the hits
interpolated, and on `yt_match40` 51.1 → 56.0 (+4.9 pts ≈ 9 hits) with **15**
interpolated. So the smoother draws more balls near where the ball is while measuring
fewer of them. **Raising recall and lowering coverage is the same trade, not a
contradiction**, and a fix for one is not automatically a fix for the other.

### Two things recorded, not smoothed over

- `gate_ball_to_court` is **not** exactly zero on `yt_match40`/TrackNet: −0.05 pts, 9
  frames. It is 0.0 on the other three arms. The "costs exactly zero" claim is now
  "costs zero on 3 of 4 arms and 0.05 pts on the fourth".
- `yt_match40`'s calibration is the one T23 flagged (manual+snap, 9.1 px reprojection).
  Every `yt_match40` number here inherits that, in **both** arms equally — it cannot
  favour one detector, but it is not a clean clip.

Artifacts: `data/output/speed_coverage/*.json` (per-arm, with resolved provenance);
tool `tools/eval_speed_coverage_chain.py`; hook pinned by
`backend/tests/test_speed_coverage_span_sink.py`.


---

## The backward-pass re-admit is measured and DEAD. 2026-09-03 (backend-dev)

This file's own requirement — *"a third attempt needs a mechanism that SEPARATES real from
false, not one that admits more of both"* — was taken up and the first candidate that met it
on paper has now failed on the bench.

The smoother is non-causal, so the RTS backward pass holds information the forward
innovation gate did not have when it rejected a detection. That looked like a separating
signal rather than a looser gate. **It is not: 0 of 3 clips, against a bar of 2 of 3.**
Best real-to-ghost exchange at any threshold was 1.14 / 2.00 / 0.56 : 1 against a >=3:1 bar,
pooled 0.93:1, and the seeded shuffled-label null control is matched or beaten by 526 of
1000 permutations — chance.

**Why, and it matters more than the number.** A ghost that continues the motion model's
stale prediction sits *on* the smoothed path, while a real detection fails a 99.9%
chi-square gate essentially only when the model is already stale — and RTS is blocked at
segment boundaries, so that frame's smoothed estimate comes off **the same stale model**.
The backward pass is a second look at the evidence the forward gate already got wrong.

> **Consequence for this row's target: any future re-admit signal must come from OUTSIDE the
> motion model** — appearance, detector confidence, cross-detector agreement. But this is the
> third measured negative in the smoother-gate family, so **rule 3 bars a fourth**, the
> cross-detector variant included. Attacking the -11.0 / -8.1 pt cost now means attacking a
> different stage, not this gate.

Full method, per-clip distributions, the null control and the provenance of every number:
[smoother-gate-backward-readmit-separation.md](smoother-gate-backward-readmit-separation.md).
