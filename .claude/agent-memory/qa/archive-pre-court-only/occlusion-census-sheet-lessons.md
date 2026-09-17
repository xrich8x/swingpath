---
name: occlusion-census-sheet-lessons
description: P2 occlusion census sheet (2026-09-16) — demo30 is a slice of yt_match40, audio-onset membership is chance-level, yt_match40 HUD leaks SwingVision bounce dots, pre-serve bounces flood audio candidates
metadata:
  type: project
---

P2 sheet built 2026-09-16, unlabelled (commit 2cd476f; pre-reg 29d2e3e). Evidence:
docs/evidence/occlusion-census.md + docs/evidence/occlusion-census/sheet.html.

Durable facts found on the way:
- **`demo30.mp4` IS `yt_match40.mp4` frames 2552-3421** (thumbnail match, constant offset). The three
  "cached clips" are two recordings. Yet the two pts files fit the same static camera at 1.38 m vs
  1.64 m, so at least one calibration is badly wrong. Separately, **`data/output/demo30.perception.json`
  has 1108 entries for an 870-frame video** — it was computed from yt_rally2 (as demo30.json says),
  not demo30.mp4.
- **`yt_match40` carries SwingVision's HUD with a mini-court showing its own bounce dots** plus a shot
  panel and scoreboard. Any human labelling pass on it must mask those (rule 12). Boxes used:
  [0,0,310,170], [1075,0,1280,335] @1280x720; am_hard_utr scoreboard [0,0,600,185] @1920x1080.
- **Audio onsets on am_hard_utr (811 in 484 s, 1.68/s) make A/V co-membership chance-level**
  (null 0.758 vs obs 0.780). Capture-recapture between audio and vision candidate sources is not
  computable at that density. Use a negative-space audit (label seeded windows from uncovered time)
  to estimate what a candidate source missed. Audio trails pipeline bounce times by +0.10..+0.20 s.
- The shipped-then-cut `audio.py` can be invoked from git (`git show 7570a2a^:backend/swingvision/audio.py`
  exec'd into a module) without restoring it to the tree.
- Rendering the first candidates showed **pre-serve ball bounces** dominate audio items. Render a
  few before sizing a founder pass.

**Why:** these change how any future census, labelling pass or clip-independence claim on these
clips should be built.
**How to apply:** count yt_match40+demo30 as one recording; never trust demo30.perception.json as
demo30's; mask HUDs before any founder labelling; when the founder's CSV arrives, compute §6/§4.2 of
the evidence file exactly as registered. Related: [[qa_does_not_write_to_codebase]].

Process slip to not repeat: a hash-compare command used a `../../../..` relative path and briefly
wrote above the repo root. Temp files go in the session scratchpad, by absolute path, only.
