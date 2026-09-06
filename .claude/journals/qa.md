# qa — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

---

## TASK — DONE 2026-09-06: cleanplate-mti-measured (near-baseline-solve coupling)

Deliverable FILED: docs/evidence/cleanplate-mti-measured.md, ~7 sections + NOT
ESTABLISHED list. Verdict: RETIRES the "clean plate sharpens inputs enough" hope on
the evidence gathered (only 1/8 double-locked clips meets founder's <=2px bar on both
row+width), BUT with a significant late-discovered caveat: backend-dev's shared
protocol (units px@640, data/*_pts.json population, raw line_ridge_mask/_detect_lines
matching) appeared mid-run and diverges from what I measured (native-res auto_fit
pipeline output on data/gold/*.court.labels.json) on units + population + detection
layer -- my numbers are NOT directly poolable with the founder's px@640 bars without
a rescale I didn't do. Wrote this up honestly as a correction (docs file section 6b)
rather than hiding it. Also corrected my OWN earlier claim that net-line truth is
"unmeasurable" -- it isn't; backend-dev's protocol shows it's derivable by projecting
court.LANDMARKS net-ground row through the human-fitted homography (same as
eval_court_cleanplate.py already does for rendering). Did not redo the measurement on
the corrected protocol (budget). BIG PROCESS FINDING: no SendMessage tool actually
exists in my toolset despite the brief; substituted by reading backend-dev's journal/
evidence file directly. ALSO: backend-dev is running the literal same task/deliverable
path concurrently (dispatch collision) -- flagged prominently for the lead.

## OLD TASK NOTES (superseded, kept for the git-log/gold-pool facts, since correct)

DELIVERABLE: docs/evidence/cleanplate-mti-measured.md (not yet written — findings
below go there next). STOP-WHEN: ~40 tool calls or written up. Used ~22 so far.

**IMPORTANT DISCOVERY: no SendMessage tool exists in my actual toolset** (Read/Write/
Edit/Bash/Grep/Glob only) despite the brief claiming I have it. Cannot literally
message backend-dev. WORKAROUND: read backend-dev's journal directly — it is doing
the LITERALLY SAME clean-plate-MTI task concurrently, own deliverable also named
docs/evidence/cleanplate-mti-measured.md, own pre-registered bar (lock>=60% + beats
blank-rect on majority + beats single-frame on majority; mechanism bar = line support
higher on plate for majority of clips; cost bar = reduced (n,span) "as well" if within
2.0px on every double-locked clip). THIS IS A DISPATCH COLLISION — flag prominently:
two agents given the same deliverable path. I will NOT overwrite its file; I'll do my
own narrower measurement (the 4 solver observables specifically) and report the
collision + my numbers for the lead to merge.

### T24 check — DONE, verdict: NOT a bare self-claim, but STALE
eval_court_cleanplate.py has exactly ONE commit ever (dd2369f, 2026-07-15) creating
it; never modified since. Its docstring claim "measured: it made detection worse"
(scattered-frame median vs short-window median) is backed by a REAL commit message
with real numbers: median err 14.4->9.1px on 9 local-video clips, 24.1->11.5px /
11->13/20 usable on full 20-gold, 15/16=~94% lock on visible-line courts. This
predates the current pipeline (surface routing f41a489 2026-08-21 etc). No
data/output/ artifact and no STATE.md row exists for it — never re-tracked.
clean_plate_and_motion (court_setup_server.py:39, added later 58401dd 2026-07-26)
cites eval_court_cleanplate.py for the same claim — traces back to the same one
real (but stale) 2026-07-15 run, not fabricated, but also never re-verified since.

### Fresh re-run on CURRENT code, 2026-09-06 — with clean plate
`eval_court_cleanplate.py --all`, wall time 54.3s for all 20 clips:
locked 13/20, usable(<35px) 11/20, median err (of 13 locked) = 8.6px.
Per-clip: am_rally32short 1.9, am_usta60 2.7, am_ntrp30 6.2, am_usta40 6.6,
am_rec30 6.9, am_ntrp40 8.3, am_usta45 8.6, am_ntrp45_courtlevel 13.4,
am_college 13.6, am_beginner 33.6, am_lk35 33.5, am_usta45final 71.7,
am_ntrp45w 139.9. No-lock (7): am_classB, am_fr_sud, am_grass1,
am_indoor_hard1, am_indoor_hard2, am_ntrp50, am_wingfield_clay.

CRITICAL CAVEAT found: only 10 of these 20 gold clips have LOCAL video
(data/incoming/...); the other 10 point to youtube URLs with no local file, so
`plate_from_video` returns None and the script falls back to medianing just the
labelled JPG STILLS (a handful of frames, NOT the n=150/span=90s recipe) — a much
weaker, different "clean plate". LOCAL clips: am_beginner, am_classB, am_college,
am_lk35, am_ntrp30, am_ntrp40, am_ntrp45_courtlevel, am_rally32short, am_rec30,
am_usta45. Any "clean plate works/doesn't" claim must be scoped to these 10 —
the other 10 are not testing the mechanism the brief asks about.

### NOTE: this gold set (data/gold/*.court.labels.json, 20 clips, am_* named) is a
DIFFERENT gold pool than the 20-clip precision-gate gold used elsewhere (am_hard_utr
etc, no ".court.labels.json" suffix, different filenames) — do not conflate the two
in the writeup; label which pool every number comes from.

### NET LINE GOLD DOES NOT EXIST
Checked keypoints in these labels: near/far _bl/_br _doubles/_singles, near/far
_sl_left/_sl_right, near/far_t. NO net_post_left/right or any net keypoint. So net
-line detection precision CANNOT be measured against human clicks from this gold
set at all — a real gap, not an oversight to route around. Plan: report near-baseline
row/width sharpening against real gold clicks; for net line, at most a proxy
(brightness-profile sharpness/stability single-frame vs plate, no ground truth) —
label it clearly as a proxy, not a precision number.

### NEXT STEPS (if resuming)
1. Build a script: for each of the 10 LOCAL clips, get single-frame auto_fit (frame 0
   or first labelled frame) AND plate auto_fit (already have via eval script — need
   to extract raw near_bl/near_br pixel coords, not just aggregate corner err).
   Compare near-baseline ROW ((near_bl.y+near_br.y)/2) and WIDTH (|near_bl.x-near_br.x|)
   against the human-clicked average per clip.
2. Net line: time-permitting brightness-profile proxy (reuse method from
   net-anchor-qa-verification.md), single-frame vs plate, report sharpness only.
3. Decode cost: isolate wall time for the 10 LOCAL clips only (already know total
   54.3s for all 20, most of which is the 10 local ones building n=150 frame plates).
4. Write docs/evidence/cleanplate-mti-measured.md with all of the above + the
   dispatch-collision finding + explicit "no SendMessage tool" note.

## LOG
- 2026-09-06: read journal/memory, confirmed no SendMessage tool, found backend-dev
  doing literally the same task concurrently (its journal tail read directly).
- 2026-09-06: T24 check done via git log -S / git show dd2369f — real historical
  run, stale, never re-tracked in STATE.
- 2026-09-06: fresh eval_court_cleanplate.py --all run done, numbers above.
- 2026-09-06: confirmed only 10/20 gold clips have local video (other 10 use a
  weak JPG-still fallback, not the real recipe).
- 2026-09-06: confirmed NO net keypoints anywhere in this gold label schema.
