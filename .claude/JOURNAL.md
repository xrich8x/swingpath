# Working journal — live state

**If a session or an agent died, read this file first.** It is the durable record of what
is in flight, what is blocked, and what was decided. It is written DURING work, not after,
so a rate-limit kill or a crash leaves it usable.

**Rules for whoever writes here (lead or teammate):**
- Update it as you go, not at the end. A journal written at the end does not survive a kill.
- **NOW** and **BLOCKED** are rewritten in place — they describe the present, not history.
- **LOG** is newest-first and gets **compacted** when it passes ~40 lines: fold resolved
  entries into one line each, delete anything superseded. This file must stay short enough
  to re-read cheaply, or it stops getting read.
- Numbers here are pointers. The authority is `docs/STATE.md` + `docs/evidence/`.
- Never put a result here that belongs in STATE. This is working state, not findings.

**Last updated:** 2026-08-28, after the detector-comparison agent was killed by a usage limit.

---

## NOW — what is running

**Nothing.** Verified with `ListAgents`, zero subagents live.

## PARKED — work that was started and stopped

- **BallNet v21 vs TrackNet, scored at the CHAIN** (pm queue item 3). backend-dev was
  killed mid-build by a usage limit (`resets 12pm Asia/Manila`). **Its work is NOT lost** —
  uncommitted in the tree: `tools/build_detector_ab_caches.py`,
  `tools/eval_detector_chain_ab.py`, `tools/compare_match_products.py` (all ~09:12-09:16),
  plus `data/output/detector_ab/`. Resume from those rather than restarting from zero.
  *Why it matters:* `mobile/models/*.onnx` are TrackNet exports while the shipped default
  is BallNet v21. STATE gives contradictory DETECTOR-level verdicts (hit@10 favours
  BallNet, F1@4 favours TrackNet on 9 of 10 clips) and neither has been scored at the
  chain, which is where rule 5 says ball work is judged. Settles which model v1 exports.

## BLOCKED — needs the founder, nothing proceeds without it

1. **Look at the P0-3 contact sheet** — `data/output/p0_3_sheet_yt_match40_crop192at640_x.png`.
   The result is recorded PROVISIONAL, not PASS, until seen. Invalidation mode is visual.
2. **Re-click `yt_match40` corners** in the court setup tool. Its calibration is confirmed
   wrong (trap T23) — all four clicked corners are off any court line, so the pipeline
   labelled the NEAR player FAR. Left near-baseline corner is unambiguous at ~(103, 448);
   `near_br_doubles` runs off-frame and needs extrapolating.
3. **Audit every other `*_pts.json` by RENDERING the corners**, not by reading residuals.
   `am_hard_utr` is "close but visibly skewed on the right." If a second gold calibration
   is wrong, more published numbers move.
4. **Refusal band: 0.15 m or 0.20 m?** Cost differs — 29.5% vs 39.0% of *close* calls
   refused. Both mounts are at/below the majority-class floor within 10 cm of a line.
5. **~3-6 human hours** for point-boundary labels (Hardcourt + Clay only; Shell and Grass
   have zero eligible footage and need new recordings).
6. **Sign-off:** P0-3's pre-registered identity test routed through the broken homography
   and was unexecutable. backend-dev substituted a calibration-free test and flagged it
   rather than swapping quietly. Accept or reject.

## DECIDED — binds everyone, do not reopen

- **iOS/iPadOS only, A13+**, Core ML/ANE the only inference target. **100% on-device
  forever** — a proposed network dependency is a scope violation.
- **Max 3 agents, 3 distinct tasks, one each.** A Pro-plan QUOTA cap, not machine load.
  Enforced by `.claude/hooks/agent-cap.sh`. A refused call is PARKED, not lost.
- **The rally/score layer is in scope but has no ground truth.** A compliant source is a
  prerequisite line item.
- Court auto-detection and the activity gate/trimmer are **not to be run unattended** —
  the first fires a stopping rule that closes a lane, the second needs a human to look at
  what it discarded.

## LOG — newest first

- **2026-08-28** — Detector comparison killed by usage limit. **Lesson: nothing restarts a
  dead subagent.** `autoContinueAtUsageLimit` resumes the SESSION; a subagent that hits the
  limit is killed outright and no mechanism polls for it. The failure notification IS the
  restart trigger — treat it as one, do not just report it.
- **2026-08-28** — Audio screen: **0 bail-outs of 88 clips, 0 of 62 Shell.** The feared
  correlated audio/vision failure on echo-heavy indoor courts did not occur. Two findings:
  the binding threshold is level-dependent (58-65% of candidates discarded on quiet indoor
  venues vs 17-25% outdoors — same class as the unscaled 720p constants), and
  `impact_envelope`'s rolling median is O(n·win) with a **13.5 GB peak allocation** on a
  28-min clip, never hit because nobody has run it on a full match. Committed `cae1dcc`.
- **2026-08-28** — Refusal band measured (qa). Both real mounts at/below the floor within
  10 cm; clear it from ~20 cm. `live.py`'s shipped `line_margin_m = 0.05` sits inside the
  unreliable zone. **qa correctly refused to write to the codebase** — its charter forbids
  it and my brief wrongly asked. Its findings still need filing by the lead.
- **2026-08-28** — P0-3 rebuilt. Crop finds the far player where full frame does not
  (0/25 control vs 15/25 crop192@640), and the mechanism is **upscale factor**, peaking at
  ~100-140 px of player in the tensor — a transferable design number. Found en route that
  `yt_match40`'s calibration is fabricated, which **withdrew P0-2's yt_match40 column**.
  Commits `10ed80f`, `8454e7e`.
- **2026-08-27** — P0-2 FAILED its gate: pose downscaling destroys the far player
  (11.0% → 0.1% → 0.0%). Closed full-frame downscaling as a way to afford pose on an A13.
- **Two lead errors worth not repeating:** sent execution work to `researcher`, which has
  no `Bash` by design; and claimed an agent was running without calling `ListAgents`.
  Match the task to the agent's `tools:` first, and verify state before asserting it.
