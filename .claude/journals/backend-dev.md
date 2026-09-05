# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

---

## TASK - CURRENT (started 2026-09-05)

Build a NET-ANCHOR calibration check: project court features NOT in the 4-corner fit
(net line at court-y 11.885 m, both NET POSTS at 0.914 m outside doubles sideline) and
render over a real frame so a human can see if they land on the real thing.
Motivation: yt_match40 re-click 2026-09-05 IMPROVED on every screen (0.2 px residual,
1.61 m height, 0.944 coverage) and was STILL WRONG — far corners on the NET. Coverage
rewards that: court squashed into near half still lands on real paint, wrong paint.
WIRE INTO: tools/validate_new_clip.py --audit and/or tools/render_corner_audit.py
(extend, do not fork). run.py parser must not change (hook).
Add post constants to backend/swingvision/court.py if missing. Add a test.
RUN over ~25 existing data/*_pts*.json with videos; report which get flagged.
DELIVERABLE: docs/evidence/net-anchor-calibration-check.md
STOP-WHEN: check runs over existing calibrations + written up, or ~40 tool calls.
NOT-THIS-RUN: editing any calibration file; verify_court thresholds; docs/STATE.md; commit.

## STATE - 2026-09-05 - STARTING

## LOG

- CARRIED FORWARD: `python` is a broken Store shim. Use backend/.venv/Scripts/python.exe
- CARRIED FORWARD: `grep -rn` across repo ROOT times out (walks .venv) — grep explicit dirs.
- CARRIED FORWARD: Grep/Glob TOOLS return false "no matches"; use bash grep.
- CARRIED FORWARD: long markdown via heredoc FAILS; use the Write tool for long docs.
- CARRIED FORWARD: bash /tmp NOT visible to Windows python.exe — use scratchpad abs path.
- court.py + court.js: added NET_POST_OFFSET .914, NET_HEIGHT_POST 1.07, NET_HEIGHT_CENTER
  .914, X_LEFT/RIGHT_POST (-0.914 / 11.884), X_LEFT/RIGHT_STICK (0.456 / 10.514),
  NET_LINE_SEGMENT, NET_POST_BASES, net_post_segments_3d(). LINES UNCHANGED (still 10) on
  purpose: overlay.py draws LINES and validate_new_clip counts horizon crossings over it.
- calibration.project_court_3d(H,img_wh,xyz,hfov_deg) exists -> post TOPS projectable.
  Feed it hfov from courtfit.cam_fit_quad focal, not the 70deg default.
- SHIPPED tools/net_anchor_check.py (shared module: geometry + measure + draw, with the
  PRE-REG bars band_ratio<1.5 and |dy|>0.5*net_px_height) and
  tools/render_corner_audit.py --net-anchors (separate <tag>_netanchor.png, net_index.json).
  NOTE: `import net_anchor_check` works because tools/ is the script dir.
- FIRST RESULTS: yt_match40 (the RE-CLICKED wrong one, stamped 0.0px LOW-CAMERA)
  ratio 0.78 -> 16.67 at dy +49, netpx 36 => FLAG, 21x separation.
  yt_rally2 (known good) ratio 1.79, dy -17 => ok. Bars survive first contact.
- *** LEAD CORRECTION 2026-09-05 (mid-run). The brief's premise was WRONG. yt_match40's
  re-click is CORRECT (residual 0.0 px, camera 1.64 m, coverage 0.948). The lead had
  compared the projected net GROUND line (z=0) against the net TOP TAPE (z=0.914) in the
  image - apples to oranges; the tape necessarily images higher. Correct arithmetic:
  (row-horizon) ~ H/depth, so a point h above ground scales by (H-h)/H. H=1.64,
  horizon 264.6, net ground row 325 -> tape must be at 291.3; observed ~295 => 3.7 px.
  Do NOT cite "wrong court scoring 0.944". .bak-2026-09-05 IS the wrong one - negative
  example only, never restore.
- CONSEQUENCE: my PRE-REGISTERED BARS FAIL. 14/27 flagged INCLUDING yt_match40 (ratio
  0.78, dy +49) which is now known CORRECT. A failed bar stays failed - report, do not move.
- My band ALREADY projects to tape height (project_court_3d + fitted hfov), so the
  machinery is right; the LABELS were not. Fix: draw+name z=0 ground line vs z=0.914/1.07
  TAPE line vs post segments distinctly, and print horizon/ground/tape ROWS so a human can
  redo the lead's arithmetic from the PNG without repeating the mistake.
- FULL SWEEP RESULT (27 rendered of 29; court/yt_court have no video) saved at
  data/output/corner_audit/net_index.json
