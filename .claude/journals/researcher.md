# researcher — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

---

## TASK — 2026-09-17 — COURT PRECISION ROUTES (answers P8 C1)

COURT-ONLY (founder 2026-09-17). No ball/bounce/physics proposals. No code/STATE/SPEC.
Deliverable: `docs/evidence/court-precision-routes.md` = ranked routes to C1 precision
(far baseline needs 0.07-0.11 px corner equiv @3 m), each w/ what pins court, precision, closed-row
check, cost; + pre-registered SYNTHETIC test (sub-pixel whole-court fit, distortion arm) + real truth.
Qs: 1 sub-px line localisation lit + our arithmetic; 2 (MOST IMPORTANT) does whole-court fit fix far
baseline; 3 iOS intrinsics/distortion exposure; 4 SV/others court setup; 5 rule-3 reading of 4 closed
rows; 6 drift detection (flow vs IMU).
Label every claim PUBLISHED(link)/MEASURED/ARITHMETIC.

## STATE (resumed once after a kill, 2026-09-17)
Repo reading DONE: memory, C1, C2, CLOSED, SPEC §1, LS-fit/snap/quad/line-ceiling evidence,
CAPTURE_PROTOCOL §3.3 F-marks + §4 (framing A = ultra-wide 0.5x), lead.md P4(ii) (IMU stillness gate,
calibrate LAST; motionless tripods' re-detected court wobbles). Next: web lit (sub-px edge, iOS
intrinsics/distortion, SV setup), then write doc.
Repo facts: calibration.py:375-473 has Fitzgibbon DIVISION k1 model (estimate_k1 = straighten chains,
normalised by half-diagonal). NO sub-pixel edge code anywhere in backend/swingvision (grep subpix/steger).
LS-fit (closed) used HoughLinesP SEGMENTS matched to model, scored vs 4 human clicks (5.8 px@640);
line residual 3.01 px < human H 6.44 -> fit converged to lines that disagree w/ clicks; not decomposed.
C2: court gold non-corner kps are COMPUTED from 4 clicks -> no independent line truth exists.

## DONE 2026-09-17. If restarted: work is FINISHED, just report it.
Written: docs/evidence/court-precision-routes.md; memory court-precision-sub-pixel.md + MEMORY.md index.
No STATE/SPEC/code/subagent. Resumed once after a kill (coordinator message).
Closed-row reading decided: quad-from-lines = grouping/search; snap = independent-assignment
robustness (net-tape confuser is the live analogue!); LS-all-lines = Hough segments vs 5.8px clicks,
cannot see sub-px, never decomposed; auto-detection = search/accept, 6.4px is agreement w/ clicks.
Lookalikes: clean-plate/MTI (retired for search at 11.5px; here = noise averaging), fitted-hfov (a
60-90 gate on 4-click focal, spread 23-104 deg; not a known-truth focal measurement).
- GDC on UW default ON (search synth + forum 741815) — iOS version UNVERIFIED.

## WEB FINDINGS (PUBLISHED)
- Steger TPAMI 20(2) 1998 unbiased curvilinear detector: sub-px position AND width, bias from asymmetric
  contrast removed analytically (dl.acm.org/doi/10.1109/34.659930). No px-number read yet.
- Trujillo-Pino et al. IVC 31(1):72-90 2013 partial-area-effect sub-px edges (sciencedirect S0262885612001850).
- Apple forum 666517 (user, Nov 2020, unanswered): builtInUltraWideCamera isCameraIntrinsicMatrixDeliverySupported
  = false. Apple forum 741815 (Apple Media Engineer, Dec 2023, VERBATIM header): AVCameraCalibrationData
  (intrinsics, lens distortion) only if virtualDeviceConstituentPhotoDelivery YES, contentAwareDistortionCorrection
  NO, GDC NO — PHOTO OUTPUT. => per-frame video path does not give distortion table.
- Urban et al. arXiv 2201.10865 (2022) TrueDepth/front cams on iPads: AVCaptureSession images arrive
  already undistorted; factory focal within ~1% on most devices, 6-7% off on 2 iPads; iOS14->15 changed it.
  (FRONT camera, not rear UW — transfer caveat.) ARITH: 1% focal @hfov100 = 0.56 deg ~ 4.5 cm (C1 slope);
  6-7% ~ 4 deg ~ 30 cm.

- SV / PB Vision / Wingfield court-calibration method: NOT publicly disclosed (fetched set-up guide via
  jina: no calibration text; PB Vision "CourtFocus lock-on indicator", camera must not move; Wingfield
  config page: no calibration text). Don't re-search.

- Steger ISPRS Comm III 1998 abstract: real images, sub-px accuracy "better than one tenth of a pixel"
  in industrial inspection (controlled). Full PDF does not extract. Datta/Kim/Kanade ICCVW 2009:
  undistort+unproject then relocalise -> reprojection ~50% lower than OpenCV.
- ITF (via Wikipedia): centre service line 5 cm, others 2.5-5 cm, BASELINE UP TO 10 cm; measured to OUTSIDE.
- ASBA 2.I (novasports): surface within 1/8" in 10' (3 mm/3 m); slope 0.83-1% ONE PLANE, never net->BL.
- Elias, Eltner, Liebold, Maas, Sensors 20(3):643, 2020 (PMC7038322): Nexus 5 + Galaxy S8, AF fixed,
  CPU temp +9.9..25.9 C: focal change 1.0-5.6 px (full res), principal point moved up to 29.2/23.5 px
  (S8 cold); error at 10 m 1.3-3.0 cm mean cold, up to 12.9 cm max; warm 0.6-0.8 cm. ANDROID, not iPhone.
- Apple forum 654288 (2020, unanswered): iPad fx,fy vary with focus locked.
- ARITH: far BL 0.14 px == 0.01 deg == 0.17 mrad rotation. IMU cannot certify that (tilt 0.05-0.2 deg best).
  SPEC §1 drift trigger 15 px == ~5.4 m at far BL: 100x coarser than §3 needs. REPORT, don't edit.

## MY ARITHMETIC (P1/C1 camera: f=805.5, h=3, setback 6, far baseline D=29.77)
- far baseline 5 cm paint = 0.136 px tall (10 cm = 0.27 px) -> SUB-PIXEL line; length ~295 px doubles.
  near baseline ~2.7 px x sec^2 (~4 px). 1 px = 36 cm down-court at far BL => 5 cm = 0.14 px.
- CRLB gaussian profile: sigma_pos = sigma_n*sqrt(2s/sqrt(pi))/a; a = C*w/(sqrt(2pi)s). C=150DN,w=0.136,
  s=1 -> a=8 DN; sigma_n=2 -> 0.27 px/column; need line-centre sigma <= ~0.04 px (p90, ends x2) ->
  N_eff >= ~45 columns*frames. Single frame N_eff 20-75 marginal; multi-frame averaging -> noise NOT binding.
- BIAS is binding. Ground error per bias: surface height dz at far BL -> dz*D/h = ~10*dz (5 mm = 5 cm);
  paint convention centre vs outer edge = 2.5 cm (0.07 px); distortion residual at frame top; OIS/focus pp.
- Net tape top hits ground at D*h/(h-0.914): h=3 -> 25.72 m, ~13 px BELOW far BL in image; h=2.5 -> 28.19,
  ~3.8 px => tape nearly ON far BL at 2.5 m (protocol A-low!). Far service line seen THROUGH MESH at h=3.
- IN/OUT SIDEDNESS IS PRESERVED BY PROJECTION: a visible line's own image position decides the call;
  the regulation model is only needed for unseen lines + metric landing.
- f from one plane view (pp known, square px): pure pitch -> orthogonality constraint vacuous, equal-norm
  constraint gives f uniquely (cos^2 pitch factor) -> identifiable; weak by dolly-zoom ambiguity, better at
  wide FOV. Singular only if plane parallel to image. Conditioning MUST be measured (test arm).

## LOG
- 2026-09-16 swingvision-teardown DONE (previous task; see memory swingvision-public-method.md).
- 2026-09-17 new task started.
